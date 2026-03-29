# Issue #220: Observability, Logging Consistency, and Cross-Cutting Concerns

*Persona: Staff Platform/SRE Engineer*
*Date: 2026-03-28*

## Summary

The API layer has the skeleton of a logging setup — every module calls `logging.getLogger(__name__)` and the global exception handler in `main.py` calls `logger.exception()` — but the configuration layer that would make that output visible is absent. No handler, no level, no format is ever configured for the application root logger. Whether any of this logging is visible in production depends entirely on how uvicorn is invoked. Layered on top of that, there is no structured logging, no request correlation, and no error aggregation service — the team has no proactive signal when the production stack breaks. The highest-leverage near-term change is two lines: configure the root logger at startup with a log level from the environment. The highest-leverage medium-term change is a request ID middleware, which unlocks end-to-end traceability across the rest of the fixes.

---

## Findings

---

**[CRITICAL] No logging configuration — application log output is undefined in production**

File(s): `api/main.py`

Finding: Every module creates `logger = logging.getLogger(__name__)` correctly, but no code anywhere calls `logging.basicConfig()`, sets a handler on the root logger, or configures log format. Python's root logger has a `NullHandler` by default. Whether application logs reach stdout depends entirely on whether the process runner (uvicorn, Railway, Modal) configures the root logger before application code runs.

Uvicorn does configure its own `uvicorn` and `uvicorn.access` loggers, and its `--log-level` flag controls those. But the application-namespace loggers (`api.main`, `api.routes.chat`, `services.llm`, `db.analytics`, etc.) are children of the root — they will propagate upward, and if the root has no handler, the output is silently discarded. `LOG_LEVEL` is not read from the environment anywhere; log verbosity cannot be changed without a code change or a uvicorn flag.

The `lifespan` function logs `"Database connection pool started"` at INFO on startup. In a bare `uvicorn api.main:app` invocation without `--log-config`, this line may never appear.

Impact: In production, all application-level log output — including `logger.exception()` calls in the global error handler — may be silently discarded. There is no way to verify the effective log level. The entire observability foundation rests on an assumption that uvicorn or the hosting platform bridges the root logger, which is not guaranteed.

Dependency note: All other log-level findings assume this is fixed first. Fixing it unlocks all existing `logger.*` calls.

---

**[HIGH] No structured logging — log entries are unqueryable in any aggregation system**

File(s): `api/main.py:32,34,42`, `api/routes/admin.py:91,99,103,108,115,120,127,132,140`, `api/routes/chat.py:141`, `db/analytics.py:28`, `services/llm.py:120`, `api/dependencies.py` (no logging)

Finding: All log calls use either f-string or %-style positional formatting, producing plain text messages with no structured metadata. Examples:

- `logger.info("Database connection pool started (min=2, max=10)")` — no host, no pid, no version
- `logger.warning("analytics.track failed for event=%r: %s", event_name, exc)` — event name and error are positional, not key-value
- `logger.error("DB error in analytics_sessions: %s", e)` — the `%s` expansion produces an opaque string

No log entry includes a request ID, user ID, ticker, session ID, or service name as structured fields. Searching for "all errors for session X" or "all log lines from the Voyage search in the last hour" requires grep on raw text, not a query.

Impact: Log aggregation tools (Datadog, Loki, CloudWatch Logs Insights) cannot extract fields without brittle regex parsing. Production incident investigation requires manual log tailing. Alerting on specific error conditions is not feasible.

Dependency note: Fixing this is a migration to `structlog` or a custom `logging.Formatter` that emits JSON. It is independent of the correlation ID work but pairs naturally with it.

---

**[HIGH] No request correlation — a single user request cannot be traced end-to-end**

File(s): `api/main.py` (no middleware), `api/routes/chat.py`, `api/routes/calls.py`, `api/routes/admin.py`

Finding: No middleware injects a request ID or trace ID into the request context. Log entries from `api/routes/chat.py`, `services/llm.py`, and `db/analytics.py` during a single chat request cannot be correlated — they share no common identifier beyond a timestamp window.

The `_sse_stream` generator logs `"SSE stream error for session %s"` using `session_id` as a loose correlation handle. This works only after a session exists; pre-session failures (auth check, ticker lookup) produce log entries with no common key.

`db/analytics.py:track` spawns a daemon thread with no request context at all. A warning from that thread cannot be linked to the originating request.

Impact: A production incident — for example, 10% of chat sessions silently failing mid-stream — requires correlating `chat.py` INFO logs, `analytics.py` WARNING logs, and `llm.py` ERROR logs by timestamp approximation. With concurrent users, that window will contain noise from multiple sessions. Root cause diagnosis is significantly slower than it needs to be.

Dependency note: A `X-Request-ID` middleware in `main.py` (or a `contextvars`-based request context) is the prerequisite. Once in place, it should be threaded into the `structlog` context (or equivalent) and into `db/analytics.py`'s tracking calls.

---

**[HIGH] `services/orchestrator.py` uses `print()` for significant pipeline events**

File(s): `services/orchestrator.py:72`, `services/orchestrator.py:83`, `services/orchestrator.py:226`

Finding: Three `print()` calls exist in production code paths:

- Line 72: `print(f"  ↳ Deterministic Q&A detection failed. Triggering LLM fallback...")` — this is an important diagnostic event (the regex parser failed; LLM fallback engaged), but it goes to stdout unformatted.
- Line 83: `print(f"    ↳ LLM identified Q&A start at turn {abs_idx} (Confidence: {result['confidence']}).")` — LLM result metadata.
- Line 226: `print(f"❌ Agentic pipeline failed: {e}")` followed immediately by `logger.warning(...)` on line 227 — the same event is emitted twice via different channels, inconsistently.

`ingestion/pipeline.py` is entirely print-based (dozens of calls). That module runs in Modal during ingestion, not in the FastAPI process, so the impact is scoped to that context — but the pattern is identical and should be noted.

Impact: Lines 72, 83, and 226 are in the `orchestrator.analyze()` path, which runs during ingestion. In Modal or any container without a tty, `print()` output may not reach the log sink at all. The duplicate at line 226 means the event gets counted twice if both channels are visible. A future structured logging migration will require hunting down these scattered prints.

---

**[HIGH] No error aggregation service — production exceptions have no proactive signal**

File(s): `api/main.py:78–82` (global exception handler), entire stack

Finding: No Sentry, OpenTelemetry, Datadog, or equivalent integration exists anywhere in the stack. The global exception handler (`main.py:78-82`) logs unhandled exceptions with `logger.exception()`, which is correct — but that log entry goes to wherever uvicorn routes the root logger, which may be nowhere (see CRITICAL finding above).

The team has no proactive alert path for a production exception. An unhandled 500 on a heavily-used route (e.g., the Feynman chat endpoint) will produce: one `logger.exception()` line, a generic `{"error": "Internal server error"}` JSON response to the client, and nothing else. The team learns about it when a user complains.

Impact: Mean time to detect (MTTD) for silent production failures is unbounded. This is not unusual for an early-stage product, but it is a known operational risk. Any future on-call or SLA commitment requires at minimum a Sentry DSN.

Dependency note: Sentry integrates as a single middleware: `SentryAsgiMiddleware(app)` after the Sentry SDK is initialized. It is independent of the structured logging work but captures unhandled exceptions and their full context automatically.

---

**[MEDIUM] `db/analytics.py` fire-and-forget opens fresh connections, bypasses the pool**

File(s): `db/analytics.py:17`

Finding: `_insert_event` calls `psycopg.connect(db_url)` directly in a daemon thread, bypassing the application-level connection pool registered in `dependencies.py`. The pool is capped at `max_size=10` (`main.py:30`). Under load — e.g., a burst of concurrent chat turns, each firing 2–3 analytics events — analytics daemon threads can open additional raw connections outside the pool's accounting.

The failure path logs a warning (`logger.warning("analytics.track failed for event=%r: %s", event_name, exc)`), which is better than silent discard. But there is no counter, no rate of analytics failure tracked, and no way to observe whether the warning rate is elevated.

Impact: Analytics events silently dropped under connection pressure. Connection counts on the database host may exceed expected pool limits without triggering any alert. Additionally, analytics failures are visible only in logs — there is no self-monitoring for tracking infrastructure health.

---

**[MEDIUM] `api/dependencies.py` swallows all auth failures with no logging**

File(s): `api/dependencies.py:83–87`

Finding: The broad `except Exception` at line 83 catches JWKS fetch failures, network errors to Supabase, and unexpected SDK errors, then raises `HTTPException(401, "Invalid token")` with no log output. There is no `logger.warning()` or `logger.exception()` in this path.

If Supabase's JWKS endpoint is unreachable, every authenticated request returns 401 and the server-side log is silent. The team cannot distinguish "users are submitting bad tokens" from "Supabase auth is down" by looking at server logs.

Impact: A Supabase auth outage produces a flood of 401s with zero server-side diagnostic signal. This is covered as an error-contract issue in `issue-197-error-handling.md`, but the logging gap is a separate concern: even if the error contract is fixed, the event still needs to be logged.

---

**[MEDIUM] `api/routes/calls.py` has no logger at all — route-level context is lost on failure**

File(s): `api/routes/calls.py`

Finding: `routes/calls.py` does not import `logging` and defines no `logger`. All three data-access routes (`list_calls`, `get_call`, `get_spans`, `search_transcript`) have zero log output on the happy path or the error path. When an unhandled exception occurs, it propagates to the global handler in `main.py`, which logs the exception — but without route-level context (ticker, query, page, user).

The route-level `track()` call in `search_transcript` (line 263) records the analytics event but fires to a daemon thread with no synchronous log entry.

Impact: The calls routes are operationally dark. A spike in errors on `GET /api/calls/{ticker}` produces log lines like `"Unhandled exception on GET /api/calls/MSFT"` with a traceback, but no ticker, no user, no timing context.

---

**[LOW] `AgenticExtractor._track_usage` swallows exceptions completely silently**

File(s): `services/llm.py:184–185`

Finding: The `except Exception: pass` at line 185 includes the comment `"tracking must never block extraction"` — the intent is correct, but the implementation discards all failure information. `db/analytics.py:track` at least logs a warning on DB failure. This path logs nothing.

If the `track` import or call fails (e.g., during a Modal container startup where `db.analytics` isn't importable), the failure is invisible. Token usage for all Claude ingestion calls may silently go untracked.

Impact: Claude API token tracking may be unreliable without any signal. Compare with `db/analytics.py:28`, which logs a warning on the same failure path in the FastAPI context — this inconsistency should be resolved in whichever direction is chosen.

---

**[LOW] DB error messages in admin route logs may include schema or query fragments**

File(s): `api/routes/admin.py:91,99,103,108,115,120,127,132`

Finding: The five analytics endpoints catch `psycopg.Error as e` and log `logger.error("DB error in analytics_X: %s", e)`. A psycopg exception message can include the SQL query text, table names, column names, and connection error details. These end up in log entries.

In the current single-tenant admin context, this is low risk. In a multi-tenant future, or if logs are shipped to a third-party system with broad access, this could expose schema internals.

Impact: Low risk now. Worth noting as a pattern to avoid establishing further. Replace with `logger.error("DB error in analytics_X", exc_info=True)` to log the traceback via the logging framework rather than embedding the exception string in the message.

---

## What Is Working

Before the remediation backlog, it is worth noting what is already correctly in place:

- The global exception handler (`main.py:78–82`) calls `logger.exception()` and returns a generic `{"error": "Internal server error"}` with no raw exception text. The error contract is correct.
- SSE error events emit a safe generic message `"Stream error"`, not `str(exc)`. This was apparently remediated as part of prior work.
- `db/analytics.py` logs a warning on failure — it does not silently discard.
- `admin.py` analytics endpoints wrap DB calls in `try/except` and log the error before re-raising as 503.
- JWT auth errors are correctly split (`ExpiredSignatureError` vs. broad `Exception`) to give callers distinct error messages.

---

## Dependency Map

```
[CRITICAL] Configure root logger  ──► unlocks all existing logger.* calls
      │
      ├──► [HIGH] Structured logging (structlog or JSON formatter)
      │                │
      │                └──► [HIGH] Request correlation middleware
      │                                │
      │                                └──► Thread request ID into analytics.py
      │
      ├──► [HIGH] Sentry integration (independent — add SentryAsgiMiddleware)
      │
      ├──► [HIGH] Replace print() in orchestrator.py (independent)
      │
      └──► [MEDIUM] Add logger to routes/calls.py (independent)
```

---

## Recommended Next Steps

**1. Configure the root logger at application startup (highest leverage, smallest diff)**

In `api/main.py`, add before the `app` is built:

```python
import sys
log_level = os.environ.get("LOG_LEVEL", "INFO").upper()
logging.basicConfig(
    stream=sys.stdout,
    level=log_level,
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)
```

This unblocks every existing `logger.*` call across the stack without changing any other file. Add `LOG_LEVEL` to the env var documentation. This is a targeted fix — no new issue needed, can be done inline.

**2. Add a request ID middleware**

Add a lightweight ASGI middleware in `main.py` that reads `X-Request-ID` from the incoming request (or generates a UUID) and stores it in a `contextvars.ContextVar`. Pass it to `logger.info(..., extra={"request_id": ...})` calls in route handlers. This is the structural prerequisite for traceability. Warrants a small standalone issue.

**3. Migrate to structured logging (new issue)**

Replace the plain-text `logging.Formatter` with a JSON formatter (either `structlog` with its stdlib bridge, or a simple `logging.Formatter` subclass that emits JSON). This is the change that makes logs queryable. It affects every module but is backward-compatible — log content doesn't change, only format. Warrants its own issue; implementation is ~1 day of work.

**4. Add Sentry integration (new issue)**

Install `sentry-sdk[fastapi]` and call `sentry_sdk.init(dsn=os.environ.get("SENTRY_DSN"))` before the `app` is built. Wrap with `SentryAsgiMiddleware`. Zero application code changes required. Warrants a small standalone issue; implementation is under an hour.

**5. Replace `print()` in `services/orchestrator.py` (targeted fix, same session as #1)**

Lines 72, 83, 226 in `orchestrator.py` should call `logger.info()` and `logger.warning()`. The duplicate at line 226 (print + logger.warning) should collapse to a single `logger.warning()`. This is a 3-line change.

**6. Add a logger to `routes/calls.py` (targeted fix)**

Add `logger = logging.getLogger(__name__)` and add `logger.info()` calls at the start of each route handler with the relevant context (ticker, user if available, query for search). This is a ~10-line change.

**7. Standardize analytics failure logging (LOW, consolidation)**

`services/llm.py:184–185` should log a warning instead of `pass`. Aligns with `db/analytics.py`'s existing behavior. One-line fix.
