---
name: vercel-ci-preview-env-vars
description: "Inject staging env vars into Vercel preview deploys via -b/-e flags; avoid vercel pull with rootDirectory"
user-invocable: false
origin: auto-extracted
---

# Vercel CI Preview Deploy with Staging Env Vars

**Extracted:** 2026-04-04
**Context:** GitHub Actions deploying Vercel previews for a Next.js app that needs different env vars (staging) than production

## Problem

When a Vercel project has `rootDirectory` configured (e.g. `"web"`), running `vercel pull` in CI downloads project settings that include this `rootDirectory`. Subsequent `vercel build` or `vercel deploy` then double the path (`web/web/package.json` not found). Every workaround (running from subdirectory, copying `.vercel/` to root, etc.) fails because the CLI compounds the paths.

Separately, `NEXT_PUBLIC_*` variables must be present at both **build time** (inlined by Next.js compiler) and **runtime** (used during SSR). Build-only injection causes "Supabase URL and Key required" errors when the preview serves requests.

## Solution

Skip `vercel pull` entirely. Use `vercel deploy` with `-b` (build-env) and `-e` (runtime env) flags:

```yaml
- name: Deploy preview
  id: deploy
  run: |
    url=$(vercel deploy --token=${{ secrets.VERCEL_TOKEN }} --yes \
      -b NEXT_PUBLIC_SUPABASE_URL=${{ secrets.STAGING_SUPABASE_URL }} \
      -b NEXT_PUBLIC_SUPABASE_ANON_KEY=${{ secrets.STAGING_SUPABASE_ANON_KEY }} \
      -b NEXT_PUBLIC_API_URL=${{ secrets.STAGING_API_URL }} \
      -e NEXT_PUBLIC_SUPABASE_URL=${{ secrets.STAGING_SUPABASE_URL }} \
      -e NEXT_PUBLIC_SUPABASE_ANON_KEY=${{ secrets.STAGING_SUPABASE_ANON_KEY }} \
      -e NEXT_PUBLIC_API_URL=${{ secrets.STAGING_API_URL }})
    echo "url=$url" >> $GITHUB_OUTPUT
  env:
    VERCEL_ORG_ID: ${{ secrets.VERCEL_ORG_ID }}
    VERCEL_PROJECT_ID: ${{ secrets.VERCEL_PROJECT_ID }}
```

Key details:
- `-b KEY=VAL` injects at build time (Next.js inlines `NEXT_PUBLIC_*`)
- `-e KEY=VAL` injects at runtime (SSR/server components can read them)
- Both are required for `NEXT_PUBLIC_*` vars used in SSR code
- `STAGING_API_URL` must NOT have a trailing slash (causes `//api/calls` double-slash → CORS failures)
- `VERCEL_ORG_ID` and `VERCEL_PROJECT_ID` as env vars let the CLI find the project without `vercel pull`

## When to Use

- Deploying Vercel previews from GitHub Actions with env var overrides
- Any Vercel project with `rootDirectory` set in dashboard settings
- When preview deployments need to point at a different backend (staging API, staging DB)
