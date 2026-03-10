-- Earnings Transcript Teacher — Initial Postgres Schema
-- Covers: current pipeline data, future annotation columns, Q&A structure, learning sessions

-- ============================================================
-- Core tables
-- ============================================================

CREATE EXTENSION IF NOT EXISTS vector;


-- One row per earnings call
CREATE TABLE calls (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    ticker          TEXT NOT NULL,
    company_name    TEXT,
    fiscal_quarter  TEXT,                              -- e.g. 'Q3 2025'
    call_date       DATE,
    transcript_json TEXT,                              -- raw API response
    transcript_text TEXT NOT NULL,                     -- extracted body
    token_count     INTEGER,
    prepared_len    INTEGER,                           -- char count of prepared remarks
    qa_len          INTEGER,                           -- char count of Q&A section
    created_at      TIMESTAMPTZ DEFAULT now(),

    -- future: market reaction
    -- post_earnings_return  NUMERIC,
    -- post_earnings_vol     NUMERIC,

    UNIQUE (ticker, fiscal_quarter)
);

-- Unique speakers per call, with enriched metadata
CREATE TABLE speakers (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    call_id     UUID NOT NULL REFERENCES calls(id) ON DELETE CASCADE,
    name        TEXT NOT NULL,
    role        TEXT NOT NULL,                         -- executive | analyst | operator | unknown
    title       TEXT,                                  -- e.g. 'Chairman and CEO'
    firm        TEXT,                                  -- e.g. 'Morgan Stanley'
    turn_count  INTEGER NOT NULL,

    -- future: cross-call identity & behavior
    -- canonical_speaker_id  UUID,
    -- avg_hedge_density      NUMERIC,
    -- avg_evasiveness        NUMERIC,

    UNIQUE (call_id, name)
);

-- Atomic text units (turns, sentences)
-- Central content table: every annotation attaches to a span.
-- Vector DB embeddings are keyed back to span.id.
CREATE TABLE spans (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    call_id         UUID NOT NULL REFERENCES calls(id) ON DELETE CASCADE,
    speaker_id      UUID REFERENCES speakers(id),
    section         TEXT NOT NULL,                     -- 'prepared' | 'qa'
    span_type       TEXT NOT NULL,                     -- 'turn' | 'sentence'
    sequence_order  INTEGER NOT NULL,                  -- position within section
    text            TEXT NOT NULL,
    char_count      INTEGER NOT NULL,

    -- current: TextRank score (NULL if not a takeaway)
    textrank_score  NUMERIC,

    -- semantic search
    embedding       vector(1024),


    -- future: communication signal annotations
    -- temporal_class    TEXT,                          -- 'historical' | 'forward_looking'
    -- temporal_subtype  TEXT,                          -- 'guidance' | 'strategic' | 'qualitative_outlook'
    -- hedge_density     NUMERIC,                      -- 0.0-1.0
    -- commitment        TEXT,                          -- 'strong' | 'moderate' | 'weak'
    -- specificity_score NUMERIC,                      -- count of metrics + concrete refs
    -- is_boilerplate    BOOLEAN DEFAULT FALSE,
    -- sentiment_score   NUMERIC,                      -- e.g. FinBERT -1.0 to 1.0
    -- sentiment_label   TEXT,                          -- 'positive' | 'neutral' | 'negative'

    CONSTRAINT valid_section CHECK (section IN ('prepared', 'qa')),
    CONSTRAINT valid_span_type CHECK (span_type IN ('turn', 'sentence'))
);

CREATE INDEX idx_spans_call ON spans(call_id);
CREATE INDEX idx_spans_speaker ON spans(speaker_id);
CREATE INDEX idx_spans_section ON spans(call_id, section);
CREATE INDEX idx_spans_embedding ON spans USING hnsw (embedding vector_cosine_ops);

-- ============================================================
-- Extracted analysis tables
-- ============================================================

-- NMF themes per call
CREATE TABLE call_topics (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    call_id     UUID NOT NULL REFERENCES calls(id) ON DELETE CASCADE,
    label       INTEGER NOT NULL,                     -- topic number
    terms       TEXT[] NOT NULL,                       -- top terms array
    weight      NUMERIC NOT NULL,                     -- NMF prominence weight
    rank_order  INTEGER NOT NULL                      -- 1 = most prominent
);

CREATE INDEX idx_topics_call ON call_topics(call_id);

-- TF-IDF keyword associations (call-level)
CREATE TABLE span_keywords (
    id         UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    call_id    UUID NOT NULL REFERENCES calls(id) ON DELETE CASCADE,
    term       TEXT NOT NULL,
    score      NUMERIC NOT NULL,
    ngram_size INTEGER NOT NULL DEFAULT 1              -- 1 = unigram, 2 = bigram
);

CREATE INDEX idx_keywords_call ON span_keywords(call_id);
CREATE INDEX idx_keywords_term ON span_keywords(term);

-- ============================================================
-- Q&A structure
-- ============================================================

-- Links question spans to answer spans
CREATE TABLE qa_pairs (
    id               UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    call_id          UUID NOT NULL REFERENCES calls(id) ON DELETE CASCADE,
    exchange_order   INTEGER NOT NULL,                 -- which exchange (1st, 2nd, ...)
    question_span_id UUID NOT NULL REFERENCES spans(id),
    answer_span_id   UUID NOT NULL REFERENCES spans(id),

    -- future: Q&A quality annotations
    -- question_type      TEXT,                        -- 'drill_down' | 'clarification' | 'challenge' | ...
    -- answer_responsive   TEXT,                       -- 'direct' | 'partial' | 'evasive'
    -- evasiveness_score   NUMERIC,

    UNIQUE (question_span_id, answer_span_id)
);

CREATE INDEX idx_qa_call ON qa_pairs(call_id);

-- ============================================================
-- Learning tool tables
-- ============================================================

-- User study sessions
CREATE TABLE learning_sessions (
    id           UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id      UUID NOT NULL,
    call_id      UUID NOT NULL REFERENCES calls(id),
    started_at   TIMESTAMPTZ DEFAULT now(),
    completed_at TIMESTAMPTZ,
    notes        TEXT
);

-- Feynman explanation exercises
CREATE TABLE concept_exercises (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id          UUID NOT NULL REFERENCES learning_sessions(id) ON DELETE CASCADE,
    concept_label       TEXT NOT NULL,                 -- e.g. 'cloud revenue guidance'
    user_explanation    TEXT,
    ai_critique         TEXT,
    revised_explanation TEXT,
    confidence          TEXT CHECK (confidence IN ('low', 'medium', 'high'))
);

-- ============================================================
-- Agentic Pipeline Outputs
-- ============================================================

CREATE TABLE transcript_chunks (
    id               UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    call_id          UUID NOT NULL REFERENCES calls(id) ON DELETE CASCADE,
    chunk_id         TEXT NOT NULL,
    chunk_type       TEXT NOT NULL,
    sequence_order   INTEGER NOT NULL,
    tier1_score      INTEGER,
    needs_deep_analysis BOOLEAN DEFAULT FALSE
);

CREATE TABLE extracted_terms (
    id         UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    call_id    UUID NOT NULL REFERENCES calls(id) ON DELETE CASCADE,
    chunk_id   TEXT NOT NULL,
    term       TEXT NOT NULL,
    definition TEXT NOT NULL,
    explanation TEXT DEFAULT ''
);

CREATE TABLE core_concepts (
    id         UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    call_id    UUID NOT NULL REFERENCES calls(id) ON DELETE CASCADE,
    chunk_id   TEXT NOT NULL,
    concept    TEXT NOT NULL
);

CREATE TABLE extracted_takeaways (
    id               UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    call_id          UUID NOT NULL REFERENCES calls(id) ON DELETE CASCADE,
    chunk_id         TEXT NOT NULL,
    takeaway         TEXT NOT NULL,
    why_it_matters   TEXT NOT NULL
);

CREATE TABLE evasion_analysis (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    call_id             UUID NOT NULL REFERENCES calls(id) ON DELETE CASCADE,
    chunk_id            TEXT NOT NULL,
    analyst_concern     TEXT NOT NULL,
    defensiveness_score INTEGER NOT NULL,
    evasion_explanation TEXT NOT NULL
);

CREATE TABLE misconceptions (
    id                UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    call_id           UUID NOT NULL REFERENCES calls(id) ON DELETE CASCADE,
    chunk_id          TEXT NOT NULL,
    fact              TEXT NOT NULL,
    misinterpretation TEXT NOT NULL,
    correction        TEXT NOT NULL
);

CREATE TABLE call_synthesis (
    id                 UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    call_id            UUID NOT NULL REFERENCES calls(id) ON DELETE CASCADE UNIQUE,
    overall_sentiment  TEXT NOT NULL,
    executive_tone     TEXT NOT NULL,
    key_themes         TEXT[] NOT NULL,
    strategic_shifts   TEXT NOT NULL,
    analyst_sentiment  TEXT NOT NULL
);

