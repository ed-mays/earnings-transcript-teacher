import json
import os
import logging
from parsing.loader import read_text_file, extract_transcript_text
from services.company_info import fetch_company_info
from nlp.analysis import clean_text, tokenize
from parsing.sections import (
    extract_transcript_sections,
    extract_qa_exchanges,
    extract_spans,
    enrich_speakers,
    TURN_PATTERN,
)
from core.models import (
    CallAnalysis,
    CallRecord,
    SpanRecord,
    KeywordRecord,
    TopicRecord,
    QAPairRecord,
)
from nlp.embedder import get_embeddings
from db.persistence import fetch_existing_embeddings
from db.repositories import SchemaRepository, OutdatedSchemaError

logger = logging.getLogger(__name__)

def analyze(ticker: str = "MSFT") -> CallAnalysis:
    """Run the full analysis pipeline and return structured results."""
    # Safety Check: Fail fast if schema is out of date
    conn_str = os.environ.get("DATABASE_URL", "dbname=earnings_teacher")
    schema_repo = SchemaRepository(conn_str)
    is_ok, error_msg = schema_repo.check_health()
    if not is_ok:
        raise OutdatedSchemaError(error_msg)

    ticker = ticker.upper()
    file_path = f"./transcripts/{ticker}.json"
    content = read_text_file(file_path)
    raw_text = extract_transcript_text(content)

    # Look up company name and industry from SEC EDGAR using the CIK in the transcript JSON
    transcript_meta = json.loads(content)
    cik = transcript_meta.get("cik", "")
    company_name, industry = fetch_company_info(cik) if cik else ("", "")
    call_date = transcript_meta.get("date")  # ISO date string, e.g. "2026-01-29"

    # Basic stats
    tokens = tokenize(clean_text(raw_text))

    # Sections
    prepared_remarks, qa = extract_transcript_sections(raw_text)

    # Fallback to LLM if both Regex and Heuristics failed to find a Q&A section
    if not qa.strip():
        try:
            from services.llm import AgenticExtractor
            extractor = AgenticExtractor()
            
            # Extract turns from the transcript
            turns_metadata = [
                {"speaker": m.group("speaker"), "text": m.group("text")}
                for m in TURN_PATTERN.finditer(raw_text)
            ]
            
            # Usually Q&A starts in the middle to late half. Look at 20% to 90%.
            start_num = int(len(turns_metadata) * 0.2)
            end_num = int(len(turns_metadata) * 0.9)
            candidate_turns = turns_metadata[start_num:end_num]
            
            if candidate_turns:
                logger.info("Deterministic Q&A detection failed; triggering LLM fallback")
                result = extractor.detect_qa_transition(candidate_turns)
                
                t_idx = result.get("transition_index", -1)
                if t_idx != -1 and result.get("confidence", 0) > 0.5:
                    abs_idx = start_num + t_idx
                    all_turns = list(TURN_PATTERN.finditer(raw_text))
                    if abs_idx < len(all_turns):
                        split_point = all_turns[abs_idx].start()
                        prepared_remarks = raw_text[:split_point]
                        qa = raw_text[split_point:]
                        logger.info("LLM identified Q&A start at turn %d (confidence=%.2f)", abs_idx, result['confidence'])
        except Exception as e:
            logger.warning(f"LLM Q&A detection fallback failed: {e}")

    # Call record
    call = CallRecord(
        ticker=ticker,
        transcript_json=content,
        transcript_text=raw_text,
        token_count=len(tokens),
        prepared_len=len(prepared_remarks),
        qa_len=len(qa),
        company_name=company_name,
        industry=industry,
        call_date=call_date,
    )

    # Speakers
    speakers = enrich_speakers(raw_text, prepared_remarks, qa)

    # Spans
    raw_spans = extract_spans(raw_text, prepared_remarks, qa)
    span_records = [
        SpanRecord(
            call_id=call.id,
            speaker_name=speaker,
            section=section,
            span_type="turn",
            sequence_order=order,
            text=text,
        )
        for speaker, section, text, order in raw_spans
    ]

    # Embeddings
    # 1. Try to load cached embeddings from Postgres
    conn_str = os.environ.get("DATABASE_URL", "dbname=earnings_teacher")
    # Using the same placeholder quarter as persistence.py for now
    fiscal_quarter = f"Q? {ticker}"
    embedding_cache = fetch_existing_embeddings(conn_str, ticker, fiscal_quarter)

    # 2. Separate spans into cache hits and cache misses
    spans_to_embed = []
    for span in span_records:
        if span.text in embedding_cache:
            span.embedding = embedding_cache[span.text]
        else:
            spans_to_embed.append(span)

    # 3. Call Voyage API only for the misses
    new_embeddings = None
    if spans_to_embed:
        texts_to_embed = [s.text for s in spans_to_embed]
        new_embeddings = get_embeddings(texts_to_embed)
        if new_embeddings and len(new_embeddings) == len(spans_to_embed):
            for span, emb in zip(spans_to_embed, new_embeddings):
                span.embedding = emb

    api_count = len(spans_to_embed) if new_embeddings else 0
    cached_count = len(span_records) - len(spans_to_embed)
    
    call.cached_embeddings_count = cached_count
    call.api_embeddings_count = api_count

    # Build a lookup: (speaker_name, text_prefix) -> SpanRecord for linking
    span_lookup: dict[tuple[str, str], SpanRecord] = {}
    for s in span_records:
        key = (s.speaker_name, s.text[:80])
        span_lookup[key] = s

    # Keywords and topics are populated by the Haiku NLP synthesis phase (Phase 4 of ingestion).
    # Initialise as empty lists here; the pipeline will replace them below.
    keywords: list[KeywordRecord] = []
    topics: list[TopicRecord] = []
    takeaway_spans: list[SpanRecord] = []

    # Q&A pairs — link exchanges to span IDs
    exchanges = extract_qa_exchanges(qa, prepared_remarks=prepared_remarks)
    qa_pairs: list[QAPairRecord] = []

    # Build a set of known executive names for classifying Q&A turns.
    exec_names = {
        p.name for p in speakers if p.role == "executive"
    }

    for exchange_idx, exchange in enumerate(exchanges, 1):
        q_ids = []
        a_ids = []
        for speaker, text in exchange:
            key = (speaker, text[:80])
            span = span_lookup.get(key)
            if span:
                if speaker.lower() == "operator" or speaker in exec_names:
                    a_ids.append(span.id)
                else:
                    q_ids.append(span.id)

        if q_ids or a_ids:
            qa_pairs.append(QAPairRecord(
                exchange_order=exchange_idx,
                question_span_ids=q_ids,
                answer_span_ids=a_ids,
            ))

    analysis = CallAnalysis(
        call=call,
        speakers=speakers,
        spans=span_records,
        keywords=keywords,
        topics=topics,
        takeaways=takeaway_spans,
        qa_pairs=qa_pairs,
    )

    # -----------------------------------------------------------------------
    # Agentic Ingestion (Optional Enhancement)
    # -----------------------------------------------------------------------
    try:
        from ingestion.pipeline import IngestionPipeline
        pipeline = IngestionPipeline()
        chunks, synthesis, token_usage, nlp_synthesis = pipeline.process(analysis)
        analysis.chunks = chunks
        analysis.synthesis = synthesis
        analysis.token_usage = token_usage

        if nlp_synthesis:
            raw_keywords = nlp_synthesis.get("keywords", [])
            analysis.keywords = [
                KeywordRecord(term=k["term"], score=len(raw_keywords) - i)
                for i, k in enumerate(raw_keywords)
                if k.get("term")
            ]
            analysis.topics = [
                TopicRecord(
                    label=i,
                    name=t.get("name", ""),
                    terms=t.get("terms", []),
                    weight=1.0,
                    rank_order=i + 1,
                )
                for i, t in enumerate(nlp_synthesis.get("themes", []))
            ]
    except Exception as e:
        logger.warning("Agentic pipeline failed or skipped: %s", e)

    return analysis
