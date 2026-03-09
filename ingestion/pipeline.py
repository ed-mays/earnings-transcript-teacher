import logging
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field

from transcript.models import CallAnalysis

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
        from ingestion.llm_clients import AgenticExtractor
        self.extractor = AgenticExtractor()

    def process(self, analysis: CallAnalysis) -> List[TranscriptChunk]:
        """Run the full ingestion pipeline on a parsed CallAnalysis."""
        logger.info(f"Starting agentic ingestion for {analysis.call.ticker}")
        
        chunks = create_chunks_from_analysis(analysis)
        prep_count = sum(1 for c in chunks if c.chunk_type == 'prepared')
        qa_count = sum(1 for c in chunks if c.chunk_type == 'qa')
        logger.info(f"Created {len(chunks)} chunks ({prep_count} prep, {qa_count} qa)")
        print(f"\n🚀 Starting Agentic LLM Ingestion Pipeline ({len(chunks)} chunks)...")
        
        # Phase 2: Tier 1 Extraction
        for i, chunk in enumerate(chunks, 1):
            print(f"  [{i}/{len(chunks)}] Analysing {chunk.chunk_id}... ", end="", flush=True)
            self._run_tier1(chunk)
            
            # Phase 3: Tier 2 Deep Enrichment (Conditional routing)
            if chunk.requires_deep_analysis and getattr(chunk, 'tier1_score', 0) >= self.tier1_threshold:
                print(f"Deep dive required (Score: {chunk.tier1_score}). Routing to Tier 2... ", end="", flush=True)
                self._run_tier2(chunk)
                print("Done.")
            else:
                print(f"Skipping Tier 2 (Score: {getattr(chunk, 'tier1_score', 0)}).")
        
        print("✅ Agentic ingestion complete.\n")
        return chunks
        
    def _run_tier1(self, chunk: TranscriptChunk) -> None:
        """Run fast, inexpensive extraction (OpenAI gpt-5-mini)."""
        tier1_data = self.extractor.extract_tier1(chunk.text, chunk.chunk_type)
        
        chunk.extracted_terms = tier1_data.get("extracted_terms", [])
        chunk.core_concepts = tier1_data.get("core_concepts", [])
        chunk.tier1_score = tier1_data.get("tier1_score", 0)
        chunk.requires_deep_analysis = tier1_data.get("requires_deep_analysis", False)
        
    def _run_tier2(self, chunk: TranscriptChunk) -> None:
        """Run deep reasoning enrichment (Anthropic claude-4.5-sonnet)."""
        tier2_data = self.extractor.extract_tier2(chunk.text, chunk.chunk_type)
        
        chunk.takeaways = tier2_data.get("takeaways", [])
        chunk.evasion_analysis = tier2_data.get("evasion_analysis")
        chunk.misconceptions = tier2_data.get("misconceptions", [])
