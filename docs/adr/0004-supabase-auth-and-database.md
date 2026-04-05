# Supabase for Auth and Database

**Status:** Accepted
**Date:** 2026-03-26

## Context

The rewrite (ADR 0001) required both a PostgreSQL database (to preserve the existing schema with pgvector) and a multi-user authentication system. The original prototype had no authentication and used a local PostgreSQL instance. The target architecture needed JWT-based auth, role-based access control, and a managed database that could handle serverless connection patterns (many short-lived connections from API and pipeline processes).

## Decision

Use Supabase as the combined database and authentication provider. Supabase provides:

- **Managed PostgreSQL** with pgvector extension support, preserving the existing schema
- **JWT-based authentication** with auto-generated JWKS endpoints for token verification
- **Row Level Security (RLS)** policies that enforce access control at the database level
- **Transaction pooler** (port 6543) for serverless-friendly connection management
- **Supabase CLI** for migration management (`supabase/migrations/` as single source of truth)

The key drivers were PostgreSQL compatibility (no schema rewrite needed) and the tight integration between auth and database (RLS policies reference `auth.uid()` directly).

## Alternatives considered

1. **Firebase (Auth + Firestore)** — The original target architecture's choice (`docs/architecture-review/02-target-architecture.md`). Rejected because: (a) Firestore's document model would require rewriting all relational queries and abandoning pgvector, (b) the existing schema with foreign keys, joins, and vector similarity search maps naturally to PostgreSQL but poorly to a document store, and (c) migrating ~20 tables with complex relationships to Firestore would consume significant effort for no product benefit.

2. **Clerk (auth) + Neon (database)** — Separate best-of-breed providers for auth and database. A viable alternative that would have worked well. Not chosen because: (a) Supabase provides both in a single platform with RLS integration, reducing the number of services to manage, and (b) Clerk's webhook-based profile sync adds latency compared to Supabase's native `auth.uid()` in SQL policies. This remains a strong migration path if Supabase auth proves limiting.

3. **Auth0 + managed PostgreSQL (RDS/Cloud SQL)** — Enterprise auth with a managed database. Rejected because Auth0's pricing scales with monthly active users, which is overkill for a learning tool, and RDS/Cloud SQL require more infrastructure management than Supabase's managed offering.

4. **Self-managed PostgreSQL + custom JWT auth** — Running PostgreSQL on a VPS with hand-rolled JWT validation. Rejected because managing database backups, upgrades, connection pooling, and a custom auth system would consume time better spent on product features.

## Consequences

**Easier:**
- Existing PostgreSQL schema migrated with minimal changes (pgvector, foreign keys, indexes all preserved)
- Authentication is a managed service — no password hashing, session management, or token refresh logic to build
- RLS policies enforce access control even if application-level checks are bypassed
- The transaction pooler handles connection limits for serverless patterns (Modal functions, API pool)
- Supabase CLI manages migrations as SQL files in version control

**Harder:**
- Vendor lock-in to Supabase's auth implementation (JWT format, JWKS endpoint, `auth.uid()` function)
- Direct Supabase connection via psql fails DNS on newer projects — must use SQL Editor for ad-hoc queries
- Free tier limits on database size and auth users require upgrading for production
- Supabase's managed infrastructure means less control over PostgreSQL configuration and extensions
