-- Feature flags table for operational kill switches and feature gates.
-- No RLS policies: only the service role (backend API) can read/write.

CREATE TABLE IF NOT EXISTS public.feature_flags (
    key         TEXT PRIMARY KEY,
    enabled     BOOLEAN NOT NULL DEFAULT FALSE,
    description TEXT NOT NULL DEFAULT '',
    category    TEXT NOT NULL DEFAULT 'feature'
                    CHECK (category IN ('feature', 'kill_switch', 'experiment')),
    metadata    JSONB NOT NULL DEFAULT '{}',
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

ALTER TABLE public.feature_flags ENABLE ROW LEVEL SECURITY;

-- Auto-update updated_at on every row modification.
CREATE OR REPLACE FUNCTION public.feature_flags_set_updated_at()
RETURNS TRIGGER
LANGUAGE plpgsql
AS $$
BEGIN
    NEW.updated_at = now();
    RETURN NEW;
END;
$$;

CREATE TRIGGER feature_flags_updated_at
    BEFORE UPDATE ON public.feature_flags
    FOR EACH ROW EXECUTE FUNCTION public.feature_flags_set_updated_at();

-- Seed kill switches (default enabled=true so the system works without intervention).
INSERT INTO public.feature_flags (key, enabled, description, category) VALUES
    ('chat_enabled',       TRUE, 'Kill switch for the Feynman learning chat feature', 'kill_switch'),
    ('ingestion_enabled',  TRUE, 'Kill switch for the admin transcript ingestion pipeline', 'kill_switch')
ON CONFLICT (key) DO NOTHING;
