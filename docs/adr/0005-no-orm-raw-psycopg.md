# No ORM — Raw psycopg + Dataclasses

**Status:** Accepted
**Date:** 2026-03-26

## Context

The application's data access layer needed to support standard CRUD operations alongside specialized queries: pgvector similarity searches with HNSW indexing, complex joins across transcript/analysis/learning tables, and bulk upserts for the ingestion pipeline. The schema was already well-understood from the prototype era, with ~20 tables and stable relationships.

## Decision

Use raw parameterized SQL via psycopg3 with results mapped to Python dataclasses. All database access is encapsulated in repository classes (ADR 0019) that return typed dataclasses rather than ORM model instances. Queries use `%s` parameterization for SQL injection prevention.

The key drivers were: (a) fine-grained control over pgvector queries (custom HNSW similarity joins like `ORDER BY embedding <=> %s LIMIT %s`), (b) avoiding ORM overhead and abstraction leakage for a schema that was already stable, and (c) keeping the data layer lightweight — the entire repository layer is plain Python with no metaclasses, migration generators, or query builders.

## Alternatives considered

1. **SQLAlchemy (Core or ORM)** — The standard Python database toolkit. Rejected because: (a) SQLAlchemy's pgvector support via `pgvector-python` works but requires learning SQLAlchemy's expression language for vector operations that are simpler in raw SQL, (b) the project's queries are mostly hand-tuned and benefit from direct SQL control, and (c) SQLAlchemy adds significant dependency weight and configuration complexity (engine, session, declarative base) for a project where raw SQL is already working. SQLAlchemy Core (without ORM) would be a reasonable middle ground if query composition becomes complex.

2. **Tortoise ORM** — An async-native Python ORM. Rejected because: (a) the service layer is synchronous Python (only streaming chat is async), so Tortoise's async-first design would require `asyncio.run()` wrappers or a full async rewrite, and (b) Tortoise's pgvector support is less mature than SQLAlchemy's.

3. **Prisma (via prisma-client-py)** — A type-safe ORM popular in the Node.js ecosystem with a Python client. Rejected because: (a) the Python client is community-maintained with less stability than psycopg, (b) Prisma's migration system would conflict with Supabase CLI migrations (ADR 0004), and (c) pgvector support requires custom raw queries anyway, negating Prisma's type-safety benefit for the most critical queries.

## Consequences

**Easier:**
- Full control over query execution plans, index usage, and pgvector-specific operators
- No ORM "magic" — what the code does is immediately visible in the SQL strings
- Minimal dependency surface — psycopg3 is the only database driver
- Dataclasses are plain Python objects with no database session lifecycle concerns
- Easy to write and review parameterized queries for security

**Harder:**
- Schema changes require manually updating both migration SQL and Python dataclass definitions (no auto-generation)
- No automatic relationship loading — joins must be written explicitly
- Query composition for dynamic filters (e.g., search with optional parameters) requires manual SQL building
- Developers must remember parameterized queries everywhere — no ORM to enforce it by default
