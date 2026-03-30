# CLAUDE.md — Earnings Transcript Teacher

This file is read automatically by Claude Code at the start of every session. It describes the project and the conventions Claude should follow when working here.

---

## Project overview

**Earnings Transcript Teacher** is a Python pipeline that parses financial earnings call transcripts and teaches their content interactively.

Two interfaces:
- **Console UI** — `main.py` (entry point) + `cli/` (display, interactive menu)
- **Web UI** — `app.py` (Streamlit; run with `streamlit run app.py`)

Core pipeline: `parsing/` → `nlp/` → `services/orchestrator.py` → `db/`

Tests: `pytest` (test suite in `tests/`).

---

## How to run

```bash
# Console (interactive menu)
python3 main.py

# Console (direct analysis)
python3 main.py AAPL --save

# Web UI
streamlit run app.py

# Tests
pytest
pytest --cov=.
```

---

## Code conventions

### Language and style
- **Python 3.10+**
- Follow **PEP 8**: 4-space indentation, snake_case names, max line length ~100 chars.
- Add **type hints** on all new function signatures (e.g., `def foo(x: str) -> list[str]:`).
- Add a **one-line docstring** to every new function or class explaining what it does.
- Prefer **explicit over implicit**: clear variable names over terse ones.

### Architecture rules
- Keep modules single-responsibility. NLP logic belongs in `nlp/`, DB logic in `db/`, etc.
- Do not import from `cli/` or `app.py` in core pipeline modules — those are output layers only.
- Database access goes through `db/repositories.py`, not via raw psycopg calls scattered elsewhere.
- New dataclasses should go in `core/models.py`.

### Testing
- Use **pytest** for all tests.
- Unit tests go in `tests/unit/`, integration tests in `tests/integration/`.
- Mirror the source tree: tests for `nlp/keywords.py` → `tests/unit/nlp/test_keywords.py`.
- When adding a new function, add at least one test for the happy path.

---

## How Claude should behave when editing this repo

- **Make small, focused diffs.** One logical change per edit. Don't clean up surrounding code unless asked.
- **Explain each change** in plain language — the owner is experienced in software engineering but new to Python.
- **Always read a file before editing it.** Never propose changes to code you haven't seen.
- **Prefer editing existing files** over creating new ones.
- **Ask before making architectural changes** (e.g., renaming modules, restructuring packages).
- **Don't add error handling for impossible cases.** Only validate at real boundaries (user input, external API calls).
- **No docstrings or comments on code you didn't touch.**
- **Keep `README.md` up to date.** When adding or changing user-facing features, setup steps, CLI flags, environment variables, or architecture, update the README in the same session. Don't leave it describing a state that no longer exists.

---

## Key dependencies

| Package | Purpose |
|---|---|
| `scikit-learn` | TF-IDF, NMF, cosine similarity |
| `psycopg[binary]` | PostgreSQL driver |
| `voyageai` | Semantic embeddings (`voyage-finance-2`) |
| `pgvector` | Vector similarity search in Postgres |
| `perplexityai` | Feynman learning chat (streaming) |
| `streamlit` | Web UI framework |
| `pytest` | Test runner |

---

## Environment variables required

```
API_NINJAS_KEY        # transcript download
VOYAGE_API_KEY        # semantic embeddings
PERPLEXITY_API_KEY    # Feynman chat
DATABASE_URL          # optional (default: dbname=earnings_teacher)
ANTHROPIC_API_KEY     # optional (Claude-based ingestion tiers)
LOG_LEVEL             # optional (default: INFO); controls log verbosity
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
