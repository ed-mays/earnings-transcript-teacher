# LLM Synthesis Pipeline (Claude)

**Status:** Accepted
**Date:** 2026-03-26

## Context

The application's core value proposition is transforming raw earnings call transcripts into structured learning content: key topics, strategic insights, financial metrics, competitive dynamics, and Socratic questions. This synthesis requires understanding financial jargon, contextualizing management commentary, and producing structured output that can be stored and queried. The prototype used Anthropic's Claude models, and the rewrite needed to decide whether to continue with Claude or evaluate alternatives.

## Decision

Use Anthropic's Claude models as the LLM backbone for the transcript analysis pipeline. The pipeline processes transcripts through three tiers (ADR 0011) with structured JSON output at each stage. Claude was chosen for its strong performance on financial text comprehension, reliable structured output generation, and consistent handling of long transcript chunks (up to ~4,000 tokens per chunk).

The pipeline is implemented in `ingestion/pipeline.py` with prompt constants in `ingestion/prompts.py` and LLM interaction managed by `AgenticExtractor` in `services/llm.py`.

## Alternatives considered

1. **OpenAI GPT-4 / GPT-4o** — The most widely used alternative. Rejected because: (a) initial testing showed Claude produced more nuanced financial analysis (better at identifying forward-looking statements vs. backward-looking metrics), (b) Claude's longer context window at the time of initial development allowed processing larger transcript chunks without splitting, and (c) the team had more experience with Claude's API and prompt engineering patterns.

2. **Open-source models (Llama, Mistral) via self-hosted inference** — Running models on Modal or a GPU instance. Rejected because: (a) financial text comprehension quality was notably lower than Claude on evaluation samples, (b) self-hosted inference adds infrastructure complexity (GPU provisioning, model versioning, load balancing), and (c) the cost savings don't justify the quality trade-off for a product whose value depends on analysis quality.

3. **Google Gemini** — Competitive on long-context tasks. Not chosen primarily because the prototype was already built on Claude and switching would require re-engineering all prompts. Gemini remains a viable fallback if Anthropic pricing or availability changes.

4. **No LLM (pure NLP pipeline)** — Relying entirely on classical NLP (TF-IDF, NMF, TextRank). Rejected because deterministic methods (ADR 0014) handle keyword extraction and topic clustering well but cannot generate the higher-order analysis the product requires: strategic insight synthesis, competitive dynamics assessment, and Socratic question generation.

## Consequences

**Easier:**
- Claude's structured output mode produces reliable JSON that maps directly to the application's dataclass models
- Single API provider simplifies key management and billing
- Prompt iteration is fast — change a constant in `ingestion/prompts.py` and re-run
- Claude's safety features reduce the risk of generating misleading financial analysis

**Harder:**
- Vendor lock-in to Anthropic's API — prompts are Claude-optimized and would need rework for other providers
- API rate limits and outages directly impact ingestion availability
- Cost scales linearly with transcript volume (mitigated by the three-tier strategy in ADR 0011)
- Model version upgrades may change output quality, requiring re-evaluation of prompts
