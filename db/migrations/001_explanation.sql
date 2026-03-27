-- Migration 001: Add contextual explanation column to extracted_terms
ALTER TABLE extracted_terms ADD COLUMN IF NOT EXISTS explanation TEXT DEFAULT '';

INSERT INTO schema_version (version) VALUES (1) ON CONFLICT DO NOTHING;
