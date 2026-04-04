> **Status: Implemented** — see PR #355 and [`docs/disaster-recovery.md`](../docs/disaster-recovery.md) for the current setup.

# Staging Environments — Supabase + Railway + Vercel

GitHub Issue: [#156](https://github.com/ed-mays/earnings-transcript-teacher/issues/156)

## Goal

Add isolated staging environments so PRs can be validated end-to-end before reaching production.

| Layer | Production | Staging / Preview |
|---|---|---|
| Frontend | Vercel (production deploy on merge) | Vercel preview (automatic per PR) |
| API | Railway production environment | Railway staging environment |
| Database | Supabase production project | Supabase staging project (second free-tier project) |
| Compute | Modal `earnings-ingestion` app | Same Modal app (no separate staging needed) |

## Current state

The code already supports multiple environments — no application code changes required:
- `CORS_EXTRA_ORIGINS` and `CORS_ORIGIN_REGEX` in `api/main.py` handle Vercel preview domains
- Supabase CLI migrations (`supabase db push`) target whichever project is linked
- Railway env vars are fully configurable per environment
- Vercel env vars can be scoped to Preview vs Production

---

## Implementation steps

### 1. Supabase staging project (~15 min, dashboard)

1. Create a second Supabase project (e.g. `earningsfluency-staging`) — free tier allows 2 projects
2. Enable the `vector` extension (Database → Extensions → search "vector" → enable)
3. Note the staging project's: **project ref**, **pooler connection string** (port 6543), **project URL**, and **anon key**
4. In Auth → URL Configuration: add the Railway staging domain and Vercel preview URL pattern to the redirect allow-list
5. In Auth → Providers: enable Google OAuth with the same Google Cloud credentials (add staging callback URL to Google's authorized redirect URIs)

### 2. Run migrations against staging (~5 min, CLI)

```bash
supabase link --project-ref <staging-project-ref>
supabase db push
```

This applies all `supabase/migrations/*.sql` files to the staging database.

**Important:** `supabase link` switches the local project's linked ref. Re-link to production afterward:
```bash
supabase link --project-ref qxdexukkmzidalnrzfqf
```

### 3. Railway staging environment (~10 min, dashboard)

1. Open the Railway project → Environments → Create → name it `staging`
2. Set these env vars (same keys as production, different values where noted):

| Var | Value |
|---|---|
| `DATABASE_URL` | Staging Supabase pooler connection string |
| `SUPABASE_URL` | Staging Supabase project URL |
| `VOYAGE_API_KEY` | Same as production |
| `PERPLEXITY_API_KEY` | Same as production |
| `ANTHROPIC_API_KEY` | Same as production |
| `API_NINJAS_KEY` | Same as production |
| `MODAL_TOKEN_ID` | Same as production |
| `NEXT_PUBLIC_VERCEL_URL` | Railway staging domain |
| `CORS_EXTRA_ORIGINS` | `https://*-ed-mays-projects.vercel.app` |
| `CORS_ORIGIN_REGEX` | `https://earningsfluency.*\.vercel\.app` |
| `SENTRY_DSN` | Same as production (or omit) |
| `ENV` | `staging` |

3. Railway will auto-deploy from `main` to staging

### 4. Vercel preview environment variables (~5 min, dashboard)

In Vercel project → Settings → Environment Variables, add/override these scoped to **Preview** only:

| Var | Value |
|---|---|
| `NEXT_PUBLIC_SUPABASE_URL` | Staging Supabase project URL |
| `NEXT_PUBLIC_SUPABASE_ANON_KEY` | Staging Supabase anon key |
| `NEXT_PUBLIC_API_URL` | Railway staging API URL |

Leave **Production** env vars untouched.

### 5. Add staging migration deploy to CI (code change — done)

A `deploy-migrations-staging` job has been added to `.github/workflows/ci.yml`. When a PR includes migration changes, CI auto-pushes them to the staging Supabase project.

**GitHub secret needed:** `SUPABASE_STAGING_PROJECT_REF` (the staging project's ref ID). The existing `SUPABASE_ACCESS_TOKEN` works for both projects if they're in the same Supabase org.

### 6. Seed staging with test data (optional)

The staging database will be empty after migrations. Options:
- Ingest 1-2 tickers via the admin panel pointing at staging
- Write a seed script

---

## Modal — why no separate environment

The ingestion pipeline is admin-only, rarely changed, and stateless. The staging API dispatches to the same Modal app, which writes to whichever database its `earnings-secrets` contain (production). This is fine because:
1. Ingestion is idempotent
2. You wouldn't typically test ingestion in preview
3. If needed later, create a `earnings-secrets-staging` Modal secret with the staging `DATABASE_URL`

---

## Verification

1. Push a feature branch with an API change
2. Vercel preview auto-deploys at `earningsfluency-git-<branch>.vercel.app`
3. Open the preview → should redirect to Supabase **staging** auth
4. After sign-in, API calls hit Railway **staging** (check logs)
5. Hit `/health` on the Railway staging URL → `{"status": "ok"}`
6. If the PR includes a migration, CI pushes it to staging Supabase

## Day-to-day workflow

1. Create feature branch, make API + frontend changes
2. Push → Vercel preview deploys; Railway staging deploys from `main`
3. If the PR has migrations, CI pushes them to staging Supabase
4. Test on the Vercel preview URL (points at staging API + staging DB)
5. Merge to main → production migrations deploy, Railway production redeploys
