# RLS Verification Runbook

**Trigger:** Run this checklist after any schema migration that touches `learning_sessions`, `analytics_events`, `profiles`, or any future table that stores user data.

---

## Why this matters

Supabase Row Level Security (RLS) is a database-layer defence that prevents a client-role connection (anon key + user JWT) from reading another user's rows even if the application layer has a bug or a key is compromised. Migrations that alter a table's structure can, in rare cases, interact with policy definitions — so a quick verification step is worth the 60 seconds it takes.

---

## Step 1 — Verify RLS is enabled on all user-data tables

Run in the **Supabase SQL Editor**:

```sql
SELECT tablename, rowsecurity
FROM pg_tables
WHERE schemaname = 'public'
  AND tablename IN ('learning_sessions', 'analytics_events', 'profiles')
ORDER BY tablename;
```

Expected result: `rowsecurity = true` for all three rows.

If any row shows `false`, re-apply the relevant block from `supabase/migrations/20260330000003_rls_policies.sql`.

---

## Step 2 — Verify policies are present

```sql
SELECT tablename, policyname, cmd, qual, with_check
FROM pg_policies
WHERE schemaname = 'public'
  AND tablename IN ('learning_sessions', 'analytics_events', 'profiles')
ORDER BY tablename, policyname;
```

Expected policies:

| Table | Policy name | Command |
|-------|-------------|---------|
| `learning_sessions` | `users_insert_own_sessions` | INSERT |
| `learning_sessions` | `users_read_own_sessions` | SELECT |
| `learning_sessions` | `users_update_own_sessions` | UPDATE |
| `profiles` | `users_read_own_profile` | SELECT |
| `analytics_events` | _(none — denied by default)_ | — |

If any policy is missing, re-run the relevant `DO $$ BEGIN … END $$` block from `supabase/migrations/20260330000003_rls_policies.sql`.

---

## Step 3 — Smoke-test client isolation (optional but recommended before launch)

Using a Supabase client initialised with the **anon key** and a real user's JWT:

1. Insert a `learning_sessions` row as user A.
2. Authenticate as user B and attempt to `SELECT` the row inserted by user A.
3. Confirm the query returns zero rows.
4. Attempt a direct `SELECT * FROM analytics_events` — confirm it returns zero rows (denied by RLS, not an empty table).

---

## Re-applying policies

The authoritative SQL is in `supabase/migrations/20260330000003_rls_policies.sql`. All statements are idempotent — paste the relevant section into the Supabase SQL Editor and run it, or run `supabase db push` from the repo root if the migration has not yet been applied.

---

## Tables not yet covered by RLS

`concept_exercises` stores user Feynman explanations and has a `session_id` FK to `learning_sessions`. It does not yet have RLS policies. Consider adding them if direct Supabase client access to that table is ever introduced.
