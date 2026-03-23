# 01 — Current System Audit

*Status: Draft — ready for review*

---

## 1. System Overview

The Earnings Transcript Teacher is a Python application that:
1. Downloads/parses earnings call transcripts (JSON format with CIK metadata)
2. Runs NLP analysis (TF-IDF, NMF topics, TextRank takeaways, semantic embeddings)
3. Runs LLM-augmented ingestion (Claude: term extraction, evasion analysis, synthesis)
4. Persists results to PostgreSQL (with pgvector for embeddings)
5. Presents an interactive learning experience (6-step path + Feynman Socratic loop)

Two frontends exist: a CLI (`main.py` + `cli/`) and a Streamlit web UI (`app.py` + `ui/`).

---

## 2. Module Inventory

### Core Pipeline (backend logic — high reuse value)

| Module | Lines | Responsibility | External Dependencies |
|--------|-------|----------------|----------------------|
| `parsing/loader.py` | ~60 | Read transcript JSON, extract text | filesystem |
| `parsing/sections.py` | ~300 | Split prepared remarks / Q&A, identify speakers, extract spans | regex |
| `parsing/financial_terms.py` | ~80 | CSV-driven financial term scanner | filesystem (CSV) |
| `nlp/analysis.py` | ~50 | Text cleaning, tokenization | — |
| `nlp/keywords.py` | ~60 | TF-IDF keyword extraction | scikit-learn |
| `nlp/themes.py` | ~80 | NMF topic modeling | scikit-learn |
| `nlp/takeaways.py` | ~70 | TextRank key passage extraction | scikit-learn |
| `nlp/embedder.py` | ~60 | Voyage AI semantic embeddings | voyageai API |
| `services/orchestrator.py` | ~250 | Full analysis pipeline coordinator | all of the above |
| `services/llm.py` | ~200 | Claude + Perplexity LLM calls (Feynman chat, agentic extraction) | anthropic, perplexity APIs |
| `services/company_info.py` | ~80 | SEC EDGAR company lookup | requests (SEC API) |
| `services/competitors.py` | ~60 | Perplexity-based competitor identification | perplexity API |
| `services/recent_news.py` | ~60 | News article fetch for call context | API Ninjas |
| `ingestion/pipeline.py` | ~300 | Tiered LLM chunk processing (Tier 1 triage → Tier 2 deep analysis → Tier 3 synthesis) | anthropic API |
| `ingestion/prompts.py` | ~200 | LLM prompt templates | — |
| `core/models.py` | ~260 | Dataclasses + Pydantic models for all domain objects | — |

### Data Layer (needs abstraction)

| Module | Lines | Responsibility | External Dependencies |
|--------|-------|----------------|----------------------|
| `db/schema.sql` | ~260 | PostgreSQL DDL (17 tables, pgvector extension) | PostgreSQL |
| `db/repositories.py` | ~1185 | All read/write operations (6 repository classes, raw psycopg) | psycopg, pgvector |
| `db/persistence.py` | ~100 | Legacy embedding cache fetch | psycopg |
| `db/search.py` | ~50 | Vector similarity search | psycopg, pgvector |
| `db/migrations/` | — | Incremental schema migrations | psycopg |

### Presentation Layer (will be replaced)

| Module | Lines | Responsibility |
|--------|-------|----------------|
| `app.py` | ~200 | Streamlit entry point, session state, page routing |
| `ui/metadata_panel.py` | ~706 | 6-step learning path renderer |
| `ui/feynman.py` | ~557 | Feynman Socratic loop (5-stage chat) |
| `ui/transcript_browser.py` | ~206 | Full transcript viewer with search |
| `ui/data_loaders.py` | ~185 | Streamlit-cached data loading wrappers |
| `ui/library.py` | ~145 | Transcript library / home page |
| `ui/sidebar.py` | ~85 | Sidebar navigation |
| `ui/term_actions.py` | ~96 | Inline term editing UI |
| `cli/display.py` | ~100 | Console text formatting |
| `cli/menu.py` | ~150 | Interactive CLI menu |

---

## 3. Data Model Summary

### Tables (17 total, schema version 8)

**Core:** `schema_version`, `calls`, `speakers`, `spans` (with vector embedding)

**Analysis:** `call_topics`, `span_keywords`, `qa_pairs`

**Agentic pipeline:** `transcript_chunks`, `extracted_terms`, `core_concepts`, `extracted_takeaways`, `evasion_analysis`, `misconceptions`, `call_synthesis`

**External context:** `competitors`

**Learning:** `learning_sessions`, `concept_exercises`, `transcript_progress`

### Key Data Characteristics

- **Calls table** stores raw JSON + extracted text (can be large — full transcript bodies)
- **Spans table** has 1024-dim vector embeddings (pgvector) — ~4KB per row for the vector alone
- **Relationships** are all UUID foreign keys with ON DELETE CASCADE from `calls`
- **No multi-user support** — `learning_sessions.user_id` exists but uses a hardcoded system UUID
- **No authentication** — entirely local

---

## 4. External Service Dependencies

| Service | Used For | Auth Method | Criticality |
|---------|----------|-------------|-------------|
| Anthropic Claude API | Tiered ingestion (Haiku/Sonnet), Q&A detection fallback | `ANTHROPIC_API_KEY` env var | Required for ingestion |
| Voyage AI | Semantic embeddings (voyage-finance-2, 1024-dim) | `VOYAGE_API_KEY` env var | Required for search |
| Perplexity AI | Feynman chat (sonar-pro), competitor research | `PERPLEXITY_API_KEY` env var | Required for learning loop |
| SEC EDGAR | Company name/industry lookup by CIK | None (public API) | Nice-to-have |
| API Ninjas | Recent news articles | `API_NINJAS_KEY` env var | Nice-to-have |

---

## 5. Coupling Analysis

### Tight Coupling (migration blockers)

1. **`db/repositories.py` ↔ PostgreSQL** — Raw psycopg calls with Postgres-specific SQL (TEXT[], JSONB[], pgvector operators, `gen_random_uuid()`). Every repository method opens its own connection. No abstraction layer.

2. **`ui/*.py` ↔ Streamlit** — Every UI module imports `streamlit as st` and uses st.session_state, st.columns, st.expander, st.chat_message, etc. The display logic and data fetching are interleaved.

3. **`services/orchestrator.py` ↔ filesystem** — Reads transcripts from `./transcripts/{TICKER}.json`. Assumes local file access.

### Moderate Coupling (manageable)

4. **`services/llm.py`** — Two unrelated responsibilities: Perplexity streaming chat and Anthropic structured extraction. These should split into separate service interfaces.

5. **`core/models.py`** — Mix of dataclasses (CallRecord, SpanRecord) and Pydantic models (TranscriptChunk). Both are used, but for different pipeline stages.

### Loose Coupling (good — preserve this)

6. **`nlp/*`** — Pure functions operating on text strings. No DB or framework dependencies. These can move to the backend unchanged.

7. **`parsing/*`** — Pure text processing. Framework-independent.

8. **`ingestion/pipeline.py`** — Takes a CallAnalysis, returns enriched data. Only depends on `services/llm.py` for LLM calls.

---

## 6. What Streamlit Is Doing That a New Stack Must Replace

| Streamlit Feature | Current Usage | Replacement Needed |
|-------------------|---------------|--------------------|
| `st.session_state` | Chat history, active ticker, Feynman stage, UI toggles | React state (useState/useReducer or Zustand) |
| `st.cache_data` / `@st.fragment` | Memoized DB queries in `data_loaders.py` | API response caching (React Query / SWR) |
| `st.chat_message` / `st.chat_input` | Feynman loop real-time chat | WebSocket or SSE streaming to React chat component |
| `st.columns` / `st.expander` / `st.tabs` | Layout for 6-step learning path | React component tree |
| `st.sidebar` | Navigation + transcript selector | React sidebar / routing |
| `st.rerun()` | Force re-render after state changes | React re-render (automatic) |
| Streamlit hosting | `streamlit run app.py` | Static frontend + API server deployment |

---

## 7. Risks and Constraints

### What's Hard About This Migration

1. **Vector search** — pgvector is deeply integrated. Firebase doesn't have a native equivalent. Options: Pinecone, Qdrant, or Firebase Vector Search (preview). This is the single hardest data layer decision.

2. **Streaming chat** — The Feynman loop streams Perplexity responses via SSE. FastAPI supports this natively, but the frontend needs to handle streaming text rendering.

3. **Long-running ingestion** — `orchestrator.analyze()` takes 30-60 seconds with LLM calls. This can't be a synchronous API call. Needs async task processing (Cloud Tasks, Celery, or Firebase Cloud Functions).

4. **Transcript storage** — Raw transcripts are large text blobs. Firestore has a 1MB document limit. May need Cloud Storage for raw transcripts with Firestore for metadata.

5. **Multi-tenancy** — Currently single-user with a hardcoded UUID. SaaS requires real authentication, per-user data isolation, and usage tracking/billing.

### What's Easy

1. **NLP pipeline** — Pure Python, no framework dependencies. Moves to backend as-is.
2. **Domain models** — Already well-structured dataclasses. Trivially serializable to JSON.
3. **Prompt templates** — Just strings. Move unchanged.
4. **External API integrations** — Already behind service modules. Easy to keep as backend services.

---

## 8. Open Questions for Next Specs

These need answers before writing the target architecture (doc 02):

1. **Vector search strategy** — Pinecone (managed, expensive), Qdrant (self-hosted, cheap), Firebase Vector Search (preview, limited), or keep a managed Postgres with pgvector (e.g., Supabase)?

2. **Authentication model** — Firebase Auth (simplest if already in Firebase ecosystem)? OAuth with a separate provider?

3. **Ingestion trigger** — User uploads a transcript file? Or the system fetches by ticker automatically? (Currently: local JSON file per ticker.)

4. **Billing model** — Per-transcript? Subscription? Free tier + paid? This affects data isolation and metering.

5. **Deployment target** — Firebase Hosting + Cloud Run? Vercel + fly.io? Fully Firebase (Functions + Hosting)?

6. **Offline/degraded mode** — If Perplexity or Claude is down, does the learning path still work with cached analysis? (Currently: yes for steps 1-6, no for Feynman chat.)

---

*Next: [02-target-architecture.md](02-target-architecture.md) — to be drafted after reviewing open questions above.*
