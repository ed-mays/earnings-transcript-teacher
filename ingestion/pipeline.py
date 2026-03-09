import logging
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field
import concurrent.futures

from core.models import CallAnalysis, CallSynthesisRecord

logger = logging.getLogger(__name__)

class TranscriptChunk(BaseModel):
    """
    A standardized chunk of the transcript ready for LLM ingestion.
    """
    chunk_id: str
    chunk_type: str  # 'prepared' or 'qa'
    text: str
    speakers: List[str]
    sequence_order: int
    
    # Tier 1 outputs (populated by cheap model)
    tier1_score: Optional[int] = None
    extracted_terms: List[Dict[str, str]] = Field(default_factory=list)
    core_concepts: List[str] = Field(default_factory=list)
    requires_deep_analysis: bool = False
    
    # Tier 2 outputs (populated by reasoning model)
    takeaways: List[Dict[str, str]] = Field(default_factory=list)
    evasion_analysis: Optional[Dict[str, Any]] = None
    misconceptions: List[Dict[str, str]] = Field(default_factory=list)

def create_chunks_from_analysis(analysis: CallAnalysis, max_chars: int = 4000) -> List[TranscriptChunk]:
    """
    Convert the deterministic output (spans and qa exchanges) into standard chunks for LLMs.
    
    Prepared remarks are chunked by length (max_chars).
    Q&A exchanges are kept intact, with each exchange forming one chunk.
    """
    chunks = []
    
    # Part 1: Chunking Prepared Remarks
    current_prepared_text = []
    current_prepared_speakers = set()
    current_prepared_chars = 0
    chunk_idx = 0
    
    prepared_spans = [s for s in analysis.spans if s.section == 'prepared']
    
    for span in prepared_spans:
        span_text = f"{span.speaker_name}: {span.text}"
        
        # If adding this span exceeds max_chars and we already have some text, yield the current chunk.
        if current_prepared_chars + len(span_text) > max_chars and current_prepared_chars > 0:
            chunks.append(TranscriptChunk(
                chunk_id=f"prep_{chunk_idx}",
                chunk_type="prepared",
                text="\n\n".join(current_prepared_text),
                speakers=list(current_prepared_speakers),
                sequence_order=chunk_idx
            ))
            chunk_idx += 1
            current_prepared_text = []
            current_prepared_speakers = set()
            current_prepared_chars = 0
            
        current_prepared_text.append(span_text)
        current_prepared_speakers.add(span.speaker_name)
        current_prepared_chars += len(span_text)
        
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
        speakers = set()
        
        # Combine question spans and answer spans in chronological order
        all_ids = pair.question_span_ids + pair.answer_span_ids
        exchange_spans_objs = [span_lookup[sid] for sid in all_ids if sid in span_lookup]
        exchange_spans_objs.sort(key=lambda s: s.sequence_order)
        
        exchange_texts = []
        for s in exchange_spans_objs:
            exchange_texts.append(f"{s.speaker_name}: {s.text}")
            speakers.add(s.speaker_name)
            
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

    def process(self, analysis: CallAnalysis) -> List[TranscriptChunk]:
        """Run the full ingestion pipeline on a parsed CallAnalysis."""
        logger.info(f"Starting agentic ingestion for {analysis.call.ticker}")
        
        chunks = create_chunks_from_analysis(analysis)
        prep_count = sum(1 for c in chunks if c.chunk_type == 'prepared')
        qa_count = sum(1 for c in chunks if c.chunk_type == 'qa')
        logger.info(f"Created {len(chunks)} chunks ({prep_count} prep, {qa_count} qa)")
        print(f"\n🚀 Starting Agentic LLM Ingestion Pipeline ({len(chunks)} chunks)...")
        
        # Phase 2: Map Phase (Concurrent Extraction)
        # Process chunks in parallel using a ThreadPoolExecutor
        max_workers = min(10, len(chunks)) # Don't spin up more threads than we have chunks
        print(f"\n[Map Phase] Running extraction on {len(chunks)} chunks with {max_workers} concurrent workers...")
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
            # Map chunk indices to future objects so we know which is which when completed
            future_to_chunk = {
                executor.submit(self._process_single_chunk, chunk, i, len(chunks)): chunk 
                for i, chunk in enumerate(chunks, 1)
            }
            
            # Wait for all futures to complete
            for future in concurrent.futures.as_completed(future_to_chunk):
                try:
                    # The chunk is updated in-place by _process_single_chunk, 
                    # we just need to catch any unhandled exceptions
                    future.result()
                except Exception as exc:
                    chunk = future_to_chunk[future]
                    logger.error(f"Chunk {chunk.chunk_id} generated an exception: {exc}")
                    print(f"❌ Chunk {chunk.chunk_id} failed: {exc}")

        # Phase 3: Reduce Phase (Synthesis)
        print(f"\n[Reduce Phase] Synthesizing insights across all {len(chunks)} chunks...")
        synthesis_text_parts = []
        for c in chunks:
            part = f"### Chunk: {c.chunk_id} ({c.chunk_type})\n"
            part += f"Terms: {c.extracted_terms}\n"
            part += f"Concepts: {c.core_concepts}\n"
            if c.takeaways:
                part += f"Takeaways: {c.takeaways}\n"
            if c.evasion_analysis:
                part += f"Evasion: {c.evasion_analysis}\n"
            if c.misconceptions:
                part += f"Misconceptions: {c.misconceptions}\n"
            synthesis_text_parts.append(part)
            
        aggregated_text = "\n\n".join(synthesis_text_parts)
        
        synthesis_data = self.extractor.extract_synthesis(aggregated_text)
        
        # Manually extract usage stats before creating the dataclass
        usage = synthesis_data.pop("_usage_stats", None)
        if usage:
            print(f"    ↳ Synthesis [Model: {usage['model']} | In: {usage['prompt_tokens']} | Out: {usage['completion_tokens']}]")
            
        analysis.synthesis = CallSynthesisRecord(
            overall_sentiment=synthesis_data.get("overall_sentiment", ""),
            executive_tone=synthesis_data.get("executive_tone", ""),
            key_themes=synthesis_data.get("key_themes", []),
            strategic_shifts=synthesis_data.get("strategic_shifts", ""),
            analyst_sentiment=synthesis_data.get("analyst_sentiment", "")
        )
        
        print("✅ Agentic ingestion complete.\n")
        return chunks
        
    def _process_single_chunk(self, chunk: TranscriptChunk, index: int, total_chunks: int) -> None:
        """Helper method to process a single chunk, designed to run in a thread."""
        logger.info(f"Processing chunk {chunk.chunk_id} [{index}/{total_chunks}]")
        # print relies on thread-safety of the built-in print, but might interleave slightly in stdout.
        # This is usually fine for a simple UI, but could be logged instead.
        print(f"  [{index}/{total_chunks}] Analysing {chunk.chunk_id}... ")
        
        t1_usage = self._run_tier1(chunk)
        if t1_usage:
            logger.info(f"Chunk {chunk.chunk_id} - Tier 1 usage: {t1_usage}")
            # print(f"    ↳ Tier 1 [Model: {t1_usage['model']} | In: {t1_usage['prompt_tokens']} | Out: {t1_usage['completion_tokens']}]")
        
        # Phase 3: Tier 2 Deep Enrichment (Conditional routing)
        if chunk.requires_deep_analysis and getattr(chunk, 'tier1_score', 0) >= self.tier1_threshold:
            print(f"    ↳ Deep dive required on {chunk.chunk_id} (Score: {chunk.tier1_score}). Routing to Tier 2... ")
            t2_usage = self._run_tier2(chunk)
            if t2_usage:
                logger.info(f"Chunk {chunk.chunk_id} - Tier 2 usage: {t2_usage}")
                # print(f"      ↳ Tier 2 [Model: {t2_usage['model']} | In: {t2_usage['prompt_tokens']} | Out: {t2_usage['completion_tokens']}]")
        else:
            logger.info(f"Chunk {chunk.chunk_id} - Skipping Tier 2 (Score: {getattr(chunk, 'tier1_score', 0)})")
            # print(f"    ↳ Skipping Tier 2 for {chunk.chunk_id} (Score: {getattr(chunk, 'tier1_score', 0)}).")
        
    def _run_tier1(self, chunk: TranscriptChunk) -> Optional[Dict[str, Any]]:
        """Run fast, inexpensive extraction (OpenAI gpt-5-mini)."""
        tier1_data = self.extractor.extract_tier1(chunk.text, chunk.chunk_type)
        
        chunk.extracted_terms = tier1_data.get("extracted_terms", [])
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
