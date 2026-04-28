-- Migration: add executive_name + suggested_probes to evasion_analysis
--
-- - executive_name: the executive who answered the question. Mirrors the
--   existing analyst_name attribution. Surfaces in the Q&A Forensics
--   detail view so the user knows whose response they're judging.
--
-- - suggested_probes: 3-4 LLM-generated, exchange-specific exploration
--   prompts (Tier 2 prompt change generates them). The Q&A Forensics
--   detail view renders them as clickable chips. Frontend falls back to
--   templated chips when this field is null (older calls / pre-update
--   ingestion).
--
-- Both columns are nullable on existing rows; new ingestions populate
-- them via the updated Tier 2 prompt schema.

ALTER TABLE evasion_analysis
    ADD COLUMN IF NOT EXISTS executive_name TEXT;

ALTER TABLE evasion_analysis
    ADD COLUMN IF NOT EXISTS suggested_probes JSONB;
