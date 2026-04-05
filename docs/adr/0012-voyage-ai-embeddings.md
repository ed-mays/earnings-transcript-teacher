# Voyage AI for Embeddings

**Status:** Accepted
**Date:** 2026-03-26

## Context

The semantic search feature requires vector embeddings that capture the meaning of financial text — earnings call transcripts contain domain-specific terminology (guidance, comps, EBITDA margin, forward-looking statements) that general-purpose embedding models may not represent well. The prototype used Voyage AI's `voyage-finance-2` model, and the rewrite needed to decide whether to continue with it or switch to a more widely used provider.

## Decision

Use Voyage AI's `voyage-finance-2` model for all semantic embeddings. The model produces 1024-dimensional vectors stored in pgvector (ADR 0006). Embedding generation is handled by `nlp/embedder.py`, which wraps the Voyage AI Python client.

The key driver was domain specialization — `voyage-finance-2` is specifically tuned for financial text, producing better similarity results for earnings transcript content than general-purpose models in informal A/B testing during the prototype phase.

## Alternatives considered

1. **OpenAI embeddings (text-embedding-3-large)** — The most widely used embedding API. Not chosen because: (a) informal testing showed `voyage-finance-2` produced more relevant search results for financial queries (e.g., "margin expansion drivers" correctly matched analyst Q&A about operating leverage), and (b) OpenAI's general-purpose model doesn't distinguish between financial terms that have different meanings in context (e.g., "guidance" as corporate forward-looking statements vs. general advice).

2. **Cohere embed-v3** — A strong general-purpose embedding model with good multilingual support. Not chosen because the application is English-only for earnings transcripts, and Cohere's general-purpose training doesn't provide the financial domain advantage of Voyage.

3. **Self-hosted embeddings (sentence-transformers with FinBERT)** — Running a fine-tuned financial BERT model locally or on Modal. Rejected because: (a) FinBERT produces 768-dim embeddings with lower semantic quality than `voyage-finance-2`'s 1024-dim output, (b) self-hosted inference adds GPU infrastructure management, and (c) the embedding API cost is minor compared to the LLM pipeline costs (ADR 0011).

4. **Anthropic embeddings** — Would simplify to a single provider. Rejected because Anthropic did not offer an embedding model at the time of the decision. If they release one with financial domain support, it would be worth evaluating to reduce provider count.

## Consequences

**Easier:**
- Domain-specific embeddings produce more relevant search results without fine-tuning
- Simple API — embed text, get vector, store in pgvector
- 1024 dimensions provide a good balance of quality and storage efficiency
- The Voyage Python client is lightweight with minimal configuration

**Harder:**
- Vendor dependency on Voyage AI — a smaller company than OpenAI or Anthropic, with less certainty about long-term availability
- Changing embedding models requires re-embedding all stored content (1024-dim assumption is baked into the HNSW index)
- No local/offline fallback — embedding requires an API call
- Voyage AI's pricing and rate limits are less well-documented than major providers
