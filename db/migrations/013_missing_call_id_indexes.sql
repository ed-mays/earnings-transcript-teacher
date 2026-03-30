-- Migration 013: Add missing call_id indexes on agentic pipeline output tables.
--
-- These tables were created without call_id indexes in the baseline schema.
-- All are queried via JOINs on call_id — without indexes PostgreSQL performs
-- sequential scans on every request.

CREATE INDEX IF NOT EXISTS idx_chunks_call        ON transcript_chunks(call_id);
CREATE INDEX IF NOT EXISTS idx_terms_call         ON extracted_terms(call_id);
CREATE INDEX IF NOT EXISTS idx_concepts_call      ON core_concepts(call_id);
CREATE INDEX IF NOT EXISTS idx_takeaways_call     ON extracted_takeaways(call_id);
CREATE INDEX IF NOT EXISTS idx_evasion_call       ON evasion_analysis(call_id);
CREATE INDEX IF NOT EXISTS idx_misconceptions_call ON misconceptions(call_id);

INSERT INTO schema_version (version) VALUES (13) ON CONFLICT DO NOTHING;
