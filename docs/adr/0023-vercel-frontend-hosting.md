# Vercel for Frontend Hosting

**Status:** Accepted
**Date:** 2026-03-27

## Context

The original target architecture (`docs/architecture-review/02-target-architecture.md`, decision D7) explicitly chose *against* Vercel, planning to use Firebase Hosting with a React SPA. When the stack shifted to Next.js + Supabase (ADRs 0004, 0017), the hosting decision needed to be revisited. Next.js has first-party deployment support on Vercel (the company that maintains Next.js), and the cloud stack analysis (`docs/architecture-review/findings/issue-221-cloud-stack-analysis.md`) evaluated the coupling implications.

## Decision

Deploy the Next.js frontend to Vercel. The configuration is minimal — `web/vercel.json` specifies `{ "framework": "nextjs" }` and Vercel handles the rest: build optimization, edge caching, automatic preview URLs per PR, and serverless function deployment for API routes.

The vendor coupling was rated LOW — the application uses standard Next.js features without Vercel-specific APIs. The frontend could be deployed to any platform that supports Next.js (Netlify, Cloudflare Pages, self-hosted) with minimal configuration changes.

## Alternatives considered

1. **Firebase Hosting** — The original plan. Rejected because: (a) Firebase Hosting is optimized for static files and SPAs, not server-rendered Next.js applications, (b) deploying Next.js on Firebase requires Cloud Functions for SSR, adding latency and complexity, and (c) the shift away from Firebase Auth (ADR 0004) removed the primary reason for staying in the Firebase ecosystem.

2. **Netlify** — A strong Vercel competitor with good Next.js support. Not chosen because: (a) Vercel's Next.js integration is first-party and more deeply optimized (automatic ISR, edge middleware, image optimization), (b) Netlify's Next.js runtime is a community adapter that occasionally lags behind Next.js releases, and (c) Vercel's preview URL workflow is seamlessly integrated with GitHub PRs.

3. **Cloudflare Pages** — Edge-first hosting with good performance. Not chosen because: (a) Cloudflare Pages' Next.js support uses `@cloudflare/next-on-pages`, which has compatibility limitations with some Next.js features (Server Actions, ISR), and (b) the application's backend is on Railway (not Cloudflare Workers), so there's no ecosystem advantage to being on Cloudflare.

4. **Self-hosted (Docker + Nginx)** — Running `next start` in a Docker container on a VPS. Rejected because: (a) managing TLS, CDN, and zero-downtime deploys for a frontend application is unnecessary when Vercel provides these out of the box, and (b) preview URLs per PR require additional CI/CD configuration that Vercel provides automatically.

5. **Railway (same platform as backend)** — Deploying both API and frontend on Railway for operational simplicity. Rejected because: (a) Railway doesn't provide edge caching or CDN for static assets, (b) Next.js on Railway requires a Docker build and `next start` process management, and (c) Vercel's zero-config Next.js deployment is significantly simpler.

## Consequences

**Easier:**
- Zero-config deployment — push to GitHub, Vercel builds and deploys automatically
- Automatic preview URLs for every PR enable review without local setup
- Edge caching, image optimization, and font optimization are built-in
- No Docker image, Nginx config, or TLS certificate management

**Harder:**
- Frontend and backend are on different platforms (Vercel and Railway), requiring CORS configuration and separate environment variable management
- Vercel's free tier has bandwidth and function execution limits
- Some Next.js features may work differently on Vercel vs. other hosting (despite LOW vendor coupling rating)
- Two deployment dashboards to monitor instead of one
