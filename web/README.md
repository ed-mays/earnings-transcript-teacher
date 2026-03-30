# web/

Next.js 16 frontend for Earnings Transcript Teacher.

> **Note:** This project uses Next.js 16, which has breaking changes from older versions.
> Read `web/AGENTS.md` before writing any frontend code.

## Prerequisites

- Node.js 20+
- The FastAPI backend running locally (`./dev.sh api` from the repo root)

## Environment variables

Copy the template and fill in your values:

```bash
cp env.example .env.local
```

| Variable | Description |
|---|---|
| `NEXT_PUBLIC_SUPABASE_URL` | Supabase project URL (Supabase → Project Settings → API) |
| `NEXT_PUBLIC_SUPABASE_ANON_KEY` | Supabase anon key (same page) |
| `NEXT_PUBLIC_API_URL` | FastAPI base URL — use `http://localhost:8000` for local dev |

## Running

```bash
npm run dev        # http://localhost:3000
```

Or start both API + frontend together from the repo root:

```bash
./dev.sh           # starts api (8000) + web (3000)
```

## How web/ connects to the backend

- **Auth:** Supabase client (`lib/supabase.ts`) handles login/session; JWT is forwarded to FastAPI on every request.
- **API calls:** `NEXT_PUBLIC_API_URL` points to the FastAPI backend. All data fetching goes through FastAPI — Supabase is auth-only on the frontend.
- **Proxy:** `proxy.ts` provides a local dev proxy to avoid CORS issues when testing against a non-local API.

## Key files

| Path | Purpose |
|---|---|
| `app/` | Next.js App Router pages and layouts |
| `components/` | Shared UI components |
| `lib/` | Supabase client, API helpers |
| `AGENTS.md` | Critical notes for AI coding agents — read before editing |
