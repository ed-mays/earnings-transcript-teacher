# Connection Pooling Strategy

**Status:** Accepted
**Date:** 2026-03-28

## Context

The architecture review's synthesis remediation plan identified that the original code opened a new TCP connection per repository method call, which would exhaust Supabase's connection limits under moderate load. The FastAPI backend needs concurrent database access from multiple request handlers, and the Modal pipeline opens connections from ephemeral serverless containers. Both patterns require connection management that avoids overwhelming the database.

## Decision

Use psycopg3's built-in `ConnectionPool` (min=2, max=10) initialized during the FastAPI lifespan event. Connections are checked out per-request via FastAPI dependency injection (`DbDep` in `api/dependencies.py`) and returned to the pool when the request completes. Test environments fall back to direct `psycopg.connect()` calls to avoid pool initialization complexity in test fixtures.

A slow query threshold (500ms) triggers warning-level log entries for performance monitoring.

## Alternatives considered

1. **Supabase's PgBouncer (transaction pooler on port 6543)** — Supabase provides a built-in PgBouncer instance. The application actually uses both — the `DATABASE_URL` connects through Supabase's transaction pooler, and psycopg3's `ConnectionPool` manages the application-side connection lifecycle. This layered approach was chosen deliberately: PgBouncer handles connection multiplexing at the database level, while the application pool prevents opening excessive connections to PgBouncer itself.

2. **No application-side pooling (PgBouncer only)** — Relying solely on Supabase's PgBouncer without an application pool. Rejected because: (a) each `psycopg.connect()` call still establishes a TCP connection to PgBouncer, which has its own connection limits, and (b) connection establishment overhead (TLS handshake, authentication) on every request adds measurable latency.

3. **SQLAlchemy connection pool** — Using SQLAlchemy's engine as a pool manager without the ORM. A viable option, but rejected because it would add SQLAlchemy as a dependency solely for pooling when psycopg3 provides a native pool implementation that integrates directly with its connection objects.

4. **External connection pooler (PgBouncer self-hosted)** — Running a dedicated PgBouncer instance on Railway. Rejected because Supabase already provides PgBouncer, and adding another pooling layer would increase complexity without meaningful benefit at the current scale.

## Consequences

**Easier:**
- Connection reuse eliminates per-request TCP and TLS handshake overhead
- Pool size limits prevent the application from overwhelming Supabase's connection limits
- FastAPI dependency injection provides clean connection lifecycle management (checkout on request start, return on request end)
- Slow query logging enables performance monitoring without external APM tools

**Harder:**
- Pool configuration (min/max sizes) needs tuning as traffic patterns change
- Pool initialization during FastAPI lifespan means the application fails to start if the database is unreachable
- Test environments use a different connection strategy (direct connect) than production (pooled), which could mask pool-specific bugs
- The dual-pool architecture (application pool → PgBouncer → PostgreSQL) can make connection debugging more complex
