-- RLS policies for all user-data tables.
-- All statements are idempotent — safe to run against a database where
-- policies are already applied.

-- ── learning_sessions ─────────────────────────────────────────────────────────
-- Users store full Feynman chat history here (notes JSONB).
-- Only the owning user should be able to read or write their own rows.
--
-- Service-role connections (FastAPI via DATABASE_URL) bypass RLS entirely,
-- so the application-layer ownership check in LearningRepository remains
-- in effect for those paths.
--
-- Rows with a NULL user_id (anonymous CLI sessions) are unreachable via JWT
-- because NULL != auth.uid() evaluates to NULL (not true) — correct behaviour.

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
-- All writes come from server-side code using the service role key, which
-- bypasses RLS. Enabling RLS with no policies denies all client-role access.

ALTER TABLE public.analytics_events ENABLE ROW LEVEL SECURITY;

-- No policies intentionally. Service role bypasses RLS; all other callers
-- are denied. Add an admin-read policy here if a Supabase client ever needs
-- direct SQL access to this table.
