# Three-Tier LLM Cost/Quality Progression

**Status:** Accepted
**Date:** 2026-03-27

## Context

Transcript ingestion involves processing many chunks per transcript (typically 20–50 chunks of ~4,000 tokens each). Using a single high-quality model for every chunk would be prohibitively expensive at scale. Not every chunk requires deep analysis — boilerplate sections (safe harbor statements, operator instructions) and low-importance chunks can be processed with a cheaper model, while strategically important sections (guidance changes, competitive commentary) benefit from more capable models.

## Decision

Implement a deliberate three-tier cost/quality progression using Claude models:

- **Tier 1 (Haiku)** — Fast extraction on every chunk. Extracts structured fields (topics, metrics, key quotes) from raw transcript text. Runs on all chunks regardless of importance. Cost: ~$0.25/million input tokens.
- **Tier 2 (Sonnet)** — Deep analysis on high-importance chunks. Performs strategic insight synthesis, competitive dynamics assessment, and forward-looking statement analysis. Only runs on chunks scoring >= 6 on strategic importance (as determined by Tier 1). Cost: ~$3/million input tokens.
- **Tier 3 (Haiku)** — Global synthesis across all Tier 1 + Tier 2 outputs. Produces transcript-level summaries, cross-chunk topic connections, and Socratic questions. Operates on already-extracted structured data, not raw transcript text, so a smaller model suffices. Cost: ~$0.25/million input tokens.

The key driver was that Tier 3 operates on pre-processed structured JSON (not raw text), so a cheaper model handles it well — reducing per-transcript cost by ~60% compared to using Sonnet for all three tiers.

## Alternatives considered

1. **Single model for all tiers (Sonnet everywhere)** — Simpler to implement and reason about. Rejected because: (a) per-transcript cost would be ~3x higher, (b) Haiku's speed advantage (lower latency) reduces total ingestion time, and (c) Tier 1's extraction task is well-defined enough that Haiku handles it reliably.

2. **Two tiers (Haiku extraction + Sonnet synthesis)** — Skip the importance-based Tier 2 and use Sonnet only for final synthesis. Rejected because the deep analysis on high-importance chunks (identifying forward-looking statements, assessing competitive positioning) requires the richer context of the raw transcript text, which is unavailable at the synthesis stage.

3. **Dynamic model selection based on chunk complexity** — Using an LLM or classifier to decide which model to use per chunk. Rejected because: (a) the importance score from Tier 1 already provides a good heuristic for routing, (b) adding a classification step increases latency, and (c) the three-tier design is simple enough to debug and tune manually.

4. **Cost-optimized open-source tiers (Haiku → Sonnet → local Llama)** — Using a self-hosted model for Tier 3. Rejected because the operational complexity of running inference infrastructure (ADR 0010, alternative 2) isn't justified by the cost savings on Tier 3, which is already the cheapest tier.

## Consequences

**Easier:**
- Per-transcript cost is predictable and bounded (only high-importance chunks hit Sonnet)
- Tier 1 and Tier 3 complete quickly due to Haiku's lower latency
- The importance threshold (>= 6) is tunable without changing prompts or pipeline code
- Each tier's prompts can be optimized independently

**Harder:**
- Three sets of prompts to maintain, test, and evaluate (ADR 0027)
- The importance scoring heuristic may misclassify chunks (important content processed by Haiku only, or boilerplate processed by Sonnet)
- Model version upgrades affect cost assumptions — a cheaper Sonnet could make the three-tier approach unnecessary
- Debugging requires tracing through all three tiers to understand how a final insight was produced
