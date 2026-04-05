# Monorepo Structure

**Status:** Accepted
**Date:** 2026-03-26

## Context

The rewrite (ADR 0001) introduced multiple services — a FastAPI backend, a Next.js frontend, a Modal pipeline, and shared Python modules (NLP, parsing, database access). These services needed to be organized in a way that supported rapid iteration during a compressed delivery window while maintaining the ability to share code between services.

## Decision

All services live in a single repository with top-level directories per concern:

- `api/` — FastAPI backend
- `web/` — Next.js frontend
- `pipeline/` — Modal ingestion functions
- `nlp/`, `parsing/`, `services/`, `db/` — Shared Python modules used by both `api/` and `pipeline/`
- `supabase/` — Database migrations
- `tests/` — Test suite mirroring the source tree

The key driver was development velocity — shared types, a single PR workflow, and the ability to keep the legacy Streamlit app (`app.py`, `pages/`) working alongside the new stack during migration. The shared Python modules (`nlp/`, `services/`, `db/`) are imported by both the API and the pipeline without duplication or package publishing.

## Alternatives considered

1. **Polyrepo (one repo per service)** — Separate repositories for `api`, `web`, and `pipeline` with shared code published as a private Python package. Rejected because: (a) the team is a single developer with AI assistance, so coordination overhead of multiple repos would slow delivery, (b) the shared Python modules change frequently and publishing a package on every change adds friction, and (c) cross-service PRs (e.g., a new API endpoint + its UI) would require coordinating merges across repos.

2. **Monorepo with a build tool (Turborepo, Nx)** — Using a monorepo orchestration tool to manage builds and caching. Rejected because the Python services don't benefit from JavaScript-oriented build caching, and the project is small enough that `dev.sh` and direct `pytest` invocations are sufficient. The Next.js frontend is the only JavaScript project, so monorepo tooling would add complexity for a single JS workspace.

3. **Git submodules for shared code** — Keeping shared modules in a separate repo referenced as a submodule. Rejected because submodules add complexity to cloning, branching, and CI without providing meaningful isolation benefit for a single-developer project.

## Consequences

**Easier:**
- Shared Python modules are always in sync — no version mismatches between API and pipeline
- Single PR for cross-cutting changes (schema migration + API route + UI component)
- Simple CI — one repository to test, one branch to deploy from
- Legacy Streamlit app coexists with new stack during incremental migration

**Harder:**
- Deployment configuration must scope to subdirectories (Railway watches `api/`, Vercel watches `web/`, Modal deploys from `pipeline/`)
- Dependency files are split across contexts (`requirements.txt` for shared Python, `api/requirements.in` for API-specific, `pipeline/requirements.txt` for Modal, `web/package.json` for frontend)
- As the project grows, the flat module layout may need restructuring into Python packages with proper `__init__.py` boundaries
