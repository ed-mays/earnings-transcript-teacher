# Disaster Recovery — Infrastructure Rebuild Guide

This document captures every manual configuration step needed to rebuild the EarningsFluency infrastructure from scratch. Use it if you need to nuke and recreate any environment, migrate to a new account, or onboard a collaborator.

---

## Architecture overview

```
Vercel (Next.js frontend)
    ↓ HTTPS
Railway (FastAPI backend)
    ↓ psycopg (PostgreSQL)
Supabase (PostgreSQL + pgvector + Auth)

Modal (async ingestion jobs, dispatched by Railway)
    ↓ psycopg
Supabase
```

Two environments exist: **production** and **staging**.

---

## 1. Supabase

Two projects: one for production, one for staging.

### 1.1 Create the project

1. Log in to [supabase.com](https://supabase.com) → New project
2. Settings to record:
   - Project name: `earningsfluency` (prod) / `earningsfluency-staging` (staging)
   - Region: `<!-- FILL IN: e.g. us-east-1 -->`
   - Password: store in 1Password

### 1.2 Enable the pgvector extension

In the Supabase SQL Editor:

```sql
create extension if not exists vector;
```

### 1.3 Run migrations

From the repo root, using the **Session mode pooler** connection string (port 5432, not 6543):


```bash
source .venv/bin/activate
DATABASE_URL="postgresql://postgres.[ref]:[password]@aws-0-[region].pooler.supabase.com:5432/postgres" \
  python migrate.py
```

Migrations are in `db/migrations/` and are applied in order. The `schema_version` table tracks which have run.

### 1.3a Provision the admin user role (one-time manual step)

After running migrations, backfill existing users and promote the first admin. Run in the Supabase SQL Editor:

```sql
-- Backfill any users who signed up before this migration
INSERT INTO public.profiles (id, role)
  SELECT id, 'learner' FROM auth.users ON CONFLICT DO NOTHING;

-- Promote your admin user (find the UUID in Authentication → Users)
UPDATE public.profiles SET role = 'admin' WHERE id = '<user-uuid>';
```

All future sign-ups get a learner row automatically via the trigger.

### 1.4 Configure Google OAuth

1. Supabase dashboard → Authentication → Providers → Google → Enable
2. Set **Client ID** and **Client Secret** from Google Cloud Console (OAuth 2.0 credentials for the EarningsFluency app)
   - Client ID: `<!-- FILL IN -->`
3. Add redirect URLs under Authentication → URL Configuration:
   - Production: `https://earningsfluency.vercel.app/auth/callback`  <!-- FILL IN: actual domain -->
   - Staging: `https://earningsfluency-git-*.vercel.app/auth/callback`
   - Local dev: `http://localhost:3000/auth/callback`

### 1.5 Collect credentials for other services

From Project Settings → API:

| Value | Where used |
|---|---|
| Project URL (`https://[ref].supabase.co`) | Vercel env vars, web/.env.local |
| Anon / public key | Vercel env vars, web/.env.local |
| JWT secret (Settings → API → JWT Settings) | Railway env vars, api/.env |
| Session mode pooler connection string (port 5432) | Railway env vars, Modal secrets, api/.env |

---

## 2. Railway

One service (`earningsfluency-api`) with two environments: **production** and **staging**.

### 2.1 Create the project and service

1. Log in to [railway.app](https://railway.app) → New project → Deploy from GitHub repo
2. Select `ed-mays/earnings-transcript-teacher`
3. Railway auto-detects `railway.toml` — no extra build configuration needed
4. Service name: `earningsfluency-api`

### 2.2 Build configuration (from `railway.toml`)

```toml
[build]
builder = "dockerfile"
dockerfilePath = "api/Dockerfile"

[deploy]
startCommand = "sh -c 'uvicorn main:app --host 0.0.0.0 --port ${PORT:-8000}'"
healthcheckPath = "/health"
```

No changes needed — Railway reads this automatically.

### 2.3 Create the staging environment

1. Railway project → Environments → New environment → name it `staging`
2. Each environment has its own set of env vars and its own Railway-generated domain

### 2.4 Set environment variables

Set these in both **production** and **staging** environments (with different values):

| Variable | Description |
|---|---|
| `DATABASE_URL` | Supabase Session mode pooler connection string (port 5432) |
| `SUPABASE_JWT_SECRET` | From Supabase → Settings → API → JWT Settings |
| `NEXT_PUBLIC_VERCEL_URL` | The bare Vercel production domain, e.g. `earningsfluency.vercel.app` — used to build the CORS allow-list |
| `CORS_ORIGIN_REGEX` | Regex matching allowed Vercel origins, e.g. `https://earningsfluency(-[a-z0-9-]+)?\.vercel\.app` — covers production and all preview deployments |
| `VOYAGE_API_KEY` | VoyageAI API key (semantic embeddings) |
| `PERPLEXITY_API_KEY` | Perplexity API key (Feynman chat) |
| `ANTHROPIC_API_KEY` | Anthropic API key (Claude for agentic ingestion) |
| `API_NINJAS_KEY` | API Ninjas key (transcript download) |

### 2.5 Verify the deploy

```bash
curl https://[railway-domain]/health
# Expected: {"status": "ok"}
```

---

## 3. Vercel

### 3.1 Create the project

1. Log in to [vercel.com](https://vercel.com) → New project → Import from GitHub
2. Select `ed-mays/earnings-transcript-teacher`
3. Set **Root Directory** to `web`
4. Framework preset: **Next.js** (auto-detected)
5. Leave build command and output directory as defaults

### 3.2 Set environment variables

In Vercel project → Settings → Environment Variables, add these with the correct **environment scope**:

| Variable | Production | Preview (staging) |
|---|---|---|
| `NEXT_PUBLIC_SUPABASE_URL` | Production Supabase URL | Staging Supabase URL |
| `NEXT_PUBLIC_SUPABASE_ANON_KEY` | Production anon key | Staging anon key |
| `NEXT_PUBLIC_API_URL` | Railway production URL | Railway staging URL |

> **How to scope**: When adding each variable, check only the environment checkboxes that apply (Production / Preview / Development).

### 3.3 Automatic preview deployments

No additional configuration needed. Every PR automatically gets a preview deployment at:

```
https://[project-name]-git-[branch-slug]-[vercel-username].vercel.app
```

The `CORS_ORIGIN_REGEX` on Railway covers these domains automatically.

---

## 4. Modal

Modal runs the async ingestion pipeline. The app is defined in `pipeline/ingest.py`.

### 4.1 Set up the Modal account and CLI

```bash
pip install modal
modal token new   # opens browser to authenticate
```

### 4.2 Create the secrets group

Modal stores secrets separately from the app definition. Create a secret group named **exactly** `earnings-secrets`:

```bash
modal secret create earnings-secrets \
  DATABASE_URL="postgresql://..." \
  API_NINJAS_KEY="..." \
  VOYAGE_API_KEY="..." \
  ANTHROPIC_API_KEY="..."
```

Or via the Modal dashboard → Secrets → New secret → name: `earnings-secrets`.

Required keys (must match exactly — `pipeline/ingest.py` references this secret group by name):

| Key | Value |
|---|---|
| `DATABASE_URL` | Supabase Session mode pooler connection string |
| `API_NINJAS_KEY` | API Ninjas key |
| `VOYAGE_API_KEY` | VoyageAI key |
| `ANTHROPIC_API_KEY` | Anthropic key |

### 4.3 Deploy the app

From the repo root with the venv active:

```bash
source .venv/bin/activate
modal deploy pipeline/ingest.py
```

This builds the Docker image, pushes it to Modal, and registers the `ingest_ticker` function under the `earnings-ingestion` app. The Railway API finds it via `modal.Function.lookup("earnings-ingestion", "ingest_ticker")`.

### 4.4 Verify

Trigger a test ingestion via the API (requires an admin user JWT — obtain from the Supabase dashboard under Authentication → Users → select admin user → copy access token, or from a signed-in browser session):

```bash
curl -X POST https://[railway-domain]/admin/ingest \
  -H "Authorization: Bearer <admin-user-jwt>" \
  -H "Content-Type: application/json" \
  -d '{"ticker": "AAPL"}'
# Expected: 202 Accepted
```

Check Modal dashboard → Apps → earnings-ingestion → Logs to confirm the job ran.

You can also verify overall system health:

```bash
curl https://[railway-domain]/admin/health \
  -H "Authorization: Bearer <admin-user-jwt>"
# Expected: {"db":{"connected":true,"schema_version":10},"env_vars":{...},"external_apis":{...}}
```

---

## Environment variable summary

Complete reference of all env vars, grouped by where they're set:

### Railway (api/.env.example for local dev)

```
DATABASE_URL=postgresql://postgres.[ref]:[pw]@aws-0-[region].pooler.supabase.com:5432/postgres
SUPABASE_JWT_SECRET=
NEXT_PUBLIC_VERCEL_URL=
CORS_ORIGIN_REGEX=
VOYAGE_API_KEY=
PERPLEXITY_API_KEY=
ANTHROPIC_API_KEY=
API_NINJAS_KEY=
```

### Vercel (web/env.example for local dev)

```
NEXT_PUBLIC_SUPABASE_URL=https://[ref].supabase.co
NEXT_PUBLIC_SUPABASE_ANON_KEY=
NEXT_PUBLIC_API_URL=http://localhost:8000
```

### Modal (secrets group `earnings-secrets`)

```
DATABASE_URL=
API_NINJAS_KEY=
VOYAGE_API_KEY=
ANTHROPIC_API_KEY=
```

---

## Rebuild checklist

If starting from zero:

- [ ] Create Supabase production project
- [ ] Enable pgvector extension on production
- [ ] Run migrations on production (`python migrate.py`)
- [ ] Backfill profiles table and promote admin user on production (see §1.3a)
- [ ] Configure Google OAuth on production (redirect URLs)
- [ ] Create Supabase staging project
- [ ] Enable pgvector extension on staging
- [ ] Run migrations on staging
- [ ] Backfill profiles table and promote admin user on staging (see §1.3a)
- [ ] Configure Google OAuth on staging (redirect URLs)
- [ ] Create Railway project from GitHub repo
- [ ] Set production env vars in Railway
- [ ] Create Railway staging environment
- [ ] Set staging env vars in Railway (including `CORS_ORIGIN_REGEX`)
- [ ] Create Vercel project from GitHub repo (root directory: `web`)
- [ ] Set production-scoped env vars in Vercel
- [ ] Set preview-scoped env vars in Vercel (staging Supabase + Railway staging)
- [ ] Create Modal `earnings-secrets` secret group
- [ ] Deploy Modal app (`modal deploy pipeline/ingest.py`)
- [ ] Smoke-test each service (Supabase auth, Railway `/health`, Vercel preview, Modal ingest)
