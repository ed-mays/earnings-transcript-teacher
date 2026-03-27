-- Migration 002: Add competitors table
CREATE TABLE IF NOT EXISTS competitors (
    id                      UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    call_id                 UUID NOT NULL REFERENCES calls(id) ON DELETE CASCADE,
    competitor_name         TEXT NOT NULL,
    competitor_ticker       TEXT,
    description             TEXT,
    mentioned_in_transcript BOOLEAN NOT NULL DEFAULT FALSE,
    fetched_at              TIMESTAMPTZ DEFAULT now(),
    UNIQUE (call_id, competitor_name)
);

CREATE INDEX IF NOT EXISTS idx_competitors_call ON competitors(call_id);

INSERT INTO schema_version (version) VALUES (2) ON CONFLICT DO NOTHING;
