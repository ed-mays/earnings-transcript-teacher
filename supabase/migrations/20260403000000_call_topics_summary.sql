-- Add narrative summary field to call_topics for #342.
ALTER TABLE call_topics ADD COLUMN IF NOT EXISTS summary TEXT DEFAULT '';
