# Issue #200: Type Coverage and Code Quality Gaps

*Persona: Python Type Safety Specialist*
*Date: 2026-03-28*

## Summary

The FastAPI route layer has solid Pydantic model coverage for GET endpoints in `calls.py` but is entirely untyped at the HTTP boundary for all admin analytics routes and the chat streaming endpoint. The repository layer correctly annotates most return types using typed tuples, but two important methods (`get_call_date` and `_save_speakers`, `_save_spans`) lack return type annotations or use unparameterized types. There is no `mypy`, `pyright`, or any static type checker configured at the project root, meaning these gaps are invisible to CI. The mixed use of plain `dataclass` and Pydantic `BaseModel` in `core/models.py` is the root cause of repeated positional-index unpacking in route handlers — a pattern that scales poorly and is error-prone.

---

## Findings

---

**[HIGH] Admin analytics routes return bare `dict` — no response_model, no typed shape**
File(s): `api/routes/admin.py:45`, `api/routes/admin.py:86`, `api/routes/admin.py:104`, `api/routes/admin.py:139`, `api/routes/admin.py:165`, `api/routes/admin.py:184`, `api/routes/admin.py:206`
Finding: Every admin endpoint declares `-> dict` or `-> list[dict]` with no `response_model`. FastAPI cannot generate OpenAPI schemas for untyped dicts. The actual shapes (e.g. `{"date": str, "count": int}`, `{"by_service": dict}`) exist only as DB cursor unpacking in route bodies.
Impact: OpenAPI docs omit these endpoints' response schemas entirely. Any consumer (a future frontend or integration test) has no machine-readable contract. Downstream breakage from DB column changes is silent — no type checker will catch it.

---

**[HIGH] `chat` endpoint missing `response_model` and return type annotation on the SSE wrapper**
File(s): `api/routes/chat.py:172`
Finding: `def chat(...) -> StreamingResponse` has no `response_model`. More importantly, the `_sse_stream` generator at line 110 has no return type annotation at all — the function signature ends with `):\` with no `->`.
Impact: The generator's yield types are invisible to tooling. The `StreamingResponse` return is correct behaviour, but FastAPI's `response_model` omission means the OpenAPI spec shows a blank response body for this endpoint. The missing return annotation on `_sse_stream` also prevents any future type-narrowing of the `str | dict` union it yields.

---

**[HIGH] `CallSynthesisRecord.strategic_shifts` typed as `list[dict]` — dict shape is undeclared**
File(s): `core/models.py:207`
Finding: `strategic_shifts: list[dict]` carries no inner type. The actual shape `{"prior_position": str, "current_position": str, "investor_significance": str}` is known (it mirrors `StrategicShift` in `calls.py`), but is not expressed in the model.
Impact: Every call site that reads `strategic_shifts` must either trust the dict shape by convention or re-validate it. `calls.py:154` does both — it calls `.get()` with default strings, which papers over the gap but makes the schema contract invisible. If the LLM changes key names, the failure is silent.

---

**[HIGH] Repository private helpers `_save_speakers` and `_save_spans` are untyped**
File(s): `db/repositories.py:680`, `db/repositories.py:695`
Finding: `_save_speakers(self, cur, call_id, speakers)` and `_save_spans(self, cur, call_id, spans, takeaways, speaker_ids)` have no parameter or return type annotations. `cur` is a raw psycopg cursor, `speakers` is a `list[SpeakerProfile]`, `spans` is `list[SpanRecord]`.
Impact: These write the two most business-critical tables (speakers and spans). Without annotations, mypy cannot verify that callers pass the right types, and refactoring the `SpanRecord` or `SpeakerProfile` shapes will not produce type errors here.

---

**[MEDIUM] `get_call_date` has no return type annotation**
File(s): `db/repositories.py:80`
Finding: `def get_call_date(self, ticker: str):` — the return type is omitted. The function returns either `row[0]` (a `datetime.date` or `str` depending on psycopg's type mapping) or `None`.
Impact: The caller at `calls.py:138` assigns `call_date = call_repo.get_call_date(ticker)` and immediately does `str(call_date) if call_date else None`. Without a declared return type, mypy treats this as `Any`, suppressing any type narrowing on `call_date`.

---

**[MEDIUM] `stream_chat` has no return type — yields `str | dict` without declaring it**
File(s): `services/llm.py:31`
Finding: `def stream_chat(messages: list[dict], system_prompt: str, model: str = "sonar-pro"):` — no `->` annotation. The generator yields both `str` chunks and a single `dict` usage event.
Impact: The caller in `chat.py:126` uses `isinstance` checks to branch on the yield type, which is correct, but without an annotated return type of `Generator[str | dict, None, None]` the type checker cannot verify the isinstance branches are exhaustive, and cannot warn if a new yield type is added.

---

**[MEDIUM] `AgenticExtractor` methods return `Dict[str, Any]` — shape not narrowed at call sites**
File(s): `services/llm.py:187`, `services/llm.py:219`, `services/llm.py:239`, `services/llm.py:258`, `services/llm.py:277`, `services/llm.py:296`
Finding: `_parse_response`, `extract_tier1`, `extract_tier2`, `extract_synthesis`, `extract_nlp_synthesis`, and `detect_qa_transition` all return `Dict[str, Any]`. The old-style `Dict` and `Any` imports from `typing` (line 8) are also present alongside modern `dict[str, Any]` usage.
Impact: All downstream consumers of these methods (in `ingestion/pipeline.py`) must key into untyped dicts. Structural changes to LLM output JSON will not be caught statically. The mixed `Dict`/`dict` usage across the file is also inconsistent with Python 3.10+ style.

---

**[MEDIUM] `core/models.py` mixes plain `dataclass` and Pydantic `BaseModel` without a clear policy**
File(s): `core/models.py:91-257`
Finding: `CallRecord`, `SpanRecord`, `KeywordRecord`, `TopicRecord`, `QAPairRecord`, `NewsItem`, `Competitor`, `CallSynthesisRecord`, `CallAnalysis` are plain `dataclass` instances. Only `TranscriptChunk` is a Pydantic `BaseModel`. The import at line 84 brings in Pydantic alongside `dataclasses`.
Impact: Plain dataclasses provide no runtime validation, no serialization helpers, and no JSON schema generation. The repository layer and route layer must unpack and repack these objects manually. If domain models were Pydantic v2 models, routes could pass them directly to `response_model` without hand-written mapping code.
Dependency note: Migrating to Pydantic v2 models in `core/models.py` is a prerequisite for eliminating the positional-index unpacking in `calls.py` and for giving admin routes typed response schemas.

---

**[MEDIUM] Route handlers unpack DB rows by positional index rather than named attributes**
File(s): `api/routes/calls.py:113-119`, `calls.py:143-148`, `calls.py:162-168`, `calls.py:172`
Finding: `r[0]`, `r[1]`, `r[2]`, `r[3]` are used throughout `get_call` and `list_calls` to construct Pydantic models from raw DB tuples. The column order in the SQL query is the only contract — there is no name binding.
Impact: A column reorder in a SQL query (or a new column added mid-SELECT) silently produces wrong data with no type error. This is a direct consequence of the repository returning `list[tuple[...]]` rather than converting to named models before returning.

---

**[LOW] No `mypy` or `pyright` configuration exists at the project root**
File(s): project root (no `mypy.ini`, no `[tool.mypy]` in `pyproject.toml`, no `pyrightconfig.json`)
Finding: There is no type checker installed or configured for this project. The `.venv` contains numpy's own `mypy.ini` but nothing at the application level.
Impact: All the type gaps above are invisible to CI. Adding mypy is feasible: the FastAPI routes, dependencies, and most repository methods already have annotations. The primary pain points on first run will be the `Dict[str, Any]` returns in `services/llm.py` and the unparameterized `list[tuple]` returns from the repository — both addressable incrementally.

---

## Dependency Map

The findings above form a resolution order:

1. **`core/models.py` first** — migrate domain models from `dataclass` to Pydantic v2 `BaseModel`. This unlocks items 2, 3, and 4 without requiring route changes upfront.
2. **Repository typed return shapes** — once domain models are Pydantic, repository `get_*` methods can return model instances instead of raw tuples. This resolves the positional-index unpacking in routes.
3. **Admin route response models** — once the repository returns typed models, admin analytics endpoints can declare `response_model` with concrete Pydantic schemas.
4. **`stream_chat` and `_sse_stream` generator types** — add `-> Generator[str | dict[str, Any], None, None]` to both. Independent of the above.
5. **`mypy` configuration last** — add `pyproject.toml` with `[tool.mypy]` once the above gaps are closed enough to get a clean first run. Start with `--ignore-missing-imports` and `--no-strict-optional` to baseline, then tighten incrementally.

---

## Recommended Next Steps

1. **Add a `pyproject.toml` with a minimal mypy config** and run `mypy api/ db/repositories.py services/llm.py core/models.py` to get a baseline error count. Even without fixing anything, this makes gaps visible to CI and prevents regression.

2. **Migrate `core/models.py` domain records to Pydantic v2 `BaseModel`** (highest leverage). Start with `CallRecord`, `SpanRecord`, and `CallSynthesisRecord` — these are the models that flow through the most route handlers. `frozen=True` models are a good default for read-side records.

3. **Add `response_model` to all admin analytics endpoints** in `api/routes/admin.py`. Each endpoint has a stable, small shape — define one Pydantic model per endpoint and the OpenAPI spec becomes accurate immediately.

4. **Type the `stream_chat` generator** in `services/llm.py:31` and the `_sse_stream` generator in `api/routes/chat.py:110`. These are two-line annotation additions with no behaviour change.

5. **Annotate `_save_speakers` and `_save_spans`** parameter types in `db/repositories.py:680,695`. These are write-path methods for the two most important tables; catching type mismatches here is high value.

6. **Replace `Dict[str, Any]` returns on `AgenticExtractor` methods** with `TypedDict` definitions for each LLM output shape. This is lower priority than items 1–5 but eliminates the last class of invisible breakage in the ingestion pipeline.
