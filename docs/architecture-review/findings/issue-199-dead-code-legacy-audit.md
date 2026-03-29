# Issue #199: Dead Code and Legacy Surface Audit

*Persona: Principal Engineer — codebase audit*
*Date: 2026-03-28*

---

## Summary

The codebase has two fully operational stacks that share the same core pipeline: a legacy Streamlit + CLI layer (`app.py`, `main.py`, `ui/`, `cli/`) and a new FastAPI + Next.js web stack (`api/`, `web/`). The shared pipeline modules (`services/orchestrator.py`, `parsing/`, `ingestion/`, `nlp/embedder.py`, `prompts/`) are actively used by both stacks and must not be deleted. Three modules are effectively dead: `utils/timing.py` has no callers anywhere in the codebase; `ui/data_loaders.py::load_competitors` and `load_recent_news` are defined but never called (the Streamlit layer migrated to background-thread patterns directly in `ui/metadata_panel.py`). The NLP modules `nlp/analysis.py`, `nlp/takeaways.py`, and `nlp/themes.py` are no longer called by the runtime pipeline — they survive only as test targets — which means they represent stranded ML code that the agentic ingestion path superseded.

---

## Component Inventory

| File / Module | Category | Notes |
|---|---|---|
| `app.py` | LEGACY_ONLY | Streamlit entry point; imports entire `ui/` layer |
| `main.py` | LEGACY_ONLY | CLI entry point; imports `cli/` and `services/orchestrator` |
| `cli/menu.py` | LEGACY_ONLY | Interactive CLI menu; calls `services/orchestrator.analyze`, `nlp/embedder`, `services/llm` |
| `cli/display.py` | LEGACY_ONLY | Console display formatter; only called from `main.py` and `cli/menu.py` |
| `ui/metadata_panel.py` | LEGACY_ONLY | Streamlit left-column learning path panel |
| `ui/feynman.py` | LEGACY_ONLY | Streamlit Feynman chat interface |
| `ui/transcript_browser.py` | LEGACY_ONLY | Streamlit searchable transcript component |
| `ui/sidebar.py` | LEGACY_ONLY | Streamlit sidebar with transcript selector |
| `ui/library.py` | LEGACY_ONLY | Streamlit transcript library landing page |
| `ui/data_loaders.py` | LEGACY_ONLY | `@st.cache_data` wrappers; `load_competitors` and `load_recent_news` are dead within this file |
| `ui/term_actions.py` | LEGACY_ONLY | Streamlit Define/Explain button handlers |
| `parsing/loader.py` | SHARED | `read_text_file` and `extract_transcript_text` called by `services/orchestrator.py` and `pipeline/ingest.py` |
| `parsing/sections.py` | SHARED | Core section/speaker extraction; called by `services/orchestrator.py`, `nlp/themes.py`, `nlp/takeaways.py` |
| `parsing/financial_terms.py` | SHARED | CSV-based financial term scanner; called by `ingestion/pipeline.py` |
| `nlp/analysis.py` | UNCLEAR | `clean_text` and `tokenize` called by `services/orchestrator.py`; `STOP_WORDS` used by `nlp/keywords.py` — but `nlp/keywords.py` itself is no longer called by the runtime |
| `nlp/keywords.py` | DEAD | Defines `extract_keywords`; only the `ALL_STOP_WORDS` constant is used (by `nlp/themes.py` and `nlp/takeaways.py`). `extract_keywords` has no callers outside tests |
| `nlp/takeaways.py` | DEAD | TextRank takeaway extraction; not imported by any runtime module (only by `tests/unit/nlp/test_takeaways.py`) |
| `nlp/themes.py` | DEAD | NMF theme extraction; not imported by any runtime module (only by `tests/unit/nlp/test_themes.py`) |
| `nlp/embedder.py` | SHARED | `get_embeddings` called by `services/orchestrator.py`, `ui/feynman.py`, `ui/term_actions.py`, `cli/menu.py`, `db/search.py` |
| `ingestion/pipeline.py` | SHARED | `IngestionPipeline` called from `services/orchestrator.py`; core of the agentic ingestion path |
| `ingestion/prompts.py` | SHARED | System prompts consumed by `services/llm.py` (via `AgenticExtractor`); no direct legacy usage |
| `pipeline/ingest.py` | WEB_ONLY | Modal serverless function; dispatched by `api/routes/admin.py` |
| `prompts/feynman/` | SHARED | All 9 prompt files read by both `ui/feynman.py` (Streamlit) and `api/routes/chat.py` (FastAPI) |
| `prompts/feynman-learning-strategy.md` | UNCLEAR | Markdown strategy doc; not loaded at runtime — likely authoring reference only |
| `utils/timing.py` | DEAD | `measure_execution_time` decorator; no callers anywhere in the codebase |
| `services/orchestrator.py` | SHARED | Core `analyze()` function; called by `main.py`, `cli/menu.py`, `pipeline/ingest.py` |
| `api/routes/calls.py` | WEB_ONLY | FastAPI endpoints for library and transcript data |
| `api/routes/admin.py` | WEB_ONLY | FastAPI admin routes; dispatches to `pipeline/ingest.py` via Modal |
| `api/routes/chat.py` | WEB_ONLY | FastAPI SSE streaming chat endpoint; reads `prompts/feynman/` directly |
| `requirements.txt` | LEGACY_ONLY | Root requirements file includes `streamlit`; Modal pipeline has its own `pipeline/requirements.txt` |

---

## Findings

**[LOW] `utils/timing.py` — Fully Dead Decorator**
File(s): `utils/timing.py`
Category: DEAD
Finding: `measure_execution_time` is a simple wall-clock timing decorator with no callers in the entire codebase. It is not imported by any module other than its own definition file.
Impact: Zero — it's two dozen lines. Keeping it adds minor confusion about whether it should be used.
Dependency note: Safe to delete immediately. No downstream dependencies.

---

**[MEDIUM] `nlp/takeaways.py` and `nlp/themes.py` — Stranded ML Modules**
File(s): `nlp/takeaways.py`, `nlp/themes.py`
Category: DEAD (runtime); tested in isolation
Finding: Both modules implement the original NLP pipeline (TextRank takeaways, NMF theme extraction). The agentic ingestion path in `ingestion/pipeline.py` replaced them. `services/orchestrator.py` no longer calls `extract_takeaways` or `extract_themes` directly — those signals are now produced by Haiku LLM in `Phase 4` of the ingestion pipeline. The only remaining references are the test files `tests/unit/nlp/test_takeaways.py` and `tests/unit/nlp/test_themes.py`.
Impact: These modules represent ~250 lines of ML code with scikit-learn dependencies that no production code path invokes. Their continued presence implies they are part of the active pipeline, which they are not. Engineers spending time on them are wasting effort.
Dependency note: Both import `nlp/keywords.py::ALL_STOP_WORDS` and `parsing/sections.py::TURN_PATTERN`. Deleting `nlp/takeaways.py` and `nlp/themes.py` does not affect the runtime, but you would also need to remove or update their test files. `nlp/keywords.py` itself becomes more obviously dead once these two are gone.

---

**[MEDIUM] `nlp/keywords.py` — `extract_keywords` Function Has No Runtime Callers**
File(s): `nlp/keywords.py`
Category: DEAD (the `extract_keywords` function); `ALL_STOP_WORDS` is still consumed
Finding: `extract_keywords` is not called by `services/orchestrator.py`, `ingestion/pipeline.py`, or any web/CLI entry point. Only `tests/unit/nlp/test_keywords.py` references it. However, `ALL_STOP_WORDS` is still used by `nlp/themes.py` and `nlp/takeaways.py` as a stop-word list.
Impact: If `nlp/themes.py` and `nlp/takeaways.py` are removed, `nlp/keywords.py` becomes fully dead and can also be deleted. Until that happens, the file is partially live through its exported constant.
Dependency note: Delete after `nlp/themes.py` and `nlp/takeaways.py` are removed. Also delete `tests/unit/nlp/test_keywords.py`.

---

**[MEDIUM] `ui/data_loaders.py::load_competitors` and `load_recent_news` — Orphaned Cache Functions**
File(s): `ui/data_loaders.py` (lines 84–114, 164–185)
Category: DEAD (two specific functions within an otherwise LEGACY_ONLY file)
Finding: `load_competitors` and `load_recent_news` are `@st.cache_data`-decorated functions defined in `ui/data_loaders.py` but not called by any module. The Streamlit layer migrated competitors and news fetching to background-thread patterns directly inside `ui/metadata_panel.py` (`_render_competitors_section`, `_render_news_section`). The two cache functions in `data_loaders.py` are now orphaned.
Impact: Dead code inside an active file. The `load_competitors` function also imports `fetch_competitors` and `fetch_recent_news` at module level (lines 26–27), pulling in service-layer dependencies unnecessarily. The comment on line 5 (`# Competitor used by load_competitors return type`) also reveals the file is aware these functions exist but incorrectly frames them as needed.
Dependency note: Safe to delete both functions and their associated imports from `data_loaders.py`. The `Competitor` and `NewsItem` import on line 5 can also be removed once these functions are gone.

---

**[LOW] `nlp/analysis.py` — Partially Consumed; `count_word_frequency` Has No Callers**
File(s): `nlp/analysis.py`
Category: UNCLEAR (partially alive)
Finding: `clean_text` and `tokenize` are called by `services/orchestrator.py` (lines 6, 49). `STOP_WORDS` is exported and used by `nlp/keywords.py`. But `count_word_frequency` is not called anywhere in the runtime.
Impact: Low — two of three public functions are still used. No action needed unless `nlp/keywords.py` is deleted.
Dependency note: If `nlp/keywords.py` is removed, check whether `STOP_WORDS` is still needed; if not, `nlp/analysis.py` can be slimmed to just `clean_text` and `tokenize`.

---

**[HIGH] `requirements.txt` — Root Requirements Include Streamlit and No Pinning**
File(s): `requirements.txt`
Category: LEGACY_ONLY (dependency file maintained for the legacy stack)
Finding: The root `requirements.txt` installs `streamlit>=1.33.0`, which is unused by the FastAPI/Modal web stack. The Modal pipeline uses `pipeline/requirements.txt` instead. The root file appears to serve only the local Streamlit dev workflow.
Impact: Any developer or CI job that installs root `requirements.txt` for the web stack gets Streamlit installed unnecessarily (~20 MB of transitive dependencies). More importantly, the file is unpinned, which creates reproducibility risk as the project matures.
Dependency note: Not safe to delete outright — it is the only requirements file for the Streamlit dev workflow. The right fix is to split it: a `requirements-legacy.txt` for Streamlit/CLI development and a `requirements-web.txt` for the FastAPI stack. This is a migration task, not a deletion task.

---

## Dependency Map

Deletion order matters for the dead NLP modules:

```
1. Delete nlp/takeaways.py        → removes dependency on nlp/keywords.py::ALL_STOP_WORDS
2. Delete nlp/themes.py           → removes dependency on nlp/keywords.py::ALL_STOP_WORDS
3. After (1) and (2): check if nlp/keywords.py is now fully dead
   → if yes, delete nlp/keywords.py
   → then check if nlp/analysis.py::STOP_WORDS is still needed
4. Delete tests/unit/nlp/test_takeaways.py, test_themes.py (after step 1/2)
5. Delete tests/unit/nlp/test_keywords.py (after step 3)
```

`utils/timing.py` has no dependents — can be deleted independently at any time.

`ui/data_loaders.py::load_competitors` and `load_recent_news` can be removed independently of the NLP cleanup.

---

## Recommended Next Steps

**Immediate (safe to do now, no migration required):**
1. Delete `utils/timing.py` — zero dependents, zero risk.
2. Remove `load_competitors` and `load_recent_news` from `ui/data_loaders.py` along with the associated imports on lines 5, 26–27. Update the comment on line 5 to remove the stale reference.

**Short-term (require test updates but no migration):**
3. Delete `nlp/takeaways.py` and its test file.
4. Delete `nlp/themes.py` and its test file.
5. After (3) and (4): delete `nlp/keywords.py` and its test file, confirming `nlp/analysis.py::STOP_WORDS` is no longer referenced.

**Deferred (requires planning, not just deletion):**
6. Decide whether the Streamlit stack (`app.py`, `ui/`, `cli/`) is still intentionally maintained as a local dev tool, or whether it should be retired. If retiring: delete in one PR after confirming the web stack serves all the same use cases. If keeping: document it explicitly in CLAUDE.md as "local dev only, not production."
7. Split `requirements.txt` into `requirements-legacy.txt` (Streamlit/CLI) and `requirements-web.txt` (FastAPI, used by CI/CD and deployment).
8. `main.py`'s `--mode gui` flag launches Streamlit via `subprocess.run(["streamlit", "run", "app.py"])` (line 40). If Streamlit is retired, this entire flag can be removed. If kept, it should be documented.
