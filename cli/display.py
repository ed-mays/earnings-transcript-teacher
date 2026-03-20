from core.models import CallAnalysis, TokenUsageSummary

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

    if result.token_usage:
        _display_token_usage(result.token_usage)


def _display_token_usage(usage: TokenUsageSummary) -> None:
    """Print a summary table of token usage and estimated cost."""
    print("\nToken Usage & Estimated Cost")
    print("-" * 28)

    col_model  = 24
    col_input  = 15
    col_output = 16
    col_cost   = 14

    header = (
        f"{'Model':<{col_model}}"
        f"{'Input Tokens':>{col_input}}"
        f"{'Output Tokens':>{col_output}}"
        f"{'Est. Cost':>{col_cost}}"
    )
    print(f"  {header}")
    print("  " + "-" * (col_model + col_input + col_output + col_cost))

    for m in usage.by_model.values():
        row = (
            f"{m.display_name:<{col_model}}"
            f"{m.input_tokens:>{col_input},}"
            f"{m.output_tokens:>{col_output},}"
            f"{'$' + f'{m.estimated_cost:.4f}':>{col_cost}}"
        )
        print(f"  {row}")

    if len(usage.by_model) > 1:
        print("  " + "-" * (col_model + col_input + col_output + col_cost))
        total_row = (
            f"{'Total':<{col_model}}"
            f"{usage.total_input_tokens:>{col_input},}"
            f"{usage.total_output_tokens:>{col_output},}"
            f"{'$' + f'{usage.total_cost:.4f}':>{col_cost}}"
        )
        print(f"  {total_row}")
