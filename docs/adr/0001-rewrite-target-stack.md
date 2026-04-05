# Rewrite Target Stack

**Status:** Accepted
**Date:** 2026-03-26

## Context

The application was a Python + Streamlit monolith that tightly coupled UI rendering, data processing, NLP analysis, and database access into a single process. The architecture audit (`docs/architecture-review/01-current-system-audit.md`) identified critical coupling issues: Streamlit's execution model (re-running the entire script on each interaction) made state management fragile, there was no API layer for external consumers, and the monolith could not scale compute-intensive ingestion independently from the user-facing application.

The project needed to separate concerns into independently deployable services while preserving the existing Python NLP and ingestion pipeline.

## Decision

Rewrite the application as a multi-service architecture:

- **FastAPI** (`api/`) — Backend API with typed endpoints, dependency injection, and async streaming support
- **Next.js** (`web/`) — Frontend with server-side rendering, replacing Streamlit's widget-based UI
- **Supabase** — Managed PostgreSQL database with built-in JWT authentication and Row Level Security
- **Modal** (`pipeline/`) — Serverless compute for long-running transcript ingestion (30–60s LLM pipeline)
- **Railway** — Container hosting for the FastAPI backend
- **Vercel** — Frontend hosting with zero-config Next.js deployment

The key driver was separating concerns — a real API layer, a modern frontend framework, and managed infrastructure — while preserving the Python NLP/ingestion pipeline unchanged. The rewrite was designed to be incremental: each service could be built and deployed independently, with the legacy Streamlit app remaining operational during migration.

## Alternatives considered

1. **Stay on Streamlit** — Adding authentication, API endpoints, and background processing to Streamlit would require fighting its execution model. Streamlit Community Cloud has no concept of API routes, background jobs, or role-based access. Rejected because the product requirements (multi-user auth, async ingestion, structured API) fundamentally exceeded Streamlit's design constraints.

2. **All-Firebase stack (Cloud Run + Firestore + Firebase Auth + Firebase Hosting)** — This was the original target architecture (`docs/architecture-review/02-target-architecture.md`). Rejected because: (a) Firestore's document model was a poor fit for the existing relational schema with pgvector, (b) migrating from PostgreSQL to Firestore would require rewriting all queries, and (c) Firebase Auth lacked the Row Level Security integration that Supabase provides natively with PostgreSQL.

3. **Django monolith** — A single Django application with Celery for background tasks. Rejected because: (a) the frontend requirements (SSR, streaming chat, client-side interactivity) would still need a separate framework or heavy Django template gymnastics, and (b) Django's ORM would add friction for the custom pgvector queries already working with raw SQL.

4. **FastAPI + React SPA (no SSR)** — The original plan before the Supabase pivot. Rejected because moving to Supabase made server-side data fetching natural (no CORS, direct database access from server components), and Next.js provided this with zero additional infrastructure.

## Consequences

**Easier:**
- Each service scales independently (ingestion compute is decoupled from API serving)
- Authentication and authorization are handled by managed infrastructure (Supabase JWTs + RLS)
- The frontend can use modern patterns (Server Components, streaming) that Streamlit cannot express
- The existing Python NLP pipeline (`nlp/`, `parsing/`, `services/`) required minimal changes

**Harder:**
- Operational complexity increased from 1 deployable to 4 (API, frontend, pipeline, database)
- Local development requires orchestrating multiple services (`dev.sh` script)
- Environment variable management across Railway, Vercel, Modal, and Supabase
- Debugging requires correlating logs across services
