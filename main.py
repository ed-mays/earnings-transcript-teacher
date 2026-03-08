import sys

from transcript.loader import read_text_file, extract_transcript_text
from transcript.analysis import clean_text, tokenize, count_word_frequency
from transcript.keywords import extract_keywords
from transcript.themes import extract_themes
from transcript.takeaways import extract_takeaways
from transcript.sections import (
    extract_transcript_sections,
    extract_qa_exchanges,
    extract_spans,
    enrich_speakers,
)
from transcript.models import (
    CallAnalysis,
    CallRecord,
    SpanRecord,
    KeywordRecord,
    TopicRecord,
    QAPairRecord,
)


# ---------------------------------------------------------------------------
# Pipeline
# ---------------------------------------------------------------------------

def analyze(ticker: str = "MSFT") -> CallAnalysis:
    """Run the full analysis pipeline and return structured results."""
    ticker = ticker.upper()
    file_path = f"./transcripts/{ticker}.json"
    content = read_text_file(file_path)
    raw_text = extract_transcript_text(content)

    # Basic stats
    tokens = tokenize(clean_text(raw_text))

    # Sections
    prepared_remarks, qa = extract_transcript_sections(raw_text)

    # Call record
    call = CallRecord(
        ticker=ticker,
        transcript_json=content,
        transcript_text=raw_text,
        token_count=len(tokens),
        prepared_len=len(prepared_remarks),
        qa_len=len(qa),
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

    return CallAnalysis(
        call=call,
        speakers=speakers,
        spans=span_records,
        keywords=keywords,
        topics=topics,
        takeaways=takeaway_spans,
        qa_pairs=qa_pairs,
    )


# ---------------------------------------------------------------------------
# Display
# ---------------------------------------------------------------------------

def display(result: CallAnalysis) -> None:
    """Print the analysis results to console."""
    call = result.call

    print(f"Analysing {call.ticker}")
    print("=" * 40)

    print("\nBasic stats:")
    print(f"Token count: {call.token_count}")

    print("\nSection Extraction")
    print(f"Prepared Remarks: {call.prepared_len} chars")
    print(f"Q&A: {call.qa_len} chars")

    print("\nSpeaker Identification")
    print(f"Speakers ({len(result.speakers)} unique):")
    for p in result.speakers:
        detail = p.title or p.firm or ""
        detail_str = f", {detail}" if detail else ""
        print(f"  [{p.role:<10}] {p.name}{detail_str} ({p.turn_count} turn{'s' if p.turn_count != 1 else ''})")

    print("\nQ&A Exchange Extraction")
    print(f"\nQ&A exchanges found: {len(result.qa_pairs)}")
    # Show first 3 exchanges using span data
    exec_names = {p.name for p in result.speakers if p.role == "executive"}
    span_by_id = {s.id: s for s in result.spans}
    for pair in result.qa_pairs[:3]:
        all_ids = pair.question_span_ids + pair.answer_span_ids
        turns = [(span_by_id[sid].speaker_name, span_by_id[sid].text)
                 for sid in all_ids if sid in span_by_id]
        print(f"\n--- Exchange {pair.exchange_order} ({len(turns)} turns) ---")
        for speaker, text in turns:
            print(f"  {speaker}: {text}")

    print("\nKeyword Extraction (TF-IDF)")
    for kw in result.keywords:
        print(f"  {kw.score:.4f}  {kw.term}")

    print("\nTheme Extraction (NMF)")
    for topic in result.topics:
        print(f"  Topic {topic.label + 1}: {', '.join(topic.terms)}")

    print("\nKey Takeaways (TextRank)")
    for i, t in enumerate(result.takeaways, 1):
        print(f"  {i}. [{t.speaker_name}] {t.text}")


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import argparse
    import os
    
    parser = argparse.ArgumentParser(description="Analyze an earnings transcript.")
    parser.add_argument("ticker", nargs="?", default="MSFT", help="Ticker symbol (e.g., AAPL)")
    parser.add_argument("--save", action="store_true", help="Save results to Postgres")
    args = parser.parse_args()

    result = analyze(args.ticker)
    display(result)

    if args.save:
        from db.persistence import save_analysis
        conn_str = os.environ.get("DATABASE_URL", "dbname=earnings_teacher")
        print(f"\nSaving analysis to database ({conn_str})...")
        try:
            save_analysis(conn_str, result)
            print("Successfully saved to database.")
        except Exception as e:
            print(f"Error saving to database: {e}", file=sys.stderr)
            sys.exit(1)