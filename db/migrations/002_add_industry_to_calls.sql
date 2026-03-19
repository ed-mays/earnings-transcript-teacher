-- Migration 002: Add industry column to calls table
ALTER TABLE calls ADD COLUMN IF NOT EXISTS industry TEXT;
INSERT INTO schema_version (version) VALUES (2) ON CONFLICT DO NOTHING;
