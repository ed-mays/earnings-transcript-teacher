# Server Components Default (Next.js App Router)

**Status:** Accepted
**Date:** 2026-03-27

## Context

The original target architecture (`docs/architecture-review/02-target-architecture.md`) proposed a React SPA (single-page application) with client-side rendering, hosted on Firebase Hosting. When the stack shifted to Supabase + Vercel (ADRs 0004, 0023), the hosting platform natively supported server-side rendering via Next.js. The frontend needed a rendering strategy that balanced developer experience, performance, and data fetching patterns.

## Decision

Use Next.js App Router with Server Components as the default rendering strategy. Pages (`page.tsx`) and layouts (`layout.tsx`) are Server Components by default. Client Components are added only when the component needs browser APIs, React hooks (useState, useEffect), or event handlers — marked with `"use client"` at the top of the file.

Server Components fetch data directly via `createSupabaseServerClient()` or the backend API, avoiding client-side waterfall requests. Client Components use the typed `web/lib/api.ts` wrapper for data fetching.

The key driver was the shift from Firebase to Supabase+Vercel, which made server-side data fetching natural — Server Components can access the database directly without exposing credentials to the browser.

## Alternatives considered

1. **React SPA (client-side rendering only)** — The original target architecture's approach. Rejected because: (a) client-side data fetching requires exposing API endpoints to the browser and managing auth tokens on every request, (b) initial page load is slower (empty HTML → JavaScript bundle → data fetch → render), and (c) SEO is limited without additional server-side rendering infrastructure. The SPA approach made sense with Firebase Hosting but not with Vercel.

2. **Next.js Pages Router** — The older Next.js routing system with `getServerSideProps`/`getStaticProps`. Not chosen because: (a) Pages Router requires explicit data fetching functions per page, while App Router's Server Components fetch data inline, (b) the App Router is Next.js's recommended approach for new projects, and (c) App Router patterns (layouts, loading states, error boundaries) provide better UX out of the box.

3. **Remix** — A React framework with server-first rendering and form-based mutations. A strong alternative with excellent data loading patterns. Not chosen because: (a) Remix had less mature Vercel deployment support than Next.js at the time, (b) the broader ecosystem (shadcn/ui, auth libraries) had more Next.js integrations, and (c) the team was more familiar with Next.js patterns.

4. **Astro with React islands** — Static-first with interactive React components only where needed. Rejected because: (a) the application is heavily interactive (chat, search, learning sessions) — too many "islands" would negate Astro's static-first advantage, and (b) Astro's partial hydration model adds complexity for a predominantly dynamic application.

## Consequences

**Easier:**
- Server Components eliminate client-side data fetching waterfalls for most pages
- Sensitive data (database credentials, API keys) never reach the browser
- Smaller JavaScript bundles — Server Component code runs only on the server
- Built-in layouts, loading states, and error boundaries improve UX with minimal code

**Harder:**
- The mental model of server vs. client components requires understanding which React features are available where
- `"use client"` boundaries must be pushed down the component tree to minimize client JavaScript
- Some libraries (e.g., chart libraries, animation libraries) only work in Client Components
- Debugging SSR-related issues (hydration mismatches, server-only APIs) can be more complex than pure client-side React
