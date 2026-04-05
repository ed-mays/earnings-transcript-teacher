# Railway for Backend Hosting

**Status:** Accepted
**Date:** 2026-03-27

## Context

The FastAPI backend (ADR 0001) needed a hosting platform that could run a long-lived Python process with WebSocket/SSE support for streaming chat, persistent connections to Supabase PostgreSQL, and straightforward Docker deployment. The vendor coupling analysis (`docs/architecture-review/findings/issue-221-cloud-stack-analysis.md`) evaluated hosting options against portability and operational complexity.

## Decision

Deploy the FastAPI backend to Railway as a Docker container. The application uses a standard Python Docker image with Uvicorn, exposes port 8000, and has no Railway-specific API dependencies. Railway provides automatic deploys from git, environment variable management, and a managed container runtime.

The vendor coupling was rated LOW — the app uses a vanilla Dockerfile that could run on any container platform without modification.

## Alternatives considered

1. **Serverless (AWS Lambda, Vercel Functions)** — Deploying each API route as a serverless function. Rejected because: (a) the connection pooling strategy (ADR 0007) relies on a persistent `ConnectionPool` initialized during the FastAPI lifespan, which doesn't survive serverless cold starts, (b) SSE streaming for chat requires long-lived connections that exceed typical serverless timeout defaults, and (c) the shared Python modules (`nlp/`, `services/`) are large enough that cold start times would noticeably impact latency.

2. **Google Cloud Run** — Container-based serverless with request-based scaling. A strong alternative that would have worked — Cloud Run supports long-lived connections and Docker containers. Not chosen primarily because Railway offered a simpler developer experience (git push to deploy, built-in log viewer, no GCP project/IAM setup) for a project in rapid prototyping phase. Cloud Run remains a viable migration target.

3. **Fly.io** — Container hosting with edge deployment. Similar to Railway in capabilities. Not chosen because Railway was already familiar from prior projects, and Fly.io's edge deployment model didn't provide meaningful benefit since the database (Supabase) is in a single region.

4. **Self-hosted (VPS with Docker Compose)** — Running the container on a DigitalOcean/Hetzner VPS. Rejected because managing TLS certificates, process supervision, and zero-downtime deploys would consume time better spent on product development.

## Consequences

**Easier:**
- Deploy is `git push` — Railway auto-builds and deploys the Docker image
- Environment variables are managed in Railway's dashboard, injected at runtime
- No vendor-specific code — the Dockerfile and Uvicorn config are platform-agnostic
- Log viewing and deployment rollback are built into Railway's UI

**Harder:**
- Single instance by default — horizontal scaling requires Railway's paid scaling features
- No edge deployment — all requests route to a single region (acceptable given Supabase is also single-region)
- Railway's free tier has usage limits that require upgrading for production workloads
- No built-in CDN or static asset serving (handled by Vercel for the frontend)
