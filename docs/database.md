# Database

## Migration system

Schema changes are managed with the [Supabase CLI](https://supabase.com/docs/reference/cli). Migration files live in `supabase/migrations/` as timestamped SQL files.

To apply all pending migrations to the linked Supabase project:

```bash
supabase db push
```

This is idempotent — already-applied migrations are tracked by Supabase and skipped.

By default this targets the linked project (production). To push to staging instead:

```bash
supabase link --project-ref <staging-project-ref>
supabase db push
```

Re-link to production afterward: `supabase link --project-ref qxdexukkmzidalnrzfqf`

CI handles this automatically — the `deploy-migrations-staging` job pushes to staging on PRs that change migration files.

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

## Schema reference

For the full data dictionary — table purposes, key columns, RLS policies, and data retention status — see [`docs/database-schema.md`](database-schema.md).
