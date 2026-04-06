# CLAUDE.md — Earnings Transcript Teacher

This file is read automatically by Claude Code at the start of every session. It describes the project and the conventions Claude should follow when working here.

---

## Project overview

**Earnings Transcript Teacher** is a Python pipeline that parses financial earnings call transcripts and teaches their content interactively.

Primary stack: **FastAPI** (`api/`) + **Next.js** (`web/`) + **Supabase** (database + auth) + **Modal** (`pipeline/`)

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
- Database access goes through `db/repositories.py`, not via raw psycopg calls scattered elsewhere.
- New dataclasses should go in `core/models.py`.

### New stack conventions (FastAPI + Next.js + Modal)

**FastAPI:**
- New routes go in `api/routes/`. Keep route handlers thin — delegate business logic to service helpers; delegate data access to repository classes.
- **Dependency injection:** use the type aliases defined in `api/dependencies.py` — `DbDep`, `CurrentUserDep`, `RequireAdminDep`. Do not call `psycopg.connect()` or validate JWTs inline in route handlers.
- **Error responses:** raise `HTTPException(status_code=..., detail="...")` for client errors (4xx). The app-level handler in `api/main.py` already catches unhandled exceptions and returns `{"error": "Internal server error"}` — do not duplicate this.
- **Response models:** define a Pydantic `BaseModel` for every response shape. Compose with nested models for complex structures. Use `list[Model]` for collections and add `total`/`page`/`page_size` fields for paginated responses.
- All database access goes through repository classes. Never make raw psycopg calls from route handlers or services.
- The `api/settings.py` `REQUIRED_ENV_VARS` list controls which env vars are validated at startup — the API returns 503 for all requests if any are missing.

**Next.js (`web/`):**
- **Read [`web/AGENTS.md`](web/AGENTS.md) before writing any code in `web/`.** This project uses a version of Next.js with breaking API changes — conventions from other projects may not apply.
- **Server vs client components:** server components are the default (`page.tsx`, `layout.tsx`). Add `"use client"` only for components that need browser APIs, React hooks, or event handlers.
- **Data fetching:** server components fetch directly via `createSupabaseServerClient()` or the backend API with `fetch(..., { next: { revalidate: N } })`. Client components call the typed `web/lib/api.ts` wrapper (`api.get<T>()`, `api.post<T>()`, etc.) which injects the Supabase auth token automatically — do not call `fetch()` directly from client components.
- **Props typing:** every component must declare a named `interface ComponentNameProps`. Callbacks must be explicitly typed (e.g., `onSelect: (id: string) => void`).
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
- `api: route or service name` — for FastAPI route and service work
- `web: component or page name` — for Next.js component and page work

Each session should have a **single, well-scoped goal**. If a conversation grows large (500+ lines), start a new session for the next feature.

---

## Prompt versioning

Prompt constants for the ingestion pipeline live in `ingestion/prompts.py`. Experimental variants go in `ingestion/prompts_candidates.py` (never imported by the pipeline). Git history is the version record — no database, no version numbers in filenames.

See `docs/prompt-versioning.md` for the full conventions including naming, promotion workflow, and commit message format.

Use `tools/prompt_tuner.py` to run a side-by-side comparison of production vs. candidate prompts and measure improvement on `tools/eval/dataset.json` before promoting anything.

---

## Feature flag conventions

Feature flags are stored in `public.feature_flags` and managed via `/admin/flags`.

**Kill switches** (category `kill_switch`): default to `True` — the system works normally without the flag row. Create the row and set `enabled = false` to disable the feature. Check with `get_flag_provider().is_enabled("key", default=True)`.

**Feature gates** (category `feature`): default to `False` — disabled until explicitly enabled. Check with `get_flag_provider().is_enabled("key", default=False)`.

Active kill switches and where they are enforced:

| Flag | Enforced in | Effect when `false` |
|---|---|---|
| `chat_enabled` | `api/routes/chat.py`, `web/app/calls/[ticker]/learn/page.tsx` | 503 from API; disabled message in UI |
| `ingestion_enabled` | `api/routes/admin.py` (`trigger_ingestion`), `web/app/admin/ingest/page.tsx` | 503 from API; form disabled in UI |

---

## Gstack (browser & QA skills)

Use `/browse` from gstack for **all web browsing** tasks. Never use `mcp__claude-in-chrome__*` tools.

Available gstack skills: `/office-hours`, `/plan-ceo-review`, `/plan-eng-review`, `/plan-design-review`, `/design-consultation`, `/design-shotgun`, `/design-html`, `/review`, `/ship`, `/land-and-deploy`, `/canary`, `/benchmark`, `/browse`, `/connect-chrome`, `/qa`, `/qa-only`, `/design-review`, `/setup-browser-cookies`, `/setup-deploy`, `/retro`, `/investigate`, `/document-release`, `/codex`, `/cso`, `/autoplan`, `/plan-devex-review`, `/devex-review`, `/careful`, `/freeze`, `/guard`, `/unfreeze`, `/gstack-upgrade`, `/learn`.

---

## Commit and PR message conventions

- Do **not** add `Co-Authored-By` trailers or any other attribution to Claude in commit or PR messages.

---

## Skill routing

When the user's request matches an available skill, ALWAYS invoke it using the Skill
tool as your FIRST action. Do NOT answer directly, do NOT use other tools first.
The skill has specialized workflows that produce better results than ad-hoc answers.

Key routing rules:
- Product ideas, "is this worth building", brainstorming → invoke office-hours
- Bugs, errors, "why is this broken", 500 errors → invoke investigate
- Ship, deploy, push, create PR → invoke ship
- QA, test the site, find bugs → invoke qa
- Code review, check my diff → invoke review
- Update docs after shipping → invoke document-release
- Weekly retro → invoke retro
- Design system, brand → invoke design-consultation
- Visual audit, design polish → invoke design-review
- Architecture review → invoke plan-eng-review
- Save progress, checkpoint, resume → invoke checkpoint
- Code quality, health check → invoke health
