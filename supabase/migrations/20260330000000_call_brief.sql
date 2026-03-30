-- Migration: add call_brief table for LLM-generated pre-reading brief
-- Generated as part of issue #206 (call brief + misconception cards)

CREATE TABLE IF NOT EXISTS call_brief (
    id                       UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    call_id                  UUID NOT NULL REFERENCES calls(id) ON DELETE CASCADE UNIQUE,
    context_line             TEXT NOT NULL,
    bigger_picture           JSONB NOT NULL DEFAULT '[]',
    interpretation_questions JSONB NOT NULL DEFAULT '[]',
    created_at               TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_call_brief_call ON call_brief(call_id);
