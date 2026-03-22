import json
import logging
from typing import List, Dict, Any, Optional, Tuple, Set
import concurrent.futures

from core.models import CallAnalysis, CallSynthesisRecord, TranscriptChunk, TokenUsageSummary
from parsing.financial_terms import scan_chunk
from services.company_info import build_company_context

logger = logging.getLogger(__name__)


def create_chunks_from_analysis(analysis: CallAnalysis, max_chars: int = 4000, overlap_chars: int = 500) -> List[TranscriptChunk]:
    """
    Convert the deterministic output (spans and qa exchanges) into standard chunks for LLMs.
    
    Prepared remarks are chunked by length (max_chars) with a sliding window (overlap_chars).
    Extremely long single spans are split into smaller pieces to avoid exceeding max_chars.
    Q&A exchanges are kept intact when possible, but will also be chunked if they exceed max_chars.
    """
    chunks = []
    chunk_idx = 0
    
    # We split spans into smaller pieces first so that overlap can pick granularly
    # rather than taking a massive chunk of text.
    MAX_PIECE_LEN = min(max_chars // 2, 1000)

    def split_span(speaker: str, text: str) -> List[str]:
        """Splits a single large text block into smaller pieces under MAX_PIECE_LEN."""
        words = text.split()
        pieces = []
        curr = []
        curr_len = 0
        prefix = f"{speaker}: "
        prefix_len = len(prefix)
        
        for w in words:
            word_len = len(w) + 1 # +1 for space
            if curr_len + word_len + prefix_len > MAX_PIECE_LEN and curr:
                pieces.append(prefix + " ".join(curr))
                curr = [w]
                curr_len = len(w)
            else:
                curr.append(w)
                curr_len += len(w) if not curr_len else word_len
        if curr:
            pieces.append(prefix + " ".join(curr))
        return pieces
        
    def add_overlap(current_texts: List[str]) -> Tuple[List[str], Set[str], int]:
        """Calculates the overlapping portion from the end of current_texts."""
        overlap_text = []
        overlap_speakers = set()
        overlap_chars_count = 0
        
        for past_text in reversed(current_texts):
            if overlap_chars_count + len(past_text) > overlap_chars:
                if overlap_chars_count == 0:
                    overlap_text.insert(0, past_text)
                    speaker_name = past_text.split(":", 1)[0]
                    overlap_speakers.add(speaker_name)
                    overlap_chars_count += len(past_text)
                break
            
            overlap_text.insert(0, past_text)
            speaker_name = past_text.split(":", 1)[0]
            overlap_speakers.add(speaker_name)
            overlap_chars_count += len(past_text)
            
        new_chars = sum(len(t) for t in overlap_text) + (max(0, len(overlap_text) - 1) * 2)
        return overlap_text, overlap_speakers, new_chars

    # Part 1: Chunking Prepared Remarks
    prepared_spans = [s for s in analysis.spans if s.section == 'prepared']
    text_blocks = []
    
    for span in prepared_spans:
        span_pieces = split_span(span.speaker_name, span.text)
        for piece in span_pieces:
            text_blocks.append((span.speaker_name, piece))

    current_prepared_text = []
    current_prepared_speakers = set()
    current_prepared_chars = 0
    
    for speaker, piece in text_blocks:
        if current_prepared_chars + len(piece) > max_chars and current_prepared_text:
            chunks.append(TranscriptChunk(
                chunk_id=f"prep_{chunk_idx}",
                chunk_type="prepared",
                text="\n\n".join(current_prepared_text),
                speakers=list(current_prepared_speakers),
                sequence_order=chunk_idx
            ))
            chunk_idx += 1
            
            current_prepared_text, current_prepared_speakers, current_prepared_chars = add_overlap(current_prepared_text)

        current_prepared_text.append(piece)
        current_prepared_speakers.add(speaker)
        current_prepared_chars += len(piece) + (2 if len(current_prepared_text) > 1 else 0)
        
    if current_prepared_text:
        chunks.append(TranscriptChunk(
            chunk_id=f"prep_{chunk_idx}",
            chunk_type="prepared",
            text="\n\n".join(current_prepared_text),
            speakers=list(current_prepared_speakers),
            sequence_order=chunk_idx
        ))
        chunk_idx += 1

    # Part 2: Chunking Q&A
    span_lookup = {s.id: s for s in analysis.spans}
    
    qa_idx = 0
    for pair in analysis.qa_pairs:
        all_ids = pair.question_span_ids + pair.answer_span_ids
        exchange_spans_objs = [span_lookup[sid] for sid in all_ids if sid in span_lookup]
        exchange_spans_objs.sort(key=lambda s: s.sequence_order)
        
        exchange_texts = []
        speakers = set()
        exchange_chars = 0
        
        for s in exchange_spans_objs:
            piece_text = f"{s.speaker_name}: {s.text}"
            exchange_texts.append(piece_text)
            speakers.add(s.speaker_name)
            exchange_chars += len(piece_text) + (2 if exchange_texts else 0)
            
        if exchange_chars > max_chars:
            qa_blocks = []
            for s in exchange_spans_objs:
                for piece in split_span(s.speaker_name, s.text):
                    qa_blocks.append((s.speaker_name, piece))
                    
            curr_text = []
            curr_speakers = set()
            curr_chars = 0
            sub_idx = 0
            
            for speaker, piece in qa_blocks:
                if curr_chars + len(piece) > max_chars and curr_text:
                    chunks.append(TranscriptChunk(
                        chunk_id=f"qa_{qa_idx}_{sub_idx}",
                        chunk_type="qa",
                        text="\n\n".join(curr_text),
                        speakers=list(curr_speakers),
                        sequence_order=chunk_idx + qa_idx
                    ))
                    sub_idx += 1
                    
                    curr_text, curr_speakers, curr_chars = add_overlap(curr_text)
                    
                curr_text.append(piece)
                curr_speakers.add(speaker)
                curr_chars += len(piece) + (2 if curr_text else 0)
                
            if curr_text:
                chunks.append(TranscriptChunk(
                    chunk_id=f"qa_{qa_idx}_{sub_idx}",
                    chunk_type="qa",
                    text="\n\n".join(curr_text),
                    speakers=list(curr_speakers),
                    sequence_order=chunk_idx + qa_idx
                ))
            qa_idx += 1
            
        else:
            chunks.append(TranscriptChunk(
                chunk_id=f"qa_{qa_idx}",
                chunk_type="qa",
                text="\n\n".join(exchange_texts),
                speakers=list(speakers),
                sequence_order=chunk_idx + qa_idx
            ))
            qa_idx += 1
            
    return chunks

class IngestionPipeline:
    def __init__(self, tier1_threshold: int = 6):
        self.tier1_threshold = tier1_threshold
        # Initialize the LLM client wrapper
        from services.llm import AgenticExtractor
        self.extractor = AgenticExtractor()

    def process(self, analysis: CallAnalysis) -> tuple[List[TranscriptChunk], CallSynthesisRecord, TokenUsageSummary]:
        """Run the full ingestion pipeline on a parsed CallAnalysis."""
        logger.info(f"Starting agentic ingestion for {analysis.call.ticker}")

        call = analysis.call
        company_context = build_company_context(call.ticker, call.company_name, call.industry)

        chunks = create_chunks_from_analysis(analysis)
        prep_count = sum(1 for c in chunks if c.chunk_type == 'prepared')
        qa_count = sum(1 for c in chunks if c.chunk_type == 'qa')
        prepared_span_count = sum(1 for s in analysis.spans if s.section == 'prepared')
        print(f"  ↳ Spans: {len(analysis.spans)} total ({prepared_span_count} prepared), QA pairs: {len(analysis.qa_pairs)}")
        logger.info(f"Created {len(chunks)} chunks ({prep_count} prep, {qa_count} qa)")
        print(f"\n🚀 Starting Agentic LLM Ingestion Pipeline ({len(chunks)} chunks)...")

        if not chunks:
            logger.warning("No chunks created from analysis — skipping LLM extraction")
            print("⚠️  No chunks created — transcript may have no prepared remarks and no Q&A pairs. Skipping agentic extraction.")
            return [], CallSynthesisRecord(
                overall_sentiment="", executive_tone="", key_themes=[],
                strategic_shifts=[], analyst_sentiment="",
            ), TokenUsageSummary()

        # Phase 2: Map Phase (Concurrent Extraction)
        # Process chunks in parallel using a ThreadPoolExecutor
        max_workers = max(1, min(10, len(chunks)))
        print(f"\n[Map Phase] Running extraction on {len(chunks)} chunks with {max_workers} concurrent workers...")
        
        all_chunk_usage: list[dict] = []

        with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
            # Map chunk indices to future objects so we know which is which when completed
            future_to_chunk = {
                executor.submit(self._process_single_chunk, chunk, i, len(chunks), company_context): chunk
                for i, chunk in enumerate(chunks, 1)
            }

            # Wait for all futures to complete, collecting per-chunk usage stats
            for future in concurrent.futures.as_completed(future_to_chunk):
                try:
                    chunk_usage = future.result()
                    if chunk_usage:
                        all_chunk_usage.extend(chunk_usage)
                except Exception as exc:
                    chunk = future_to_chunk[future]
                    logger.error(f"Chunk {chunk.chunk_id} generated an exception: {exc}")
                    print(f"❌ Chunk {chunk.chunk_id} failed: {exc}")

        # Phase 3: Reduce Phase (Synthesis)
        print(f"\n[Reduce Phase] Synthesizing insights across all {len(chunks)} chunks...")
        compact_summaries = []
        for c in chunks:
            summary = {
                "chunk_id": c.chunk_id,
                "type": c.chunk_type,
                "score": c.tier1_score,
                "top_terms": [t["term"] for t in c.extracted_terms[:5]],
                "top_concept": c.core_concepts[0] if c.core_concepts else "",
                "top_takeaway": c.takeaways[0]["takeaway"] if c.takeaways else "",
            }
            if c.evasion_analysis:
                summary["evasion_score"] = c.evasion_analysis.get("score")
            compact_summaries.append(summary)

        aggregated_text = json.dumps(compact_summaries, indent=2)
        
        synthesis_data = self.extractor.extract_synthesis(aggregated_text)

        # Manually extract usage stats before creating the dataclass
        synthesis_usage = synthesis_data.pop("_usage_stats", None)
        if synthesis_usage:
            print(f"    ↳ Synthesis [Model: {synthesis_usage['model']} | In: {synthesis_usage['prompt_tokens']} | Out: {synthesis_usage['completion_tokens']}]")

        # Normalise strategic_shifts: accept list[str] (old prompts) or list[dict] (new prompt)
        raw_shifts = synthesis_data.get("strategic_shifts", [])
        structured_shifts = []
        for s in raw_shifts:
            if isinstance(s, dict):
                structured_shifts.append(s)
            else:
                structured_shifts.append({
                    "prior_position": "",
                    "current_position": str(s),
                    "investor_significance": "",
                })

        synthesis = CallSynthesisRecord(
            overall_sentiment=synthesis_data.get("overall_sentiment", ""),
            executive_tone=synthesis_data.get("executive_tone", ""),
            key_themes=synthesis_data.get("key_themes", []),
            strategic_shifts=structured_shifts,
            analyst_sentiment=synthesis_data.get("analyst_sentiment", ""),
            call_summary=synthesis_data.get("call_summary") or None,
        )

        # Aggregate all token usage across chunks and synthesis
        token_usage = TokenUsageSummary()
        for u in all_chunk_usage:
            token_usage.add(u["model"], u["prompt_tokens"], u["completion_tokens"])
        if synthesis_usage:
            token_usage.add(
                synthesis_usage["model"],
                synthesis_usage["prompt_tokens"],
                synthesis_usage["completion_tokens"],
            )

        print("✅ Agentic ingestion complete.\n")
        return chunks, synthesis, token_usage
        
    def _process_single_chunk(self, chunk: TranscriptChunk, index: int, total_chunks: int, company_context: str = "") -> list[dict]:
        """Helper method to process a single chunk, designed to run in a thread.

        Returns a list of ``_usage_stats`` dicts (one per LLM call made).
        """
        logger.info(f"Processing chunk {chunk.chunk_id} [{index}/{total_chunks}]")
        print(f"  [{index}/{total_chunks}] Analysing {chunk.chunk_id}... ")

        usage_records: list[dict] = []

        t1_usage = self._run_tier1(chunk, company_context)
        if t1_usage:
            logger.info(f"Chunk {chunk.chunk_id} - Tier 1 usage: {t1_usage}")
            usage_records.append(t1_usage)

        # Phase 3: Tier 2 Deep Enrichment (Conditional routing)
        if chunk.requires_deep_analysis and getattr(chunk, 'tier1_score', 0) >= self.tier1_threshold:
            print(f"    ↳ Deep dive required on {chunk.chunk_id} (Score: {chunk.tier1_score}). Routing to Tier 2... ")
            t2_usage = self._run_tier2(chunk)
            if t2_usage:
                logger.info(f"Chunk {chunk.chunk_id} - Tier 2 usage: {t2_usage}")
                usage_records.append(t2_usage)
        else:
            logger.info(f"Chunk {chunk.chunk_id} - Skipping Tier 2 (Score: {getattr(chunk, 'tier1_score', 0)})")

        return usage_records
        
    def _run_tier1(self, chunk: TranscriptChunk, company_context: str = "") -> Optional[Dict[str, Any]]:
        """Run Tier 1 extraction: LLM for industry terms + CSV scan for financial terms."""
        tier1_data = self.extractor.extract_tier1(chunk.text, chunk.chunk_type, company_context)

        industry_terms = [
            {**t, "category": "industry"}
            for t in tier1_data.get("extracted_terms", [])
        ]
        financial_terms = scan_chunk(chunk.text)

        chunk.extracted_terms = industry_terms + financial_terms
        chunk.core_concepts = tier1_data.get("core_concepts", [])
        chunk.tier1_score = tier1_data.get("tier1_score", 0)
        chunk.requires_deep_analysis = tier1_data.get("requires_deep_analysis", False)

        return tier1_data.get("_usage_stats")
        
    def _run_tier2(self, chunk: TranscriptChunk) -> Optional[Dict[str, Any]]:
        """Run deep reasoning enrichment (Anthropic claude-4.5-sonnet)."""
        tier2_data = self.extractor.extract_tier2(chunk.text, chunk.chunk_type)
        
        chunk.takeaways = tier2_data.get("takeaways", [])
        chunk.evasion_analysis = tier2_data.get("evasion_analysis")
        chunk.misconceptions = tier2_data.get("misconceptions", [])
        
        return tier2_data.get("_usage_stats")
