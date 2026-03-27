# Staging Environments — Supabase + Railway + Vercel

GitHub Issue: [#156](https://github.com/ed-mays/earnings-transcript-teacher/issues/156)

## Goal

Add isolated staging environments so PRs can be validated before reaching production.

| Layer | Staging |
|---|---|
| Frontend | Vercel preview (automatic per PR) |
| API | Railway staging environment |
| Database | Supabase staging project (second free-tier project) |

## Current state

The code already supports this. No code changes required:
- `CORS_EXTRA_ORIGINS` in `api/main.py:build_cors_origins()` handles Vercel preview domains
- `migrate.py` reads `DATABASE_URL` from env — run it against staging by setting that var
- Railway env vars are fully configurable per environment in their dashboard

---

## Implementation steps

### 1. Supabase staging project

1. Create a second Supabase project (e.g. `earningsfluency-staging`) — free tier allows 2 projects
2. Note the staging project's pooler connection string, JWT secret, URL, and anon key
3. Run migrations against staging:
   ```bash
   DATABASE_URL="postgresql://postgres.[staging-ref]:[pw]@aws-0-[region].pooler.supabase.com:5432/postgres" python migrate.py
   ```
4. In Auth settings for the staging project: add the Railway staging API URL and Vercel preview URL pattern to the Google OAuth redirect allow-list

### 2. Railway staging environment

1. Open the Railway project → create a new environment named `staging`
2. Set these env vars in staging (same keys as production, different values):

| Var | Value |
|---|---|
| `DATABASE_URL` | Staging Supabase pooler connection string |
| `SUPABASE_JWT_SECRET` | Staging project JWT secret |
| `NEXT_PUBLIC_VERCEL_URL` | Railway staging domain (e.g. `earningsfluency-staging.up.railway.app`) |
| `CORS_EXTRA_ORIGINS` | Vercel preview URL patterns, comma-separated (e.g. `https://earningsfluency-git-*.vercel.app`) |
| `VOYAGE_API_KEY` | Same as production |
| `PERPLEXITY_API_KEY` | Same as production |
| `ANTHROPIC_API_KEY` | Same as production |
| `API_NINJAS_KEY` | Same as production |
| `ADMIN_SECRET_TOKEN` | Same as production (or staging-specific) |

3. Deploy — Railway builds from the same `railway.toml` + `api/Dockerfile`

### 3. Vercel preview environment variables

1. Go to Vercel project Settings → Environment Variables
2. Add these scoped to **Preview** only:

| Var | Value |
|---|---|
| `NEXT_PUBLIC_SUPABASE_URL` | Staging Supabase project URL |
| `NEXT_PUBLIC_SUPABASE_ANON_KEY` | Staging Supabase anon key |
| `NEXT_PUBLIC_API_URL` | Railway staging API URL |

3. Leave **Production** env vars untouched

---

## Verification

1. Push a feature branch → Vercel auto-creates a preview at `earningsfluency-git-[branch].vercel.app`
2. Preview URL hits Railway staging API → check Railway logs for requests
3. Railway staging connects to Supabase staging → confirm via `/health` and a test API call
4. Auth flow works on the preview URL (Google OAuth redirects back correctly)

---

## Notes

- Supabase branching (Git-style DB branches per PR) is a paid feature; two separate projects achieves the same isolation on the free tier
- Vercel preview deployments are automatic for GitHub-connected Next.js projects — no extra config beyond env var groups
- The `CORS_EXTRA_ORIGINS` wildcard pattern approach means any new Vercel preview subdomain is covered without additional config changes
