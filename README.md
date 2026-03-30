# Earnings Transcript Teacher

[![CI](https://github.com/ed-mays/earnings-transcript-teacher/actions/workflows/ci.yml/badge.svg)](https://github.com/ed-mays/earnings-transcript-teacher/actions/workflows/ci.yml)
[![codecov](https://codecov.io/gh/ed-mays/earnings-transcript-teacher/graph/badge.svg)](https://codecov.io/gh/ed-mays/earnings-transcript-teacher)
[![Python 3.12](https://img.shields.io/badge/python-3.12-blue?logo=python&logoColor=white)](https://www.python.org/)
[![uv](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/uv/main/assets/badge/v0.json)](https://github.com/astral-sh/uv)
[![Docker](https://img.shields.io/badge/docker-ready-blue?logo=docker&logoColor=white)](api/Dockerfile)

A Python pipeline that downloads, parses, and teaches earnings call transcripts. It extracts structured insights using classical NLP (TF-IDF, NMF, TextRank) and a three-tier LLM pipeline (Claude), stores everything in PostgreSQL, and surfaces it through a **FastAPI + Next.js web app** backed by Supabase and Modal.

---

## Features

- **Transcript Browser** — read the full transcript in the web UI with browser-style search: live highlighting, match count, and prev/next navigation.
- **Speaker Roster** — identifies every speaker by role, enriching executives with their title and analysts with their firm name.
- **Financial Jargon** — scans for standard financial terms (EBITDA, free cash flow, etc.) against a curated dictionary, with on-demand definitions.
- **Industry Jargon** — extracts company- and sector-specific terminology using the LLM, with on-demand contextual explanations sourced via RAG.
- **Key Takeaways (TextRank)** — extracts the most central sentences using graph-based ranking.
- **Theme Extraction (NMF)** — discovers core topics via Non-Negative Matrix Factorization.
- **Keyword Extraction (TF-IDF)** — identifies statistically significant terms unique to the transcript.
- **Semantic Search (Voyage AI + pgvector)** — embeds every speaker turn and stores vectors in Postgres for natural language retrieval.
- **General Q&A** — ask anything about the transcript; answers are grounded in relevant passages retrieved via semantic search.
- **Feynman Learning Loop** — a multi-turn AI chat session that guides you to teach the material back, exposing gaps in understanding.
- **Smart Caching** — reuses cached Voyage AI embeddings from Postgres to avoid redundant API calls.

---

## Architecture

```
earnings-transcript-teacher/
├── api/                # FastAPI backend (new)
│   ├── main.py          # FastAPI app entry point
│   ├── routes/          # Route modules
│   ├── Dockerfile
│   └── requirements.txt
├── web/                # Next.js frontend (new)
│   └── ...
├── pipeline/           # Modal ingestion functions (new)
│   ├── ingest.py
│   └── requirements.txt
│
├── main.py             # Console UI entry point (legacy)
├── app.py              # Web UI entry point — Streamlit (legacy)
├── migrate.py          # Schema migration script — run after upgrades
├── setup.sh            # One-time setup script (macOS/Linux)
├── setup.ps1           # One-time setup script (Windows)
├── requirements.txt    # Python dependencies (legacy pipeline)
│
├── core/               # Shared data models (CallAnalysis, TranscriptChunk, SpanRecord, etc.)
├── parsing/            # Transcript loading, section extraction, financial term scanner
├── nlp/                # NLP algorithms (TF-IDF keywords, NMF themes, TextRank takeaways)
├── services/           # Orchestration and external service integrations
│   ├── orchestrator.py  # Main analysis pipeline — wires all modules together
│   ├── company_info.py  # SEC EDGAR company lookup and context formatting
│   ├── competitors.py   # Competitor identification via Claude Haiku
│   └── llm.py           # Anthropic API client with rate limiting (Haiku + Sonnet)
├── ingestion/          # Three-tier agentic LLM enrichment pipeline (Claude Haiku + Sonnet)
├── cli/                # Console UI display and interactive menu
├── db/                 # PostgreSQL repository layer and semantic search
├── utils/              # Shared utilities
├── prompts/feynman/    # Pedagogical prompt files for the Feynman learning loop
└── tests/              # pytest test suite (unit + integration)
```

---

## Documentation

| Path | Contents |
|---|---|
| [`docs/getting-started.md`](docs/getting-started.md) | New developer onboarding: clone → running stack → first test |
| [`docs/architecture-review/`](docs/architecture-review/00-index.md) | Architecture specs and production-readiness findings |
| [`docs/runbooks/`](docs/runbooks/) | Operational runbooks (migration rollback, RLS verification) |
| [`docs/disaster-recovery.md`](docs/disaster-recovery.md) | Infrastructure rebuild guide |
| [`docs/database.md`](docs/database.md) | Migration system and schema reference |
| [`docs/llm_usage.md`](docs/llm_usage.md) | LLM integration reference (models, tiers, endpoints) |
| [`docs/legacy-stack.md`](docs/legacy-stack.md) | Legacy Python/Streamlit setup (deprecated) |

---

## Quick start

> Primary development path: FastAPI + Next.js + Supabase + Modal

### First-time setup

1. Copy the env templates and fill in your values:

```bash
cp api/.env.example api/.env
cp web/env.example web/.env.local
```

**`api/.env` variables:**

| Variable | Description |
|---|---|
| `DATABASE_URL` | Supabase connection string (Supabase → Project Settings → Database → URI) |
| `SUPABASE_URL` | Supabase project URL, e.g. `https://[ref].supabase.co` (Supabase → Project Settings → API) |
| `VOYAGE_API_KEY` | Required for the `/search` endpoint; other endpoints work without it |
| `PERPLEXITY_API_KEY` | Required for the Feynman chat endpoint |
| `MODAL_TOKEN_ID` | Required — Modal token ID for dispatching ingestion jobs (`modal token new` to generate) |

> `api/.env.example` is the canonical reference for all API env vars with inline comments.

**`web/.env.local` variables:**

| Variable | Description |
|---|---|
| `NEXT_PUBLIC_SUPABASE_URL` | Supabase project URL (Supabase → Project Settings → API) |
| `NEXT_PUBLIC_SUPABASE_ANON_KEY` | Supabase anon key (same page) |
| `NEXT_PUBLIC_API_URL` | FastAPI base URL — use `http://localhost:8000` for local dev |

### Starting the dev servers

```bash
./dev.sh          # start API + Next.js together (Ctrl-C stops both)
./dev.sh api      # API only (http://localhost:8000)
./dev.sh web      # Next.js only (http://localhost:3000)
```

The script reads env vars from `api/.env` and `web/.env.local` directly — no need to source them manually.

### Modal ingestion pipeline

**One-time setup:**

1. Authenticate: `modal setup` (opens browser)
2. Create a custom secret named `earnings-secrets` in the [Modal dashboard](https://modal.com/secrets) with these keys:
   - `DATABASE_URL`
   - `API_NINJAS_KEY`
   - `VOYAGE_API_KEY`
   - `ANTHROPIC_API_KEY`

**Test run** (executes in Modal cloud, streams logs locally):

```bash
modal run pipeline/ingest.py --ticker AAPL
```

**Deploy** (required before the FastAPI admin endpoint can dispatch jobs):

```bash
modal deploy pipeline/ingest.py
```

### Verify the API is running

```bash
curl http://localhost:8000/health
# → {"status":"ok"}
```

### Smoke-test the /api/calls endpoints (requires at least one ingested transcript)

```bash
# List all calls
curl http://localhost:8000/api/calls

# Full detail for a ticker
curl http://localhost:8000/api/calls/AAPL

# Paginated transcript turns (prepared remarks only)
curl "http://localhost:8000/api/calls/AAPL/spans?section=prepared&page=1&page_size=10"

# Semantic search (requires VOYAGE_API_KEY)
curl "http://localhost:8000/api/calls/AAPL/search?q=AI+infrastructure+spending"

# Trigger ingestion (requires Modal deployed + admin JWT)
curl -X POST http://localhost:8000/admin/ingest \
  -H "Authorization: Bearer <admin-user-jwt>" \
  -H "Content-Type: application/json" \
  -d '{"ticker": "AAPL"}'
# → {"status":"accepted","ticker":"AAPL","message":"Ingestion dispatched"}

# Check system health (requires admin JWT)
curl http://localhost:8000/admin/health \
  -H "Authorization: Bearer <admin-user-jwt>"
# → {"db":{"connected":true,"schema_version":10},"env_vars":{...},"external_apis":{...}}
```

### Run the API unit tests

```bash
pytest tests/unit/api/ -v
```

---

## Running tests

```bash
pytest                      # run all tests
pytest tests/unit/          # run only unit tests
pytest -v                   # verbose output (shows each test name)
pytest --cov=.              # run with coverage report
```

---

## Dependencies

Dependencies are managed with [uv](https://github.com/astral-sh/uv) using a two-file pattern:

| File | Purpose |
|---|---|
| `requirements.in` | Abstract deps — edit this file to add or change a dependency |
| `requirements.txt` | Locked deps — generated by `uv pip compile`, do not edit by hand |
| `api/requirements.in` | Abstract deps for the FastAPI backend |
| `api/requirements.txt` | Locked deps for the FastAPI backend |

To update a dependency:

```bash
# 1. Edit the .in file
# 2. Re-compile the lock file
uv pip compile requirements.in -o requirements.txt --python-version 3.12
uv pip compile api/requirements.in -o api/requirements.txt --python-version 3.12

# 3. Commit both files
git add requirements.in requirements.txt
git commit -m "chore: update <package> to x.y.z"
```

---

## Deployment

### Railway (FastAPI API)

1. railway.app → **New Project** → **Deploy from GitHub repo** → select this repo
2. Service → **Variables** — add the env vars from the table below (API column)
3. Saving variables auto-triggers a redeploy; verify at `https://<railway-domain>/health`
4. Copy the Railway public domain — you'll need it for the Vercel `NEXT_PUBLIC_API_URL` var

> **DATABASE_URL**: use the Supabase **Transaction pooler** URL (port 6543), not the direct connection (port 5432). The direct connection has DNS reliability issues on newer Supabase projects.

### Vercel (Next.js frontend)

1. vercel.com → **Add New → Project** → import this repo
2. Set **Root Directory** to `web`
3. Add env vars (Frontend column below) under **Environment Variables → Production**
4. After deploy, copy the Vercel production domain
5. Back in Railway → Variables → set `NEXT_PUBLIC_VERCEL_URL` to the Vercel domain (without `https://`)

Vercel automatically creates preview deployments for every PR. To allow all preview URLs through Railway's CORS, set `CORS_ORIGIN_REGEX` in Railway to a regex matching your app's preview URL pattern (e.g. `https://myapp(-[a-z0-9-]+)?\.vercel\.app`).

---

## Legacy CLI (not recommended)

> The original Python/Streamlit interface still works but is no longer the primary development target. See [docs/legacy-stack.md](docs/legacy-stack.md) for full setup instructions.

Quick reference for the legacy entry point:

```bash
python3 main.py                    # interactive terminal menu
python3 main.py --mode cli         # explicit; same as above
python3 main.py --mode gui         # launch Streamlit web UI
python3 main.py AAPL               # direct analysis
python3 main.py AAPL --save        # analyze and save to PostgreSQL
python3 main.py --reset-db         # clear all data
```

---

## Environment variable reference

| Variable | Used by | Description |
|---|---|---|
| `API_NINJAS_KEY` | Modal pipeline, legacy pipeline | API key for fetching raw transcripts ([api-ninjas.com](https://api-ninjas.com)) |
| `VOYAGE_API_KEY` | Modal pipeline, legacy pipeline, FastAPI `/search` | Voyage AI key for semantic embeddings ([voyageai.com](https://www.voyageai.com)) |
| `PERPLEXITY_API_KEY` | Legacy pipeline | Perplexity key for Feynman learning chat ([perplexity.ai](https://www.perplexity.ai)) |
| `ANTHROPIC_API_KEY` | Modal pipeline, legacy pipeline | Anthropic key for the LLM ingestion pipeline ([console.anthropic.com](https://console.anthropic.com)) |
| `DATABASE_URL` | Modal pipeline, legacy pipeline, FastAPI | PostgreSQL connection string (default: `dbname=earnings_teacher`) |
| `SUPABASE_URL` | FastAPI | Supabase project URL — used to fetch JWKS public keys for JWT verification |
| `NEXT_PUBLIC_SUPABASE_URL` | Next.js frontend | Supabase project URL |
| `NEXT_PUBLIC_SUPABASE_ANON_KEY` | Next.js frontend | Supabase anon key |
| `NEXT_PUBLIC_API_URL` | Next.js frontend | FastAPI base URL (Railway domain in production, `http://localhost:8000` locally) |
| `NEXT_PUBLIC_VERCEL_URL` | FastAPI CORS | Vercel production domain (without `https://`) — set in Railway production |
| `CORS_ORIGIN_REGEX` | FastAPI CORS | Regex matching allowed origin patterns — covers all Vercel preview URLs without enumerating them |
| `CORS_EXTRA_ORIGINS` | FastAPI CORS | Optional comma-separated extra allowed origins (e.g., Vercel preview URLs in staging) |
| `MODAL_TOKEN_ID` | FastAPI (admin ingest endpoint) | Modal token ID — required at startup; generate with `modal token new` |
| `SENTRY_DSN` | FastAPI (optional) | Sentry DSN — enables production exception alerting; service starts without it but logs a warning |
