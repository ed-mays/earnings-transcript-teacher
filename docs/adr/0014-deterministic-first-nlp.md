# Deterministic-First NLP Pipeline

**Status:** Accepted
**Date:** 2026-03-26

## Context

Transcript analysis involves multiple tasks: keyword extraction, topic clustering, Q&A section detection, importance scoring, and entity recognition. Some of these tasks are well-suited to classical NLP methods (fast, deterministic, zero API cost), while others require the reasoning capabilities of LLMs. The pipeline needed a strategy for when to use each approach.

## Decision

Use classical NLP methods as the primary analysis layer, with LLM calls as fallback or enrichment:

- **TF-IDF** — Keyword extraction and document similarity scoring (`nlp/text_processing.py`)
- **NMF (Non-negative Matrix Factorization)** — Topic clustering across transcript chunks
- **TextRank** — Extractive summarization and key sentence identification
- **Regex-based section detection** — Identifying prepared remarks, Q&A transitions, and safe harbor statements
- **scikit-learn cosine similarity** — Finding related transcript spans without embedding API calls

LLM fallback is used when deterministic methods fail — for example, `detect_qa_transition()` in `AgenticExtractor` calls Claude only when regex-based Q&A boundary detection doesn't find a match.

The key driver was cost and reliability — deterministic methods handle ~80% of analysis tasks without API calls, with LLM fallback only for tasks requiring reasoning (strategic insight synthesis, competitive dynamics, Q&A detection in unusual transcript formats).

## Alternatives considered

1. **LLM-first pipeline (all analysis via Claude)** — Sending every analysis task to Claude and skipping classical NLP entirely. Rejected because: (a) LLM calls for keyword extraction and topic clustering are 100–1000x more expensive than TF-IDF/NMF, (b) LLM results are non-deterministic (same input can produce different keywords on different runs), which makes testing and evaluation harder, and (c) API latency for simple extraction tasks is unnecessary when scikit-learn computes results in milliseconds.

2. **Hybrid with LLM-first, classical verification** — Use LLMs for all analysis, then verify with classical methods. Rejected because this doubles the work without clear benefit — if the classical method can verify the result, it could have produced the result directly.

3. **Pure classical NLP (no LLM at all)** — Relying entirely on TF-IDF, NMF, and TextRank. Rejected because: (a) classical methods cannot generate strategic insights or Socratic questions (they can only extract and cluster existing text), (b) Q&A section detection fails on ~20% of transcripts with non-standard formatting, where LLM reasoning is needed, and (c) the product's value depends on synthesis and interpretation that only LLMs can provide.

4. **Fine-tuned smaller models for specific tasks** — Training task-specific models (e.g., a classifier for Q&A detection, an NER model for financial entities). A viable approach that could improve quality on specific tasks. Rejected because: (a) training data curation and model management adds significant overhead for a small team, and (b) the LLM fallback approach achieves good-enough quality without the upfront investment.

## Consequences

**Easier:**
- ~80% of per-transcript cost is eliminated by avoiding LLM calls for commodity NLP tasks
- Deterministic methods produce reproducible results, simplifying testing and evaluation
- No API dependency for basic analysis — the pipeline partially works even if Claude is down
- scikit-learn and NLTK are mature, well-documented libraries with no API key requirements

**Harder:**
- Two code paths for some tasks (deterministic + LLM fallback) increase testing surface
- Classical NLP quality is bounded — TF-IDF can't understand context, NMF topics may not be semantically coherent
- Maintaining both classical and LLM approaches requires expertise in two different domains
- The 80/20 split is an approximation — some transcripts may need more LLM intervention than others
