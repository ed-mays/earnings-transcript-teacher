-- Migration 006: Convert strategic_shifts from TEXT[] to JSONB[]
-- PostgreSQL does not allow subqueries in ALTER COLUMN TYPE ... USING,
-- so we add a new column, populate it via UPDATE, then rename.
ALTER TABLE call_synthesis ADD COLUMN IF NOT EXISTS strategic_shifts_new JSONB[] DEFAULT '{}';

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
ALTER TABLE call_synthesis RENAME COLUMN strategic_shifts_new TO strategic_shifts;

INSERT INTO schema_version (version) VALUES (7) ON CONFLICT DO NOTHING;
