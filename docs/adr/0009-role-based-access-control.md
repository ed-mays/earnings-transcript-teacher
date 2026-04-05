# Role-Based Access Control

**Status:** Accepted
**Date:** 2026-03-27

## Context

The rewrite introduced multi-user authentication via Supabase (ADR 0004). The application needed an authorization model to distinguish between regular users (learners) and administrators who can manage transcripts, trigger ingestion, and access admin-only endpoints. The auth fragmentation analysis (`docs/architecture-review/findings/issue-196-auth-fragmentation.md`) evaluated approaches to enforce access control consistently across the API.

## Decision

Implement a simple two-role model using a custom `user_role` PostgreSQL enum (`admin` | `learner`) stored in a `profiles` table. A `SECURITY DEFINER` trigger auto-provisions a profile row with the default `learner` role when a new user is created in Supabase Auth.

Access control is enforced at two levels:

- **Database level:** Row Level Security policies use `auth.uid()` to restrict data access per user
- **API level:** FastAPI dependency injection (`RequireAdminDep` in `api/dependencies.py`) checks the user's role from the `profiles` table before allowing admin-only operations

## Alternatives considered

1. **Supabase built-in RBAC (custom claims in JWT)** — Storing roles as custom claims in the Supabase JWT token. Rejected because: (a) Supabase custom claims require a database function to set and are immutable for the token's lifetime (role changes don't take effect until re-authentication), and (b) the `profiles` table approach allows role checks against live data and supports future role extensions without JWT schema changes.

2. **External authorization service (Clerk, Auth0 RBAC, Oso)** — Using a dedicated authorization provider. Rejected because: (a) two roles with a single SQL check don't justify an external service, (b) it would add another dependency and network hop for every authorized request, and (c) Supabase's RLS already provides database-level enforcement that external services can't replicate without proxying all database access.

3. **Permission-based model (fine-grained permissions)** — Defining granular permissions (`can_ingest`, `can_delete_transcript`, `can_view_analytics`) instead of broad roles. Rejected because the current feature set maps cleanly to two roles, and permission-based models add configuration complexity that isn't justified until there are at least 3–4 distinct access patterns.

4. **No authorization (auth-only, all users equal)** — Relying solely on authentication without role differentiation. Rejected because the ingestion pipeline triggers expensive LLM calls that should be restricted to administrators, and future features (analytics dashboards, user management) require admin-only access.

## Consequences

**Easier:**
- Two roles are trivial to understand, implement, and test
- Auto-provisioned profiles mean no separate registration step — sign up via Supabase Auth and a profile is created automatically
- RLS policies and API dependencies use the same `profiles` table, ensuring consistency
- Role checks are a single SQL query per request (cached in the connection for the request lifecycle)

**Harder:**
- Adding a third role (e.g., `instructor`) requires a schema migration to alter the enum and updating all RLS policies
- Role assignment is manual (database UPDATE) — no self-service role management UI
- The `SECURITY DEFINER` trigger runs with elevated privileges, which requires careful SQL to avoid privilege escalation
- No audit trail for role changes — would need to add a separate audit table if compliance requires it
