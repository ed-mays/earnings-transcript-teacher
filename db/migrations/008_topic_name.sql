-- Migration 008: Add topic_name column to call_topics for Haiku NLP synthesis
ALTER TABLE call_topics ADD COLUMN IF NOT EXISTS topic_name TEXT DEFAULT '';

INSERT INTO schema_version (version) VALUES (9) ON CONFLICT DO NOTHING;
