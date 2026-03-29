-- RLS Policies for EarningsFluency
-- ============================================================
-- Apply these via the Supabase SQL Editor — do not run through
-- migrate.py (these are idempotent DDL statements that complement
-- the migration history, not replace it).
--
-- All statements are idempotent (IF NOT EXISTS / OR REPLACE) so
-- they can be re-run safely after any schema migration.
--
-- Verified status (2026-03-29):
--   learning_sessions  RLS enabled  ← applied as part of #227 (launch blocker)
--   analytics_events   RLS enabled  ← applied as part of #227
--   profiles           RLS enabled  ← applied in migration 010
--
-- Re-verify after any migration that touches these tables; see
-- docs/runbooks/rls-verification.md for the verification checklist.
-- ============================================================


-- ── learning_sessions ─────────────────────────────────────────────────────────
-- Users store full Feynman chat history here (notes JSONB).
-- Only the owning user should be able to read or write their own rows.
--
-- Service-role connections (CLI, Streamlit, FastAPI via DATABASE_URL)
-- bypass RLS entirely, so the existing application-layer ownership
-- check in LearningRepository.get_session_by_id() remains in effect
-- for those paths.
--
-- Rows with a NULL user_id (SYSTEM_USER_ID / anonymous CLI sessions)
-- are unreachable via JWT because NULL != auth.uid() evaluates to NULL
-- (not true), which is correct — those rows are internal only.

ALTER TABLE public.learning_sessions ENABLE ROW LEVEL SECURITY;

DO $$ BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM pg_policies
    WHERE tablename = 'learning_sessions' AND policyname = 'users_read_own_sessions'
  ) THEN
    CREATE POLICY "users_read_own_sessions"
      ON public.learning_sessions
      FOR SELECT
      USING (auth.uid() = user_id);
  END IF;
END $$;

DO $$ BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM pg_policies
    WHERE tablename = 'learning_sessions' AND policyname = 'users_insert_own_sessions'
  ) THEN
    CREATE POLICY "users_insert_own_sessions"
      ON public.learning_sessions
      FOR INSERT
      WITH CHECK (auth.uid() = user_id);
  END IF;
END $$;

DO $$ BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM pg_policies
    WHERE tablename = 'learning_sessions' AND policyname = 'users_update_own_sessions'
  ) THEN
    CREATE POLICY "users_update_own_sessions"
      ON public.learning_sessions
      FOR UPDATE
      USING (auth.uid() = user_id)
      WITH CHECK (auth.uid() = user_id);
  END IF;
END $$;


-- ── analytics_events ──────────────────────────────────────────────────────────
-- Aggregate observability data; no user_id column.
-- All writes come from server-side code using the service role key,
-- which bypasses RLS. No Supabase client (anon key + user JWT) path
-- should read or write this table directly.
--
-- Enabling RLS with no policies means client-role connections are
-- denied by default — all access is forced through the internal API.

ALTER TABLE public.analytics_events ENABLE ROW LEVEL SECURITY;

-- No policies intentionally. Service role bypasses RLS; all other
-- callers are denied. Add an admin-read policy here if an admin
-- Supabase client ever needs direct SQL access.


-- ── profiles ──────────────────────────────────────────────────────────────────
-- RLS already applied in migration 010. Documented here for completeness.
--
-- Existing policy (do not re-create):
--   "users_read_own_profile"  FOR SELECT  USING (auth.uid() = id)
--
-- No INSERT/UPDATE policies: profile rows are created by the
-- handle_new_user() trigger (SECURITY DEFINER) and are not
-- writable by end users.
