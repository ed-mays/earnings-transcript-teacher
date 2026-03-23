# UX Improvement Opportunities — Post-Spike #48

*Generated after all spike #48 implementation issues (#80–#90) were merged and the 6-step learning path structure was stabilised.*

---

## Context

All 11 issues (#80–#90) spawned by spike #48 are merged. The step structure is now stable (6 steps + Feynman). This unblocks a second wave of work across three categories: **step quality**, **engagement mechanics**, and **UX architecture**.

Spike #49 (flashcard) is also complete — but its implementation issues were never filed. Those need to be created before work begins.

---

## Phase 1 — Completion & Engagement Foundations

*Pre-requisite for everything else that references "completion" or "step tracking"*

| Issue | Work | Notes |
|---|---|---|
| **#91** | Per-transcript completion tracking | DB-backed; defines "done with a transcript" — everything else builds on this signal |
| **#65** | Learning objectives framing | Pure UI; derives from existing synthesis data; sets learner intent before any step |
| **#70** | Progress/completion indicator | Dependent on #91; once tracking exists, the indicator is mostly a display layer |

#65 can run in parallel with #91. #70 should follow #91.

---

## Phase 2 — Step Quality Improvements

*Pedagogical upgrades to existing steps — no schema changes, no pipeline changes*

| Issue | Step | Work |
|---|---|---|
| **#60** | Step 5 (Bigger Picture — News) | Add intro sentence + make "Explain relevance" prominent; pure UI |
| **#61** | Step 5 (Bigger Picture — Competitors) | Add framing + link competitor mentions back to transcript sections |
| **#63** | Step 2 (Who Was In The Room) | Surface derived insights from existing span data (e.g., analyst turn counts) |
| **#68** | Pre-reading checklist | Collapsible section at top; session state only; links to steps |
| **#59** | Step 3 (Said vs. Avoided) | Add "What this signals" investor framing to each evasion card — generate on-demand (similar to "Explain relevance" pattern) |

These are all independent and can be parallelised or tackled sequentially in any order. #59 is the most complex (on-demand LLM call) — do it last in this phase.

---

## Phase 3 — Flashcard Feature (Spike #49 deliverables)

*Stage 1 only — within-transcript capstone*

The spike design is complete in `docs/feature-ideation/spike-49-flashcard-review-mode.md`. These implementation issues need to be **filed on GitHub first**, then worked in order:

| New Issue | Work |
|---|---|
| Add `Flashcard` dataclass to `core/models.py` | 5 fields: front, back, card_type, source_table, source_id |
| Add `get_flashcards_for_call()` to `db/repositories.py` | Queries extracted_terms, misconceptions, evasion_analysis, extracted_takeaways; weighted sampling |
| Build `ui/flashcard.py` — card renderer + session state | Flip-card interaction; "Got it / Review again" buttons |
| Add `render_quick_review()` to learning path | Appears after Language Lab (Step 6); 5-card session |
| Wire flashcard completion into transcript completion (#91) | Completion signal: all 6 steps read + ≥1 quick review done |

Each step depends on the prior — implement in order.

---

## Phase 4 — Feynman Bridge

*Depends on Phase 1 (#91) and Phase 3 (flashcard quick review) both being done*

| Issue | Work |
|---|---|
| **#71** | Add CTA after last step with top 1–2 topic suggestions + "continue" state if a Feynman session is already in progress |

Note: #69 (topic prioritisation) is already merged, so prioritised topic suggestions are available. #71 is unblocked once Phase 1 and 3 are done.

---

## Phase 5 — UX Architecture

*Do after step structure and engagement mechanics are stable — these are larger, riskier changes*

| Issue | Work | Dependency |
|---|---|---|
| **#76** | Rethink two-column layout | Independent, but coordinate with #77 |
| **#77** | Wizard flow for learning path | After #76 layout decision; also requires #91 step tracking to exist |
| **#79** | Deep links to sections | Independent; lower urgency than layout/wizard |

#76 and #77 should be designed together in one session. They share the same risk surface (layout regression) and the issues note they should ship together or in sequence.

---

## Deferred — Needs Spike Output First

| Issue | Blocker |
|---|---|
| **#50** | Spike: Quiz/test modality — complete the spike before filing implementation issues |

The flashcard spike recommends building flashcards before quizzes, since quizzes build on the same card generation logic. Stage 2 flashcards (SRS library tab) and quizzes can both be scoped after Stage 1 ships.

---

## Sequencing Summary

```
Phase 1  ──── #91 (completion tracking) + #65 (learning objectives) [parallel]
               └── #70 (progress indicator) [after #91]

Phase 2  ──── #60, #61, #63, #68 [parallel] → #59 [last, needs LLM call]

Phase 3  ──── File flashcard issues → implement in order (models → repo → UI → wiring)

Phase 4  ──── #71 [after Phase 1 + Phase 3]

Phase 5  ──── #76 + #77 [together] → #79

Deferred ──── #50 [spike first]
```

### Immediate action items

1. File the 5 flashcard implementation issues (see spike #49 doc, section 8)
2. Start #91 — it is the most foundational piece and currently has no dependencies
