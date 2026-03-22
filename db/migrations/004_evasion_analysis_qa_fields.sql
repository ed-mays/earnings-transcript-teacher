-- Migration 004: Add structured Q&A fields to evasion_analysis
ALTER TABLE evasion_analysis
    ADD COLUMN IF NOT EXISTS analyst_name   TEXT,
    ADD COLUMN IF NOT EXISTS question_topic TEXT,
    ADD COLUMN IF NOT EXISTS question_text  TEXT,
    ADD COLUMN IF NOT EXISTS answer_text    TEXT;
INSERT INTO schema_version (version) VALUES (5) ON CONFLICT DO NOTHING;
