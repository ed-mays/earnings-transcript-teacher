# Milestone 7: Architecture Review Synthesis

*Date: 2026-03-28*
*Reviews completed: #195, #196, #197, #198, #199, #200, #220*
*Additional gaps documented: [cross-cutting-concerns-gaps.md](cross-cutting-concerns-gaps.md)*

## Executive Summary

The codebase is architecturally coherent at the macro level — FastAPI + Next.js layers are well-separated, the repository pattern is established, and the SSE streaming contract is sound. Two problems demand immediate attention before any new feature work: the admin API route handlers do not enforce the admin role (authenticated non-admins can call every `/api/admin/*` route directly), and every repository method swallows all exceptions and returns empty defaults, meaning a database outage is indistinguishable from "no data" at the HTTP boundary. Beneath these critical issues, the codebase has three compounding structural debts: `db/repositories.py` is a 1,229-line monolith that is already a merge-conflict magnet; raw SQL is scattered across route handlers bypassing the repository layer; and connection pooling is entirely absent, creating a hard scalability ceiling. A separate set of operational gaps — rate limiting, startup validation, migration strategy, graceful shutdown, CI/CD pipeline, data retention, and input bounds — are documented in `cross-cutting-concerns-gaps.md`; three of them (rate limiting, startup validation, migration strategy) are prerequisites before the service carries production traffic. The recommended approach is to address the security/integrity issues first, then execute the structural refactors, then close the operational gaps before launch.

---

## Cross-Cutting Themes

### Silent failure is the dominant thread

The most pervasive problem across #197, #198, and #195 is that failures are silently swallowed rather than propagated. `db/repositories.py` returns empty defaults on every exception (#197 CRITICAL). `routes/calls.py` makes up to seven separate database connections per request with no error handling on three of them (#197 HIGH, #195 HIGH). `_sse_stream` in `chat.py` emits raw Python exception strings across the wire (#197 HIGH, #195 MEDIUM). There is no global FastAPI exception handler to catch what falls through (#197 LOW). The net effect: the system looks healthy under monitoring even when it is partially broken.

### Repository bypass is the structural rot

Raw psycopg queries appear inline in `routes/calls.py`, `routes/chat.py`, and `routes/admin.py` (#195 HIGH, #198 HIGH). `_db_url()` is duplicated across three route files. `chat.py:_upsert_session` is a near-duplicate of `LearningRepository.save_session` that can silently diverge (#198 MEDIUM). `db/persistence.py` is a dead shim that adds a second calling convention to the same data layer (#198 MEDIUM). This pattern means schema changes require hunting multiple files rather than updating a single repository method.

### Auth checks are inconsistent at every boundary

`proxy.ts` middleware uses `getUser()` (correct) but its admin path check uses `/admin` and silently misses `/api/admin/*` (#196 HIGH/MEDIUM). Route handlers use `getSession()` (weaker) and check only authentication, not the admin role (#196 HIGH). FastAPI enforces the role correctly, so data operations are protected, but the Next.js proxy tier is fully open to authenticated non-admins. Three independent layers each apply a different subset of the required checks.

### Type system is advisory, not enforced

`db/repositories.py` returns `list[tuple]` unpacked by positional index in routes (#200 MEDIUM). `core/models.py` mixes plain `dataclass` and Pydantic `BaseModel` with no policy (#200 MEDIUM). Admin analytics routes return bare `dict` with no `response_model` (#200 HIGH). No mypy or pyright is configured (#200 LOW). The type gaps are invisible to CI and compound silently as new endpoints are added.

### Dead code is understated but actively misleading

`nlp/takeaways.py`, `nlp/themes.py`, and `nlp/keywords.py` are test-only modules that imply an active NLP pipeline that no longer exists (#199 MEDIUM). `db/persistence.py` is a dead shim with a different calling convention (#198 MEDIUM). `utils/timing.py` has no callers (#199 LOW). New contributors navigating these files will waste time understanding code that runs nowhere in production.

---

## Delivery Plan — Vertical Slices

Each PR is cohesive by concern, touches a bounded set of files, and ships independently. Issues are not split across PRs.

### PR 1 — Auth hardening
*Source reviews: #196 (all findings)*

All auth gaps in one go. No schema changes, no new dependencies.

| Finding | Action |
|---|---|
| Admin API routes do not verify admin role [HIGH] | Add `getUser()` + role check to all 7 `web/app/api/admin/*/route.ts` handlers |
| `getSession()` used instead of `getUser()` [HIGH] | Replace in route handlers and admin page server components |
| Middleware admin path check misses `/api/admin/*` [MEDIUM] | Extend path check or remove (redundant once handlers self-enforce) |
| OAuth callback `next` param is an open redirect [MEDIUM] | Validate against a static allowlist before redirecting |
| `SUPABASE_JWT_SECRET` surfaced in health response [MEDIUM] | Remove from `_HEALTH_ENV_VARS` |

Files touched: `web/app/api/admin/*/route.ts`, `web/proxy.ts`, `web/app/auth/callback/route.ts`, `api/routes/admin.py`

### PR 2 — Error contract
*Source reviews: #197 (all findings), #195 (SSE findings)*

Establish a consistent, safe error contract end-to-end. Requires PR 1 to be merged first so the global handler is the safety net before repository exceptions start propagating.

| Finding | Action |
|---|---|
| Global FastAPI exception handler missing [structural root cause] | Add `@app.exception_handler(Exception)` to `api/main.py` |
| Repository exceptions swallowed — "no data" ≡ "DB failure" [CRITICAL] | Establish and apply failure policy across all 23 affected methods in `db/repositories.py` |
| SSE error events emit raw Python exception strings [HIGH] | Replace `str(exc)` with generic message; log server-side |
| `search_transcript` may leak Voyage API exception text [HIGH] | Add `try/except` in `routes/calls.py` around Voyage SDK call |
| Admin route handlers have no exception handling [HIGH] | Wrap analytics + ingestion endpoints |
| Error shape inconsistent: FastAPI (`detail`) vs Next.js (`error`) [MEDIUM] | Align proxy early-exit responses; update `web/lib/api.ts` |
| `feynman_stage_completed` tracked at session creation, not completion [MEDIUM] | Move `track()` to after `yield done` in `_sse_stream` |

Files touched: `api/main.py`, `db/repositories.py`, `api/routes/chat.py`, `api/routes/calls.py`, `api/routes/admin.py`, `web/lib/api.ts`

### PR 3 — Repository consolidation
*Source reviews: #198 (all findings), #195 (raw SQL / session duplication findings)*

Consolidate all data access behind the repository layer and introduce connection pooling. Depends on PR 2 (repositories now raise on failure, so callers must be updated as raw SQL is removed).

| Finding | Action |
|---|---|
| No connection pooling — one TCP connection per call [HIGH] | Introduce `psycopg_pool`; analytics daemon threads share the pool |
| `db/repositories.py` is a 1,229-line monolith [MEDIUM] | Split into one file per class with a re-export `__init__.py` |
| Raw SQL in route handlers bypasses repository layer [HIGH] | Move `list_calls`, `get_spans`, `search_transcript` (calls.py) and admin analytics queries to repository methods |
| `chat.py:_upsert_session` duplicates `LearningRepository.save_session` [MEDIUM] | Collapse into one; delete `_upsert_session` from the route |
| Feynman completion business rule inside repository [HIGH] | Extract to `LearningService`; repository becomes two atomic write methods |
| `db/persistence.py` is a dead shim [MEDIUM] | Delete once import paths are stable after the split |
| `routes/calls.py` opens up to 7 connections per request [LOW] | Resolved automatically once raw SQL is replaced by injected `get_db` |

Files touched: `db/repositories.py` (split into `db/`), `api/routes/calls.py`, `api/routes/chat.py`, `api/routes/admin.py`, `api/dependencies.py`, `db/persistence.py` (deleted), new `services/learning.py`

### PR 4 — Dead code and type coverage
*Source reviews: #199 (all findings), #200 (all findings)*

Safe to parallelize internally. No ordering dependency on PR 3 except `persistence.py` deletion (which PR 3 handles).

| Finding | Action |
|---|---|
| `utils/timing.py` has no callers [LOW] | Delete |
| `ui/data_loaders.py` orphaned functions [MEDIUM] | Delete `load_competitors`, `load_recent_news` |
| `nlp/takeaways.py`, `nlp/themes.py` are dead ML modules [MEDIUM] | Delete both + test files; then delete `nlp/keywords.py` |
| No mypy/pyright configured [LOW] | Add `pyproject.toml` with baseline mypy config; wire to CI |
| `core/models.py` mixes `dataclass` and Pydantic [MEDIUM] | Migrate domain models to Pydantic v2 `BaseModel` |
| Admin analytics routes return bare `dict`, no `response_model` [HIGH] | Add typed Pydantic response models to all 7 admin endpoints |
| SSE stream has no abort path / timeout [MEDIUM] | Add `AbortController` to `streamChat`; wire to component unmount |
| Learn page re-fetches full `CallDetail` client-side [HIGH] | Wrap `LearnPage` in a server component; pass `themes`/`keywords` as props |

Files touched: `utils/timing.py` (deleted), `ui/data_loaders.py`, `nlp/` (3 files deleted), `pyproject.toml` (new), `core/models.py`, `api/routes/admin.py`, `web/lib/chat.ts`, `web/app/calls/[ticker]/learn/page.tsx`

### Defer (no PR yet)

| Finding | Rationale |
|---|---|
| Streamlit stack retirement decision | Product decision required — document in CLAUDE.md first |
| Split `requirements.txt` | Depends on Streamlit retirement decision |
| `AgenticExtractor` → TypedDict | Revisit once mypy is configured and baseline is known |
| JWKS vs token error differentiation | Defer until 503 vs 401 ambiguity causes an actual incident |
| Zod parsing for `CallDetail` | Low probability; revisit when schema changes become frequent |
| `lib/api.ts` direct browser → FastAPI | Not a security gap; address in a future API gateway effort |

---

## Fix-Order Dependencies

1. **PR 1 before PR 2** — the global exception handler must be in place before repositories start raising exceptions.
2. **PR 2 before PR 3** — raw SQL removal requires a consistent error contract already established so new repository callers handle failures correctly.
3. **PR 3 before `persistence.py` deletion in PR 4** — the shim's callers need stable import paths after the repository split.
4. **Within PR 3: split `repositories.py` before adding raw SQL methods** — avoids adding methods to a monolith immediately before splitting it.
5. **Within PR 3: collapse `_upsert_session` before extracting Feynman business logic** — both implementations must be unified before the rule extraction is safe.
6. **Within PR 4: delete `nlp/takeaways.py` and `nlp/themes.py` before `nlp/keywords.py`** — `keywords.py` exports `ALL_STOP_WORDS` which those files consume.
7. **Within PR 4: add mypy before migrating models to Pydantic** — the baseline makes regression visible.

---

## Recommended First PR

**PR 1 — Auth hardening** (all of #196)

Ships everything auth-related in one go: admin API role check, `getSession` → `getUser`, middleware path fix, OAuth redirect validation, JWT secret removal from health response. Closes the authentication bypass (any authenticated user can invoke all admin operations today) with minimal blast radius — only route files and middleware, no schema changes, no new dependencies. Every other issue is a quality or scalability concern; this one is a security concern. It ships before any feature work resumes.
