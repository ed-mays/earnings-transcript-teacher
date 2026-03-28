-- Migration 011: analytics_events table for observability instrumentation.
-- Stores fire-and-forget events emitted by API, Streamlit, and CLI layers.

CREATE TABLE analytics_events (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    event_name  TEXT NOT NULL,
    session_id  UUID,
    properties  JSONB,
    created_at  TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX idx_analytics_event_name ON analytics_events (event_name);
CREATE INDEX idx_analytics_created_at  ON analytics_events (created_at);

INSERT INTO schema_version (version) VALUES (11);
