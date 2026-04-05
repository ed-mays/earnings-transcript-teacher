# Data Retention Policy

**Status:** Accepted
**Date:** 2026-03-30

> **Note:** This decision has **Medium confidence** in rationale reconstruction. The retention thresholds (90 days for sessions, 1 year for analytics) were found in migration SQL comments but the original analysis or user research that determined these specific values was not documented. The Alternatives Considered section below reflects reasonable inferences; the actual evaluation may have been less formal.

## Context

The application generates learning session records and analytics events that grow unboundedly over time. Without automated cleanup, the Supabase-managed PostgreSQL database would accumulate stale data, increasing storage costs and potentially degrading query performance on tables that are frequently scanned (e.g., analytics dashboards). The production readiness backlog identified data retention as a requirement.

## Decision

Implement automated data cleanup via pg_cron scheduled jobs running inside Supabase's PostgreSQL:

- Learning sessions older than 90 days are deleted automatically
- Analytics events older than 1 year are deleted automatically

The jobs are defined in `supabase/migrations/20260330000001_retention_cleanup.sql` and managed entirely within the database — no application-level cron infrastructure required.

The key driver was keeping cleanup within the database layer where it can execute efficiently (bulk DELETE with index scans) without requiring a separate scheduler service or application-level batch job.

## Alternatives considered

1. **No automated cleanup** — Relying on manual database maintenance. Rejected because storage growth is predictable and unbounded, and manual intervention is easy to forget. For a managed database with storage-based pricing, automated cleanup is operationally necessary.

2. **Application-level batch jobs (FastAPI scheduled task or Modal cron)** — Running cleanup as an API endpoint triggered by an external scheduler. Rejected because: (a) it adds an external dependency (the scheduler must be running and authenticated), (b) application-level DELETE loops are slower than database-internal bulk operations, and (c) if the application is down, cleanup stops — whereas pg_cron runs inside PostgreSQL regardless of application state.

3. **Soft deletes with archival** — Marking records as deleted and moving them to an archive table or cold storage. Not chosen because: (a) the data has limited long-term value (learning sessions are ephemeral by nature), and (b) soft deletes add query complexity (every query needs a `WHERE deleted_at IS NULL` filter). Archival could be added later if analytics requirements change.

4. **Supabase Edge Functions on a cron schedule** — Running cleanup as a Supabase Edge Function. Rejected because pg_cron is simpler for pure SQL operations and doesn't require a separate JavaScript runtime for what is essentially a `DELETE FROM ... WHERE created_at < NOW() - INTERVAL '...'`.

## Consequences

**Easier:**
- Storage growth is bounded and predictable
- No external scheduler to manage — pg_cron is built into Supabase's PostgreSQL
- Cleanup runs even if the application is down or being redeployed
- Retention thresholds are visible in migration SQL files (version controlled)

**Harder:**
- Retention thresholds are baked into SQL migrations — changing them requires a new migration
- No soft-delete recovery — data is permanently removed (acceptable for ephemeral session data)
- pg_cron job failures are only visible in PostgreSQL logs, not application monitoring
- If retention thresholds prove too aggressive, historical data cannot be recovered
