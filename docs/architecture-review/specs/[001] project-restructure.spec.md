# S1 — Project Restructure & Core Extraction

*Status: Draft*
*Depends on: Nothing (first spec)*
*Estimated issues: 4-6*

---

## Implementation status

**Status:** Not implemented as specified

**What happened instead:** The FastAPI backend (`api/`) was built directly against the existing top-level module structure. The `nlp/`, `parsing/`, `services/`, `ingestion/`, and `db/` directories were never moved under `core/`. The `core/` package exists but contains only `models.py`.

**Remaining (deferred):**
- Move `nlp/`, `parsing/`, `services/`, `ingestion/` under `core/`
- Move `db/` under `core/db/`
- Rewrite all consumer imports across `api/`, `app.py`, `ui/`, `cli/`, `tests/`
- Delete original top-level module directories

**Note:** The practical goal of this spec — keeping `api/` thin and delegating to business logic modules — was achieved without the physical restructure. The move may still be worth doing for long-term maintainability, but it is not blocking any current work.

---

## Goal

Move all framework-independent business logic into a `core/` package so that both the existing Streamlit app and the new FastAPI backend can import from the same place. At the end of this spec, the Streamlit app and CLI work exactly as before — the only change is where imports come from.

---

## Why this is first

Every subsequent spec (data layer, backend API, frontend) depends on `core/` existing as a clean, importable package. If we start building the FastAPI backend before extracting core logic, we'll either duplicate code or create circular imports.

---

## Scope

### In scope
- Create `core/` package with `__init__.py`
- Move `nlp/`, `parsing/`, `services/`, `ingestion/` under `core/`
- Move `core/models.py` stays in place (already under `core/`)
- Move `db/` under `core/db/`
- Update all imports across `app.py`, `ui/*`, `cli/*`, `main.py`, `tests/*`
- Verify Streamlit, CLI, and all tests still work

### Out of scope
- Refactoring repository classes (that's S2)
- Adding FastAPI (that's S3)
- Changing any business logic

---

## Target structure

```
core/
├── __init__.py
├── models.py                  # Already here — unchanged
├── nlp/
│   ├── __init__.py
│   ├── analysis.py
│   ├── keywords.py
│   ├── themes.py
│   ├── takeaways.py
│   └── embedder.py
├── parsing/
│   ├── __init__.py
│   ├── loader.py
│   ├── sections.py
│   ├── financial_terms.py
│   └── financial-terms.csv
├── services/
│   ├── __init__.py
│   ├── orchestrator.py
│   ├── llm.py
│   ├── company_info.py
│   ├── competitors.py
│   └── recent_news.py
├── ingestion/
│   ├── __init__.py
│   ├── pipeline.py
│   └── prompts.py
└── db/
    ├── __init__.py
    ├── repositories.py
    ├── persistence.py
    ├── search.py
    ├── schema.sql
    └── migrations/
```

---

## Import rewrite rules

| Old import | New import |
|------------|-----------|
| `from nlp.analysis import clean_text` | `from core.nlp.analysis import clean_text` |
| `from parsing.loader import read_text_file` | `from core.parsing.loader import read_text_file` |
| `from services.orchestrator import analyze` | `from core.services.orchestrator import analyze` |
| `from ingestion.pipeline import IngestionPipeline` | `from core.ingestion.pipeline import IngestionPipeline` |
| `from db.repositories import CallRepository` | `from core.db.repositories import CallRepository` |
| `from core.models import CallAnalysis` | `from core.models import CallAnalysis` (unchanged) |

---

## Compatibility shims

To avoid breaking third-party references or scripts during the transition, the original top-level directories (`nlp/`, `parsing/`, etc.) can be replaced with re-export shim files. However, since this is a small project with no external consumers, **we will delete the old directories entirely** and fix all imports in one pass. This is cleaner than maintaining shims.

---

## Verification criteria

- [ ] `streamlit run app.py` launches and all 6 learning path steps render
- [ ] `python3 main.py AAPL --save` runs the full pipeline and persists to DB
- [ ] `pytest` passes with no import errors
- [ ] No top-level `nlp/`, `parsing/`, `services/`, `ingestion/`, or `db/` directories remain (except `__pycache__`)
- [ ] `core/` is a proper Python package (has `__init__.py` at every level)

---

## Risks

| Risk | Mitigation |
|------|------------|
| Circular imports when moving modules | Move all modules atomically in one commit; run tests immediately |
| Relative imports within moved modules break | All internal cross-references use absolute imports (`from core.nlp...`) |
| IDE / editor path caches stale | Delete all `__pycache__` directories after the move |

---

## Issue breakdown

### Epic: Project Restructure & Core Extraction [001]

| Sub-issue | Title | Description | Depends on |
|-----------|-------|-------------|------------|
| `[001.1]` | Create `core/` package structure | Create directory tree with `__init__.py` files | — |
| `[001.2]` | Move `nlp/` and `parsing/` into `core/` | Move pure-function modules, update their internal imports | 001.1 |
| `[001.3]` | Move `services/` and `ingestion/` into `core/` | Move service modules, update internal imports | 001.1 |
| `[001.4]` | Move `db/` into `core/db/` | Move data layer, update internal imports | 001.1 |
| `[001.5]` | Update all consumer imports | Rewrite imports in `app.py`, `ui/*`, `cli/*`, `main.py`, `migrate.py` | 001.2, 001.3, 001.4 |
| `[001.6]` | Update test imports and verify | Rewrite test imports, run full test suite, delete old directories | 001.5 |

> 001.2 through 001.4 can be worked in parallel. 001.5 and 001.6 must wait until all moves are complete. Issues 001.1–001.4 could also be combined into a single PR if preferred — the key constraint is that the test suite must pass after each merge.

See [conventions.md](../conventions.md) for epic/sub-issue naming and workflow.
