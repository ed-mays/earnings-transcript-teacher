# Analysis Pipeline

## Parsing layer

These stages run for every transcript during ingestion, extracting structural information from the raw text.

| # | Stage | Module | Output |
|---|---|---|---|
| 1 | **Basic stats** | `parsing/analysis.py` | Token count from cleaned/tokenized text |
| 2 | **Section extraction** | `parsing/sections.py` | Splits transcript into **Prepared Remarks** and **Q&A** sections |
| 3 | **Speaker identification** | `parsing/sections.py` | Speaker profiles with **role** (executive/analyst/operator), **title**, and **firm** |
| 4 | **Q&A threading** | `parsing/sections.py` | Structured question-answer exchanges grouped by analyst |

## LLM enrichment pipeline

After parsing, the ingestion pipeline runs a three-tier LLM analysis defined in `ingestion/prompts.py`. Tiers use different models and run selectively to balance cost and depth.

| Tier | Model | Runs on | Output |
|---|---|---|---|
| **Tier 1** | Claude Haiku | Every chunk | Industry jargon + definitions, core concepts (1–3 bullet points), importance score (1–10), `requires_deep_analysis` flag |
| **Tier 2** | Claude Sonnet | High-score chunks only (`tier1_score >= 6`) | Beginner-friendly takeaways with "why it matters", analyst evasion/skepticism detection (Q&A only) |
| **Tier 3** | Claude Sonnet | Full call (synthesis pass) | Cross-chunk themes and key takeaways summarising the entire call |

See `ingestion/prompts.py` for the authoritative prompt text and JSON output schemas for each tier.
