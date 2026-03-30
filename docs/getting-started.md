# Getting started

This guide takes you from a fresh clone to a running, testable local environment. It covers the primary stack only: **FastAPI + Next.js + Supabase + Modal**.

> The original Python/Streamlit CLI is **deprecated**. If you need it for reference, see [docs/legacy-stack.md](legacy-stack.md). Do not start there for new development work.

---

## Prerequisites

### Tools

| Tool | Minimum version | Install |
|---|---|---|
| Python | 3.12 | [python.org](https://www.python.org/downloads/) or `brew install python@3.12` |
| uv | latest | `pip install uv` or [astral.sh/uv](https://github.com/astral-sh/uv) |
| Node.js | 18 | [nodejs.org](https://nodejs.org/) or `brew install node` |
| Git | any | pre-installed on most systems |

### API keys and accounts

You will need accounts and keys for the following services. Gather them before starting — the API will refuse to start if any required key is missing.

| Service | Required for | Notes |
|---|---|---|
| [Supabase](https://supabase.com) | Database + auth | Free tier is sufficient for local dev |
| [API Ninjas](https://api-ninjas.com) | Transcript download | Free tier available |
| [Voyage AI](https://www.voyageai.com) | Semantic search (`/search` endpoint) | Required for search; other endpoints work without it |
| [Perplexity AI](https://www.perplexity.ai) | Feynman chat endpoint | |
| [Anthropic](https://console.anthropic.com) | LLM ingestion pipeline | |
| [Modal](https://modal.com) | Cloud ingestion | Free tier available; required even for local dev (see note below) |
| [Sentry](https://sentry.io) | Exception alerting | Optional; production only |

> **`MODAL_TOKEN_ID` is required at startup.** The FastAPI app validates all required env vars at launch and returns HTTP 503 for every request if any are missing. Generate a token with `modal token new` before filling in your `.env`.

---

## Clone and install

```bash
git clone https://github.com/ed-mays/earnings-transcript-teacher
cd earnings-transcript-teacher

# Python dependencies (backend + shared pipeline)
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\Activate.ps1
pip install -r requirements.txt
pip install -r api/requirements.txt

# Node dependencies (Next.js frontend)
cd web && npm install && cd ..
```

---

## Configure environment

Copy both env templates and fill in your values:

```bash
cp api/.env.example api/.env
cp web/env.example web/.env.local
```

### `api/.env`

| Variable | Required | How to get it |
|---|---|---|
| `DATABASE_URL` | Yes | See [Database setup](#database-setup) below |
| `SUPABASE_URL` | Yes | Supabase dashboard → Project Settings → API → Project URL |
| `VOYAGE_API_KEY` | Yes | voyageai.com |
| `PERPLEXITY_API_KEY` | Yes | perplexity.ai |
| `ANTHROPIC_API_KEY` | Yes | console.anthropic.com |
| `API_NINJAS_KEY` | Yes | api-ninjas.com |
| `MODAL_TOKEN_ID` | Yes | `modal token new` (opens browser) |
| `SENTRY_DSN` | No | Sentry project settings; omit for local dev |
| `NEXT_PUBLIC_VERCEL_URL` | No | Set in Railway for production CORS; omit locally |
| `CORS_EXTRA_ORIGINS` | No | Comma-separated extra allowed origins; omit locally |

> `api/.env.example` is the canonical reference with inline comments for all variables.

### `web/.env.local`

| Variable | Value for local dev |
|---|---|
| `NEXT_PUBLIC_SUPABASE_URL` | Your Supabase project URL |
| `NEXT_PUBLIC_SUPABASE_ANON_KEY` | Supabase dashboard → Project Settings → API → anon key |
| `NEXT_PUBLIC_API_URL` | `http://localhost:8000` |

---

## Database setup

Migrations are managed with the Supabase CLI. Ensure you have it installed (`brew install supabase/tap/supabase`) and are linked to the project (`supabase link`).

1. Create a Supabase project at [supabase.com](https://supabase.com) (free tier is sufficient).

2. Get your connection string: Dashboard → **Project Settings** → **Database** → **Connection string** → **URI**.
   - Select **Transaction pooler** — this uses **port 6543**.
   - Do **not** use the direct connection (port 5432). Newer Supabase projects have DNS reliability issues on the direct port.

3. Set `DATABASE_URL` to the transaction pooler URI in `api/.env`.

4. Set `SUPABASE_URL` to your project URL (Dashboard → Project Settings → API → Project URL).

5. Apply schema migrations:
   ```bash
   supabase db push
   ```
   This applies all pending migrations from `supabase/migrations/` and is idempotent.

6. Apply Row Level Security policies — migrations do **not** apply RLS. Apply them separately:
   - Supabase dashboard → **SQL Editor**
   - Paste the contents of `db/rls-policies.sql`
   - Click **Run**
   - Verify using the checklist in [`docs/runbooks/rls-verification.md`](runbooks/rls-verification.md)

> **Migrations are not auto-applied.** Any time you pull changes that add files to `supabase/migrations/`, run `supabase db push` manually.

---

## Start the dev stack

```bash
./dev.sh          # API (localhost:8000) + Next.js (localhost:3000) together; Ctrl-C stops both
./dev.sh api      # API only
./dev.sh web      # Next.js only
```

The script loads env vars from `api/.env` and `web/.env.local` — no need to source them manually.

**Verify the API is up:**
```bash
curl http://localhost:8000/health
# → {"status":"ok"}
```

**Verify the frontend:** open [http://localhost:3000](http://localhost:3000) in your browser.

---

## Ingest your first transcript

The ingestion pipeline runs on Modal. There are two modes: a local test run that executes in the Modal cloud and streams logs back locally, and a deployed function that the FastAPI admin endpoint can dispatch on demand.

### One-time Modal setup

1. Authenticate: `modal setup` (opens browser)
2. In the [Modal dashboard](https://modal.com/secrets) → **Secrets** → create a secret named **`earnings-secrets`** with these keys:
   - `DATABASE_URL` — your Supabase transaction pooler URI
   - `API_NINJAS_KEY`
   - `VOYAGE_AI_KEY`
   - `ANTHROPIC_API_KEY`

### Local test run

Executes in Modal's cloud, streams logs to your terminal:

```bash
modal run pipeline/ingest.py --ticker AAPL
```

### Deploy and dispatch via API

Required before the FastAPI admin endpoint can trigger ingestion jobs:

```bash
modal deploy pipeline/ingest.py
```

Then trigger ingestion from the API:

```bash
curl -X POST http://localhost:8000/admin/ingest \
  -H "Authorization: Bearer <admin-user-jwt>" \
  -H "Content-Type: application/json" \
  -d '{"ticker": "AAPL"}'
# → {"status":"accepted","ticker":"AAPL","message":"Ingestion dispatched"}
```

---

## Run the tests

```bash
# All unit tests
pytest tests/unit/ -v

# API unit tests only
pytest tests/unit/api/ -v

# With coverage report
pytest --cov=.
```

---

## Architecture orientation

Before making changes, get your bearings:

```
Request → api/routes/       # FastAPI route handlers
              ↓
          services/          # Business logic, orchestration
              ↓
          db/repositories.py # All database access (never bypass this layer)
```

**Key rules:**
- New routes go in `api/routes/`. Do not put business logic in route handlers.
- All database access goes through `db/repositories.py` — no raw psycopg calls elsewhere.
- New domain dataclasses go in `core/models.py`.
- Tests mirror the source tree: `api/routes/calls.py` → `tests/unit/api/test_calls.py`.
- The OpenAPI docs are available at [http://localhost:8000/docs](http://localhost:8000/docs) while the API is running.

**Before touching anything in `web/`:** read [`web/AGENTS.md`](../web/AGENTS.md). This project uses a version of Next.js with breaking API changes — conventions you know from other projects may not apply.

**Branch workflow:** always create a feature branch before making changes. Never commit directly to `main`.

---

## Where to go next

| Task | Where to look |
|---|---|
| Database schema and migration system | [`docs/database.md`](database.md) |
| LLM models, tiers, and endpoints | [`docs/llm_usage.md`](llm_usage.md) |
| Architecture decisions and specs | [`docs/architecture-review/`](architecture-review/00-index.md) |
| Operational runbooks | [`docs/runbooks/`](runbooks/) |
| Legacy CLI / Streamlit (deprecated) | [`docs/legacy-stack.md`](legacy-stack.md) |
