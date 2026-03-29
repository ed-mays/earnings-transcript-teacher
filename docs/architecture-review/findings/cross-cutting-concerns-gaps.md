# Production Readiness Gaps — Cross-Cutting Concerns

*Date: 2026-03-28*
*Scope: Areas not covered by reviews #195–#200 and #220*

## Summary

The completed reviews (#195–#200, #220) address the internal quality of the existing code: layering, auth, error contracts, repository design, dead code, types, and logging. What they do not address is the set of operational and lifecycle concerns that determine whether the service can be safely operated once it is deployed. The seven areas below are independent of each other and of the existing remediation PRs, with one exception: configuration validation overlaps slightly with the startup logging work in #220. Three of them — rate limiting, startup configuration validation, and database migration strategy — are prerequisites before the service carries production traffic.

---

## Findings

---

**[HIGH] No rate limiting — LLM and embedding endpoints are unbounded**

File(s): `api/routes/chat.py:155`, `api/routes/calls.py:237`, `api/routes/admin.py:135`

Finding: No rate limiting middleware exists anywhere in the stack. Three endpoints trigger paid external API calls with no per-user or per-IP enforcement:

- `POST /api/calls/{ticker}/chat` — each request triggers a streaming Perplexity call billed per token
- `GET /api/calls/{ticker}/search` — each request triggers a Voyage embed call billed per token
- `POST /admin/ingest` — each request spawns a Modal job billed per GPU-second

The chat endpoint accepts a `message` field with no `max_length` constraint (`ChatRequest` in `chat.py:147`). A single authenticated user can send arbitrarily large messages in rapid succession.

The analytics tables record token usage after the fact (`db/analytics.py`, `services/llm.py:171–185`) but nothing enforces limits before the API call is made.

The recommended Python library is `slowapi` (wraps `limits`, integrates with FastAPI). At minimum: per-user rate limits on chat (e.g., 60 req/hour) and search (e.g., 100 req/hour). The ingestion endpoint already requires admin role, which limits exposure, but a per-user cool-down (e.g., one ingest per ticker per 10 minutes) prevents accidental re-triggering.

Impact: An adversarial user or runaway client can exhaust Perplexity, Voyage, and Modal budgets. A legitimate user with a misbehaving client can do the same accidentally. No current signal would alert the team before the bill arrives.

---

**[HIGH] Startup configuration validation is incomplete — missing keys surface as runtime errors**

File(s): `api/main.py:22–25`, `api/routes/chat.py:174`, `api/routes/calls.py:250`, `api/routes/admin.py:138`

Finding: The lifespan function validates only `DATABASE_URL` and `SUPABASE_URL` at startup. Every other required key is checked lazily:

| Variable | Checked where | Failure mode |
|---|---|---|
| `VOYAGE_API_KEY` | `routes/calls.py:250` at request time | 503 on first search request |
| `PERPLEXITY_API_KEY` | `routes/chat.py:174` at request time | 503 on first chat request |
| `MODAL_TOKEN_ID` | Implicitly by Modal SDK | Unhandled exception in `trigger_ingestion` |
| `ANTHROPIC_API_KEY` | `AgenticExtractor.__init__` during ingestion | Exception mid-pipeline in Modal container |

The `/admin/health` endpoint checks `bool(os.environ.get(key))` for presence only (`admin.py:51`). It does not validate format, make a test API call, or block readiness.

A deployment with a misconfigured environment variable succeeds at startup (exits lifespan cleanly), passes any health check, and then fails for the first user who exercises the affected feature.

The fix is straightforward: move the `required` list in `lifespan()` to include all production-required keys, or implement a tiered check (hard-required at startup, soft-required logged as warnings). A `settings.py` module using Pydantic `BaseSettings` would make the environment contract explicit and type-safe.

Impact: Misconfigured deploys are invisible until a user hits the broken path. The team has no proactive signal (without the Sentry integration also recommended in #220) that a feature is completely broken.

Dependency note: Pairs naturally with the startup logging work in #220. Both belong in the same targeted fix.

---

**[HIGH] Database migration strategy has no CI enforcement — a missed migration is a deploy incident**

File(s): `migrate.py`, `db/repositories/schema.py`

Finding: `migrate.py` applies SQL files from `db/migrations/` in order and tracks the applied version in a `schema_versions` table. The memory note for this project records: *"Supabase does not auto-run migrations; manual apply required — CI/CD blocker until solved."*

Open questions that determine operational risk:

1. **Idempotency:** If `migrate.py` is run twice against the same database, does it skip already-applied migrations or fail? The `schema_versions` tracking implies it should skip, but this is not tested in CI.
2. **CI enforcement:** Is there a step in the PR/deploy pipeline that verifies the migration runs clean against a test database before the code ships? If not, a migration + code change can be merged and deployed out of order.
3. **Rollback:** There are no down-migrations. Rolling back a bad migration requires manual SQL. This is acceptable for a small team but needs to be documented so the operator knows what to do during an incident.
4. **Environment drift:** `schema.sql` is noted as out of sync with `migrate.py`. If a new contributor uses `schema.sql` to bootstrap a dev database, they get a different schema than production.

Impact: A deploy where `migrate.py` was not run before the new code hits production will produce 500s on any endpoint that uses the new schema. Without structured logging and Sentry (#220), this will not be caught until a user reports it.

Dependency note: This is a prerequisite for reliable deploys. It does not depend on any other remediation PR.

---

**[MEDIUM] Graceful shutdown does not drain in-flight requests or flush background threads**

File(s): `api/main.py:18–42`, `db/analytics.py:41`

Finding: The `lifespan` context manager closes the connection pool on exit. This is correct for pool cleanup. Two gaps remain:

1. **Daemon thread lifecycle:** `db/analytics.py:41` spawns daemon threads for analytics inserts. Daemon threads are killed immediately when the main process exits — any in-flight insert is dropped without warning or retry. During a rolling deploy (Railway sends SIGTERM, then SIGKILL after a timeout), analytics events for the last few seconds of a deployment window are silently lost.

2. **In-flight SSE streams:** When the process receives SIGTERM, active SSE generators (`chat.py:_sse_stream`) are abandoned mid-stream. The client (browser EventSource or `web/lib/chat.ts`) receives a network close, not a `{type: done}` or `{type: error}` event. The `web/lib/chat.ts` reader loop (`onmessage` + `onerror`) will fire `onerror` from the connection drop, but the error message will be browser-generic ("network error"), not informative.

The fix for (1) is to switch analytics inserts to non-daemon threads with a short join timeout in the lifespan shutdown, or use an asyncio background task with a shutdown event. The fix for (2) is a SIGTERM handler that sets a shutdown flag checked by active SSE generators, allowing them to emit a `{type: error, message: "Server restarting, please retry"}` before the process exits.

Impact: Users in an active Feynman session during a deploy see a silent mid-stream failure with no recovery instruction. Analytics data has a silent gap around every deploy.

---

**[MEDIUM] No CI/CD pipeline is visible in the repository**

File(s): `.github/workflows/` (does not exist)

Finding: There is no `.github/workflows/` directory and no CI configuration file in the repository. The deployment spec `[004]` describes a target pipeline but does not match an implemented one. As of this review:

- It is unknown whether tests run automatically on PRs.
- It is unknown whether there is a staging environment.
- It is unknown whether the Docker image build is automated or manual.
- Dependencies are in `requirements.txt` with no lock file (no `pip-compile` output, no `poetry.lock`, no `uv.lock`). A `pip install -r requirements.txt` on two different dates may produce different transitive dependency versions.

This is not a code issue — it is an operational gap. The remediation is to implement the pipeline described in spec `[004]`, prioritizing: (a) test run on PR, (b) dependency locking, (c) staging environment with its own Supabase project.

Impact: Without CI, the only regression signal is manual testing before merge. As the codebase grows and the team adds contributors, this becomes unreliable. Dependency drift is silent until a package break surfaces in production.

---

**[MEDIUM] User data retention and access controls are unspecified**

File(s): `db/repositories/learning.py`, `db/repositories/analytics.py`, Supabase RLS policies (not in repo)

Finding: Two tables store user-associated content indefinitely with no documented retention policy:

- `learning_sessions`: stores full chat message history as JSONB, including user-authored messages about financial topics. Linked to `user_id`.
- `analytics_events`: stores `session_id`, event metadata, turn counts, message lengths, and latency. Not directly linked to `user_id` but `session_id` links to `learning_sessions` which links to `user_id`.

Open questions:

1. **Row Level Security:** Are Supabase RLS policies applied to `learning_sessions` and `analytics_events`? The API layer enforces user scoping in `LearningRepository.get_session_by_id` (checks `user_id`), but if RLS is not also set on the table, a compromised API key or a SQL injection vulnerability bypasses the application-layer check entirely.
2. **Retention:** There is no scheduled cleanup of old sessions or analytics events. As the user base grows, these tables grow unbounded.
3. **Account deletion:** There is no endpoint or documented process for deleting a user's data. If a user closes their account, their chat history persists.
4. **Data residency:** Supabase project region determines where this data is stored. This is relevant if the user base is in a jurisdiction with data residency requirements (EU/GDPR, etc.).

Impact: Low risk today with a small user base. Becomes a compliance liability at scale. RLS enforcement is the one item here that should be verified before the service goes public, because it is a security boundary, not just a policy question.

---

**[MEDIUM] Input validation has unbounded fields on paid API paths**

File(s): `api/routes/chat.py:147–150`, `api/routes/calls.py:241`

Finding: Two request fields that trigger paid API calls have no upper bound:

- `ChatRequest.message` (`chat.py:149`): no `max_length`. Sent directly to Perplexity as the user turn. A 100KB message is accepted, tokenized, and billed.
- `q` query parameter in `search_transcript` (`calls.py:241`): `min_length=1`, no `max_length`. Sent to Voyage for embedding. Same issue.

Both are straightforward Pydantic constraints: `message: str = Field(..., max_length=4000)` and `q: str = Query(min_length=1, max_length=500)`. The values should be informed by actual model token limits (Perplexity sonar-pro context window) and reasonable UX expectations.

Also: the `history` list in a resumed session (`chat.py:192`) grows without bound. A session with 200 turns accumulates a large context window that is sent to Perplexity on every turn. There is no maximum session length check.

Impact: Without rate limiting (see first finding), a single large message is cheap to send. With rate limiting in place, this becomes a lower-priority concern. Both fixes should ship together.

Dependency note: Should be implemented alongside rate limiting — they address the same threat model from complementary angles.

---

## Dependency Map

These findings are independent of each other and of the existing PR sequence (#195–#200, #220 remediation). Internal ordering:

```
[HIGH] Startup config validation  ──(same PR)──►  [HIGH] Rate limiting
                                                        │
                                                        └──► [MEDIUM] Input validation bounds

[HIGH] Migration strategy  ──► prerequisite for reliable deploys, no code dependency

[MEDIUM] CI/CD pipeline  ──► prerequisite for all other quality gates being trustworthy

[MEDIUM] Graceful shutdown  ──► independent; pairs with #220 SSE teardown work

[MEDIUM] Data retention / RLS  ──► independent; RLS verification is a pre-launch gate
```

---

## Recommended Next Steps

**1. Add startup validation for all required env vars + input bounds (one targeted PR)**

Extend the `required` list in `lifespan()` to include `VOYAGE_API_KEY`, `PERPLEXITY_API_KEY`, and `MODAL_TOKEN_ID`. Add `max_length` to `ChatRequest.message` and the search `q` parameter. Add a session turn-count guard before building the Perplexity payload. This is a small, focused PR with no new dependencies.

**2. Verify and document the migration strategy (one targeted PR or doc commit)**

Run `migrate.py` against a clean database and confirm idempotency. Add a CI step (even a simple `python migrate.py` against a test database in GitHub Actions) to validate migrations before merge. Document the rollback procedure in the README or a runbook. Reconcile `schema.sql` with the current migration sequence or delete it.

**3. Implement the CI/CD pipeline described in spec [004]**

Minimum: GitHub Actions workflow that runs `pytest` on every PR, locks dependencies (`pip-compile` or `uv`), and validates the Docker image builds. A staging Supabase project is the next priority. This is a new implementation issue.

**4. Add rate limiting (new issue)**

Install `slowapi`. Add `@limiter.limit("60/hour")` to the chat endpoint and `@limiter.limit("100/hour")` to search, keyed on the authenticated user ID (available from `CurrentUserDep`). The admin ingest endpoint should have a per-ticker cooldown. Define and document the limit values in a `settings.py` alongside the env var validation.

**5. Verify Supabase RLS policies (can be done outside the codebase)**

Confirm that `learning_sessions` and `analytics_events` have RLS policies that prevent cross-user reads even if the API layer is bypassed. Document the policy in the repo (a `db/rls-policies.sql` or similar). If RLS is not yet applied, this is a pre-launch security gate.

**6. Implement graceful shutdown (new issue, pairs with #220 SSE work)**

Add a shutdown event to the lifespan that signals active SSE generators to emit a terminal event before exit. Convert analytics daemon threads to tracked non-daemon threads with a join timeout in the shutdown path. This can be scoped to one small issue.

**7. Document a data retention policy (decision required, not a code change)**

Decide on retention windows for `learning_sessions` and `analytics_events` (e.g., 90 days for sessions, 1 year for analytics aggregates). Once decided, implement a Supabase scheduled function or a cron-triggered Modal job to enforce it. The decision itself is the prerequisite — the implementation is straightforward once it exists.
