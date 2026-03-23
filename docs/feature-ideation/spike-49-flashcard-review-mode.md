# Spike #49 — Flashcard-Style Review Mode

*A design spike answering the questions posed in [GitHub issue #49](https://github.com/ed-mays/earnings-transcript-teacher/issues/49).*

---

## Executive Summary

The earnings transcript pipeline already generates four data types that translate directly into high-quality flashcards: misconceptions, evasion analysis, extracted terms, and takeaways. **No new ingestion is required.** A flashcard mode can be built entirely by reading existing DB tables.

The recommended approach is a two-stage rollout:

1. **Within-transcript review** (lower effort, higher immediate value): A "Review" mode that appears as a capstone after the learning path steps, serving flashcards from the current transcript before the user enters the Feynman Loop.
2. **Cross-transcript spaced repetition** (higher effort, higher long-term value): A library-level review queue that mixes cards from all ingested transcripts, paced by a lightweight SRS algorithm.

Both stages share the same card rendering and interaction model. The only additional work for Stage 2 is a `flashcard_reviews` table and a scheduling query.

---

## 1. Source Material Analysis

### Which data types make good flashcard source material?

All four Tier 2 pipeline outputs are suitable. They differ in the *type* of cognitive exercise they produce.

| Source Table | # Cards / Transcript (est.) | Card Type | Cognitive Load |
|---|---|---|---|
| `extracted_terms` | 15–30 | Vocabulary recall | Low — recognise and define |
| `misconceptions` | 5–10 | Error detection | Medium — spot what's wrong |
| `evasion_analysis` | 5–15 | Analytical interpretation | Medium-High — read intent behind language |
| `extracted_takeaways` | 10–20 | Significance reasoning | Medium — explain "why it matters" |
| `core_concepts` | 10–20 | Comprehension | Low — recall that X was discussed |

**Not recommended as flashcard sources (yet):**
- `call_synthesis.key_themes` and `strategic_shifts` — too high-level; better as Feynman Loop topics than bite-sized recall exercises
- `spans` / `qa_pairs` — raw text, not structured enough for auto-generated Q&A without an additional LLM pass
- `call_topics` (NMF) — NMF topic labels are opaque (e.g. "topic 3: cloud, margin, infrastructure"); not learner-friendly without enrichment

**Priority order for implementation:** terms → misconceptions → evasion → takeaways. Terms are the simplest to implement (term→definition) and create an instant foundation. Misconceptions and evasion are the highest pedagogical value.

---

## 2. Interaction Model

### Card anatomy

Every card has three states:

```
STATE 1 — PROMPT (shown on load)
┌──────────────────────────────────────────────┐
│  [card type badge]   [ticker · quarter]       │
│                                               │
│  FRONT TEXT                                   │
│  (the question or prompt)                     │
│                                               │
│  [ Flip ]                                     │
└──────────────────────────────────────────────┘

STATE 2 — REVEALED (after Flip)
┌──────────────────────────────────────────────┐
│  [card type badge]   [ticker · quarter]       │
│                                               │
│  FRONT TEXT                                   │
│  ─────────────────                            │
│  BACK TEXT                                    │
│  (the answer or explanation)                  │
│                                               │
│  [ Got it ]   [ Review again ]                │
└──────────────────────────────────────────────┘

STATE 3 — RATED (after Got it / Review again)
→ Advance to next card
```

### Card type — Vocabulary (extracted_terms)
- **Front:** Term name + "What does this mean in the context of [ticker]'s call?"
- **Back:** `definition` + `explanation` (the explanation field grounds it in the transcript's specific usage)

### Card type — Misconception (misconceptions)
- **Front:** `misinterpretation` phrased as a statement — "True or false: [misinterpretation]"
- **Back:** "False. [correction]" + `fact` for grounding context
- *Rationale:* Confronting the user with the wrong belief first is more effective at correcting it than showing the correct answer. This is the "generation effect" in learning science.

### Card type — Evasion Probe (evasion_analysis)
- **Front:** `question_text` (what the analyst asked) + "What was the analyst really trying to find out?"
- **Back:** `analyst_concern` + `evasion_explanation` + defensiveness score badge
- *Rationale:* This is the highest-value card type pedagogically. Reading an earnings call without understanding subtext is surface-level. These cards train the user to read between the lines — a skill that transfers across companies and quarters.

### Card type — Takeaway Significance (extracted_takeaways)
- **Front:** `takeaway` (the fact) + "Why does this matter for investors?"
- **Back:** `why_it_matters`
- *Rationale:* Takeaways train the user to move from "what happened" to "so what" — exactly the reasoning skill the app is trying to develop.

### Why flip-card over multiple choice or type-in?

**Multiple choice** would require generating distractors — either via an LLM pass (new ingestion cost) or from other transcripts (complex sampling logic). It is not derivable from existing fields.

**Type-in** requires an answer-evaluation step. Possible with Claude (similar to the Feynman loop), but heavy UX machinery for quick recall. Better suited to the Feynman Loop itself.

**Flip-card with self-assessment** (Got it / Review again) requires no new LLM calls, works in Streamlit with minimal widget logic, and is the standard SRS input mechanism. It is the right default for a first implementation.

Multiple choice can be revisited once the card corpus is large enough to generate plausible distractors from within-ticker or cross-ticker material.

---

## 3. Placement in the App

### Option A — Within-Transcript Capstone (recommended for Stage 1)

After the last learning path step ("Language Lab"), add a **"Quick Review"** section:

```
Step 6 · Language Lab
   ↓
[ Quick Review — 5 cards ] ← new
   ↓
→ Feynman Loop (CTA)
```

The review section serves a random selection of 5 cards from the current transcript, weighted toward misconceptions and evasion (highest pedagogical value). Completion of the review is recorded as a signal that the user is ready for the Feynman Loop.

**Relationship to learning path redesign (Spike #48):** The Language Lab step in the proposed redesign already surfaces vocabulary terms and misconceptions in a read-only format. The quick review is the *active recall* complement to that passive reading. It fits naturally as a bridge between reading and teaching-back.

### Option B — Library-Level Review Queue (recommended for Stage 2)

A dedicated **"Review"** tab in the library (alongside "Browse") that serves a cross-transcript SRS queue. Cards are sorted by due date (spaced repetition schedule). The user can filter by ticker or card type.

```
Library
├── Browse (current)
└── Review ← new tab
    ├── Due today: 12 cards
    ├── [Filter: All tickers | AAPL | MSFT]
    └── [Card deck]
```

This is the "habit-forming" version. It gives the user a reason to return to the app even when they're not studying a new transcript.

### Recommendation

Build Option A first. It is a contained feature with no new tables required. Option B builds on A but requires the `flashcard_reviews` table and scheduling logic described in Section 4.

---

## 4. Data Model

### Stage 1 — No new tables required

In the within-transcript mode, cards are generated at query time by selecting from existing tables:

```python
# Pseudocode for card generation (no materialization needed)
def get_flashcards_for_call(call_id: UUID, limit: int = 5) -> list[Flashcard]:
    cards = []
    cards += term_cards(call_id)          # from extracted_terms
    cards += misconception_cards(call_id) # from misconceptions
    cards += evasion_cards(call_id)       # from evasion_analysis
    cards += takeaway_cards(call_id)      # from extracted_takeaways
    return weighted_sample(cards, limit)
```

Each card is a lightweight dataclass with `front`, `back`, `card_type`, `source_table`, `source_id`, and `call_id`. Nothing needs to be persisted.

### Stage 2 — flashcard_reviews table

To support spaced repetition and cross-transcript review, the app needs to track which cards a user has seen and how they rated them.

**New table: `flashcard_reviews`**

```sql
CREATE TABLE flashcard_reviews (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id         UUID NOT NULL,           -- future multi-user; for now, a fixed sentinel UUID
    call_id         UUID NOT NULL REFERENCES calls(id) ON DELETE CASCADE,
    source_table    TEXT NOT NULL,           -- 'extracted_terms' | 'misconceptions' | 'evasion_analysis' | 'extracted_takeaways'
    source_id       UUID NOT NULL,           -- FK to the specific row in source_table
    card_type       TEXT NOT NULL,           -- 'vocabulary' | 'misconception' | 'evasion' | 'takeaway'
    result          TEXT NOT NULL CHECK (result IN ('got_it', 'review_again')),
    reviewed_at     TIMESTAMPTZ DEFAULT now(),
    next_review_at  TIMESTAMPTZ NOT NULL     -- computed by SRS algorithm at review time
);

CREATE INDEX idx_flashcard_reviews_user_due ON flashcard_reviews(user_id, next_review_at);
CREATE INDEX idx_flashcard_reviews_call ON flashcard_reviews(call_id);
```

**SRS algorithm:** A simplified SM-2 variant. On first "got it", schedule review in 1 day. On second "got it", 4 days. On each subsequent "got it", multiply by 2.5. On "review again", reset interval to same day. This requires no stored state beyond `next_review_at` — the schedule is recomputed at each review event.

**Note on `user_id`:** There is currently no authentication or multi-user model. For Stage 2, use a fixed sentinel UUID stored in `st.session_state` (persisted to `localStorage` or a browser cookie if Streamlit supports it in the target version). The schema is multi-user-ready without requiring authentication to be shipped first.

### Do existing tables need any changes?

No. The four source tables (`extracted_terms`, `misconceptions`, `evasion_analysis`, `extracted_takeaways`) already have the fields needed to generate cards. No new columns, no schema migrations required for Stage 1.

For Stage 2, one new table (`flashcard_reviews`) and one migration.

---

## 5. Ingestion Prompt Assessment

**No ingestion prompt changes are required.**

The four source tables are already populated by the Tier 1/Tier 2 pipeline. Cards are derived entirely at query time.

However, two **optional enrichments** would improve card quality:

| Enrichment | Source | Card Impact | Effort |
|---|---|---|---|
| Add `context_snippet` to `extracted_terms` — a 1–2 sentence excerpt where the term appears | Tier 1 prompt tweak | Vocabulary cards become context-grounded, not dictionary-style | Low — add one output field to existing prompt |
| Add `common_follow_up_question` to `extracted_takeaways` — what would a practitioner ask next? | Tier 2 prompt tweak | Takeaway cards become more Socratic | Medium — requires prompt redesign for takeaway extraction |

Both are optional. The base implementation works without them. If card quality in practice feels too "textbook" (particularly for vocab cards), the `context_snippet` enrichment is the first thing to add.

---

## 6. Relationship to Other Spikes and Features

| Related Issue | Relationship |
|---|---|
| Spike #48 — Learning path redesign | Flashcard review is a natural capstone after Language Lab (Step 6). The two spikes should be sequenced so that the learning path redesign lands first, then flashcards slot into the structure it establishes. |
| Spike #50 — Quiz and test modality | Quizzes (#50) are a heavier version of the same idea. They should share the card generation logic and potentially the `flashcard_reviews` table. Do flashcards first — quizzes are built on top. |
| Issue #70 — Progress and completion indicator | Completing a quick review session is a natural completion signal. The "done with a transcript" definition in Spike #48 should include "completed quick review." |
| Issue #91 — Per-transcript completion tracking | Same as above — flashcard completion is one completion signal among several. |
| Future multi-user model | The `flashcard_reviews` schema is designed to be multi-user-ready. The `user_id` column is present from day one; authentication can be layered in later. |

---

## 7. Proposed UX Flow

### Stage 1 — Within-Transcript Quick Review

```
User selects a transcript from the library
    ↓
User reads Steps 1–6 of the learning path
    ↓
Step 6 · Language Lab (end)
    ↓
┌─────────────────────────────────────────────────────┐
│  Quick Review                                        │
│  "Test yourself on what you just read — 5 cards"    │
│                                                      │
│  [Start Review →]                                    │
└─────────────────────────────────────────────────────┘
    ↓ (click Start Review)
Card 1/5 shown (flip-card interaction)
    ↓
Card 2/5 ... Card 5/5
    ↓
┌─────────────────────────────────────────────────────┐
│  Done. 4/5 correct.                                  │
│                                                      │
│  [Teach it back →]  (links to Feynman Loop)         │
│  [Review missed cards]                               │
└─────────────────────────────────────────────────────┘
```

The card session is short by design (5 cards). This is not a comprehensive test — it is an activation exercise to prime the user before the Feynman Loop. The goal is to surface the 1–2 concepts the user is shakiest on so the Feynman Loop can address them.

Card selection is weighted: evasion and misconception cards are prioritised (higher cognitive value). Vocabulary cards fill remaining slots.

### Stage 2 — Library Review Queue

```
Library tab bar:
[ Browse ] [ Review · 12 due ]
                ↑ badge shows due count

Review tab:
─────────────────────────────────────────────
Due today from:
  AAPL Q3 2025  ·  7 cards
  MSFT Q2 2025  ·  5 cards
─────────────────────────────────────────────
[ Start Review Session → ]

(Card deck follows same flip-card UX as Stage 1)
```

---

## 8. Implementation Issues

### Stage 1 — Within-Transcript Quick Review

| # | Title | Type | Notes |
|---|---|---|---|
| A | Add `get_flashcards_for_call()` to `db/repositories.py` | Backend | Queries 4 tables; returns list of `Flashcard` dataclass; no new schema |
| B | Add `Flashcard` dataclass to `core/models.py` | Backend | Fields: `front`, `back`, `card_type`, `source_table`, `source_id`, `call_id`, `ticker`, `quarter` |
| C | Build `ui/flashcard.py` — card rendering and session state | Frontend | Flip animation via `st.empty()` + button toggle; self-contained component |
| D | Add `render_quick_review()` to `ui/metadata_panel.py` | Frontend | Calls `get_flashcards_for_call()`; renders after Language Lab section |
| E | Wire quick review completion into transcript completion tracking | Frontend | Depends on Issue #91 (per-transcript completion tracking) |

### Stage 2 — Cross-Transcript SRS (after Stage 1 ships)

| # | Title | Type | Notes |
|---|---|---|---|
| F | DB migration: add `flashcard_reviews` table | Backend/DB | Schema described in Section 4 |
| G | Add `record_flashcard_review()` and `get_due_cards()` to `db/repositories.py` | Backend | SRS scheduling logic lives here |
| H | Add `FlashcardReview` dataclass to `core/models.py` | Backend | Mirrors `flashcard_reviews` table |
| I | Add "Review" tab to `ui/library.py` | Frontend | Calls `get_due_cards()`; reuses card component from Issue C |
| J | Add due-count badge to library tab bar | Frontend | Minor — session_state query on load |
| K | Persist `user_id` sentinel across sessions | Frontend | `st.session_state` + `st.query_params` or Streamlit `localStorage` workaround |

---

## 9. Open Questions

1. **Card count for quick review:** 5 cards is the proposed default. Is this the right number? Too few to feel substantive; too many breaks the flow into the Feynman Loop. Could make it configurable, but default to 5.

2. **Card deduplication across sessions:** If the user does the quick review twice for the same transcript, they'll see some of the same cards. In Stage 1 (no persistence), this is unavoidable. Stage 2's `flashcard_reviews` table fixes this. Is Stage 1's repetition acceptable given how quick the session is?

3. **Evasion cards without a question:** Some `evasion_analysis` rows have a null `question_text` (scripted remarks, not Q&A). These rows have `analyst_concern` but no natural "front" question. Options: (a) skip null-question rows, (b) generate a synthetic prompt like "Management addressed [topic] in prepared remarks — what signal were they sending?". Recommend (a) for now; (b) is a future enrichment.

4. **Card difficulty signal:** "Got it / Review again" is binary. A three-level rating ("Hard / Medium / Easy") would give the SRS algorithm more signal. But it adds UX friction. Start binary; upgrade if users want finer control.

---

## 10. Summary

| Question (from issue) | Answer |
|---|---|
| Which data types make good flashcard source material? | All four: terms (vocab), misconceptions (error detection), evasion (analytical), takeaways (significance). Evasion + misconceptions are highest value. |
| What is the right interaction model? | Flip-card with binary self-assessment (Got it / Review again). Multiple choice deferred until card corpus is large enough for quality distractors. |
| Does this require new ingestion content? | No. All card content is derivable from existing DB tables. Two optional prompt enrichments would improve quality but are not required. |
| Where does flashcard review live? | Stage 1: within-transcript capstone between Language Lab and Feynman Loop. Stage 2: "Review" tab in the library with SRS scheduling. |
| How does this interact with a future multi-user model? | The `flashcard_reviews` table is designed multi-user-ready from day one (user_id column). Authentication can be layered in later. |
