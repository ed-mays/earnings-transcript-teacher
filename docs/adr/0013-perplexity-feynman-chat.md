# Perplexity for Feynman Chat

**Status:** Accepted
**Date:** 2026-03-26

## Context

The application's Feynman learning feature provides a Socratic dialogue where users explain what they've learned from an earnings transcript, and the AI asks probing questions to deepen understanding. This chat experience requires streaming responses, grounded knowledge (not hallucinated financial claims), and a teaching-oriented interaction style. The prototype used Perplexity AI's models, and the rewrite needed to decide whether to continue with Perplexity or consolidate onto Claude.

## Decision

Use Perplexity AI's `sonar-pro` model for the Feynman learning chat, accessed via the OpenAI-compatible API. A cheaper `sonar` model is used for supplementary features (recent news search in `services/recent_news.py`). Streaming responses are delivered via SSE (ADR 0018).

The key drivers were: (a) Perplexity's research-oriented response style with built-in citation support aligns with the Feynman teaching methodology of grounding explanations in source material, and (b) cost separation — keeping chat on a different provider than the Claude models used for ingestion avoids having a single provider's rate limits or outages affect both features.

## Alternatives considered

1. **Claude for chat (consolidate on Anthropic)** — Using Claude for both ingestion and chat would simplify to a single provider. Not chosen because: (a) Perplexity's citation-grounded responses are more natural for the Feynman methodology (it naturally references sources rather than generating plausible-sounding claims), and (b) Claude's per-token cost is higher than `sonar-pro` for the conversational workload pattern (many short exchanges vs. the batch processing in ingestion).

2. **OpenAI GPT-4o for chat** — GPT models are strong at conversational tasks. Not chosen because: (a) GPT-4o doesn't have Perplexity's built-in search/citation behavior, which is central to the grounded-explanation feature, and (b) adding a third LLM provider would increase API key and billing management complexity without a clear quality advantage for this specific use case.

3. **RAG-based chat (Claude + retrieved context)** — Using Claude with a retrieval-augmented generation pipeline that fetches relevant transcript spans before generating responses. A viable architecture that could produce higher-quality grounded responses. Not chosen because: (a) implementing a RAG pipeline requires significant infrastructure (retrieval, re-ranking, context window management), and (b) Perplexity's built-in search provides a simpler approximation of grounded responses for the current feature scope. This remains a future enhancement path.

4. **Open-source chat model (Llama, Mixtral)** — Self-hosted conversational model. Rejected for the same infrastructure complexity reasons as ADR 0010 alternative 2, compounded by the need for streaming support and low-latency responses in a real-time chat context.

## Consequences

**Easier:**
- Perplexity's citation behavior provides grounded responses without building a RAG pipeline
- Cost-effective for conversational workloads (cheaper per-token than Claude Sonnet)
- OpenAI-compatible API means the client code is standard and portable
- Provider isolation — Anthropic outages don't affect chat, and Perplexity outages don't affect ingestion

**Harder:**
- Perplexity produces inconsistent JSON for structured output — it should only be used for streaming chat, not structured data extraction
- Two LLM providers to manage (API keys, rate limits, billing, version tracking)
- Perplexity's model behavior is less predictable across versions than Claude's
- If Perplexity's citation quality degrades or the service becomes unavailable, migrating chat to Claude requires prompt re-engineering
