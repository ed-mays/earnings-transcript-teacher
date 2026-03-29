-- Migration 000: Baseline schema — all tables and indexes that existed before
-- the first incremental migration was applied.
--
-- migrate.py applies this first when bootstrapping a fresh database.
-- Subsequent migrations (001–011) build on top of this baseline.
-- All statements use IF NOT EXISTS so this is safe to apply against an
-- existing database (e.g. a Supabase instance that already has the full schema).

-- ============================================================
-- Extensions
-- ============================================================

CREATE EXTENSION IF NOT EXISTS vector;

-- ============================================================
-- Core tables
-- ============================================================

CREATE TABLE IF NOT EXISTS calls (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    ticker          TEXT NOT NULL,
    company_name    TEXT,
    industry        TEXT,
    fiscal_quarter  TEXT,
    call_date       DATE,
    transcript_json TEXT,
    transcript_text TEXT NOT NULL,
    token_count     INTEGER,
    prepared_len    INTEGER,
    qa_len          INTEGER,
    created_at      TIMESTAMPTZ DEFAULT now(),
    UNIQUE (ticker, fiscal_quarter)
);

CREATE TABLE IF NOT EXISTS speakers (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    call_id     UUID NOT NULL REFERENCES calls(id) ON DELETE CASCADE,
    name        TEXT NOT NULL,
    role        TEXT NOT NULL,
    title       TEXT,
    firm        TEXT,
    turn_count  INTEGER NOT NULL,
    UNIQUE (call_id, name)
);

CREATE TABLE IF NOT EXISTS spans (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    call_id         UUID NOT NULL REFERENCES calls(id) ON DELETE CASCADE,
    speaker_id      UUID REFERENCES speakers(id),
    section         TEXT NOT NULL,
    span_type       TEXT NOT NULL,
    sequence_order  INTEGER NOT NULL,
    text            TEXT NOT NULL,
    char_count      INTEGER NOT NULL,
    textrank_score  NUMERIC,
    embedding       vector(1024),
    CONSTRAINT valid_section CHECK (section IN ('prepared', 'qa')),
    CONSTRAINT valid_span_type CHECK (span_type IN ('turn', 'sentence'))
);

CREATE INDEX IF NOT EXISTS idx_spans_call      ON spans(call_id);
CREATE INDEX IF NOT EXISTS idx_spans_speaker   ON spans(speaker_id);
CREATE INDEX IF NOT EXISTS idx_spans_section   ON spans(call_id, section);
CREATE INDEX IF NOT EXISTS idx_spans_embedding ON spans USING hnsw (embedding vector_cosine_ops);

-- ============================================================
-- Extracted analysis tables
-- ============================================================

-- topic_name column added later in migration 008
CREATE TABLE IF NOT EXISTS call_topics (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    call_id     UUID NOT NULL REFERENCES calls(id) ON DELETE CASCADE,
    label       INTEGER NOT NULL,
    terms       TEXT[] NOT NULL,
    weight      NUMERIC NOT NULL,
    rank_order  INTEGER NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_topics_call ON call_topics(call_id);

CREATE TABLE IF NOT EXISTS span_keywords (
    id         UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    call_id    UUID NOT NULL REFERENCES calls(id) ON DELETE CASCADE,
    term       TEXT NOT NULL,
    score      NUMERIC NOT NULL,
    ngram_size INTEGER NOT NULL DEFAULT 1
);

CREATE INDEX IF NOT EXISTS idx_keywords_call ON span_keywords(call_id);
CREATE INDEX IF NOT EXISTS idx_keywords_term ON span_keywords(term);

-- ============================================================
-- Q&A structure
-- ============================================================

CREATE TABLE IF NOT EXISTS qa_pairs (
    id               UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    call_id          UUID NOT NULL REFERENCES calls(id) ON DELETE CASCADE,
    exchange_order   INTEGER NOT NULL,
    question_span_id UUID NOT NULL REFERENCES spans(id),
    answer_span_id   UUID NOT NULL REFERENCES spans(id),
    UNIQUE (question_span_id, answer_span_id)
);

CREATE INDEX IF NOT EXISTS idx_qa_call ON qa_pairs(call_id);

-- ============================================================
-- Learning tool tables
-- ============================================================

-- user_id column added later in migration 009
CREATE TABLE IF NOT EXISTS learning_sessions (
    id           UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    call_id      UUID NOT NULL REFERENCES calls(id),
    started_at   TIMESTAMPTZ DEFAULT now(),
    completed_at TIMESTAMPTZ,
    notes        TEXT
);

CREATE TABLE IF NOT EXISTS concept_exercises (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id          UUID NOT NULL REFERENCES learning_sessions(id) ON DELETE CASCADE,
    concept_label       TEXT NOT NULL,
    user_explanation    TEXT,
    ai_critique         TEXT,
    revised_explanation TEXT,
    confidence          TEXT CHECK (confidence IN ('low', 'medium', 'high'))
);

-- ============================================================
-- Agentic pipeline output tables
-- ============================================================

CREATE TABLE IF NOT EXISTS transcript_chunks (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    call_id             UUID NOT NULL REFERENCES calls(id) ON DELETE CASCADE,
    chunk_id            TEXT NOT NULL,
    chunk_type          TEXT NOT NULL,
    sequence_order      INTEGER NOT NULL,
    tier1_score         INTEGER,
    needs_deep_analysis BOOLEAN DEFAULT FALSE,
    chunk_text          TEXT
);

-- explanation column added later in migration 001
CREATE TABLE IF NOT EXISTS extracted_terms (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    call_id     UUID NOT NULL REFERENCES calls(id) ON DELETE CASCADE,
    chunk_id    TEXT NOT NULL,
    term        TEXT NOT NULL,
    definition  TEXT NOT NULL,
    category    TEXT NOT NULL DEFAULT 'industry'
);

CREATE TABLE IF NOT EXISTS core_concepts (
    id       UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    call_id  UUID NOT NULL REFERENCES calls(id) ON DELETE CASCADE,
    chunk_id TEXT NOT NULL,
    concept  TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS extracted_takeaways (
    id             UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    call_id        UUID NOT NULL REFERENCES calls(id) ON DELETE CASCADE,
    chunk_id       TEXT NOT NULL,
    takeaway       TEXT NOT NULL,
    why_it_matters TEXT NOT NULL
);

-- analyst_name/question_topic/question_text/answer_text added later in migration 004
CREATE TABLE IF NOT EXISTS evasion_analysis (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    call_id             UUID NOT NULL REFERENCES calls(id) ON DELETE CASCADE,
    chunk_id            TEXT NOT NULL,
    analyst_concern     TEXT NOT NULL,
    defensiveness_score INTEGER NOT NULL,
    evasion_explanation TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS misconceptions (
    id                UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    call_id           UUID NOT NULL REFERENCES calls(id) ON DELETE CASCADE,
    chunk_id          TEXT NOT NULL,
    fact              TEXT NOT NULL,
    misinterpretation TEXT NOT NULL,
    correction        TEXT NOT NULL
);

-- strategic_shifts: TEXT initially, converted to TEXT[] (migration 003) then JSONB[] (migration 006)
-- call_summary column added in migration 005
CREATE TABLE IF NOT EXISTS call_synthesis (
    id                 UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    call_id            UUID NOT NULL REFERENCES calls(id) ON DELETE CASCADE UNIQUE,
    overall_sentiment  TEXT NOT NULL,
    executive_tone     TEXT NOT NULL,
    key_themes         TEXT[] NOT NULL,
    strategic_shifts   TEXT,
    analyst_sentiment  TEXT NOT NULL
);

INSERT INTO schema_version (version) VALUES (0) ON CONFLICT DO NOTHING;
