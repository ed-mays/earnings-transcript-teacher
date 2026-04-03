CREATE TABLE IF NOT EXISTS news_items (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    call_id     UUID NOT NULL REFERENCES calls(id) ON DELETE CASCADE,
    headline    TEXT NOT NULL,
    url         TEXT NOT NULL,
    source      TEXT NOT NULL,
    date        TEXT NOT NULL,
    summary     TEXT NOT NULL,
    fetched_at  TIMESTAMPTZ DEFAULT now(),
    UNIQUE (call_id, headline)
);

CREATE INDEX IF NOT EXISTS news_items_call_id_idx ON news_items(call_id);
