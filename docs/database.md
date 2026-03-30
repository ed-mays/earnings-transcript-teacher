# Database

## Migration system

Schema changes are managed with the [Supabase CLI](https://supabase.com/docs/reference/cli). Migration files live in `supabase/migrations/` as timestamped SQL files.

To apply all pending migrations to the linked Supabase project:

```bash
supabase db push
```

This is idempotent — already-applied migrations are tracked by Supabase and skipped.

## Adding a migration

1. Create a new file: `supabase/migrations/YYYYMMDDHHMMSS_description.sql`
2. Write the DDL changes (no version tracking boilerplate required)
3. Run `supabase db push` to apply

To generate a migration from a local diff:

```bash
supabase db diff -f description_of_change
```

## Rollback

See `docs/runbooks/migration-rollback.md` for the compensating-migration rollback procedure.
