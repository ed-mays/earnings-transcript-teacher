# Data Retention Policy

This document records the retention windows, account deletion process, data residency, and planned implementation approach for EarningsFluency user data.

---

## Scope

Two tables contain user-generated data that grows unbounded:

| Table | Contents | User-linked via |
|---|---|---|
| `learning_sessions` | Full chat history for each Q&A session | `user_id` (UUID) |
| `concept_exercises` | Per-concept explanation attempts | `session_id` FK → `learning_sessions` |
| `analytics_events` | Usage metadata (event name, properties, timestamp) | `session_id` FK (no direct `user_id` column) |

`concept_exercises` is a child of `learning_sessions` with `ON DELETE CASCADE`, so session deletions automatically remove exercises.

---

## Retention windows

| Table | Retention | Rationale |
|---|---|---|
| `learning_sessions` | **90 days** | Keeps recent learning context accessible; older sessions are rarely revisited |
| `concept_exercises` | **90 days** (cascades from sessions) | Child table; matches parent |
| `analytics_events` | **1 year** | Longer window supports product analytics and year-over-year comparisons |

These are starting points. Review annually or when the user base grows significantly.

---

## Account deletion process

When a user closes their account:

1. **Hard-delete** all rows in `learning_sessions` where `user_id = <closed_user_id>`. `concept_exercises` rows cascade automatically.
2. **Anonymize** `analytics_events` linked to any of the deleted sessions: set `session_id = NULL` on those rows. The events are retained for aggregate stats but are no longer traceable to the user.

The SQL helper function `delete_user_data(user_id UUID)` (to be added in #242) will encapsulate these two steps for use by the account-deletion auth webhook.

---

## Data residency

- **Supabase region:** `us-east-2` (AWS Ohio, United States)
- No EU data residency is provided today. If EU users are onboarded at scale, a separate Supabase project in `eu-west-1` or `eu-central-1` will be required to satisfy GDPR Article 46 data transfer requirements.

---

## Implementation approach

Scheduled cleanup will be handled by **Supabase `pg_cron`** — a Postgres-native scheduler that runs SQL jobs inside the database. No additional infrastructure is required.

Implementation tracked in **#242**. Once that issue is complete, cron job details will be added here.

---

## Review cadence

Revisit retention windows:
- Annually (each January)
- When monthly active users exceed 1,000
- If a compliance or legal requirement changes
