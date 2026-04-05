# Rate Limiting Strategy

**Status:** Accepted
**Date:** 2026-03-29

## Context

The application exposes several endpoints that trigger expensive operations: chat (LLM API calls to Perplexity), search (embedding API calls to Voyage AI), and ingest (multi-tier LLM pipeline via Claude). Without rate limiting, a single user or bot could exhaust API quotas and run up significant costs. The production readiness backlog identified rate limiting as a gate for production deployment.

## Decision

Implement rate limiting at two levels:

**Application-level (per-endpoint):**
- Chat: 60 requests per hour per user
- Search: 100 requests per hour per user
- Ingest: 600-second cooldown per user per ticker (prevents re-ingesting the same transcript repeatedly)

Limits are configured as constants in `api/settings.py` and enforced via FastAPI middleware.

**LLM service-level (token-bucket):**
- A custom `RateLimiter` class in `services/llm.py` implements token-bucket rate limiting with dual RPM (requests per minute) and RPS (requests per second) limits
- Exponential backoff retry for transient provider errors (429, 500, 503)

## Alternatives considered

1. **Redis-based distributed rate limiting** — Using Redis (e.g., Upstash) with sliding window counters for rate limiting across multiple instances. Rejected because: (a) the application runs as a single Railway instance, so in-process limiting is sufficient, (b) adding Redis as a dependency for rate limiting alone is over-provisioning, and (c) in-process token-bucket is simpler to debug and reason about. Redis-based limiting should be reconsidered if the application scales to multiple instances.

2. **API Gateway rate limiting (Railway/Cloudflare)** — Using infrastructure-level rate limiting before requests reach the application. Not chosen because: (a) Railway doesn't provide built-in rate limiting, (b) adding Cloudflare or an API gateway would add infrastructure complexity, and (c) the per-endpoint limits need application context (user identity, ticker) that gateway-level limiting can't provide.

3. **Third-party rate limiting library (slowapi, limits)** — Using an existing Python rate limiting library. A reasonable alternative — `slowapi` wraps `limits` and integrates with FastAPI. Not chosen because: (a) the per-endpoint limits have custom logic (ticker-based cooldown for ingest) that doesn't fit the library's decorator pattern cleanly, and (b) the LLM service layer needs its own rate limiter with retry logic, which no library provides out of the box.

4. **No application-level rate limiting (rely on provider limits)** — Letting Anthropic, Perplexity, and Voyage AI enforce their own rate limits and handling 429 errors. Rejected because: (a) provider rate limits are shared across all API consumers, not per-user, (b) hitting provider limits means all users are affected, not just the abusive one, and (c) cost control requires limiting before API calls are made, not after.

## Consequences

**Easier:**
- Per-user rate limits prevent any single user from exhausting shared API quotas
- The token-bucket implementation with exponential backoff handles transient provider errors gracefully
- Rate limit configuration is centralized in `api/settings.py`
- The ingestion cooldown prevents accidental duplicate processing

**Harder:**
- In-process rate limiting is lost on server restart (rate limit counters reset)
- Single-instance assumption — rate limits are not coordinated across instances if the application scales
- Rate limit values are hardcoded constants — no dynamic adjustment based on current API quota usage
- No rate limit response headers (X-RateLimit-Remaining, etc.) for client-side awareness
