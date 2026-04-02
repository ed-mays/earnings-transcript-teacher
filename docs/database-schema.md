# Database Schema Reference

This document is the data dictionary for the Earnings Transcript Teacher schema. It covers every table's purpose, key columns, Row Level Security (RLS) status, and data retention policy.

For the migration system and how to apply or create migrations, see [`docs/database.md`](database.md).

---

## Quick reference: Row Level Security

| Table | RLS enabled | Policy |
|-------|-------------|--------|
| `learning_sessions` | Yes | Users read/insert/update their own rows (`auth.uid() = user_id`) |
| `analytics_events` | Yes | No policies — denies all callers except service-role |
| `profiles` | Yes | Users read their own row (`auth.uid() = id`) |
| All other tables | No | No RLS — access controlled at the application layer |

Service-role connections (FastAPI via `DATABASE_URL`) bypass RLS entirely. Application-layer ownership checks in `LearningRepository` are still enforced for those paths.

---

## Quick reference: Data retention

| Table | Schedule | Retention period | Notes |
|-------|----------|------------------|-------|
| `learning_sessions` | Daily at 03:00 UTC | 90 days | Cascades to `concept_exercises` |
| `analytics_events` | Daily at 03:30 UTC | 1 year | Staggered 30 min after sessions to spread load |

pg_cron jobs are defined in `supabase/migrations/20260330000001_retention_cleanup.sql`. They check for the `pg_cron` extension at runtime and silently skip on plain Postgres (CI environments).

The `delete_user_data(p_user_id UUID)` helper function hard-deletes a user's `learning_sessions` and anonymises their `analytics_events` rows (sets `session_id = NULL`) so aggregate statistics are preserved but events become untraceable.

---

## Transcript data

These tables hold the raw transcript and speaker data ingested from earnings calls. They are shared (no RLS) — all authenticated users can read them via the application layer.

### `calls`

One row per earnings call. This is the root table; every other table references it via `call_id`.

| Column | Type | Notes |
|--------|------|-------|
| `id` | UUID | Primary key |
| `ticker` | TEXT | Stock ticker symbol (e.g., `AAPL`) |
| `company_name` | TEXT | Full company name |
| `industry` | TEXT | Industry classification |
| `fiscal_quarter` | TEXT | e.g., `Q1 2025` |
| `call_date` | DATE | Date of the earnings call |
| `transcript_json` | JSONB | Raw structured transcript from source |
| `transcript_text` | TEXT | Plain-text version used for NLP |
| `token_count` | INTEGER | Total token count of the transcript |
| `prepared_len` | INTEGER | Character length of the prepared-remarks section |
| `qa_len` | INTEGER | Character length of the Q&A section |
| `created_at` | TIMESTAMPTZ | Row insertion timestamp |

**Constraints:** `UNIQUE(ticker, fiscal_quarter)`

**RLS:** No | **Retention:** None

---

### `speakers`

One row per unique speaker per call, enriched with role and firm metadata.

| Column | Type | Notes |
|--------|------|-------|
| `id` | UUID | Primary key |
| `call_id` | UUID | FK → `calls.id` |
| `name` | TEXT | Speaker's full name |
| `role` | TEXT | e.g., `executive`, `analyst` |
| `title` | TEXT | Job title |
| `firm` | TEXT | Employer or bank name |
| `turn_count` | INTEGER | Number of speaking turns in the call |

**Constraints:** `UNIQUE(call_id, name)`

**RLS:** No | **Retention:** None

---

### `spans`

Atomic text units — either full speaking turns or individual sentences. Embeddings live here for semantic search.

| Column | Type | Notes |
|--------|------|-------|
| `id` | UUID | Primary key |
| `call_id` | UUID | FK → `calls.id` |
| `speaker_id` | UUID | FK → `speakers.id` |
| `section` | TEXT | `prepared` or `qa` |
| `span_type` | TEXT | `turn` (full speaking turn) or `sentence` (split unit) |
| `sequence_order` | INTEGER | Position within the call |
| `text` | TEXT | Span content |
| `char_count` | INTEGER | Character count |
| `textrank_score` | FLOAT | TextRank salience score; used to select takeaways |
| `embedding` | vector(1024) | Voyage AI `voyage-finance-2` embedding for semantic search |

**Index:** `idx_spans_embedding` — HNSW index with `vector_cosine_ops` for approximate nearest-neighbour search.

**RLS:** No | **Retention:** None

---

## Analysis outputs

These tables hold the enrichment and analysis produced by the NLP and LLM pipeline. All are shared (no RLS).

### `call_topics`

NMF (Non-negative Matrix Factorisation) topics extracted per call.

| Column | Type | Notes |
|--------|------|-------|
| `id` | UUID | Primary key |
| `call_id` | UUID | FK → `calls.id` |
| `label` | TEXT | Topic identifier |
| `terms` | TEXT[] | Top terms for this topic |
| `weight` | FLOAT | Topic weight in the call |
| `rank_order` | INTEGER | Rank among topics for this call |
| `topic_name` | TEXT | Human-readable topic name (added migration 008) |

**RLS:** No | **Retention:** None

---

### `span_keywords`

TF-IDF keywords computed at the call level.

| Column | Type | Notes |
|--------|------|-------|
| `id` | UUID | Primary key |
| `call_id` | UUID | FK → `calls.id` |
| `term` | TEXT | Keyword |
| `score` | FLOAT | TF-IDF score |
| `ngram_size` | INTEGER | 1 for unigrams, 2 for bigrams, etc. |

**RLS:** No | **Retention:** None

---

### `extracted_takeaways`

Key sentences selected by TextRank salience scoring.

| Column | Type | Notes |
|--------|------|-------|
| `id` | UUID | Primary key |
| `call_id` | UUID | FK → `calls.id` |
| `chunk_id` | UUID | FK → `transcript_chunks.id` |
| `takeaway` | TEXT | The selected sentence |
| `why_it_matters` | TEXT | LLM-generated explanation of significance |

**RLS:** No | **Retention:** None

---

### `call_synthesis`

Aggregated analysis of the entire call — one row per call.

| Column | Type | Notes |
|--------|------|-------|
| `id` | UUID | Primary key |
| `call_id` | UUID | FK → `calls.id` (UNIQUE) |
| `overall_sentiment` | TEXT | Call-level sentiment classification |
| `executive_tone` | TEXT | Qualitative tone of executives |
| `key_themes` | TEXT[] | High-level themes from the call |
| `strategic_shifts` | JSONB[] | Array of shift objects: topic, before, after, signal |
| `analyst_sentiment` | TEXT | Sentiment from analyst questions |
| `call_summary` | TEXT | Free-text narrative summary |

**RLS:** No | **Retention:** None

---

### `qa_pairs`

Structured pairings of analyst questions to executive answers.

| Column | Type | Notes |
|--------|------|-------|
| `id` | UUID | Primary key |
| `call_id` | UUID | FK → `calls.id` |
| `exchange_order` | INTEGER | Sequence within the Q&A section |
| `question_span_id` | UUID | FK → `spans.id` |
| `answer_span_id` | UUID | FK → `spans.id` |

**Constraints:** `UNIQUE(question_span_id, answer_span_id)`

**RLS:** No | **Retention:** None

---

### `transcript_chunks`

LLM-processed logical chunks of the transcript, scored for analytical depth.

| Column | Type | Notes |
|--------|------|-------|
| `id` | UUID | Primary key |
| `call_id` | UUID | FK → `calls.id` |
| `chunk_id` | TEXT | Stable identifier within the call |
| `chunk_type` | TEXT | Classification of the chunk's content type |
| `sequence_order` | INTEGER | Position within the call |
| `tier1_score` | FLOAT | Relevance score from first-pass analysis |
| `needs_deep_analysis` | BOOLEAN | Whether the chunk was routed to deep analysis |
| `chunk_text` | TEXT | The chunk content |

**RLS:** No | **Retention:** None

---

### `extracted_terms`

Industry-specific and financial jargon extracted and defined by the LLM pipeline.

| Column | Type | Notes |
|--------|------|-------|
| `id` | UUID | Primary key |
| `call_id` | UUID | FK → `calls.id` |
| `chunk_id` | TEXT | Source chunk identifier |
| `term` | TEXT | The jargon term |
| `definition` | TEXT | Concise definition |
| `explanation` | TEXT | Extended explanation (default `''`) |
| `category` | TEXT | `industry` or `financial` (default `industry`) |

**RLS:** No | **Retention:** None

---

### `core_concepts`

High-level learning concepts extracted per chunk, used to build study exercises.

| Column | Type | Notes |
|--------|------|-------|
| `id` | UUID | Primary key |
| `call_id` | UUID | FK → `calls.id` |
| `chunk_id` | TEXT | Source chunk identifier |
| `concept` | TEXT | Concept label |

**RLS:** No | **Retention:** None

---

### `evasion_analysis`

Scores each Q&A exchange for analyst defensiveness and executive evasion.

| Column | Type | Notes |
|--------|------|-------|
| `id` | UUID | Primary key |
| `call_id` | UUID | FK → `calls.id` |
| `chunk_id` | TEXT | Source chunk identifier |
| `analyst_name` | TEXT | Analyst who asked the question |
| `question_topic` | TEXT | Topic classification of the question |
| `question_text` | TEXT | Full question text |
| `answer_text` | TEXT | Full answer text |
| `analyst_concern` | TEXT | Underlying concern inferred from the question |
| `defensiveness_score` | FLOAT | 0–1 score; higher = more evasive |
| `evasion_explanation` | TEXT | LLM rationale for the score |

**RLS:** No | **Retention:** None

---

### `misconceptions`

Common misinterpretations of transcript content, paired with corrections.

| Column | Type | Notes |
|--------|------|-------|
| `id` | UUID | Primary key |
| `call_id` | UUID | FK → `calls.id` |
| `chunk_id` | TEXT | Source chunk identifier |
| `fact` | TEXT | What was actually said |
| `misinterpretation` | TEXT | How it might be misread |
| `correction` | TEXT | The accurate interpretation |

**RLS:** No | **Retention:** None

---

### `competitors`

Competitor companies mentioned in the transcript, with optional enrichment data.

| Column | Type | Notes |
|--------|------|-------|
| `id` | UUID | Primary key |
| `call_id` | UUID | FK → `calls.id` |
| `competitor_name` | TEXT | Competitor's company name |
| `competitor_ticker` | TEXT | Ticker symbol (nullable) |
| `description` | TEXT | Brief description of the competitor |
| `mentioned_in_transcript` | BOOLEAN | Whether the mention is explicit in the transcript |
| `fetched_at` | TIMESTAMPTZ | When enrichment data was last fetched |

**Constraints:** `UNIQUE(call_id, competitor_name)`

**RLS:** No | **Retention:** None

---

### `call_brief`

LLM-generated pre-reading brief — one row per call. Shown to users before they read the transcript.

| Column | Type | Notes |
|--------|------|-------|
| `id` | UUID | Primary key |
| `call_id` | UUID | FK → `calls.id` (UNIQUE) |
| `context_line` | TEXT | One-sentence framing of why this call matters |
| `bigger_picture` | JSONB | Array of broader-context bullet points (default `[]`) |
| `interpretation_questions` | JSONB | Array of guiding questions for the reader (default `[]`) |
| `created_at` | TIMESTAMPTZ | Row insertion timestamp |

**RLS:** No | **Retention:** None

---

## Learning tools

These tables track user progress and study activity. `learning_sessions` and `profiles` are RLS-protected.

### `learning_sessions`

One row per study session. Holds the full Feynman chat history in `notes`.

| Column | Type | Notes |
|--------|------|-------|
| `id` | UUID | Primary key |
| `user_id` | UUID | FK → `auth.users.id`; nullable for anonymous CLI sessions |
| `call_id` | UUID | FK → `calls.id` |
| `started_at` | TIMESTAMPTZ | Session start time |
| `completed_at` | TIMESTAMPTZ | Session end time (nullable if in progress) |
| `notes` | JSON | Full Feynman conversation history |

**RLS:** Yes — users can only select/insert/update rows where `auth.uid() = user_id`. Rows with `user_id = NULL` (anonymous CLI sessions, identified by `SYSTEM_USER_ID` in `LearningRepository`) are unreachable via JWT because `NULL != auth.uid()` evaluates to NULL.

**Retention:** Deleted daily at 03:00 UTC after 90 days. Deletion cascades to `concept_exercises`.

---

### `concept_exercises`

One row per Feynman explanation exercise within a session.

| Column | Type | Notes |
|--------|------|-------|
| `id` | UUID | Primary key |
| `session_id` | UUID | FK → `learning_sessions.id` (ON DELETE CASCADE) |
| `concept_label` | TEXT | The concept the user was asked to explain |
| `user_explanation` | TEXT | User's explanation attempt |
| `ai_critique` | TEXT | AI feedback on the explanation |
| `revised_explanation` | TEXT | User's revised explanation after critique (nullable) |
| `confidence` | TEXT | User's self-assessed confidence: `low`, `medium`, or `high` |

**RLS:** No direct RLS — access is controlled indirectly because rows are only reachable through `learning_sessions`, which is RLS-protected.

**Retention:** Cascade-deleted when the parent `learning_session` row is deleted (90-day retention).

---

### `transcript_progress`

Tracks which steps of the structured reading flow a user has completed.

| Column | Type | Notes |
|--------|------|-------|
| `id` | UUID | Primary key |
| `call_id` | UUID | FK → `calls.id` |
| `step_number` | INTEGER | Step index 1–6 |
| `viewed_at` | TIMESTAMPTZ | When the step was marked complete |

**Constraints:** `UNIQUE(call_id, step_number)`

**RLS:** No | **Retention:** None

Note: This table has no `user_id` column — progress is currently tracked per call, not per user. This is a known limitation; user-scoped progress tracking is planned.

---

### `profiles`

One row per authenticated user. Created automatically by a `handle_new_user()` trigger on `auth.users` insert.

| Column | Type | Notes |
|--------|------|-------|
| `id` | UUID | PK — mirrors `auth.users.id` |
| `role` | ENUM | `admin` or `learner`; default `learner` |

**RLS:** Yes — users can only select their own row (`auth.uid() = id`). Admins are distinguished at the application layer by checking `profiles.role`.

**Retention:** None (deleted when the `auth.users` row is deleted via Supabase auth lifecycle).

---

## Observability and auth

### `analytics_events`

Usage event log. Written exclusively by the FastAPI service via service-role connection.

| Column | Type | Notes |
|--------|------|-------|
| `id` | UUID | Primary key |
| `event_name` | TEXT | Event identifier (e.g., `call_viewed`, `session_started`) |
| `session_id` | UUID | Anonymous session identifier; set to NULL by `delete_user_data()` |
| `properties` | JSONB | Arbitrary event metadata |
| `created_at` | TIMESTAMPTZ | Event timestamp |

**RLS:** Yes — RLS is enabled with no policies. This denies all callers except service-role connections (which bypass RLS). No JWT-authenticated user can read or write this table directly.

**Retention:** Deleted daily at 03:30 UTC after 1 year. The `delete_user_data()` function anonymises events by setting `session_id = NULL` rather than deleting them, so aggregate statistics are preserved.
