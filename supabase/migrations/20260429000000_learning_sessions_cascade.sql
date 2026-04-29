-- Migration: align learning_sessions.call_id FK with the rest of the schema
-- (ON DELETE CASCADE).
--
-- Every other table that references calls(id) — transcript_chunks,
-- evasion_analysis, extracted_terms, call_brief, call_synthesis, news_items,
-- and a dozen others — was created with ON DELETE CASCADE so that
-- re-ingesting a call (which deletes-and-replaces the row in `calls`)
-- cascades cleanly through every dependent analysis table.
-- `learning_sessions` was the lone exception, blocking re-ingest with a
-- FK violation whenever any chat session existed for that call.
--
-- Tradeoff: re-ingesting now wipes any learning_sessions tied to that
-- call. Acceptable while the data model has no real users yet. Preserving
-- chat sessions across re-ingestions would require switching ingestion
-- from delete-and-replace to update-in-place — out of scope for this fix.

ALTER TABLE learning_sessions
    DROP CONSTRAINT IF EXISTS learning_sessions_call_id_fkey;

ALTER TABLE learning_sessions
    ADD CONSTRAINT learning_sessions_call_id_fkey
        FOREIGN KEY (call_id) REFERENCES calls(id) ON DELETE CASCADE;
