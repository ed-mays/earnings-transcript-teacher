-- Add user_id to learning_sessions for per-user session scoping.
-- No-op for fresh installs from schema.sql (column already present).
ALTER TABLE learning_sessions
  ADD COLUMN IF NOT EXISTS user_id UUID;

CREATE INDEX IF NOT EXISTS idx_sessions_user
  ON learning_sessions (user_id);
