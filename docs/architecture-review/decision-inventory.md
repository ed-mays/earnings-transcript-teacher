# Architectural Decision Inventory

**Date:** 2026-04-05
**Purpose:** Comprehensive inventory of every non-trivial architectural and technical decision in the Earnings Transcript Teacher codebase. This document is the authoritative input for issue #223 (ADR documentation).
**Scope:** Decisions made during the initial prototype era through the FastAPI + Next.js rewrite (March–April 2026).

---

## Methodology

The following sources were systematically audited to extract decisions:

| Source | Files examined |
|---|---|
| Architecture review docs | `docs/architecture-review/01-current-system-audit.md`, `02-target-architecture.md` |
| Review findings | `findings/issue-195` through `issue-221`, `synthesis-remediation-plan.md`, `cross-cutting-concerns-gaps.md`, `production-readiness-backlog.md` |
| Implementation specs | `specs/[001]` through `[005]` |
| Project conventions | `CLAUDE.md`, `web/AGENTS.md`, `docs/architecture-review/conventions.md` |
| Dependency manifests | `requirements.txt`, `api/requirements.in`, `web/package.json` |
| Deployment config | `api/Dockerfile`, `web/vercel.json` |
| Database schema | `supabase/migrations/` (7 migration files) |
| Pipeline code | `pipeline/ingest.py`, `ingestion/prompts.py`, `ingestion/pipeline.py` |
| Service layer | `services/llm.py`, `services/competitors.py`, `services/recent_news.py` |
| Data access layer | `db/repositories/` (8 repository modules) |
| Auth & config | `api/dependencies.py`, `api/settings.py` |
| Frontend | `web/proxy.ts`, `web/app/api/`, `web/lib/api.ts` |
| NLP modules | `nlp/embedder.py`, `nlp/text_processing.py` |
| Git history | Major PRs (#149, #150, #227, #236, #277, #294, #355) |
| Issue #223 | Cross-referenced all 9 candidate decisions |

Each decision was extracted, categorized, and assigned a confidence level for rationale reconstruction.

---

## Inventory

### Stack & Platform

#### 1. Rewrite Target Stack

**Category:** Stack & Platform
**Era:** Rewrite kickoff (March 2026)
**Confidence:** High
**Already in #223:** Yes — item 1

**Summary:** The application was rewritten from a Python + Streamlit monolith to FastAPI (backend) + Next.js (frontend) + Supabase (auth + database) + Modal (compute) + Railway (backend hosting) + Vercel (frontend hosting). The primary alternative was staying on Streamlit or adopting a single-platform approach (e.g., all-Firebase with Cloud Run). The key driver was separating concerns — a real API layer, a modern frontend framework, and managed infrastructure — while preserving the Python NLP/ingestion pipeline unchanged.

**Evidence:**
- `docs/architecture-review/02-target-architecture.md` — full target stack rationale
- `docs/architecture-review/01-current-system-audit.md` — coupling analysis of the monolith
- `CLAUDE.md` — "Primary stack: FastAPI (api/) + Next.js (web/) + Supabase (database + auth) + Modal (pipeline/)"

---

#### 2. Monorepo Structure

**Category:** Stack & Platform
**Era:** Rewrite kickoff (March 2026)
**Confidence:** High
**Already in #223:** No

**Summary:** Backend, frontend, pipeline, and shared modules live in a single repository rather than separate repos per service. The alternative was a polyrepo with independent deploy cycles. The key driver was development velocity during the rewrite — shared types, single PR workflow, and the ability to keep the legacy Streamlit app working alongside the new stack during migration.

**Evidence:**
- `docs/architecture-review/02-target-architecture.md` — monorepo project structure
- `docs/architecture-review/specs/[001] project-restructure.spec.md` — core extraction within monorepo
- Repository root: `api/`, `web/`, `pipeline/`, `nlp/`, `parsing/`, `services/`, `db/` all coexist

---

#### 3. Railway for Backend Hosting

**Category:** Stack & Platform
**Era:** Rewrite (March 2026)
**Confidence:** High
**Already in #223:** No

**Summary:** The FastAPI backend deploys to Railway as a Docker container, rather than serverless (e.g., AWS Lambda, Vercel Functions) or other container platforms (Cloud Run, Fly.io). The key driver was simplicity — Railway provides a managed container runtime with minimal configuration, and the vendor coupling analysis (issue #221) rated it LOW because the app uses a vanilla Docker image with no Railway-specific APIs.

**Evidence:**
- `api/Dockerfile` — standard Python Docker image, Uvicorn on port 8000
- `docs/architecture-review/findings/issue-221-cloud-stack-analysis.md` — vendor coupling rated LOW for Railway
- `api/requirements.in` — compiled to `api/requirements.txt` for Railway deploys

---

### Data & Storage

#### 4. Supabase for Auth + Database

**Category:** Data & Storage
**Era:** Rewrite (March 2026)
**Confidence:** High
**Already in #223:** Yes — item 2

**Summary:** Supabase provides both the PostgreSQL database and JWT-based authentication, replacing the original local Postgres + no-auth setup. The primary alternative was Firebase (Auth + Firestore) or separate providers (e.g., Clerk for auth, Neon for database). The key drivers were: PostgreSQL compatibility (preserving pgvector and the existing schema), managed auth with RLS integration, and the transaction pooler for serverless-friendly connections.

**Evidence:**
- `api/dependencies.py` — JWKS-based JWT validation against Supabase
- `supabase/migrations/` — 7 migration files, baseline schema + RLS policies
- `CLAUDE.md` — `DATABASE_URL` uses Supabase transaction pooler (port 6543)
- `supabase/migrations/20260330000003_rls_policies.sql` — Row Level Security policies

---

#### 5. No ORM — Raw psycopg + Dataclasses

**Category:** Data & Storage
**Era:** Pre-rewrite (legacy), carried forward
**Confidence:** High
**Already in #223:** No

**Summary:** All database access uses raw parameterized SQL via psycopg3, with results mapped to Python dataclasses. The alternative was an ORM like SQLAlchemy or Tortoise. The key drivers were: fine-grained control over pgvector queries (custom HNSW similarity joins), avoiding ORM overhead for a schema that was already well-understood, and keeping the data layer lightweight for a small team.

**Evidence:**
- `db/repositories/` — 8 repository modules, all raw SQL with `%s` parameterization
- `requirements.txt` — `psycopg[binary]` present, no SQLAlchemy/Tortoise
- `CLAUDE.md` — "Database access goes through `db/repositories.py`, not via raw psycopg calls scattered elsewhere"
- `docs/architecture-review/findings/issue-198-repository-service.md` — repository consolidation analysis

---

#### 6. pgvector for Native Vector Search

**Category:** Data & Storage
**Era:** Pre-rewrite (legacy), carried forward
**Confidence:** High
**Already in #223:** No

**Summary:** Semantic vector search uses the pgvector extension within PostgreSQL rather than a dedicated vector database (Pinecone, Weaviate, Qdrant). The alternative was a separate vector store with its own query API. The key driver was operational simplicity — a single database for both relational data and vector similarity, with HNSW indexing for performant nearest-neighbor lookups on 1024-dimensional Voyage embeddings.

**Evidence:**
- `supabase/migrations/20260329180609_remote_schema.sql` — `CREATE EXTENSION IF NOT EXISTS vector`, HNSW index on `spans(embedding)`
- `nlp/embedder.py` — 1024-dim vectors from `voyage-finance-2`
- `db/repositories/embedding_repository.py` — vector upsert with `register_vector()`
- `requirements.txt` — `pgvector` package

---

#### 7. Connection Pooling Strategy

**Category:** Data & Storage
**Era:** Rewrite (March 2026)
**Confidence:** High
**Already in #223:** No

**Summary:** The API uses psycopg3's `ConnectionPool` (min=2, max=10) initialized during the FastAPI lifespan, with a fallback to direct `psycopg.connect()` for test environments. The alternative was Supabase's built-in PgBouncer or an external pooler. The key driver was the synthesis remediation plan's finding that the original code opened a new TCP connection per repository method call, which would exhaust Supabase connection limits under moderate load.

**Evidence:**
- `api/dependencies.py` — module-level `_pool` with lifespan initialization
- `docs/architecture-review/findings/synthesis-remediation-plan.md` — "No connection pooling — one TCP connection per call" (finding #5)
- `api/settings.py` — `LOG_SLOW_QUERY_THRESHOLD_MS = 500` for pool performance tracking

---

#### 8. Data Retention Policy

**Category:** Data & Storage
**Era:** Rewrite (March–April 2026)
**Confidence:** Medium
**Already in #223:** No

**Summary:** Learning sessions older than 90 days and analytics events older than 1 year are automatically cleaned up via pg_cron scheduled jobs. The alternative was no automated cleanup or application-level batch jobs. The key driver was managing storage growth in Supabase's managed PostgreSQL without requiring application-side cron infrastructure.

**Evidence:**
- `supabase/migrations/20260330000001_retention_cleanup.sql` — pg_cron retention jobs
- `docs/architecture-review/findings/production-readiness-backlog.md` — retention policy requirements

---

### Auth & Security

#### 9. Role-Based Access Control

**Category:** Auth & Security
**Era:** Rewrite (March 2026)
**Confidence:** High
**Already in #223:** Yes — item 8

**Summary:** Access control uses a custom `user_role` enum (`admin` | `learner`) stored in a `profiles` table, enforced via a `SECURITY DEFINER` trigger that auto-provisions profiles on user creation. The alternative was Supabase's built-in RBAC or an external authorization service. The key driver was simplicity — two roles with a single SQL check in the FastAPI dependency injection layer.

**Evidence:**
- `supabase/migrations/20260329180609_remote_schema.sql` — `user_role` enum, `profiles` table, auto-provision trigger
- `api/dependencies.py` — `RequireAdminDep` checks `profiles.role`
- `docs/architecture-review/findings/issue-196-auth-fragmentation.md` — auth hardening analysis
- `supabase/migrations/20260330000003_rls_policies.sql` — RLS policies using `auth.uid()`

---

### LLM & AI Pipeline

#### 10. LLM Synthesis Pipeline (Claude)

**Category:** LLM & AI Pipeline
**Era:** Pre-rewrite (legacy), evolved during rewrite
**Confidence:** High
**Already in #223:** Yes — item 5

**Summary:** Transcript analysis uses Anthropic's Claude models in a three-tier pipeline: Tier 1 (Haiku, fast extraction on every chunk), Tier 2 (Sonnet, deep analysis on high-importance chunks), Tier 3 (Haiku, global synthesis). The alternative was a single-model approach or a non-LLM pipeline. The key driver was cost optimization — Haiku handles volume work cheaply, Sonnet is reserved for chunks scoring >= 6 on strategic importance.

**Evidence:**
- `ingestion/prompts.py` — tier documentation and all prompt constants
- `services/llm.py` — `AgenticExtractor` class with tier-specific model assignments
- `ingestion/pipeline.py` — tier dispatch logic

---

#### 11. Three-Tier LLM Cost/Quality Progression

**Category:** LLM & AI Pipeline
**Era:** Rewrite (March 2026)
**Confidence:** High
**Already in #223:** No

**Summary:** The pipeline uses a deliberate Haiku → Sonnet → Haiku progression: cheap model for triage (Tier 1), expensive model for deep analysis (Tier 2), cheap model for synthesis (Tier 3). The alternative was uniform model usage or a two-tier approach. The key driver was that synthesis (Tier 3) operates on already-extracted structured data, not raw transcript text, so a smaller model suffices — reducing per-call cost by ~10x for that phase.

**Evidence:**
- `ingestion/prompts.py:1-30` — tier architecture documentation
- `services/llm.py` — Tier 1: `claude-haiku-4-5-20251001`, Tier 2: `claude-sonnet-4-5`, Tier 3: `claude-haiku-4-5-20251001`

---

#### 12. Voyage AI for Embeddings

**Category:** LLM & AI Pipeline
**Era:** Pre-rewrite (legacy), carried forward
**Confidence:** High
**Already in #223:** Yes — item 6

**Summary:** Semantic embeddings use Voyage AI's `voyage-finance-2` model (1024 dimensions), stored in pgvector. The alternative was OpenAI embeddings or a general-purpose model. The key driver was domain specialization — `voyage-finance-2` is tuned for financial text, producing better similarity results for earnings transcript content than general-purpose embedding models.

**Evidence:**
- `nlp/embedder.py` — `voyage-finance-2` model, 1024-dim output
- `requirements.txt` — `voyageai` package
- `CLAUDE.md` — "voyageai: Semantic embeddings (voyage-finance-2)"

---

#### 13. Perplexity for Feynman Chat

**Category:** LLM & AI Pipeline
**Era:** Pre-rewrite (legacy), carried forward
**Confidence:** High
**Already in #223:** Yes — item 7

**Summary:** The Feynman learning chat uses Perplexity AI's `sonar-pro` model for streaming Socratic dialogue. The alternative was using Claude or GPT for chat. The key driver was Perplexity's research-oriented response style and built-in citation support, which aligns with the Feynman teaching methodology of grounding explanations in source material. A secondary driver was cost — keeping chat on a cheaper provider than the Claude models used for ingestion.

**Evidence:**
- `services/llm.py` — `stream_chat()` function using `sonar-pro` via OpenAI-compatible API
- `services/recent_news.py` — `sonar` (non-pro) for cheaper news search
- `CLAUDE.md` — "perplexityai: Feynman learning chat (streaming)"

---

#### 14. Deterministic-First NLP

**Category:** LLM & AI Pipeline
**Era:** Pre-rewrite (legacy), carried forward
**Confidence:** High
**Already in #223:** No

**Summary:** The pipeline uses classical NLP (TF-IDF, NMF topic modeling, TextRank, regex-based section detection) as the primary analysis layer, with LLM calls as fallback or enrichment. The alternative was an LLM-first pipeline. The key driver was cost and reliability — deterministic methods handle ~80% of analysis tasks (keyword extraction, topic clustering, Q&A section detection) without API calls, with LLM fallback only when heuristics fail (e.g., `detect_qa_transition()` in `AgenticExtractor`).

**Evidence:**
- `nlp/text_processing.py` — TF-IDF, NMF, TextRank implementations
- `services/orchestrator.py` — deterministic pipeline with LLM fallback for Q&A detection
- `requirements.txt` — `scikit-learn` for TF-IDF, NMF, cosine similarity
- `ingestion/prompts.py` — `QA_DETECTION_SYSTEM_PROMPT` documented as "fallback for detecting the Prepared Remarks → Q&A section boundary when deterministic methods fail"

---

#### 15. Prompt-as-Code Versioning

**Category:** LLM & AI Pipeline
**Era:** Rewrite (March 2026)
**Confidence:** High
**Already in #223:** No

**Summary:** Prompt constants are versioned as Python source files (`ingestion/prompts.py` for production, `ingestion/prompts_candidates.py` for experiments), with git history as the version record. The alternative was database-stored prompts or a prompt management platform. The key driver was simplicity and auditability — prompts are code-reviewed in PRs, diffs are visible in git, and there is no runtime dependency on an external prompt store.

**Evidence:**
- `ingestion/prompts.py` — all production prompt constants
- `ingestion/prompts_candidates.py` — experimental variants (never imported by pipeline)
- `docs/prompt-versioning.md` — full convention including naming, promotion workflow, and commit format
- `CLAUDE.md` — "Prompt constants live in `ingestion/prompts.py`. Experimental variants go in `ingestion/prompts_candidates.py`"

---

### Frontend Architecture

#### 16. Tailwind + shadcn/ui Component System

**Category:** Frontend Architecture
**Era:** Rewrite (March 2026)
**Confidence:** High
**Already in #223:** No

**Summary:** The frontend uses Tailwind CSS for styling and shadcn/ui (with Base UI primitives) for the component library, rather than a pre-built component library (Material UI, Chakra) or CSS-in-JS. The key driver was flexibility — shadcn copies component source into the project, allowing full customization without fighting library abstractions, while Tailwind provides utility-first styling that avoids CSS specificity issues.

**Evidence:**
- `web/package.json` — `tailwindcss`, `@base-ui/react`, `lucide-react`
- `web/components/ui/` — shadcn component source files
- `CLAUDE.md` — references shadcn/ui patterns

---

#### 17. Server Components Default (Next.js App Router)

**Category:** Frontend Architecture
**Era:** Rewrite (March 2026)
**Confidence:** High
**Already in #223:** No

**Summary:** The frontend uses Next.js App Router with Server Components as the default rendering strategy, adding `"use client"` only for components requiring browser APIs or React hooks. The alternative was the Pages Router or a client-rendered SPA (the original target architecture proposed a React SPA with no SSR). The key driver was the shift from Firebase to Supabase+Vercel, which made server-side rendering natural — Server Components fetch data directly via `createSupabaseServerClient()` without client-side waterfall requests.

**Evidence:**
- `web/AGENTS.md` — "server components are the default (page.tsx, layout.tsx)"
- `CLAUDE.md` — "Server vs client components: server components are the default"
- `web/vercel.json` — `{ "framework": "nextjs" }`
- `web/proxy.ts` — middleware-based auth for all routes

---

#### 18. SSE for Chat Streaming

**Category:** Frontend Architecture
**Era:** Pre-rewrite (legacy), carried forward
**Confidence:** High
**Already in #223:** No

**Summary:** The Feynman chat streams responses via Server-Sent Events (SSE) rather than WebSockets or long-polling. The alternative was WebSocket-based bidirectional communication. The key driver was simplicity — SSE is unidirectional (server → client), which matches the chat pattern (user sends message, server streams response), works natively with HTTP/2, requires no connection upgrade negotiation, and is trivially compatible with both FastAPI's `StreamingResponse` and the Perplexity API's streaming mode.

**Evidence:**
- `api/routes/chat.py` — `StreamingResponse` with `text/event-stream` content type
- `services/llm.py` — `stream_chat()` yields chunks from Perplexity's streaming API
- `docs/architecture-review/01-current-system-audit.md` — "Streaming chat — Feynman loop streams Perplexity via SSE"

---

### Backend Architecture

#### 19. Repository Pattern for Data Access

**Category:** Backend Architecture
**Era:** Pre-rewrite (legacy), formalized during rewrite
**Confidence:** High
**Already in #223:** Yes — item 4

**Summary:** All database access is encapsulated in domain-specific repository classes (CallRepository, AnalysisRepository, LearningRepository, etc.) rather than scattered raw SQL or an ORM's active record pattern. The alternative was inline SQL in route handlers or a service-layer query builder. The key driver was separation of concerns — route handlers stay thin, SQL is centralized for schema change impact analysis, and repositories can be injected as dependencies for testing.

**Evidence:**
- `db/repositories/` — 8 repository modules with backwards-compatible `__init__.py` re-exports
- `CLAUDE.md` — "Database access goes through `db/repositories.py`"
- `docs/architecture-review/findings/issue-198-repository-service.md` — repository consolidation
- `docs/architecture-review/specs/[002] data-layer.spec.md` — repository abstraction spec

---

#### 20. Environment-Driven Configuration

**Category:** Backend Architecture
**Era:** Rewrite (March 2026)
**Confidence:** High
**Already in #223:** No

**Summary:** All configuration is via environment variables with startup validation — no config files, no `.ini`/`.yaml`, no settings classes with defaults. The alternative was a configuration file hierarchy or a settings framework like Pydantic Settings. The key driver was deployment simplicity across three environments (local, Railway, Modal) that each inject env vars differently, plus fail-fast behavior — the API returns 503 for all requests if any required var is missing.

**Evidence:**
- `api/settings.py` — `REQUIRED_ENV_VARS` list with startup validation
- `CLAUDE.md` — canonical env var reference with `api/.env.example`
- `pipeline/ingest.py` — Modal secrets injected via `earnings-secrets` secret, not from `api/.env`

---

#### 21. Rate Limiting Strategy

**Category:** Backend Architecture
**Era:** Rewrite (March–April 2026)
**Confidence:** High
**Already in #223:** No

**Summary:** Rate limiting uses per-endpoint limits configured as application constants (chat: 60/hr, search: 100/hr, ingest: 600s cooldown per user per ticker), enforced via FastAPI middleware. The LLM service layer adds a custom token-bucket `RateLimiter` class with dual RPM/RPS limits and exponential backoff retry for transient provider errors. The alternative was a centralized rate limiting service or Redis-based distributed limiting. The key driver was simplicity at current scale — in-process limiting is sufficient for a single-instance deployment.

**Evidence:**
- `api/settings.py` — `CHAT_RATE_LIMIT`, `SEARCH_RATE_LIMIT`, `INGEST_RATE_LIMIT_WINDOW_SECONDS`
- `services/llm.py` — `RateLimiter` class with token-bucket implementation
- `docs/architecture-review/findings/production-readiness-backlog.md` — rate limiting as production gate

---

### Compute & Infrastructure

#### 22. Modal for Distributed Compute

**Category:** Compute & Infrastructure
**Era:** Rewrite (March 2026)
**Confidence:** High
**Already in #223:** Yes — item 3

**Summary:** Long-running transcript ingestion (30–60 seconds with LLM calls) runs on Modal's serverless compute platform rather than as background tasks in the API process, Celery workers, or AWS Lambda. The alternative was Cloud Run Jobs or a task queue. The key driver was developer experience — Modal provides a Python-native decorator-based interface (`@app.function`), automatic container image building from a pip requirements file, secret injection, and a 1-hour timeout without infrastructure management.

**Evidence:**
- `pipeline/ingest.py` — Modal app definition, image build, `@app.function` decorator with 3600s timeout
- `pipeline/requirements.txt` — separate dependency file for Modal container
- `CLAUDE.md` — "Modal pipeline (pipeline/): Ingestion functions use the @app.function decorator"

---

#### 23. Vercel for Frontend Hosting

**Category:** Compute & Infrastructure
**Era:** Rewrite (March 2026)
**Confidence:** High
**Already in #223:** No (item 1 mentions Vercel in the stack but doesn't treat it as a separate decision)

**Summary:** The Next.js frontend deploys to Vercel rather than self-hosted or another static/SSR hosting platform (Netlify, Cloudflare Pages, Firebase Hosting). The original target architecture (02-target-architecture.md) specified Firebase Hosting with a React SPA, but the shift to Next.js + Supabase made Vercel the natural choice. The key driver was zero-config Next.js deployment with automatic preview URLs, edge caching, and Supabase integration.

**Evidence:**
- `web/vercel.json` — `{ "framework": "nextjs" }`
- `docs/architecture-review/02-target-architecture.md` — original plan was Firebase Hosting (decision D7: "No Vercel"), later reversed
- `docs/architecture-review/findings/issue-221-cloud-stack-analysis.md` — Vercel coupling rated LOW

---

### Testing & Quality

#### 24. Testing Strategy

**Category:** Testing & Quality
**Era:** Pre-rewrite (legacy), formalized during rewrite
**Confidence:** High
**Already in #223:** No

**Summary:** Tests use pytest with a mirrored source tree (`tests/unit/`, `tests/integration/`), pytest-mock for mocking, and pytest-cov for coverage tracking. There are no ORM-based fixtures, async test runners, or integration test databases. The alternative was a Django-style test framework or async testing with pytest-asyncio. The key driver was alignment with the synchronous service layer — most business logic is synchronous Python with streaming as the only async concern.

**Evidence:**
- `CLAUDE.md` — "Use pytest for all tests. Unit tests go in tests/unit/, integration tests in tests/integration/"
- `requirements.txt` — `pytest`, `pytest-cov`, `pytest-mock`
- `tests/` directory — mirrors source tree structure

---

### Process & Delivery

#### 25. Vertical Slice Delivery Model

**Category:** Process & Delivery
**Era:** Rewrite (March 2026)
**Confidence:** High
**Already in #223:** Yes — item 9

**Summary:** Each issue delivers a complete vertical slice — data layer + API endpoint + UI component — rather than horizontal layers (all repositories first, then all routes, then all UI). The alternative was layer-by-layer delivery. The key driver was demo-ability — every merged PR produces a user-visible feature, enabling feedback loops and reducing integration risk from layer mismatches.

**Evidence:**
- `docs/architecture-review/conventions.md` — epic/sub-issue conventions
- Issue #223 — item 9, vertical slice delivery
- Memory: `feedback_vertical_slices.md` — "Always slice features vertically"

---

#### 26. Structured Logging with JSON/Text Mode

**Category:** Backend Architecture
**Era:** Rewrite (March–April 2026)
**Confidence:** High
**Already in #223:** No

**Summary:** The API uses structured logging with two output modes: JSON format in production (machine-parseable for log aggregation) and plain text in local development (human-readable). A slow query threshold (500ms) triggers warnings for database operations. The alternative was unstructured `print()` statements or a third-party logging framework. The key driver was observability — JSON logs integrate with Railway's log viewer and future log aggregation tools, while the text mode preserves developer experience locally.

**Evidence:**
- `api/settings.py` — `LOG_FORMAT_DEFAULT = "text"`, `LOG_SLOW_QUERY_THRESHOLD_MS = 500`
- `api/settings.py` — `SENTRY_DSN_ENV_VAR` for error alerting
- `docs/architecture-review/findings/issue-220-observability-logging.md` — observability gap analysis

---

#### 27. Prompt Evaluation Tooling

**Category:** LLM & AI Pipeline
**Era:** Rewrite (March–April 2026)
**Confidence:** Medium
**Already in #223:** No

**Summary:** Prompt quality is evaluated using a custom `tools/prompt_tuner.py` script that runs side-by-side comparisons of production vs. candidate prompts against a golden evaluation dataset (`tools/eval/dataset.json`). The alternative was manual A/B testing or a prompt management platform (LangSmith, Braintrust). The key driver was keeping the evaluation loop local and reproducible — no external service dependency, results are visible in the terminal, and the dataset is version-controlled alongside the prompts.

**Evidence:**
- `CLAUDE.md` — "Use tools/prompt_tuner.py to run a side-by-side comparison"
- `tools/eval/dataset.json` — golden evaluation dataset
- `docs/prompt-versioning.md` — promotion workflow requires metric comparison before promoting candidates

---

## Coverage Summary

| Category | Count | Decisions |
|---|---|---|
| Stack & Platform | 3 | #1, #2, #3 |
| Data & Storage | 5 | #4, #5, #6, #7, #8 |
| Auth & Security | 1 | #9 |
| LLM & AI Pipeline | 6 | #10, #11, #12, #13, #14, #15 |
| Frontend Architecture | 3 | #16, #17, #18 |
| Backend Architecture | 4 | #19, #20, #21, #26 |
| Compute & Infrastructure | 2 | #22, #23 |
| Testing & Quality | 1 | #24 |
| Process & Delivery | 1 | #25 |
| **Total** | **27** | |

### #223 Coverage

All 9 decisions from issue #223 are present: items 1–9 map to inventory entries #1, #4, #22, #19, #10, #12, #13, #9, #25.

### Codebase Audit Coverage

All 14 additional decisions from the codebase audit are present:

| Audit item | Inventory entry |
|---|---|
| 10. No ORM | #5 |
| 11. pgvector | #6 |
| 12. Monorepo | #2 |
| 13. Deterministic-first NLP | #14 |
| 14. Three-tier LLM pipeline | #11 |
| 15. Prompt-as-code | #15 |
| 16. SSE for chat | #18 |
| 17. Environment-driven config | #20 |
| 18. Data retention | #8 |
| 19. Railway hosting | #3 |
| 20. Connection pooling | #7 |
| 21. Testing strategy | #24 |
| 22. Tailwind + shadcn/ui | #16 |
| 23. Server Components default | #17 |

### New Decisions Surfaced

The audit surfaced 4 decisions not in either prior list:

- **#21** — Rate limiting strategy (custom token-bucket + per-endpoint limits)
- **#23** — Vercel for frontend hosting (treated as implicit in #223 item 1, but is a distinct decision with its own rationale — the original target architecture explicitly chose *against* Vercel)
- **#26** — Structured logging with JSON/text mode switching
- **#27** — Prompt evaluation tooling (local eval harness with golden dataset)

### Confidence Assessment

| Level | Count | Entries |
|---|---|---|
| High | 25 | All except #8, #27 |
| Medium | 2 | #8 (retention policy — rationale partially reconstructed from migration comments), #27 (eval tooling — tooling exists but adoption depth unclear) |
| Low | 0 | — |
