-- Migration 006: Convert strategic_shifts from TEXT[] to JSONB[]
-- Guarded: no-op if the column is already JSONB[].
-- Uses a new-column + UPDATE + rename approach because PostgreSQL does not
-- allow subqueries in ALTER COLUMN TYPE ... USING.
DO $$
DECLARE
    col_type TEXT;
BEGIN
    SELECT udt_name INTO col_type
    FROM information_schema.columns
    WHERE table_name = 'call_synthesis' AND column_name = 'strategic_shifts';

    IF col_type = '_jsonb' THEN
        RETURN; -- Already migrated
    END IF;

    ALTER TABLE call_synthesis ADD COLUMN IF NOT EXISTS strategic_shifts_new JSONB[] DEFAULT '{}';

    IF col_type = '_text' THEN
        UPDATE call_synthesis
        SET strategic_shifts_new = (
            SELECT array_agg(
                jsonb_build_object(
                    'prior_position', '',
                    'current_position', s,
                    'investor_significance', ''
                )
            )
            FROM unnest(strategic_shifts) AS s
        )
        WHERE strategic_shifts IS NOT NULL AND array_length(strategic_shifts, 1) > 0;

        ALTER TABLE call_synthesis DROP COLUMN strategic_shifts;
    END IF;

    ALTER TABLE call_synthesis RENAME COLUMN strategic_shifts_new TO strategic_shifts;
END $$;

INSERT INTO schema_version (version) VALUES (6) ON CONFLICT DO NOTHING;
