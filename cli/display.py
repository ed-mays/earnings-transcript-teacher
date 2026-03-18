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

    print("\nAI Insights")
    print("-" * 11)
    
    # Count takeaways across all chunks
    takeaways_count = 0
    industry_jargon_count = 0
    for chunk in getattr(result, "chunks", []):
        takeaways_count += len(getattr(chunk, "takeaways", []))
        industry_jargon_count += len([t for t in getattr(chunk, "extracted_terms", []) if t.get("category") == "industry"])
    
    themes_count = len(result.synthesis.key_themes) if result.synthesis else 0
    
    print(f"  AI identified {takeaways_count} key takeaways")
    print(f"  AI identified {themes_count} key themes")
    print(f"  AI identified and defined {industry_jargon_count} relevant industry jargon terms")

    print("\nExtraction & Analysis")
    print("-" * 21)
    
    # Count financial jargon across all chunks
    financial_jargon_count = 0
    for chunk in getattr(result, "chunks", []):
        financial_jargon_count += len([t for t in getattr(chunk, "extracted_terms", []) if t.get("category") == "financial"])

    print(f"  TF-IDF analysis identified {len(result.keywords)} relevant keywords")
    print(f"  Identified {financial_jargon_count} relevant financial jargon terms")
    print(f"  Identified {len(result.speakers)} speakers")
    print(f"  Identified {len(result.qa_pairs)} Q&A exchanges")

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
