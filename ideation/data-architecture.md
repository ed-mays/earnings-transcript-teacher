For a split setup, think in terms of clear responsibilities: Postgres (or similar) is your **source of truth and analytics**, and the vector DB is your **semantic index** over transcript spans.

## 1. What lives where

- Postgres (structured side)
  - Calls: call metadata (ticker, date, quarter, filing links, price reaction).
  - Speakers: identities, roles, firms, plus aggregate behavior metrics over time.
  - Spans: each prepared remark paragraph, question, and answer, with all your annotations (section type, speaker, topics, keywords, forward‑looking flags, etc.).
  - QA pairs: explicit links between question span and answer span.
  - User/learning sessions, exercises done, notes, scores.

- Vector DB (semantic side)
  - Chunks: embedded text snippets (usually aligned to spans or small groups of spans) plus minimal metadata (ids, call/ticker, section_type, etc.).

Postgres is where you _compute and store meaning_; the vector DB is how you _quickly find relevant text_.

## 2. Retrieval flow pattern

For each learning interaction:

1. Use Postgres to narrow scope: filter by user’s context (ticker, quarter, section, theme, etc.) and get candidate `span_id`s / `call_id`s.
2. Query vector DB over only those candidates (via metadata filters) to get the top N chunks.
3. Fetch full annotations for those spans from Postgres (QA links, hedging, guidance flags, etc.).
4. Build the LLM prompt with both the raw text and a compact representation of the annotations.

This keeps retrieval fast while still giving the tutor rich structure to reason over.

## 3. Practical next steps

- Design schemas in Postgres for `calls`, `speakers`, `spans`, and `qa_pairs` keyed by stable IDs.
- Decide a chunking strategy (e.g., one chunk per span or merged small spans) and index those in your vector DB with foreign keys back to `span_id` and `call_id`.
- Implement a small “retrieval service” that encapsulates:
  - Postgres filters → candidate ids
  - Vector search over candidates → chunk ids
  - Postgres hydration → annotations and text for the prompt.

Once you have a first pass at your Postgres schemas, I can help you refine them to best support the learning flows you care about most.

Sources
