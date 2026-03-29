# Issue #198: Repository Layer and Service Organization

*Persona: Senior Python Engineer*
*Date: 2026-03-28*

## Summary

The repository layer is structurally sound — all classes follow a consistent conn_str pattern, methods stay close to raw data access, and there is no business logic leaking into repositories. The main liabilities are: (1) `db/repositories.py` has grown to 1,229 lines across eight classes with no sign of slowing, making it a merge-conflict magnet and a difficult file to navigate; (2) the API layer has bypassed the repository pattern entirely in several places, writing raw psycopg queries inline in route handlers; and (3) there is no connection pooling anywhere — every method opens and closes a fresh TCP connection to Postgres, which will become a scalability ceiling as concurrent request volume grows. None of these are emergencies today, but the connection-per-call pattern and the raw SQL in routes will both require structural changes before the system handles meaningful user load.

---

## Findings

**[HIGH] No connection pooling — every method opens a new TCP connection**
File(s): `db/repositories.py:37`, `db/repositories.py:67`, `db/repositories.py:83`, `api/dependencies.py:28-35`, `db/analytics.py:17`
Finding: Every repository method calls `psycopg.connect(self.conn_str)` as a context manager, opening and closing a connection per call. `api/dependencies.py:get_db()` does the same for FastAPI-injected connections. `db/analytics.py:_insert_event` opens its own connection per event in a background thread. There is no use of `psycopg_pool` or any other pooling mechanism anywhere in the codebase.
Impact: Under concurrent load each request makes several serial repository calls, each paying the TCP handshake + TLS + auth round-trip to Supabase. Supabase also enforces a hard connection limit per plan tier. At moderate concurrency (10–20 simultaneous users) this pattern will exhaust the pool and produce connection-refused errors. The analytics background threads compound this: each `track()` call spawns a daemon thread that opens its own connection, creating an unbounded number of short-lived connections under chat load.

**[HIGH] Raw SQL queries written directly in route handlers, bypassing the repository layer**
File(s): `api/routes/calls.py:15-25`, `api/routes/calls.py:107-121`, `api/routes/calls.py:204-232`, `api/routes/chat.py:41-47`, `api/routes/chat.py:54-71`, `api/routes/chat.py:74-107`, `api/routes/admin.py:88-100`, `api/routes/admin.py:104-135`, `api/routes/admin.py:139-161`, `api/routes/admin.py:165-180`, `api/routes/admin.py:184-202`
Finding: Multiple route files contain inline `psycopg.connect()` calls with hand-written SQL that duplicates or should belong to a repository. The most notable cases: `calls.py:_ticker_exists` and `calls.py:list_calls` (lines 15–121) bypass `CallRepository` entirely. `chat.py:_ticker_exists`, `chat.py:_load_session`, and `chat.py:_upsert_session` (lines 41–107) duplicate logic that already exists in `LearningRepository.get_session_by_id` and `LearningRepository.save_session`. The `admin.py` analytics endpoints (lines 88–202) contain five separate inline queries against `analytics_events` that have no repository home.
Impact: The same SQL for ticker existence is duplicated in at least three files (`calls.py:20-25`, `chat.py:43-46`, `AnalysisRepository` methods). Schema changes require hunting multiple locations. `chat.py:_upsert_session` (lines 74–107) constructs the same `INSERT ... ON CONFLICT` that `LearningRepository.save_session` (repositories.py:1008–1016) already has — the two are nearly identical but not identical, meaning they can silently diverge.

**[HIGH] `LearningRepository.save_session` contains business logic inside the repository**
File(s): `db/repositories.py:986-1036`
Finding: `save_session` does more than persist data. Lines 1019–1031 implement a business rule: "if the session is completed, find the most recent stage-5 assistant message and write a concept exercise row." The message-scanning loop (`next(m["content"] for m in reversed(messages) if m.get("role") == "assistant" and m.get("feynman_stage") == 5)`) is domain logic about the Feynman learning model embedded inside a storage method. Additionally, the `json.dumps` call at line 1006 serialises the entire message list into the `notes` column as a blob, which is a storage-format decision, not data access.
Impact: The business rule about when to create a concept exercise and what constitutes a "completed" Feynman session is invisible to anyone reading the service layer. Tests for this rule must go through the repository, requiring a real (or heavily mocked) database. Future Feynman logic changes will not obviously require touching `repositories.py`.

**[MEDIUM] `AnalysisRepository.get_strategic_shifts_for_ticker` performs data normalisation/migration logic**
File(s): `db/repositories.py:230-257`
Finding: Lines 248–253 contain a data migration guard: `if isinstance(item, dict): ... else: shifts.append({"prior_position": "", "current_position": str(item), "investor_significance": ""})`. The comment notes "old TEXT[] rows may have been migrated." This compatibility shim for a previous schema version is now a permanent fixture of the read path. Repositories should return what is in the database; shape normalisation for callers is a service-layer concern.
Impact: The schema migration debt is now encoded in application read logic. If the old rows are cleaned up in a future migration, this guard cannot be safely removed without cross-referencing the migration history. It will sit here indefinitely, confusing future maintainers.

**[MEDIUM] `db/repositories.py` is a maintenance liability at 1,229 lines with eight classes**
File(s): `db/repositories.py:1-1229`
Finding: The file contains eight distinct repository classes: `SchemaRepository`, `CallRepository`, `EmbeddingRepository`, `AnalysisRepository`, `CompetitorRepository`, `LearningRepository`, `ProgressRepository`, and a module-level `reset_all_data` function. `AnalysisRepository` alone spans lines 164–866 (702 lines, 28+ methods), making it the largest class by far. The file is already past the 800-line maximum recommended in project coding standards.
Impact: Any two developers touching different repository classes in parallel will produce git conflicts. Navigation requires scrolling through hundreds of lines. The `AnalysisRepository` split is the highest priority because it is growing fastest — each new data extraction feature adds read methods there.
Proposed splitting strategy (minimises churn):
- `db/repositories/call_repo.py` — `CallRepository` (lines 60–112)
- `db/repositories/embedding_repo.py` — `EmbeddingRepository` (lines 114–162)
- `db/repositories/analysis_repo.py` — `AnalysisRepository` (lines 164–866)
- `db/repositories/competitor_repo.py` — `CompetitorRepository` (lines 871–968)
- `db/repositories/learning_repo.py` — `LearningRepository` (lines 974–1162)
- `db/repositories/progress_repo.py` — `ProgressRepository` (lines 1164–1229)
- `db/repositories/schema_repo.py` — `SchemaRepository` + `OutdatedSchemaError` + `reset_all_data` (lines 1–57)
- `db/repositories/__init__.py` — re-exports all public names to preserve existing import paths

**[MEDIUM] `chat.py:_upsert_session` and `LearningRepository.save_session` are near-duplicates that can silently diverge**
File(s): `api/routes/chat.py:74-107`, `db/repositories.py:986-1036`
Finding: Both implement `INSERT INTO learning_sessions ... ON CONFLICT (id) DO UPDATE`. The route-level function uses `%s::uuid` for `call_id` (line 97) while the repository uses `%s` (line 1012). The route function does not write a concept exercise on completion; the repository does. If either is modified without the other, the system's session persistence behaviour becomes inconsistent depending on which code path was invoked.
Impact: Whoever adds the next feature to Feynman sessions will need to update two places and may not realise it. This is the most immediate source of subtle bugs.

**[MEDIUM] `db/persistence.py` is a dead-weight shim that serves no purpose**
File(s): `db/persistence.py:1-99`
Finding: Every function in `persistence.py` is a one-liner wrapper that instantiates a repository and delegates immediately. The file's own docstring says "Persistence wrapper to maintain API compatibility during refactoring." The refactoring it was preserving compatibility for appears to be complete — the API routes now import directly from `db.repositories`. The shim adds an indirection layer with no value: callers who use it must pass `conn_str` as the first argument, which is a different calling convention from the repository classes themselves.
Impact: New developers must decide whether to use `db.persistence` or `db.repositories` directly, and may use the wrong one. The two calling conventions (free functions with `conn_str` first vs. repository instances) make the codebase harder to grep and refactor.

**[MEDIUM] `api/dependencies.py:get_db` yields a connection but repositories do not accept it**
File(s): `api/dependencies.py:28-35`, `api/routes/calls.py:133-135`
Finding: FastAPI has a proper dependency injection mechanism for database connections (`get_db` yields a `psycopg.Connection`), and `DbDep` is defined at line 76. However, `calls.py:get_call` instantiates `CallRepository(db_url)` and `AnalysisRepository(db_url)` directly using the raw URL string (lines 133–135), creating new connections inside the repository, rather than injecting the already-open request-scoped connection. The `DbDep` injection is used in `admin.py` for raw queries but not for repository construction.
Impact: The dependency injection system is present but the repositories don't participate in it. A request to `GET /api/calls/{ticker}` opens at least 7 distinct database connections (one in `_ticker_exists`, one per repository method call in `get_call`). If repositories accepted an injected connection, the request could use one connection for all its data access.

**[LOW] `_ticker_exists` is duplicated verbatim in `calls.py` and `chat.py`**
File(s): `api/routes/calls.py:20-25`, `api/routes/chat.py:41-46`
Finding: Identical private functions in two modules. Each opens its own connection.
Impact: Low risk today, but any change to the ticker existence check (e.g. adding soft-delete support) requires updating both.

**[LOW] `db/search.py` is a standalone CLI script with no relation to the repository layer**
File(s): `db/search.py:1-77`
Finding: This file adds `sys.path` manipulation at the top (line 8), uses `if __name__ == "__main__"` as an entry point, and contains a `semantic_search` function that duplicates vector search logic already in `EmbeddingRepository.search_spans`. It lives in `db/` but does not use any repository class.
Impact: Not a runtime risk, but the duplication means vector search SQL exists in two places. If the schema changes (table aliases, vector column name), `db/search.py` will break silently since it is not exercised by the test suite through normal code paths.

**[LOW] `CompetitorRepository.get` applies TTL business logic inside the repository**
File(s): `db/repositories.py:883-922`
Finding: Lines 908–912 check whether cached competitors have expired and return an empty list if so. The TTL decision (`_COMPETITOR_CACHE_TTL_DAYS = 30`, defined at line 868) is a business rule — "competitors are valid for 30 days" — embedded in the read method. The repository is making the expiry decision rather than returning the data and letting the service layer decide.
Impact: The TTL constant and the expiry check are invisible to callers who might want to override the policy (e.g. force-refresh on demand). The `delete` method already exists as the "force invalidate" mechanism, but it requires the caller to know that getting an empty list means "expired" vs. "no competitors stored."

---

## Dependency Map

Fix order within this issue:

1. **Connection pooling** (HIGH) — prerequisite for production traffic; independent of all other changes
2. **Repository split** (MEDIUM) — reduces merge-conflict risk; do this before adding more repository methods; independent of pooling
3. **Remove `chat.py:_upsert_session` / merge into `LearningRepository`** (MEDIUM/HIGH) — eliminates the divergence risk; depends on the split being complete so the target file is small
4. **Remove `db/persistence.py` shim** (MEDIUM) — safe to do after the repository split stabilises import paths; update all callers to import directly from the split modules
5. **Extract Feynman business logic from `LearningRepository.save_session`** (HIGH) — depends on the split so the learning repo is in its own file and easy to test in isolation
6. **Migrate raw SQL from route handlers into repositories** (HIGH) — calls.py `list_calls`, `_ticker_exists`; admin.py analytics queries; depends on the split to know which file to add methods to
7. **Repositories accept injected connection** (MEDIUM) — can follow pooling and the route SQL migration; lowest-risk last

Cross-references:
- Connection pooling changes will interact with any issue adding new API routes (check open issues in the `feat/` space before pooling work begins)
- The `persistence.py` removal will produce a large diff touching CLI code (`main.py`, `app.py`) and any Modal ingestion code that imports from `db.persistence` — coordinate with the Modal ingestion work

---

## Recommended Next Steps

**1. Introduce `psycopg_pool` before any traffic scaling work**
Swap `psycopg.connect(self.conn_str)` for a module-level `ConnectionPool` instance. All repository classes should accept either a `conn_str` (pool initialisation) or a pre-opened connection. This is the change with the highest return-on-investment before any user-facing launch. The analytics `track()` daemon threads need particular attention — they should share the pool rather than opening unbounded connections.

**2. Split `db/repositories.py` into one file per class**
The split is low-risk if done with a re-export `__init__.py`. It has no functional impact. Do this early so that all subsequent changes (pooling, business logic extraction, adding new methods) happen in small, focused files rather than a 1,200-line monolith. The `AnalysisRepository` (700+ lines) is the most urgent.

**3. Collapse `chat.py:_upsert_session` into `LearningRepository.save_session`**
The route handler should call the repository, not reimplement it. This also means the concept-exercise creation logic in the repository needs to be moved out — see step 4.

**4. Extract Feynman completion logic from `LearningRepository.save_session` into a service**
The rule "on session completion, extract the stage-5 teaching note and create a concept exercise" belongs in a `LearningService` or similar. The repository should have two atomic methods: `upsert_session` and `create_concept_exercise`. The orchestration between them is a service concern.

**5. Delete `db/persistence.py`**
Once the split is done and all callers are confirmed to import directly from the repository modules, delete the shim. It is dead weight and a navigational hazard for new contributors.
