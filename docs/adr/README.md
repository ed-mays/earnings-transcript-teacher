# Architecture Decision Records

This directory contains Architecture Decision Records (ADRs) for the Earnings Transcript Teacher project. ADRs capture the key architectural and technical decisions made during the project's evolution from a Python + Streamlit monolith to the current FastAPI + Next.js + Supabase + Modal stack.

## What is an ADR?

An Architecture Decision Record is a short document that captures a single architectural decision, including the context that motivated it, the alternatives that were considered, and the consequences of the choice. ADRs provide a decision log so that future contributors can understand *why* the system has its current shape.

## Format

We use a lightweight [MADR](https://adr.github.io/madr/) (Markdown Architectural Decision Records) format:

```markdown
# [Short noun phrase title]

**Status:** Accepted | Superseded | Deprecated
**Date:** YYYY-MM-DD (when the decision was effectively made)

## Context
What situation or constraint prompted this decision?

## Decision
What was decided, and why?

## Alternatives considered
What else was evaluated and why was it not chosen?

## Consequences
What becomes easier or harder as a result of this decision?
```

## File naming

`NNNN-short-title.md` — sequential numbering, lowercase with hyphens.

## Index

### Stack & Platform

| ADR | Decision | Date |
|-----|----------|------|
| [0001](0001-rewrite-target-stack.md) | Rewrite target stack (FastAPI + Next.js + Supabase + Modal) | 2026-03-26 |
| [0002](0002-monorepo-structure.md) | Monorepo structure | 2026-03-26 |
| [0003](0003-railway-backend-hosting.md) | Railway for backend hosting | 2026-03-27 |

### Data & Storage

| ADR | Decision | Date |
|-----|----------|------|
| [0004](0004-supabase-auth-and-database.md) | Supabase for auth + database | 2026-03-26 |
| [0005](0005-no-orm-raw-psycopg.md) | No ORM — raw psycopg + dataclasses | 2026-03-26 |
| [0006](0006-pgvector-native-vector-search.md) | pgvector for native vector search | 2026-03-26 |
| [0007](0007-connection-pooling-strategy.md) | Connection pooling strategy (psycopg3 pool) | 2026-03-28 |
| [0008](0008-data-retention-policy.md) | Data retention policy (pg_cron) | 2026-03-30 |

### Auth & Security

| ADR | Decision | Date |
|-----|----------|------|
| [0009](0009-role-based-access-control.md) | Role-based access control (custom user_role enum) | 2026-03-27 |

### LLM & AI Pipeline

| ADR | Decision | Date |
|-----|----------|------|
| [0010](0010-llm-synthesis-pipeline.md) | LLM synthesis pipeline (Claude) | 2026-03-26 |
| [0011](0011-three-tier-llm-cost-quality.md) | Three-tier LLM cost/quality progression | 2026-03-27 |
| [0012](0012-voyage-ai-embeddings.md) | Voyage AI for embeddings (voyage-finance-2) | 2026-03-26 |
| [0013](0013-perplexity-feynman-chat.md) | Perplexity for Feynman chat (sonar-pro) | 2026-03-26 |
| [0014](0014-deterministic-first-nlp.md) | Deterministic-first NLP pipeline | 2026-03-26 |
| [0015](0015-prompt-as-code-versioning.md) | Prompt-as-code versioning | 2026-03-27 |
| [0027](0027-prompt-evaluation-tooling.md) | Prompt evaluation tooling (local eval harness) | 2026-03-27 |

### Frontend Architecture

| ADR | Decision | Date |
|-----|----------|------|
| [0016](0016-tailwind-shadcn-component-system.md) | Tailwind + shadcn/ui component system | 2026-04-02 |
| [0017](0017-server-components-default.md) | Server Components default (Next.js App Router) | 2026-03-27 |
| [0018](0018-sse-chat-streaming.md) | SSE for chat streaming | 2026-03-26 |

### Backend Architecture

| ADR | Decision | Date |
|-----|----------|------|
| [0019](0019-repository-pattern.md) | Repository pattern for data access | 2026-03-26 |
| [0020](0020-environment-driven-configuration.md) | Environment-driven configuration | 2026-03-26 |
| [0021](0021-rate-limiting-strategy.md) | Rate limiting strategy (token-bucket + per-endpoint) | 2026-03-29 |
| [0026](0026-structured-logging.md) | Structured logging with JSON/text mode | 2026-03-29 |

### Compute & Infrastructure

| ADR | Decision | Date |
|-----|----------|------|
| [0022](0022-modal-distributed-compute.md) | Modal for distributed compute | 2026-03-27 |
| [0023](0023-vercel-frontend-hosting.md) | Vercel for frontend hosting | 2026-03-27 |

### Testing & Quality

| ADR | Decision | Date |
|-----|----------|------|
| [0024](0024-testing-strategy.md) | Testing strategy (pytest, mirrored tree) | 2026-03-26 |

### Process & Delivery

| ADR | Decision | Date |
|-----|----------|------|
| [0025](0025-vertical-slice-delivery.md) | Vertical slice delivery model | 2026-03-26 |

## Adding new ADRs

When making a new architectural decision:

1. Copy the format template above into a new file with the next sequential number
2. Fill in the Context, Decision, Alternatives Considered, and Consequences sections
3. Set the date to when the decision is made
4. Add an entry to the index table in this README
5. Commit the ADR alongside the code change it relates to (or separately for retroactive records)
