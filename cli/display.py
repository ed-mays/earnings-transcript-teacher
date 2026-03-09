from core.models import CallAnalysis

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

    print("\nKey Takeaways (Agentic)")
    agentic_takeaways = []
    for chunk in getattr(result, "chunks", []):
        agentic_takeaways.extend(getattr(chunk, "takeaways", []))
    for i, t in enumerate(agentic_takeaways[:5], 1):
        print(f"  {i}. {t.get('takeaway', '')}")
        print(f"     Significance: {t.get('why_it_matters', '')}")
        
    print("\nSemantic Search")
    num_embeddings = sum(1 for s in result.spans if s.embedding is not None)
    if num_embeddings > 0:
        cached = getattr(call, "cached_embeddings_count", 0)
        api = getattr(call, "api_embeddings_count", 0)
        print(f"  {num_embeddings} span embeddings available")
        print(f"    - {cached} loaded from Postgres cache")
        print(f"    - {api} generated via Voyage AI API")
    else:
        print("  Skipped (VOYAGE_API_KEY not set)")
