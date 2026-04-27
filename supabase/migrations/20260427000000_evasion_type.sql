-- Migration: add evasion_type categorical column to evasion_analysis
-- Powers Q&A Forensics mode: pattern recognition across exchanges requires
-- a named taxonomy (deflect, reframe, verbose non-answer, etc.) rather than
-- only the free-text evasion_explanation.
--
-- Nullable on existing rows; new ingestions populate it from the Tier 2 prompt.

ALTER TABLE evasion_analysis
    ADD COLUMN IF NOT EXISTS evasion_type TEXT;

ALTER TABLE evasion_analysis
    DROP CONSTRAINT IF EXISTS evasion_analysis_evasion_type_check;

ALTER TABLE evasion_analysis
    ADD CONSTRAINT evasion_analysis_evasion_type_check
    CHECK (
        evasion_type IS NULL
        OR evasion_type IN (
            'deflect_to_forward_looking',
            'reframe',
            'verbose_non_answer',
            'redirect_to_different_metric',
            'partial_answer',
            'run_out_clock',
            'none'
        )
    );

CREATE INDEX IF NOT EXISTS idx_evasion_analysis_type
    ON evasion_analysis(evasion_type)
    WHERE evasion_type IS NOT NULL;
