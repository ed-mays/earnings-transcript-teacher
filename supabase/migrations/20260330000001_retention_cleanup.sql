-- Scheduled retention cleanup and account-deletion helper.
-- Implements pg_cron jobs for data retention policy (docs/data-retention-policy.md):
--   - learning_sessions (+ cascading concept_exercises): 90 days
--   - analytics_events: 1 year
--
-- Prerequisites: pg_cron extension must be enabled before running this migration.
-- Enable via: Supabase Dashboard → Database → Extensions → pg_cron
-- On plain Postgres (e.g., CI), the cron.schedule calls are skipped automatically.

-- Helper function for account deletion: hard-delete sessions/exercises and
-- anonymize analytics events so they are retained for aggregate stats but are
-- no longer traceable to the deleted user.
CREATE OR REPLACE FUNCTION delete_user_data(p_user_id UUID)
RETURNS void
LANGUAGE plpgsql
AS $$
DECLARE
    deleted_session_ids UUID[];
BEGIN
    SELECT array_agg(id) INTO deleted_session_ids
    FROM learning_sessions
    WHERE user_id = p_user_id;

    DELETE FROM learning_sessions WHERE user_id = p_user_id;

    IF deleted_session_ids IS NOT NULL THEN
        UPDATE analytics_events
        SET session_id = NULL
        WHERE session_id = ANY(deleted_session_ids);
    END IF;
END;
$$;

-- Schedule daily cleanup of learning_sessions older than 90 days (03:00 UTC).
-- concept_exercises rows cascade automatically via ON DELETE CASCADE.
-- Skipped if pg_cron is not installed (e.g., plain Postgres in CI).
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_extension WHERE extname = 'pg_cron') THEN
        RETURN;
    END IF;
    EXECUTE $cmd$
        SELECT cron.schedule(
            'cleanup-learning-sessions',
            '0 3 * * *',
            'DELETE FROM learning_sessions WHERE started_at < now() - INTERVAL ''90 days'''
        ) WHERE NOT EXISTS (
            SELECT 1 FROM cron.job WHERE jobname = 'cleanup-learning-sessions'
        )
    $cmd$;
END $$;

-- Schedule daily cleanup of analytics_events older than 1 year (03:30 UTC).
-- Staggered 30 minutes after the sessions job to avoid simultaneous heavy deletes.
-- Skipped if pg_cron is not installed (e.g., plain Postgres in CI).
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_extension WHERE extname = 'pg_cron') THEN
        RETURN;
    END IF;
    EXECUTE $cmd$
        SELECT cron.schedule(
            'cleanup-analytics-events',
            '30 3 * * *',
            'DELETE FROM analytics_events WHERE created_at < now() - INTERVAL ''1 year'''
        ) WHERE NOT EXISTS (
            SELECT 1 FROM cron.job WHERE jobname = 'cleanup-analytics-events'
        )
    $cmd$;
END $$;
