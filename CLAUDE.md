# CLAUDE.md — Earnings Transcript Teacher

This file is read automatically by Claude Code at the start of every session. It describes the project and the conventions Claude should follow when working here.

---

## Project overview

**Earnings Transcript Teacher** is a Python pipeline that parses financial earnings call transcripts and teaches their content interactively.

Primary stack: **FastAPI** (`api/`) + **Next.js** (`web/`) + **Supabase** (database + auth) + **Modal** (`pipeline/`)

> The original console CLI (`main.py`) and Streamlit web UI (`app.py`) are **deprecated**. They remain runnable for reference but receive no new features. Do not target them for new development work.

Core pipeline: `parsing/` → `nlp/` → `services/orchestrator.py` → `db/`

Tests: `pytest` (test suite in `tests/`).

---

## How to run

```bash
# New stack (primary)
./dev.sh              # API (localhost:8000) + Next.js (localhost:3000) together
./dev.sh api          # FastAPI only
./dev.sh web          # Next.js only

# Tests
pytest
pytest --cov=.

# Deprecated — do not use for new work
python3 main.py       # legacy console UI
streamlit run app.py  # legacy Streamlit UI
```

See [`docs/getting-started.md`](docs/getting-started.md) for the full setup walkthrough.

---

## Code conventions

### Language and style
- **Python 3.12**
- Follow **PEP 8**: 4-space indentation, snake_case names, max line length ~100 chars.
- Add **type hints** on all new function signatures (e.g., `def foo(x: str) -> list[str]:`).
- Add a **one-line docstring** to every new function or class explaining what it does.
- Prefer **explicit over implicit**: clear variable names over terse ones.

### Architecture rules
- Keep modules single-responsibility. NLP logic belongs in `nlp/`, DB logic in `db/`, etc.
- Do not import from `cli/` or `app.py` in core pipeline modules — those are output layers only.
- Database access goes through `db/repositories.py`, not via raw psycopg calls scattered elsewhere.
- New dataclasses should go in `core/models.py`.

### New stack conventions (FastAPI + Next.js + Modal)

**FastAPI:**
- New routes go in `api/routes/`. Keep route handlers thin — call into `services/` for business logic.
- Return structured JSON errors with appropriate HTTP status codes. Follow the pattern used in existing route handlers.
- All database access goes through `db/repositories.py`. Never make raw psycopg calls from route handlers or services.
- The `api/settings.py` `REQUIRED_ENV_VARS` list controls which env vars are validated at startup — the API returns 503 for all requests if any are missing.

**Next.js (`web/`):**
- **Read [`web/AGENTS.md`](web/AGENTS.md) before writing any code in `web/`.** This project uses a version of Next.js with breaking API changes — conventions from other projects may not apply.
- Environment variables for the frontend live in `web/.env.local` (see `web/env.example`).

**Modal pipeline (`pipeline/`):**
- Ingestion functions use the `@app.function` decorator. Module-level code runs in the container context — avoid side effects at import time.
- Secrets are injected via the `earnings-secrets` Modal secret (not from `api/.env`).

### Testing
- Use **pytest** for all tests.
- Unit tests go in `tests/unit/`, integration tests in `tests/integration/`.
- Mirror the source tree: tests for `api/routes/calls.py` → `tests/unit/api/test_calls.py`.
- When adding a new function, add at least one test for the happy path.

---

## How Claude should behave when editing this repo

- **Make small, focused diffs.** One logical change per edit. Don't clean up surrounding code unless asked.
- **Always read a file before editing it.** Never propose changes to code you haven't seen.
- **Prefer editing existing files** over creating new ones.
- **Ask before making architectural changes** (e.g., renaming modules, restructuring packages).
- **Don't add error handling for impossible cases.** Only validate at real boundaries (user input, external API calls).
- **No docstrings or comments on code you didn't touch.**
- **Keep `README.md` up to date.** When adding or changing user-facing features, setup steps, CLI flags, environment variables, or architecture, update the README in the same session.

---

## Key dependencies

| Package | Purpose |
|---|---|
| `fastapi` | API framework (new stack) |
| `scikit-learn` | TF-IDF, NMF, cosine similarity |
| `psycopg[binary]` | PostgreSQL driver |
| `voyageai` | Semantic embeddings (`voyage-finance-2`) |
| `pgvector` | Vector similarity search in Postgres |
| `perplexityai` | Feynman learning chat (streaming) |
| `pytest` | Test runner |

---

## Environment variables

The canonical reference is `api/.env.example` (with inline comments). Key required variables:

```
DATABASE_URL          # PostgreSQL connection string (Supabase transaction pooler, port 6543)
SUPABASE_URL          # Supabase project URL — used to verify JWTs
VOYAGE_API_KEY        # Semantic embeddings (/search endpoint)
PERPLEXITY_API_KEY    # Feynman chat endpoint
ANTHROPIC_API_KEY     # LLM ingestion pipeline
API_NINJAS_KEY        # Transcript download
MODAL_TOKEN_ID        # Required at startup — generate with `modal token new`
LOG_LEVEL             # Optional (default: INFO)
```

---

## Session naming suggestions

Name Claude Code sessions descriptively so you can find them later:
- `feat: add X feature` — for new features
- `fix: describe the bug` — for bug fixes
- `refactor: module name` — for refactoring work
- `test: module name` — for writing tests
- `docs: readme/cleanup` — for documentation

Each session should have a **single, well-scoped goal**. If a conversation grows large (500+ lines), start a new session for the next feature.

---

## Commit and PR message conventions

- Do **not** add `Co-Authored-By` trailers or any other attribution to Claude in commit or PR messages.
