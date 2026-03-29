# Issue #197: Error Handling Contract and API Response Consistency

*Persona: API Design Engineer*
*Date: 2026-03-28*

## Summary

The FastAPI layer uses HTTP status codes correctly and raises typed `HTTPException` consistently for expected failures. The Next.js proxy route handlers are well-structured thin proxies. The fundamental problem is a pervasive pattern in `db/repositories.py`: every repository method catches broad `Exception`, logs a warning, and returns a silent default (empty list, `None`, `False`). This means a database outage or schema incompatibility surfaces to the route as "no data found" rather than a server error, turning a 500 into a 200 with empty fields. A secondary problem is that the SSE error event carries `str(exc)` — a raw Python exception string that may leak internal details across the wire.

---

## Findings

---

**[CRITICAL] Repository exceptions are swallowed and replaced with empty defaults — callers cannot distinguish "no data" from "DB failure"**

File(s): `db/repositories.py:44–46`, `db/repositories.py:76–78`, `db/repositories.py:109–111`, `db/repositories.py:137–139`, `db/repositories.py:159–161`, `db/repositories.py:185–187`, `db/repositories.py:207–209`, `db/repositories.py:226–228`, `db/repositories.py:255–257`, `db/repositories.py:275–278`, `db/repositories.py:327–329`, `db/repositories.py:347–350`, `db/repositories.py:369–371`, `db/repositories.py:392–394`, `db/repositories.py:413–416`, `db/repositories.py:443–445`, `db/repositories.py:463–466`, `db/repositories.py:484–487`, `db/repositories.py:506–509`, `db/repositories.py:528–531`, `db/repositories.py:551–553`, `db/repositories.py:572–575`, `db/repositories.py:593–597`

Finding: Every public method in every repository class follows the same pattern: wrap the entire body in `try/except Exception as e`, log `logger.warning(...)`, then return an empty default (`[]`, `None`, `False`, `{}`). There is no re-raise, no status propagation, and no way for the caller to distinguish "this ticker genuinely has no keywords" from "the database connection failed while fetching keywords."

The callers in `api/routes/calls.py:get_call` (lines 137–185) pass these empty defaults directly into the `CallDetail` response model. A complete database failure on `get_call` will return HTTP 200 with `keywords: []`, `themes: []`, `speakers: []`, `synthesis: null`, and `evasion_analyses: []` — a valid-looking but entirely empty response. The client has no signal that anything went wrong.

The same pattern applies in `routes/chat.py`: `_sse_stream` calls `_upsert_session` with no error handling around it (line 135), but `_upsert_session` itself issues raw psycopg calls without wrapping — so a session-save failure during streaming will propagate as an unhandled exception and terminate the generator mid-stream without emitting a `{type: error}` event.

Impact: Silent data loss masquerades as empty state. A database outage during a live call detail fetch returns 200 with blank fields. Monitoring will not see 5xx errors; it will see 200s with structurally valid but semantically empty payloads. Users see a blank page with no error message. Debugging requires log correlation rather than HTTP status codes.

---

**[HIGH] SSE error events emit raw Python exception strings**

File(s): `api/routes/chat.py:158–159`

Finding: The `_sse_stream` generator's `except` clause at line 158 emits:

```python
yield f"data: {json.dumps({'type': 'error', 'message': str(exc)})}\n\n"
```

`str(exc)` on a psycopg exception may include the connection string fragment, table names, SQL text, or OS-level socket error messages. On a `jwt.DecodeError` it would echo the malformed token fragment. This crosses the wire to the browser as plaintext JSON inside an SSE frame.

The client at `web/lib/chat.ts:91` forwards `parsed.message` directly to the `onError` callback, which in practice renders in the UI.

Impact: Internal infrastructure details (database URLs, table names, query fragments) may be displayed to end users or captured in browser logs. This is an information-disclosure risk.

---

**[HIGH] `routes/calls.py` endpoints have no exception handling — a DB failure returns an unformatted 500**

File(s): `api/routes/calls.py:107–121`, `api/routes/calls.py:221–233`, `api/routes/calls.py:260–296`

Finding: `list_calls`, `get_spans`, and `search_transcript` all open `psycopg.connect` directly (bypassing the repository layer) with no `try/except` wrapper. If the database is unreachable, FastAPI's default unhandled exception handler will return a 500 with the following shape:

```json
{"detail": "Internal Server Error"}
```

This is the one place in the codebase where FastAPI's default error shape is used rather than a developer-controlled `HTTPException`. The response shape is consistent with `HTTPException` (both use `{"detail": ...}`), but the content is entirely opaque — no error code, no actionable message.

Additionally, `search_transcript` (lines 260–261) calls `voyageai.Client.embed()` with no exception handling. A Voyage API timeout or auth failure will produce an unhandled 500 whose `detail` will contain the VoyageAI SDK exception text, potentially including the API key hint or rate-limit headers in the SDK's exception string.

Impact: These three endpoints are more fragile than `get_call`, which delegates to repositories (which at least swallow errors silently). Here, any infrastructure failure becomes a raw 500. More critically, the Voyage exception text leaking is a higher-risk variant of the SSE issue above.

---

**[HIGH] `admin.py` analytics endpoints have no exception handling**

File(s): `api/routes/admin.py:88–100`, `api/routes/admin.py:106–135`, `api/routes/admin.py:139–161`, `api/routes/admin.py:164–180`, `api/routes/admin.py:183–202`

Finding: All five analytics GET endpoints (`analytics_sessions`, `analytics_chat`, `analytics_costs`, `analytics_feynman`, `analytics_ingestions`) open `psycopg.connect` and execute SQL with no `try/except` guard. A database failure returns a raw 500 with `{"detail": "Internal Server Error"}`.

The `trigger_ingestion` endpoint at line 206 calls `modal.Function.lookup("earnings-ingestion", "ingest_ticker")` and `fn.spawn(body.ticker)` with no exception handling. If Modal is unreachable, misconfigured, or the function name is wrong, this propagates as an unhandled 500. The client receives no actionable error (e.g., "Modal unavailable — retry later").

Impact: Admin UI has no way to distinguish a broken database connection from a missing Modal deployment from a network timeout. All failures look identical.

---

**[MEDIUM] Error response shape is inconsistent between FastAPI and the Next.js proxy layer**

File(s): `api/routes/calls.py:128–131`, `api/routes/admin.py` (various), `web/app/api/admin/health/route.ts:9–11`, `web/app/api/admin/ingest/route.ts:9–11`

Finding: FastAPI uses `{"detail": "..."}` for all `HTTPException` responses (FastAPI's default). The Next.js proxy route handlers return `{"error": "..."}` for their own early-exit errors (missing env var, unauthenticated, unreachable backend). When the proxy successfully forwards a FastAPI error response (lines 30, 41 of the respective route files), it passes through the FastAPI-shaped `{"detail": "..."}` body with the original status code.

This means the client can receive error payloads with two different keys:
- `{"error": "Not authenticated"}` — from the Next.js layer
- `{"detail": "Admin role required"}` — forwarded from FastAPI

The `web/lib/api.ts` fetch wrapper at line 35 calls `response.text()` and embeds the entire raw body in a thrown `Error` string: `API error ${response.status}: ${message}`. This means the client code that consumes `api.get()` / `api.post()` never has a structured error — it always parses a string. No caller can reliably extract just the error message without string manipulation.

Impact: Any UI component that wants to display a user-facing error message (e.g., "You are not authorized") must parse the error string rather than accessing a consistent field. Different error origins produce different JSON keys. Adding a typed error boundary or centralized error display is unnecessarily difficult.

---

**[MEDIUM] `SchemaRepository.get_current_version` swallows all non-schema exceptions and returns 0**

File(s): `db/repositories.py:44–46`

Finding: The method catches `psycopg.errors.UndefinedTable` specifically (expected case: schema not initialized), but then catches bare `Exception` and also returns `0`. `SchemaRepository.check_health` at line 48 interprets `version == 0` as "schema version table is missing" and returns a human-readable message telling the operator to run `migrate.py`. If `version == 0` was actually caused by a connection failure, the operator gets misleading guidance.

The `admin.py` `/admin/health` endpoint calls `repo.get_current_version()` at line 49 and reports `"connected": version > 0`. A connection failure is reported as `"connected": false` — which is accidentally correct — but the `db.schema_version` field would show `0`, implying an uninitialized schema rather than a connectivity failure.

Impact: Misleading health check output. Operators may run `migrate.py` against a database that is simply unreachable, causing confusion during an outage.

---

**[MEDIUM] `_upsert_session` in `chat.py` has no exception handling — a save failure mid-stream terminates the generator silently**

File(s): `api/routes/chat.py:84–107`, `api/routes/chat.py:135`

Finding: `_upsert_session` issues a raw `psycopg.connect` + `conn.commit()` with no `try/except`. It is called at line 135 inside `_sse_stream`, which is itself wrapped in `try/except Exception` — so a session-save failure will be caught by the outer handler and yield an SSE error event. This is technically safe.

However, the error message emitted will be a psycopg exception string (see the CRITICAL finding on SSE error content), and the streaming context means accumulated tokens are already sent to the client. The client will receive a partial response followed by `{type: error}`, but the `web/lib/chat.ts` reader loop at lines 61–93 does not clear or discard the partial `onToken` calls on receiving `onError`. The UI will display whatever partial text was accumulated, followed by an error state — a confusing experience.

Impact: Session persistence failures produce a visible split-response (partial answer + error banner) without clear UX recovery. Combined with the raw exception string issue, this is user-visible and potentially revealing.

---

**[LOW] `dependencies.py` catches all non-JWT exceptions and returns a generic "Invalid token" 401**

File(s): `api/dependencies.py:61–65`

Finding: The broad `except Exception` at line 61 collapses all JWKS fetch failures, network errors, and unexpected SDK errors into `{"detail": "Invalid token"}`. A JWKS endpoint being unreachable (e.g., Supabase outage) will return 401 "Invalid token" rather than 503 "Authentication service unavailable." This makes it harder to distinguish an attacker submitting a bad token from a configuration or infrastructure failure.

Impact: Ops visibility is reduced. During a Supabase auth outage, all authenticated routes return 401 — easily misread as a mass token expiry or auth misconfiguration rather than a dependency failure.

---

**[LOW] No global exception handler registered on the FastAPI app**

File(s): `api/main.py` (entire file)

Finding: `api/main.py` registers CORS middleware and includes routers, but defines no `@app.exception_handler(Exception)` or similar global handler. FastAPI's default 500 handler returns `{"detail": "Internal Server Error"}` with no request ID, no timestamp, and no structured error code. This is consistent with the `HTTPException` shape only in that both use the `detail` key, but the default 500 response provides no context.

Without a global handler, there is no single place to: sanitize exception messages before they reach the wire, inject a correlation/request ID, log unhandled exceptions with full context, or return a structured error envelope.

Impact: Adding structured error handling later requires touching every route. The absence of a global handler is the root enabler of the raw exception string leak identified in the SSE and Voyage findings above.

---

## Dependency Map

The findings above are ordered by severity and fix dependency:

1. The **global exception handler** (LOW finding, last) is actually the structural fix that would prevent the HIGH/CRITICAL symptoms from reaching the wire. It is the right first fix.
2. The **SSE error string exposure** (HIGH) and **Voyage exception leak** (HIGH) are both direct consequences of no handler sanitization. They are fixed by the global handler plus a dedicated `_sse_stream` sanitization step.
3. The **repository silent-default pattern** (CRITICAL) is independent of the handler; it requires a deliberate design choice about whether repository methods should raise or return a sentinel. Fixing it without the global handler in place risks unhandled 500s surfacing from routes that currently succeed silently.
4. The **error shape inconsistency** (MEDIUM) between `{"error": ...}` and `{"detail": ...}` is a standalone issue independent of the others. Fixing it requires aligning the Next.js proxy layer's early-exit responses to use the same key as FastAPI, or standardizing on an envelope and updating both layers.

Cross-references to other findings documents:
- The repository bypass in `routes/calls.py` is catalogued in `issue-195-layering-boundary-integrity.md` (HIGH finding). Fixing the bypass will also consolidate where exception handling lives for those endpoints.

---

## Recommended Next Steps

**1. Add a global FastAPI exception handler (highest leverage)**

Register `@app.exception_handler(Exception)` in `api/main.py`. This handler should: log the full exception with context, return `{"detail": "Internal server error", "code": "INTERNAL_ERROR"}` (no raw exception text), and emit a request correlation ID. This single change stops raw Python exception strings from escaping across the wire and provides a consistent error shape for all unhandled cases.

**2. Sanitize SSE error events**

In `api/routes/chat.py:158–159`, replace `str(exc)` with a generic message: `"An error occurred during streaming. Please try again."`. Log the full exception server-side. The client already has an `onError` callback path — it just needs a safe string.

**3. Establish a policy for repository failures and apply it consistently**

Two viable options — pick one and apply uniformly:

- *Option A (raise):* Repository methods re-raise after logging. Routes that want to present clean data wrap calls in `try/except` and decide how to handle missing data vs. errors. This is the safest approach for data integrity.
- *Option B (typed sentinel):* Return a typed `Result` or raise a custom `RepositoryError` subclass so callers can distinguish "not found" from "query failed." Routes map `RepositoryError` to 503.

The current approach (return empty default for all failures) should be abandoned. It is the root cause of the CRITICAL finding.

**4. Standardize the error envelope across FastAPI and Next.js**

Pick one key (`detail` is already used by FastAPI everywhere) and update the Next.js proxy early-exit responses in `web/app/api/admin/health/route.ts` and `web/app/api/admin/ingest/route.ts` to use `{ detail: "..." }` instead of `{ error: "..." }`. Update `web/lib/api.ts` to parse the structured `detail` field rather than embedding the raw text into an error string.

**5. Add exception handling to the three unguarded admin analytics endpoints**

Wrap the `psycopg.connect` blocks in `api/routes/admin.py` analytics endpoints in `try/except`. Raise `HTTPException(503, "Analytics database unavailable")` on failure. Apply the same treatment to `trigger_ingestion`'s Modal calls.

**6. Differentiate auth errors from infrastructure errors in `dependencies.py`**

Catch `jwt.PyJWKClientConnectionError` (or equivalent) separately from `jwt.InvalidTokenError` before the broad `except Exception`. Return 503 for JWKS fetch failures rather than 401.
