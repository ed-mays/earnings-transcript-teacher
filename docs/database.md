# Database

## Authoritative bootstrap

`migrate.py` is the single source of truth for the database schema. To initialize a fresh database, run:

```bash
python migrate.py
```

This applies all migration files from `db/migrations/` in order and tracks applied versions in the `schema_version` table. Running it again on an already-migrated database is safe — already-applied migrations are skipped.

## Migration files

All schema changes live in `db/migrations/` as numbered SQL files (`NNN_description.sql`). Each file is self-contained and ends with an idempotent version insert:

```sql
INSERT INTO schema_version (version) VALUES (NNN) ON CONFLICT DO NOTHING;
```

The current schema version is tracked in `db/repositories/schema.py` (`REQUIRED_SCHEMA_VERSION`). The app will refuse to start if the database is below this version.

## Adding a migration

1. Create `db/migrations/NNN_description.sql` (next sequential number)
2. Write the DDL changes
3. End with the version insert (see above)
4. Run `python migrate.py` to apply

## schema.sql

`db/schema.sql` has been removed. It was a partial snapshot (v3) that diverged from the actual migration sequence (now at v11+) and caused confusion for new contributors. Use `migrate.py` to bootstrap any environment.

## Rollback

See `docs/runbooks/migration-rollback.md` for the compensating-migration rollback procedure.
