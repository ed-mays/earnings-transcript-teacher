# Production Readiness — Issue Backlog Draft

*Generated: 2026-03-28*
*Source: `cross-cutting-concerns-gaps.md`*
*Milestone: Production Readiness (new — create before importing issues)*

Review each issue below. Once approved, create the milestone and then create issues in the order listed. Set `Depends on` / `Blocks` fields after all issues exist and have numbers.

---

## Milestone

**Name:** Production Readiness
**Description:** Operational and lifecycle gaps that must be addressed before the service carries real user traffic. Separate from the code quality reviews in #195–#220.

---

## Gate Issues — must be resolved before first real user

---

### Issue 1

**Title:** Add rate limiting and input bounds on all paid API paths

**Labels:** `enhancement`, `infra`

**Problem:**
Three endpoints trigger paid external API calls with no enforcement. A single authenticated user can send arbitrarily large messages or search queries in rapid succession, exhausting Perplexity, Voyage, and Modal budgets. With no pre-call enforcement and no alerting, the team has no signal before the bill arrives.

**Acceptance criteria:**
- [ ] `slowapi` installed and configured as FastAPI middleware
- [ ] `POST /api/calls/{ticker}/chat` limited to 60 req/hour per authenticated user
- [ ] `GET /api/calls/{ticker}/search` limited to 100 req/hour per authenticated user
- [ ] `POST /admin/ingest` limited to one ingest per ticker per 10 minutes per user
- [ ] `ChatRequest.message` has `max_length=4000` (Pydantic Field constraint)
- [ ] `q` query parameter in `search_transcript` has `max_length=500`
- [ ] Session history in resumed sessions has a turn-count guard before building the Perplexity payload (value TBD — suggest 50 turns)
- [ ] Rate limit values and field lengths defined as constants in a new `api/settings.py`
- [ ] Tests cover: request within limit succeeds; request over limit returns 429; oversized message rejected at validation before any API call

**Files:**
- `api/routes/chat.py:147–155` — `ChatRequest` model, chat endpoint
- `api/routes/calls.py:237–241` — search endpoint, `q` param
- `api/routes/admin.py:135` — ingest endpoint
- `api/main.py` — middleware registration
- `api/settings.py` — new file for constants

**Notes:**
Rate limiting and input bounds address the same threat model from complementary angles — ship together. Rate limit values (60/hour, 100/hour) are starting points; adjust based on observed usage patterns.

---

### Issue 2

**Title:** Validate all required environment variables at startup

**Labels:** `enhancement`, `infra`

**Problem:**
The FastAPI `lifespan()` function validates only `DATABASE_URL` and `SUPABASE_URL`. Every other required key (`VOYAGE_API_KEY`, `PERPLEXITY_API_KEY`, `MODAL_TOKEN_ID`, `ANTHROPIC_API_KEY`) is checked lazily at request time. A deployment with a misconfigured environment variable passes startup and health checks, then silently fails for the first user who exercises the broken path.

**Acceptance criteria:**
- [ ] All four keys (`VOYAGE_API_KEY`, `PERPLEXITY_API_KEY`, `MODAL_TOKEN_ID`, `ANTHROPIC_API_KEY`) validated in `lifespan()` before the app accepts traffic
- [ ] Startup fails fast with a clear error message identifying the missing key(s)
- [ ] `/admin/health` endpoint reflects startup validation status (not just key presence via `os.environ.get`)
- [ ] Optional: introduce `api/settings.py` using Pydantic `BaseSettings` to make the environment contract explicit and type-safe (consolidate with Issue 1 constants if both land in the same PR)
- [ ] Tests cover: startup with all keys present succeeds; startup with a missing key raises on boot

**Files:**
- `api/main.py:22–25` — `lifespan()` function, current `required` list
- `api/routes/chat.py:174` — lazy `PERPLEXITY_API_KEY` check
- `api/routes/calls.py:250` — lazy `VOYAGE_API_KEY` check
- `api/routes/admin.py:138` — lazy `MODAL_TOKEN_ID` check, `/admin/health`
- `api/settings.py` — new file (may be shared with Issue 1)

**Dependencies:**
Pairs naturally with the startup logging work in #220. Consider whether both can land in the same PR.

---

### Issue 3

**Title:** Verify and document Supabase RLS policies for user data tables

**Labels:** `spike`, `infra`

**Problem:**
Two tables store user-associated data indefinitely: `learning_sessions` (full chat history linked to `user_id`) and `analytics_events` (session metadata). The API layer enforces user scoping in `LearningRepository.get_session_by_id`, but if Supabase Row Level Security (RLS) is not also set on the tables, a compromised API key or SQL injection vulnerability bypasses the application-layer check entirely. RLS status is unknown — it is not tracked in the repository.

**Acceptance criteria:**
- [ ] RLS policies on `learning_sessions` verified: users can only read/write their own rows
- [ ] RLS policies on `analytics_events` verified: appropriate restrictions in place (or rationale documented if left open)
- [ ] Current policy SQL documented in `db/rls-policies.sql` (create file if it doesn't exist)
- [ ] If RLS is not currently applied, applying it is treated as a blocking action before launch — document the steps taken
- [ ] README or a `docs/` runbook notes that RLS policies must be re-verified after any schema migration

**Files:**
- `db/repositories/learning.py` — application-layer user scoping
- `db/repositories/analytics.py` — analytics table operations
- `db/rls-policies.sql` — new file

**Notes:**
This is primarily a Supabase SQL Editor task, not a code change. The deliverable is verification + documentation. If RLS is not applied, this issue escalates from spike to launch blocker.

---

## Sprint 1 Issues — complete shortly after launch

---

### Issue 4

**Title:** Add CI enforcement for database migrations

**Labels:** `quality`, `infra`

**Problem:**
`migrate.py` applies SQL files from `db/migrations/` in order and tracks versions in a `schema_versions` table. There is no CI step that validates migrations run clean before code ships. A deploy where `migrate.py` was not run before the new code reaches production produces 500s on any endpoint using the new schema. Additionally, `schema.sql` is noted as out of sync with `migrate.py`, meaning a new contributor who bootstraps from `schema.sql` gets a different schema than production.

**Acceptance criteria:**
- [ ] `migrate.py` idempotency confirmed: running twice against the same database skips already-applied migrations without error
- [ ] GitHub Actions step (can be part of Issue 5's workflow) runs `migrate.py` against a test database on every PR that touches `db/migrations/`
- [ ] Rollback procedure documented in `docs/runbooks/migration-rollback.md` (or equivalent location)
- [ ] `schema.sql` either reconciled with the current migration sequence (v9) or deleted, with a note in `docs/` explaining that `migrate.py` is the authoritative bootstrap path
- [ ] Tests cover idempotency: `migrate.py` run twice produces the same schema without error

**Files:**
- `migrate.py`
- `db/repositories/schema.py`
- `db/schema.sql` — reconcile or delete
- `.github/workflows/` — CI step (coordinate with Issue 5)

**Notes:**
Per project memory: Supabase does not auto-run migrations; manual apply is required. This is the CI/CD blocker. The CI test database should be a local Postgres instance (not Supabase) to avoid environment complexity.

---

### Issue 5

**Title:** Implement baseline CI/CD pipeline

**Labels:** `quality`, `infra`

**Problem:**
There is no `.github/workflows/` directory. Tests do not run automatically on PRs. Dependencies are pinned in `requirements.txt` with no lock file — a `pip install` on two different dates may produce different transitive dependency versions. Without CI, the only regression signal is manual testing before merge. This makes all other quality gates (migration enforcement, test coverage targets) unenforceable.

**Acceptance criteria:**
- [ ] GitHub Actions workflow runs `pytest` on every PR targeting `main`
- [ ] Dependencies locked using `uv` (preferred) or `pip-compile`; lock file committed and used in CI install
- [ ] CI validates that the Docker image builds without error (build step, not deploy)
- [ ] Workflow passes on the current codebase before merge
- [ ] README updated to reflect the lock file and CI status badge

**Files:**
- `.github/workflows/ci.yml` — new file
- `requirements.txt` → `requirements.in` + `requirements.lock` (or `uv.lock`) — restructure
- `Dockerfile` — verify it works with locked deps
- `README.md` — CI badge + lock file instructions

**Notes:**
Staging environment is out of scope for this issue. A staging Supabase project is the logical next issue after this one ships. The Docker image build step validates the artifact without requiring a deployment target.

---

## Backlog Issues — operational polish, no launch dependency

---

### Issue 6

**Title:** Implement graceful shutdown for SSE streams and analytics threads

**Labels:** `enhancement`, `infra`, `polish`

**Problem:**
When Railway sends SIGTERM before a rolling deploy, two things happen silently: (1) daemon analytics threads are killed mid-insert, dropping the last few seconds of analytics events around every deploy; (2) active SSE streaming sessions are abandoned mid-stream — the client receives a network close with a browser-generic error message, not an informative terminal event.

**Acceptance criteria:**
- [ ] SIGTERM handler sets a shutdown flag checked by active SSE generators in `chat.py`
- [ ] SSE generators emit `{type: "error", message: "Server restarting, please retry"}` before the process exits
- [ ] Analytics daemon threads in `db/analytics.py` converted to non-daemon threads with a join timeout (suggest 5 seconds) in the `lifespan()` shutdown path
- [ ] If an analytics thread does not join within the timeout, the failure is logged (not silently dropped)
- [ ] Tests cover: shutdown flag causes SSE generator to emit terminal event; analytics thread is joined on shutdown

**Files:**
- `api/main.py:18–42` — `lifespan()` context manager
- `db/analytics.py:41` — daemon thread spawn
- `api/routes/chat.py` — SSE stream generator

**Notes:**
Pairs with #220 SSE teardown work — coordinate to avoid conflicting changes to the SSE stream path.

---

### Issue 7

**Title:** Define and document data retention policy for user sessions and analytics

**Labels:** `spike`, `documentation`

**Problem:**
`learning_sessions` (full chat history) and `analytics_events` (usage metadata) grow unbounded. There is no documented retention policy, no scheduled cleanup, and no process for deleting a user's data on account closure. This is low risk today with a small user base, but becomes a compliance liability at scale. The retention windows must be decided before implementation can proceed.

**Acceptance criteria:**
- [ ] Retention windows decided and documented: e.g., `learning_sessions` for 90 days, `analytics_events` for 1 year (values are proposals — decision required from owner)
- [ ] Account deletion process defined: what happens to a user's sessions and analytics when they close their account
- [ ] Data residency: Supabase project region noted in `docs/` (relevant for GDPR if EU users are expected)
- [ ] Implementation approach decided: Supabase scheduled function vs. cron-triggered Modal job
- [ ] Once decisions are made, this issue spawns a follow-on implementation issue — it is not closed until the policy is documented, even if implementation is deferred

**Files:**
- `db/repositories/learning.py`
- `db/repositories/analytics.py`
- `docs/` — new policy document

**Notes:**
This is a decision issue. The implementation (scheduled cleanup function) is straightforward once the decisions exist — it should not be blocked indefinitely waiting for a perfect policy. A 90-day / 1-year starting point is reasonable and can be adjusted.

---

## Dependency Map

```
Issue 1 (Rate limiting + input bounds)  ──────────────────────────────────────► Gate
Issue 2 (Startup config validation)     ──── pairs with #220 ────────────────► Gate
Issue 3 (RLS verification)              ──────────────────────────────────────► Gate

Issue 4 (Migration CI)                  ──── contributes to Issue 5 ─────────► Sprint 1
Issue 5 (CI/CD pipeline)               ──── depends on nothing ─────────────► Sprint 1

Issue 6 (Graceful shutdown)             ──── pairs with #220 ────────────────► Backlog
Issue 7 (Data retention policy)         ──── decision first ─────────────────► Backlog
```

---

## Pre-creation checklist

- [ ] Milestone "Production Readiness" created in GitHub
- [ ] Confirm no existing issues duplicate any of the above (search: `rate limit`, `lifespan`, `RLS`, `migrate.py`, `GitHub Actions`)
- [ ] Decide whether Issues 1 and 2 share a `settings.py` file (they likely should — coordinate in issue bodies once created)
- [ ] Note: no `security` label exists — consider creating one before Issue 3, or use `spike` + `infra`
