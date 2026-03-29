# Runbook: Migration Rollback

## Overview

`migrate.py` applies forward-only migrations. Postgres does not support automatic DDL rollback, so reverting a migration requires a compensating migration — a new SQL file that undoes the schema change.

---

## Step 1: Identify the current schema version

```sql
SELECT MAX(version) FROM schema_version;
```

Via Supabase SQL Editor or local psql:

```bash
psql $DATABASE_URL -c "SELECT MAX(version) FROM schema_version;"
```

---

## Step 2: Determine what needs to be undone

Review the migration file that introduced the problem:

```bash
cat db/migrations/NNN_name.sql
```

Identify the DDL statements (e.g. `ALTER TABLE ADD COLUMN`, `CREATE TABLE`, `CREATE INDEX`).

---

## Step 3: Write a compensating migration

Create a new migration file with the next version number that reverses the change:

```bash
# Example: undo column added in migration 010
touch db/migrations/012_rollback_010_added_column.sql
```

Common compensating statements:

| Original | Compensating |
|----------|-------------|
| `ALTER TABLE t ADD COLUMN c TYPE` | `ALTER TABLE t DROP COLUMN c` |
| `CREATE TABLE t (...)` | `DROP TABLE t` |
| `CREATE INDEX idx ON t (col)` | `DROP INDEX idx` |
| `ALTER TABLE t ALTER COLUMN c TYPE new` | `ALTER TABLE t ALTER COLUMN c TYPE original` |

End the file with the standard version insert:

```sql
INSERT INTO schema_version (version) VALUES (NNN) ON CONFLICT DO NOTHING;
```

---

## Step 4: Apply the compensating migration

**Local Postgres:**

```bash
DATABASE_URL=postgresql://... python migrate.py
```

**Supabase (production/staging):**

Use the Supabase SQL Editor — Supabase does not auto-run migrations. Paste the contents of the compensating migration file and execute manually.

> Note: Direct psql connections to Supabase may fail DNS resolution on newer projects. Always use the SQL Editor for Supabase targets.

---

## Step 5: Verify

```sql
SELECT MAX(version) FROM schema_version;
-- Should reflect the new compensating migration version
```

Confirm the schema change was reverted by inspecting the table structure:

```sql
\d table_name
```

---

## Escalation

If a migration causes data loss or cannot be compensated without restoring from backup, contact the project owner before proceeding. Supabase supports point-in-time recovery (PITR) on paid plans.
