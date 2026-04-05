# Repository Pattern for Data Access

**Status:** Accepted
**Date:** 2026-03-26

## Context

The application's data access was originally scattered across service modules as inline SQL queries. The architecture review (`docs/architecture-review/findings/issue-198-repository-service.md`) found that SQL was mixed with business logic, making schema changes risky (no single place to audit query impact) and testing difficult (mocking database calls required patching at many call sites). The data layer specification (`docs/architecture-review/specs/[002] data-layer.spec.md`) proposed consolidating all database access behind a consistent interface.

## Decision

Encapsulate all database access in domain-specific repository classes:

- `CallRepository` — Earnings call CRUD
- `AnalysisRepository` — Analysis results
- `LearningRepository` — Learning sessions and progress
- `EmbeddingRepository` — Vector embeddings (pgvector operations)
- Plus 4 additional repositories for supporting domains

All repositories live in `db/repositories/` with a backwards-compatible `__init__.py` that re-exports for existing import paths. Repositories accept a database connection as a constructor parameter (injected via FastAPI's `DbDep`) and return typed Python dataclasses. Route handlers stay thin — they delegate to repositories for data access and to service modules for business logic.

## Alternatives considered

1. **Inline SQL in route handlers** — Writing SQL directly in FastAPI route functions. This was the pre-rewrite pattern. Rejected because: (a) SQL scattered across route handlers makes schema changes risky (must audit every handler), (b) testing requires mocking the database connection at every call site, and (c) query optimization is harder when the same query pattern is duplicated across handlers.

2. **Active Record pattern (ORM models with query methods)** — Each model class has methods like `User.find_by_id()`, `Analysis.create()`. Rejected because: (a) the project uses raw SQL without an ORM (ADR 0005), so there are no model classes to attach methods to, and (b) Active Record conflates data representation with persistence, which makes testing harder (model objects carry database state).

3. **Service-layer query builder** — Business logic and data access combined in service classes with a query builder for dynamic queries. Rejected because: (a) combining business logic with data access violates single-responsibility, (b) service modules would become large and hard to test, and (c) the repository pattern provides a clearer seam for mocking in tests.

4. **CQRS (Command Query Responsibility Segregation)** — Separate read and write models with different repositories. Rejected because the application's query patterns are straightforward (no complex read projections or event sourcing), and CQRS adds architectural complexity that isn't justified at the current scale.

## Consequences

**Easier:**
- Schema changes require auditing only the repository modules, not the entire codebase
- Route handlers are thin and focused on HTTP concerns (request validation, response formatting)
- Repositories can be injected as dependencies, making unit tests straightforward with mock repositories
- Query optimization is centralized — a slow query in `CallRepository` is found and fixed in one place

**Harder:**
- Adding a new database operation requires creating a repository method (even for one-off queries)
- The repository layer adds indirection — developers must navigate from route handler → repository → SQL
- Complex queries spanning multiple domains may not fit cleanly into a single repository
- The backwards-compatible `__init__.py` re-exports add import complexity
