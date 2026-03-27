# Earnings Transcript Teacher

A Python pipeline that downloads, parses, and teaches earnings call transcripts. It extracts structured insights using classical NLP (TF-IDF, NMF, TextRank) and a three-tier LLM pipeline (Claude), stores everything in PostgreSQL, and surfaces it through two interfaces:

- **Console UI** (`main.py`) — interactive terminal menu and direct analysis
- **Web UI** (`app.py`) — Streamlit browser app with transcript browser, live chat, and metadata exploration

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

## Prerequisites

The setup scripts handle most of the installation automatically. You need to install the following manually first:

**macOS / Linux**

| Requirement | Notes |
|---|---|
| Python 3.10+ | `brew install python@3.12` or [python.org](https://www.python.org/downloads/) |
| PostgreSQL | `brew install postgresql@16 && brew services start postgresql@16` |
| pgvector | `brew install pgvector` |

**Windows**

| Requirement | Notes |
|---|---|
| Python 3.10+ | [python.org](https://www.python.org/downloads/) — check "Add Python to PATH" |
| Docker Desktop | [docker.com](https://www.docker.com/products/docker-desktop/) — used to run PostgreSQL + pgvector |

You will also need API keys for the four services listed in the [Environment variable reference](#environment-variable-reference) below.

---

## Setup

### macOS / Linux

```bash
bash setup.sh
```

The script will:
1. Verify Python 3.10+ and PostgreSQL are available
2. Create a `.venv` virtual environment and install all dependencies
3. Create the `earnings_teacher` database, enable the pgvector extension, and apply the schema
4. Copy `set_env.sh.template` to `set_env.sh` if it doesn't already exist

Then open `set_env.sh` and fill in your API keys. Once done, activate the environment for each new terminal session:

```bash
source .venv/bin/activate
source set_env.sh
```

### Windows (PowerShell)

```powershell
.\setup.ps1
```

The script will:
1. Verify Python 3.10+ and Docker Desktop are available
2. Create a `.venv` virtual environment and install all dependencies
3. Pull and start the `pgvector/pgvector:pg16` Docker image, create the database, and apply the schema
4. Copy `set_env.ps1.template` to `set_env.ps1` if it doesn't already exist

Then open `set_env.ps1` and fill in your API keys. The `DATABASE_URL` entry is pre-filled to point at the Docker container and does not need to be changed. Activate the environment for each new terminal session:

```powershell
.venv\Scripts\Activate.ps1
. .\set_env.ps1
```

> **Note:** The database runs in a Docker container named `earnings_teacher_db`. Stop it when not in use with `docker stop earnings_teacher_db` and restart it with `docker start earnings_teacher_db`.

---

## Running the app

### Console UI (interactive terminal menu)

```bash
python3 main.py
```

### Console UI (direct analysis)

```bash
python3 main.py AAPL            # analyze and print results
python3 main.py AAPL --save     # analyze and save to PostgreSQL
python3 main.py --reset-db      # clear all data (prompts for confirmation)
```

### Web UI (Streamlit)

```bash
streamlit run app.py
```

Open `http://localhost:8501` in your browser. The left column shows the analysis panel (jargon, speakers, takeaways, themes); the right column shows the transcript browser and chat interface.

---

## Running tests

```bash
pytest                      # run all tests
pytest tests/unit/          # run only unit tests
pytest -v                   # verbose output (shows each test name)
pytest --cov=.              # run with coverage report
```

---

## Downloading a transcript

```bash
./download_transcript.sh MSFT
```

This calls the API Ninjas endpoint and saves the raw JSON to `transcripts/MSFT.json`. The `transcripts/` directory is git-ignored (local data only).

---

## Semantic search

Once transcripts are saved with `--save`, search across all of them:

```bash
python3 db/search.py "AI infrastructure capital expenditures" -k 5
```

---

## Database management

The application uses PostgreSQL with `pgvector`.

### Schema migrations
When upgrading from an older version, apply any schema changes before starting the app:
```bash
python3 migrate.py
```
This is idempotent — safe to run multiple times. The web UI (`app.py`) now only checks that the schema is current; it no longer auto-migrates on startup. Migration files live in `db/migrations/` as `NNN_name.sql`; add a new file there to introduce future schema changes.

### Clearing data
To delete all stored analysis while keeping the database schema intact:
```bash
python3 main.py --reset-db
```

### Full reset (Schema changes)
If the database schema has changed or the database is in an inconsistent state, you can perform a full reset. This will drop the database and recreate it using `setup.sh`:
```bash
./reset_db.sh
```
*Note: This preserves your raw transcript files in `transcripts/` but deletes all processed data.*

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

### Local development (new stack)

#### First-time setup

1. Copy the env templates and fill in your values:

```bash
cp api/.env.example api/.env
cp web/.env.example web/.env.local
```

**`api/.env` variables:**

| Variable | Description |
|---|---|
| `DATABASE_URL` | Supabase connection string (Supabase → Project Settings → Database → URI) |
| `SUPABASE_JWT_SECRET` | JWT secret (Supabase → Project Settings → API) |
| `ADMIN_SECRET_TOKEN` | Any strong random string — protects admin-only routes |
| `VOYAGE_API_KEY` | Required for the `/search` endpoint; other endpoints work without it |
| `PERPLEXITY_API_KEY` | Required for the Feynman chat endpoint |

**`web/.env.local` variables:**

| Variable | Description |
|---|---|
| `NEXT_PUBLIC_SUPABASE_URL` | Supabase project URL (Supabase → Project Settings → API) |
| `NEXT_PUBLIC_SUPABASE_ANON_KEY` | Supabase anon key (same page) |
| `NEXT_PUBLIC_API_URL` | FastAPI base URL — use `http://localhost:8000` for local dev |

#### Starting the dev servers

```bash
./dev.sh          # start API + Next.js together (Ctrl-C stops both)
./dev.sh api      # API only (http://localhost:8000)
./dev.sh web      # Next.js only (http://localhost:3000)
```

The script reads env vars from `api/.env` and `web/.env.local` directly — no need to source them manually.

#### Modal ingestion pipeline

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

#### Verify the API is running

```bash
curl http://localhost:8000/health
# → {"status":"ok"}
```

#### Smoke-test the /api/calls endpoints (requires at least one ingested transcript)

```bash
# List all calls
curl http://localhost:8000/api/calls

# Full detail for a ticker
curl http://localhost:8000/api/calls/AAPL

# Paginated transcript turns (prepared remarks only)
curl "http://localhost:8000/api/calls/AAPL/spans?section=prepared&page=1&page_size=10"

# Semantic search (requires VOYAGE_API_KEY)
curl "http://localhost:8000/api/calls/AAPL/search?q=AI+infrastructure+spending"

# Trigger ingestion (requires Modal deployed + ADMIN_SECRET_TOKEN)
curl -X POST http://localhost:8000/admin/ingest \
  -H "X-Admin-Token: $ADMIN_SECRET_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"ticker": "AAPL"}'
# → {"status":"accepted","ticker":"AAPL","message":"Ingestion dispatched"}
```

#### Run the API unit tests

```bash
pytest tests/unit/api/ -v
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
| `SUPABASE_JWT_SECRET` | FastAPI | JWT secret — Supabase → Project Settings → API |
| `ADMIN_SECRET_TOKEN` | FastAPI | Secret for admin-only routes — any strong random string |
| `NEXT_PUBLIC_SUPABASE_URL` | Next.js frontend | Supabase project URL |
| `NEXT_PUBLIC_SUPABASE_ANON_KEY` | Next.js frontend | Supabase anon key |
| `NEXT_PUBLIC_VERCEL_URL` | FastAPI CORS | Set automatically by Vercel; omit in local dev |
