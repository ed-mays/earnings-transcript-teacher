# Issue #195: Layering and Boundary Integrity (FastAPI / Next.js)

*Persona: Senior Backend Architect*
*Date: 2026-03-28*

## Summary

The overall layering posture is good: the Next.js admin route handlers are disciplined thin proxies, the FastAPI dependency injection handles auth and RBAC cleanly, and the SSE streaming contract between `lib/chat.ts` and `routes/chat.py` is well-specified. Two structural issues stand out. First, the `/calls/[ticker]/learn` page is a `"use client"` page that re-fetches `CallDetail` at runtime from the browser purely to generate UI suggestions — data the parent server component already fetched on the same render path. Second, `routes/calls.py` bypasses the repository layer entirely, issuing raw psycopg queries inline for every endpoint except `get_call`, which creates split responsibility for the same data. Several smaller SSE and data-transformation issues are catalogued below.

---

## Findings

---

**[HIGH] Learn page re-fetches CallDetail client-side when the data is already available server-side**

File(s): `web/app/calls/[ticker]/learn/page.tsx:30–38`

Finding: `LearnPage` is a `"use client"` component that fires `api.get<CallDetail>(`/api/calls/${ticker}`)` in a `useEffect` on mount. This round-trips to FastAPI from the browser solely to extract `themes` and `keywords` for the `buildSuggestions` call. The parent route `web/app/calls/[ticker]/page.tsx` already fetches the same `CallDetail` server-side. Because `LearnPage` is a separate route (`/calls/[ticker]/learn`), the parent's data is not in scope, but the fix does not require a `useEffect`; it requires either (a) fetching `CallDetail` in a server wrapper around `LearnPage` and passing `themes`/`keywords` as props, or (b) having FastAPI expose a lightweight `/api/calls/:ticker/suggestions` endpoint that returns only the pre-computed suggestion strings so the client fetch is narrowly scoped.

Impact: Every chat session open triggers a full `CallDetail` fetch (speakers, evasion analyses, strategic shifts, topics, keywords — all of it) from the browser. This is wasted bandwidth and latency on the hot path. If the API is slow or unreachable the `useEffect` silently degrades (`catch(() => {})`), which is intentional, but it means the full-detail fetch never had a reason to be in this component in the first place.

---

**[HIGH] `routes/calls.py` bypasses the repository layer for spans, search, and the list endpoint**

File(s): `api/routes/calls.py:107–121`, `api/routes/calls.py:204–233`, `api/routes/calls.py:257–297`

Finding: `list_calls`, `get_spans`, and `search_transcript` all open `psycopg.connect` directly and execute inline SQL. Only `get_call` (lines 134–135) uses `CallRepository` and `AnalysisRepository`. The `db/repositories.py` file already has `AnalysisRepository.get_spans_for_ticker` and `EmbeddingRepository.search_spans`. `list_calls` duplicates what `CallRepository.get_all_calls` already does (though the route projection differs slightly — it omits `fiscal_quarter`). The `get_spans` endpoint adds pagination and filtering that don't exist in the repository, so it has reasonable justification for a custom query, but the query is still inline rather than on a repository method.

Impact: Database access conventions are split between the repository pattern and inline psycopg calls within the same module. The `_db_url()` helper is duplicated across `calls.py`, `chat.py`, and `admin.py` (three copies, lines 15–17, 30–32, 80–82 respectively). Schema changes require hunting down raw queries across route files rather than updating a single repository.

Dependency note: Fixing this is a prerequisite for making the data layer independently testable via mock repositories.

---

**[HIGH] `routes/chat.py` contains session management and persistence logic that belongs in a service layer**

File(s): `api/routes/chat.py:49–107`, `api/routes/chat.py:172–225`

Finding: The `chat` endpoint handler directly calls `_load_session` and `_upsert_session`, which are module-level functions containing psycopg logic, JSON serialisation of the session state, and ownership checks. Session ownership enforcement (line 66–69), session note serialisation (line 92), and the UPSERT SQL (lines 94–106) all live in `routes/chat.py`. This is business logic and persistence logic embedded in a route module. The repository pattern used elsewhere (`db/repositories.py`) has no corresponding `LearningSessionRepository`. As a result, the session contract (schema for `notes` JSONB, the `completed_at` coalesce logic) is encoded only in this one route and cannot be reused or tested in isolation.

Impact: Any change to the session data model (adding fields to `notes`, changing stage logic) touches a route file instead of a repository. The ownership check is only applied via `_load_session`; if a second endpoint ever reads sessions (e.g. a history endpoint), that check must be manually replicated.

---

**[MEDIUM] SSE stream swallows the incomplete-buffer remainder on connection close**

File(s): `web/lib/chat.ts:61–94`

Finding: After the `while (true)` read loop exits on `done === true`, the code breaks out of the loop without processing `buffer`. Any SSE event that arrived in the last TCP segment without a trailing `\n\n` will be silently discarded. This is the standard partial-frame problem with manual SSE parsing. The `buffer` variable is never flushed after the loop.

Impact: The `done` event from the server — `{"type":"done","session_id":"..."}` — arrives as the last event before the stream closes. If it happens to land in a segment without a trailing double-newline (unlikely in practice but possible under load or proxying), `onDone` is never called. The UI ends up stuck in `isStreaming: true` with no session ID persisted to state.

---

**[MEDIUM] SSE stream has no timeout or abort path for hung connections**

File(s): `web/lib/chat.ts:21–95`

Finding: `streamChat` issues a plain `fetch` with no `AbortController` and no timeout. If the FastAPI process stalls mid-stream (e.g. Perplexity API hangs), the `reader.read()` call will block indefinitely. There is no way for the caller to cancel the stream (e.g. when the user navigates away or clicks "New session"). The `handleNewSession` function in `learn/page.tsx` (line 70–75) clears local state but cannot cancel the underlying fetch — the in-flight HTTP connection continues consuming server resources.

Impact: A stalled stream leaks both a browser connection and the FastAPI `StreamingResponse` generator. Under concurrency, this can exhaust connection pools.

---

**[MEDIUM] `_sse_stream` in `routes/chat.py` emits error events but the generator continues to yield**

File(s): `api/routes/chat.py:158–159`

Finding: The `except Exception` block in `_sse_stream` yields an error event and then returns (the generator ends). However, `_upsert_session` (line 135) is called before the `yield done` line. If `_upsert_session` raises (e.g. a DB timeout), the error `except` catches it and emits `{"type":"error"}`, but the session is not persisted. More importantly, `track("chat_turn", ...)` at line 136 is also inside the try block before `yield done`, meaning analytics are tracked before the `done` event is actually sent — a partially-consumed stream will be logged as a completed turn.

Impact: Analytics over-count completed turns when the stream errors mid-way. Session persistence is silently skipped on DB errors with no retry or visibility.

---

**[MEDIUM] `feynman_stage_completed` is tracked unconditionally at session start, not at stage completion**

File(s): `api/routes/chat.py:216`

Finding: On line 216, `track("feynman_stage_completed", ...)` is called inside the `else` branch that fires when `body.session_id` is `None` (i.e. a new session is created). This fires at session *creation*, not when a stage is completed. The event name suggests it marks the end of a stage, but it is emitted at the start.

Impact: The `analytics_feynman` endpoint in `admin.py` queries this event to report stage completion rates. The current data is stage *start* counts mislabelled as completions, which makes the admin dashboard misleading.

---

**[MEDIUM] `proxy.ts` performs an extra DB round-trip for every request to `/admin` routes**

File(s): `web/proxy.ts:43–55`

Finding: The middleware queries `profiles.role` via Supabase on every request to any `/admin/*` path. This is the correct place for a redirect guard. However, `api/dependencies.py:80–90` (`require_admin`) also queries `profiles.role` in FastAPI via the `RequireAdminDep` dependency. For the server-side proxy routes (e.g. `route.ts` for health and costs), this means two `profiles` lookups occur on each admin action: one in Next.js middleware (Supabase JS client) and one in FastAPI (`psycopg` direct). Neither is wrong in isolation, but the duplication is invisible and will silently double the admin route latency on every call.

Impact: Operational overhead, not a correctness issue. If the `profiles` table ever becomes a bottleneck, this will be hard to diagnose because the duplication spans two services.

---

**[LOW] `CallDetail` type is defined in both `routes/calls.py` and `web/components/transcript/types`**

File(s): `api/routes/calls.py:62–74`, `web/app/calls/[ticker]/learn/page.tsx:11`

Finding: The `CallDetail` Pydantic model in `routes/calls.py` is the authoritative shape. The TypeScript `CallDetail` imported by the learn page from `@/components/transcript/types` is a hand-maintained parallel. Any field addition or rename on the Python side requires a manual update on the TypeScript side with no tooling enforcement.

Impact: Low probability of immediate breakage (the API contract is stable), but a latent drift risk. The TypeScript type `CallDetail` in the learn page's `useEffect` cast (`api.get<CallDetail>(...)`) will not fail at runtime if new fields appear or optional fields are removed — TypeScript `as Promise<T>` in `api.ts:38` is a cast, not a parse.

---

**[LOW] `routes/calls.py` opens a new `psycopg` connection for every query within a single `get_call` request**

File(s): `api/routes/calls.py:125–186`

Finding: `get_call` makes seven separate repository or inline calls, each of which calls `psycopg.connect(...)`. That is up to seven separate TCP connections opened and closed for one HTTP request. There is no connection pooling configured in either `routes/calls.py` or `db/repositories.py`. The `dependencies.py` `get_db` dependency (lines 28–35) provides a shared connection per request, but `routes/calls.py` does not use it for these calls — it constructs repositories by passing `db_url` string and lets each repository open its own connection.

Impact: Latency and connection count scale with query count per request rather than being bounded per request. Under moderate traffic, Postgres `max_connections` will be reached faster than expected.

Dependency note: Fixing the repository bypass (HIGH finding above) is a prerequisite for addressing this, since using `get_db` consistently would naturally consolidate the connection.

---

## Dependency Map

```
[LOW] connection-per-query
    └── depends on [HIGH] bypass repository layer
            └── depends on [MEDIUM] chat.py session logic extraction
                    (independent: [HIGH] learn page re-fetch)
                    (independent: [MEDIUM] SSE buffer remainder)
                    (independent: [MEDIUM] SSE no abort path)
                    (independent: [MEDIUM] error tracking order)
                    (independent: [MEDIUM] stage tracking mislabelled)
                    (independent: [MEDIUM] dual admin role lookup)
                    (independent: [LOW] CallDetail type drift)
```

---

## Recommended Next Steps

1. **Add `LearningSessionRepository` to `db/repositories.py` and move `_load_session` / `_upsert_session` there.** This eliminates the most egregious business-logic-in-a-route violation and makes session ownership enforcement reusable. It is a self-contained refactor with high test leverage. Do this before any session feature work (history, replay, export).

2. **Move all raw psycopg queries in `routes/calls.py` onto repository methods.** Start by updating `list_calls` to call `CallRepository.get_all_calls` (adjusting its projection if needed). For `get_spans` and `search_transcript`, add `get_spans_paginated` and `search_spans_with_similarity` methods to `AnalysisRepository` and `EmbeddingRepository` respectively. Centralise `_db_url()` into a shared module or use the `get_db` dependency consistently.

3. **Fix the `feynman_stage_completed` tracking event.** Move the `track("feynman_stage_completed", ...)` call from session creation (line 216) to the end of `_sse_stream` after the `yield done` line, triggered by a parameter indicating the stage that just completed. This is a one-line move with immediate dashboard accuracy payoff.

4. **Flush the SSE buffer after the read loop closes.** After `if done: break`, process any remaining content in `buffer` using the same event-parsing logic before returning from `streamChat`. This closes the partial-frame edge case on the hot path (last event = done event).

5. **Add `AbortController` support to `streamChat`.** Thread an optional `signal` parameter through `streamChat` and wire it to the `fetch` call. Call `controller.abort()` in `handleNewSession` and on component unmount. This bounds the server-side resource leak.

6. **Replace the `api.get<T>()` cast with Zod parsing for `CallDetail`.** The `as Promise<T>` in `api.ts:38` is a type assertion, not a runtime guarantee. Define a Zod schema for `CallDetail` on the frontend and parse responses through it. This closes the type-drift gap between the Python and TypeScript models and surfaces schema changes at runtime rather than silently.

7. **Consolidate the learn page's `CallDetail` fetch into a server component.** Wrap `LearnPage` in a server component that fetches `CallDetail` and passes `themes` and `keywords` as props (or use a dedicated `/api/calls/:ticker/suggestions` endpoint). Remove the `useEffect` fetch from the client entirely. This eliminates the full `CallDetail` over-fetch on every chat session open.
