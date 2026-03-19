import json
import os
import logging
from parsing.loader import read_text_file, extract_transcript_text
from services.company_info import fetch_company_info
from nlp.analysis import clean_text, tokenize
from nlp.keywords import extract_keywords
from nlp.themes import extract_themes
from nlp.takeaways import extract_takeaways
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
    cik = json.loads(content).get("cik", "")
    company_name, industry = fetch_company_info(cik) if cik else ("", "")

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
                print(f"  ↳ Deterministic Q&A detection failed. Triggering LLM fallback...")
                result = extractor.detect_qa_transition(candidate_turns)
                
                t_idx = result.get("transition_index", -1)
                if t_idx != -1 and result.get("confidence", 0) > 0.5:
                    abs_idx = start_num + t_idx
                    all_turns = list(TURN_PATTERN.finditer(raw_text))
                    if abs_idx < len(all_turns):
                        split_point = all_turns[abs_idx].start()
                        prepared_remarks = raw_text[:split_point]
                        qa = raw_text[split_point:]
                        print(f"    ↳ LLM identified Q&A start at turn {abs_idx} (Confidence: {result['confidence']}).")
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

    # Keywords
    keyword_results = extract_keywords(raw_text)
    keywords = [
        KeywordRecord(term=term, score=score)
        for term, score in keyword_results
    ]

    # Topics
    theme_results = extract_themes(raw_text)
    topics = [
        TopicRecord(
            label=t.label,
            terms=t.terms,
            weight=t.weight,
            rank_order=rank,
        )
        for rank, t in enumerate(theme_results, 1)
    ]

    # Takeaways — link back to span records
    takeaway_results = extract_takeaways(raw_text)
    takeaway_spans: list[SpanRecord] = []
    for t in takeaway_results:
        key = (t.speaker, t.text[:80])
        if key in span_lookup:
            span = span_lookup[key]
            span.textrank_score = t.score
            takeaway_spans.append(span)
        else:
            # Takeaway didn't match a span (e.g. sentence-level split);
            # create a standalone span for it.
            takeaway_span = SpanRecord(
                call_id=call.id,
                speaker_name=t.speaker,
                section="qa",
                span_type="turn",
                sequence_order=-1,
                text=t.text,
                textrank_score=t.score,
            )
            takeaway_spans.append(takeaway_span)

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
        chunks, synthesis = pipeline.process(analysis)
        analysis.chunks = chunks
        analysis.synthesis = synthesis
    except Exception as e:
        logger.warning(f"Agentic pipeline failed or skipped: {e}")

    return analysis
