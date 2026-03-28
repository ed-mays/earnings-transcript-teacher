-- Migration 010: Add profiles table for per-user role-based access control.
-- Replaces ADMIN_SECRET_TOKEN with a DB-backed role lookup.

CREATE TYPE public.user_role AS ENUM ('admin', 'learner');

CREATE TABLE public.profiles (
    id   UUID PRIMARY KEY REFERENCES auth.users(id) ON DELETE CASCADE,
    role public.user_role NOT NULL DEFAULT 'learner'
);

-- Auto-insert a learner profile when a new auth user is created.
-- SECURITY DEFINER is required because auth.users is in the Supabase-managed schema.
CREATE OR REPLACE FUNCTION public.handle_new_user()
RETURNS TRIGGER AS $$
BEGIN
    INSERT INTO public.profiles (id, role) VALUES (NEW.id, 'learner');
    RETURN NEW;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

CREATE TRIGGER on_auth_user_created
    AFTER INSERT ON auth.users
    FOR EACH ROW EXECUTE FUNCTION public.handle_new_user();

-- Allow authenticated users to read their own profile row.
-- Required for the Next.js server client (anon key + user JWT) to query role.
ALTER TABLE public.profiles ENABLE ROW LEVEL SECURITY;

CREATE POLICY "users_read_own_profile"
    ON public.profiles
    FOR SELECT
    USING (auth.uid() = id);

INSERT INTO schema_version (version) VALUES (10) ON CONFLICT DO NOTHING;
