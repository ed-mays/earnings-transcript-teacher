-- Migration 003: Convert strategic_shifts from TEXT to TEXT[]
-- Guarded: no-op if the column is already TEXT[] or JSONB[].
DO $$
BEGIN
    IF EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'call_synthesis'
          AND column_name = 'strategic_shifts'
          AND data_type = 'text'
    ) THEN
        ALTER TABLE call_synthesis
            ALTER COLUMN strategic_shifts TYPE TEXT[]
            USING ARRAY[strategic_shifts];
    END IF;
END $$;

INSERT INTO schema_version (version) VALUES (3) ON CONFLICT DO NOTHING;
