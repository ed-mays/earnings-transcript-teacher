-- Migration 007: Add transcript_progress table for per-step completion tracking
CREATE TABLE IF NOT EXISTS transcript_progress (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    call_id     UUID NOT NULL REFERENCES calls(id) ON DELETE CASCADE,
    step_number INTEGER NOT NULL CHECK (step_number BETWEEN 1 AND 6),
    viewed_at   TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (call_id, step_number)
);

CREATE INDEX IF NOT EXISTS idx_transcript_progress_call ON transcript_progress(call_id);

INSERT INTO schema_version (version) VALUES (7) ON CONFLICT DO NOTHING;
