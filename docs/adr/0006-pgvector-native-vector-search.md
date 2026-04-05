# pgvector for Native Vector Search

**Status:** Accepted
**Date:** 2026-03-26

## Context

The application provides semantic search over earnings transcript content. Users can search by meaning (not just keywords) to find relevant transcript spans. This requires storing vector embeddings alongside relational data (transcripts, companies, analysis results) and performing nearest-neighbor similarity queries. The prototype already used pgvector with PostgreSQL, and the rewrite needed to decide whether to keep this approach or migrate to a dedicated vector database.

## Decision

Continue using the pgvector extension within PostgreSQL (via Supabase) for all vector storage and similarity search. Embeddings are 1024-dimensional vectors from Voyage AI's `voyage-finance-2` model (ADR 0012), stored in the `spans` table with an HNSW index for approximate nearest-neighbor lookups.

The key driver was operational simplicity — a single database for both relational data and vector similarity eliminates the need for cross-system joins, separate connection management, and dual-write consistency concerns.

## Alternatives considered

1. **Pinecone** — A dedicated managed vector database. Rejected because: (a) querying requires a separate API call that cannot join with relational data (e.g., filtering spans by company or date requires either duplicating relational data into Pinecone metadata or making two round trips), (b) adds a new service to manage with its own API keys and billing, and (c) Pinecone's metadata filtering is less expressive than SQL WHERE clauses for the complex filters the application needs.

2. **Weaviate** — An open-source vector database with hybrid search. A strong alternative with good hybrid (keyword + vector) search capabilities. Rejected because: (a) the application already has deterministic keyword search via TF-IDF (ADR 0014), so Weaviate's hybrid search would duplicate existing functionality, and (b) running Weaviate requires a separate deployment and data sync pipeline.

3. **Qdrant** — A high-performance vector search engine. Similar trade-offs to Pinecone — excellent at vector search but adds operational complexity for a project where PostgreSQL already handles the workload. The current dataset size (thousands of transcript spans, not millions) doesn't require Qdrant's performance optimizations.

4. **ChromaDB** — An embedded vector database for local/development use. Rejected because it's designed for prototyping and doesn't scale to production multi-user workloads.

## Consequences

**Easier:**
- Single database for all data — no cross-system consistency concerns
- Vector queries can join directly with relational data in SQL (`SELECT ... FROM spans JOIN calls ON ... ORDER BY embedding <=> %s`)
- Supabase manages PostgreSQL + pgvector together — no separate infrastructure
- HNSW indexing provides good approximate nearest-neighbor performance for the current dataset scale
- Backup and restore cover both relational and vector data

**Harder:**
- pgvector's HNSW performance degrades at very large scale (millions of high-dimensional vectors) compared to purpose-built vector databases
- Limited to similarity metrics pgvector supports (L2, inner product, cosine) — no custom distance functions
- Index tuning (m, ef_construction parameters) requires PostgreSQL-level knowledge
- If the application needs real-time index updates at high write throughput, pgvector's single-writer HNSW rebuild could become a bottleneck
