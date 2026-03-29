# Issue #196: Authentication and Authorization Fragmentation

*Persona: Security Engineer*
*Date: 2026-03-28*

## Summary

The system uses three distinct auth layers — `proxy.ts` middleware, Next.js route handlers, and FastAPI `require_admin` — that are architecturally consistent in intent but inconsistent in the specific mechanisms they use at each boundary. The most significant structural problem is that every Next.js admin route handler checks only for an authenticated session (`getSession()`), not for the admin role, relying entirely on the middleware's role check for access control. Since Next.js API routes under `/app/api/` are not covered by the middleware `matcher` pattern as written, this creates a realistic path where an authenticated non-admin user can directly call the admin API routes and receive data. FastAPI does enforce the role correctly, so the data tier is protected, but the proxy tier is not, and error messages and internal state can leak. There is no `ADMIN_EMAIL` env var check anywhere in the current codebase — that is a previous design pattern that has been removed.

---

## Findings

**[HIGH] Next.js admin API route handlers do not verify the admin role**

File(s):
- `web/app/api/admin/health/route.ts:18–22`
- `web/app/api/admin/ingest/route.ts:18–22`
- `web/app/api/admin/analytics/costs/route.ts:18–22`
- (same pattern in: `analytics/sessions`, `analytics/chat`, `analytics/feynman`, `analytics/ingestions`)

Finding: Every admin route handler checks only `supabase.auth.getSession()` — it verifies the user is authenticated, but does not verify the user has the `admin` role. The admin role check lives only in `proxy.ts:44–54`, which guards page routes under `/admin`. The `proxy.ts` `matcher` pattern (`/((?!_next/static|_next/image|favicon.ico|.*\\.(?:svg|png|jpg|jpeg|gif|webp)$).*)`) does match `/api/admin/*` paths, so the middleware does run for those API routes. However, within the middleware, the admin role check is only applied when `pathname.startsWith("/admin")` (line 43) — and Next.js API routes live at `/api/admin/*`, not `/admin/*`. The prefix test fails for API routes, so the role check in the middleware is silently skipped for all API calls.

Impact: Any authenticated user (non-admin) can call `POST /api/admin/ingest`, `GET /api/admin/health`, and all analytics routes directly. The FastAPI backend will enforce the role, so actual data operations are blocked there, but:
1. Error messages from FastAPI (e.g., "Admin role required") are proxied back to the caller, confirming the route exists and is reachable.
2. If the FastAPI URL is ever unreachable (502), the handler still returns a response without having enforced the role — the route just proxied a network error rather than a 403.
3. Future route handlers that forget to proxy to FastAPI (or that add local logic before the proxy call) would have no role gate at all.

---

**[HIGH] `getSession()` is used in route handlers instead of `getUser()`**

File(s):
- `web/app/api/admin/health/route.ts:17`
- `web/app/api/admin/ingest/route.ts:17`
- `web/app/api/admin/analytics/costs/route.ts:17`
- `web/lib/api.ts:17`
- `web/lib/chat.ts:30`
- `web/app/admin/page.tsx:51`
- `web/app/admin/health/page.tsx:34`

Finding: `supabase.auth.getSession()` reads the session from the cookie store without contacting the Supabase Auth server. It trusts the local session data. In contrast, `proxy.ts:32` correctly uses `supabase.auth.getUser()`, which makes a network request to verify the JWT with the Auth server. The Supabase documentation explicitly warns that `getSession()` should not be used for server-side auth checks because the session data in the cookie can be tampered with by the client.

The divergence is intentional-looking but is a security gap: the middleware validates the token properly, but once past the middleware, all subsequent server-side checks in route handlers use the weaker `getSession()`.

Impact: A user who can forge or replay a session cookie could potentially pass the `getSession()` check in a route handler even if their JWT has been revoked. The window is small — Supabase JWTs are short-lived and the middleware refresh handles the normal case — but the pattern establishes a weaker-than-necessary boundary inside the trusted Next.js server context.

---

**[MEDIUM] The middleware admin path check uses `/admin` but API routes live at `/api/admin`**

File(s): `web/proxy.ts:43`

Finding: `if (user && pathname.startsWith("/admin"))` — this condition will never be true for requests to `/api/admin/*`. The two route trees are distinct. The admin role enforcement in the middleware therefore applies only to page routes (`/admin`, `/admin/health`, `/admin/ingest`) and never to API routes (`/api/admin/health`, `/api/admin/ingest`, etc.).

Impact: As noted in the HIGH finding above, this means the middleware's role check provides no protection for the API surface. The fix requires either (a) extending the condition to also match `/api/admin`, or (b) moving the role check into the route handlers themselves. Option (b) is more robust because it does not rely on a path string match that can diverge as routes are added.

---

**[MEDIUM] `lib/api.ts` calls FastAPI directly from the browser using `getSession()`**

File(s): `web/lib/api.ts:14–27`

Finding: `apiFetch()` creates a browser Supabase client, reads the session via `getSession()`, and attaches the access token directly to a `fetch()` call to `NEXT_PUBLIC_API_URL`. This means some FastAPI calls bypass the Next.js proxy layer entirely and come from the browser. Two consequences: (1) the FastAPI URL is exposed to the browser via `NEXT_PUBLIC_API_URL`; (2) the `getSession()` token attached here is not validated against the Auth server before being sent to FastAPI.

FastAPI will validate the JWT independently via JWKS (`dependencies.py:49–55`), so the data tier is still protected. But the architecture is inconsistent: some admin-adjacent API calls go browser → FastAPI directly, others go browser → Next.js proxy → FastAPI. The direct path is harder to audit and rate-limit centrally.

---

**[MEDIUM] The OAuth callback `next` parameter is an open redirect**

File(s): `web/app/auth/callback/route.ts:8,23`

Finding: `const next = searchParams.get("next") ?? "/"` followed by `NextResponse.redirect(\`${origin}${next}\`)`. The `next` value comes from an attacker-controlled query string. While `origin` is prepended (which prevents off-site redirects to a different domain), the path portion is not validated. An attacker could craft a callback URL with `?next=/some/sensitive/path` or `?next=%2Fauth%2Fcallback%3Fnext%3D...` to chain redirects. The PKCE state parameter is not validated here — that is delegated entirely to `supabase.auth.exchangeCodeForSession(code)`, which is correct for Supabase's PKCE flow. However the `next` redirect target is not constrained to a known-good allowlist.

Impact: Post-auth redirect to unexpected application paths. Not an account takeover vector (origin is fixed), but a phishing aid if combined with a malicious path that renders attacker-controlled content.

---

**[MEDIUM] `SUPABASE_JWT_SECRET` appears in the health check env var list**

File(s): `web/app/api/admin/routes.py` (FastAPI): `api/routes/admin.py:39`

Finding: `_HEALTH_ENV_VARS = ["VOYAGE_API_KEY", "PERPLEXITY_API_KEY", "MODAL_TOKEN_ID", "SUPABASE_JWT_SECRET"]`. The health endpoint reports whether `SUPABASE_JWT_SECRET` is set (`bool(os.environ.get(key))`). The JWT secret is a signing secret — its presence or absence is operational information that should not be surfaced in an API response, even a boolean. If the response is ever cached, logged, or leaked, it tells an attacker which signing materials are in scope. Additionally, the FastAPI JWT validation uses JWKS (`dependencies.py:21–24`), not a raw secret, raising the question of whether `SUPABASE_JWT_SECRET` is actually needed at all.

Impact: Information disclosure. Low direct exploitability but inconsistent with least-disclosure principle.

---

**[LOW] `web/lib/api.ts` throws at module load if `NEXT_PUBLIC_API_URL` is unset**

File(s): `web/lib/api.ts:5–7`

Finding: The module-level `throw` (`if (!API_URL) { throw new Error(...) }`) runs when the module is first imported. In a server-side Next.js context this will crash the process rather than returning a structured error to the client. All route handlers and server components that import this module will fail at startup rather than at the point of use.

Impact: Poor operational resilience. Missing env var causes a hard crash rather than a graceful 500. This is a reliability issue, not a security issue, but it is noted here because it affects the availability of auth-related routes.

---

## Dependency Map

```
Fix 1 (route handler role check) unblocks:
  → MEDIUM finding: middleware path mismatch (becomes irrelevant once handlers self-enforce)

Fix 2 (getUser instead of getSession in route handlers) is independent.

Fix 3 (callback next validation) is independent.

Fix 4 (SUPABASE_JWT_SECRET in health response) is independent.

Fix 5 (api.ts direct browser→FastAPI path) is architectural;
  → should be addressed as part of the broader layering boundary work in issue #195.
```

Cross-references:
- Issue #195 (Layering Boundary Integrity): `lib/api.ts` calling FastAPI directly from the browser is the same boundary violation documented there. Auth fragmentation in that path is a consequence of the boundary problem, not an independent root cause.

---

## Recommended Next Steps

**1. Add the admin role check to every Next.js admin route handler (HIGH, immediate)**

Each of the seven `web/app/api/admin/*/route.ts` files should verify the admin role using `profiles.role` before proxying to FastAPI. The check should use `getUser()` (not `getSession()`) to match the trust level the middleware uses. This is the highest-leverage fix: it closes the bypass path regardless of how the middleware matcher is configured, and it makes each handler independently safe.

**2. Replace `getSession()` with `getUser()` in all server-side auth checks (HIGH)**

In route handlers and server components that use the Supabase client server-side, replace `supabase.auth.getSession()` with `supabase.auth.getUser()`. The middleware already does this correctly. The fix should be applied to: all `web/app/api/admin/*/route.ts` files, `web/app/admin/page.tsx`, and `web/app/admin/health/page.tsx`.

**3. Constrain the `next` redirect in `callback/route.ts` to known paths (MEDIUM)**

Validate the `next` parameter against a static allowlist of permitted post-auth destinations (e.g., `/`, `/admin`, `/admin/health`, `/admin/ingest`) before redirecting. Reject or ignore values that do not match.

**4. Remove `SUPABASE_JWT_SECRET` from the health check env var list (MEDIUM)**

Remove it from `_HEALTH_ENV_VARS` in `api/routes/admin.py:39`. Audit whether the secret is actually used anywhere — if FastAPI validates tokens via JWKS (which it does), the raw secret may be an unused legacy value that can be removed from the deployment environment entirely.

**5. Extend the middleware admin path check or remove it (MEDIUM)**

Either extend `proxy.ts:43` to `pathname.startsWith("/admin") || pathname.startsWith("/api/admin")`, or remove the middleware role check for API routes entirely in favor of the handler-level check introduced in step 1. The second option is preferred: defense-in-depth is valuable, but a middleware check that silently misses API routes gives false confidence.
