# Testing Strategy

**Status:** Accepted
**Date:** 2026-03-26

## Context

The project needed a testing approach that supported the multi-service architecture (FastAPI backend, shared Python modules, Modal pipeline) while remaining simple enough for a small team to maintain. The test suite needed to cover business logic (NLP processing, orchestration), API endpoints (route handlers, auth), and data access (repository queries) without requiring a running database or external services for unit tests.

## Decision

Use pytest as the test framework with a mirrored source tree structure:

- `tests/unit/` — Unit tests mirroring the source directory (e.g., `tests/unit/api/test_calls.py` for `api/routes/calls.py`)
- `tests/integration/` — Integration tests for cross-module behavior
- `pytest-mock` for mocking external dependencies (database, API clients)
- `pytest-cov` for coverage tracking

Key conventions:
- No ORM-based fixtures or async test runners — most business logic is synchronous Python
- When adding a new function, add at least one test for the happy path
- Tests mock external dependencies (Supabase, Voyage AI, Perplexity, Claude) rather than calling live services

## Alternatives considered

1. **Django test framework** — Django's test runner with `TestCase`, database transactions, and built-in fixtures. Rejected because: (a) the project doesn't use Django (ADR 0001), and (b) Django's test framework is tightly coupled to Django's ORM and middleware, which don't exist in this stack.

2. **pytest-asyncio for async tests** — Adding async test support for testing streaming endpoints and async code. Not chosen as the default because: (a) the service layer is synchronous Python — only the chat streaming endpoint is truly async, and (b) async test setup and teardown adds complexity for the small number of async code paths. Individual async tests can still use `pytest-asyncio` where needed.

3. **Integration tests with a real database (testcontainers)** — Running PostgreSQL in Docker for integration tests. A strong approach for catching SQL bugs. Not chosen because: (a) it would slow the test suite significantly (container startup time), (b) the repository pattern (ADR 0019) provides a clean seam for mocking database access in unit tests, and (c) Supabase-specific features (RLS, triggers) would need a Supabase instance, not just PostgreSQL, for full fidelity.

4. **Behavior-driven testing (behave, pytest-bdd)** — Writing tests as user stories in Gherkin syntax. Rejected because: (a) the team is developer-only (no non-technical stakeholders reading test specs), and (b) Gherkin adds a translation layer between intent and implementation that slows test writing without providing readability benefit for this audience.

5. **Property-based testing (Hypothesis)** — Generating random inputs to find edge cases. Not added as a default requirement because: (a) the application's core logic is string processing and API calls, which benefit more from representative examples than random generation, and (b) Hypothesis can be added for specific modules (e.g., NLP parsing) where edge case discovery is valuable.

## Consequences

**Easier:**
- pytest is the de facto Python testing standard — no learning curve for contributors
- Mirrored source tree makes it obvious where tests live for any module
- Mocking external dependencies keeps tests fast and deterministic
- Coverage tracking identifies untested code paths

**Harder:**
- Mocked database tests can't catch SQL bugs (wrong column names, missing joins, pgvector query issues)
- No end-to-end tests covering the full stack (frontend → API → database → pipeline)
- The 80% coverage target requires discipline to maintain as the codebase grows
- Mock-heavy tests can become brittle if repository interfaces change frequently
