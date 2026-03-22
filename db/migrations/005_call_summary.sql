-- Migration 005: Add call_summary to call_synthesis
ALTER TABLE call_synthesis ADD COLUMN IF NOT EXISTS call_summary TEXT;
INSERT INTO schema_version (version) VALUES (6) ON CONFLICT DO NOTHING;
