-- Migration 003: Convert strategic_shifts from TEXT to TEXT[]
ALTER TABLE call_synthesis
    ALTER COLUMN strategic_shifts TYPE TEXT[]
    USING ARRAY[strategic_shifts];
INSERT INTO schema_version (version) VALUES (4) ON CONFLICT DO NOTHING;
