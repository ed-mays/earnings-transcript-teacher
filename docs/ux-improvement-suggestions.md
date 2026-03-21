# UX & Product Improvement Suggestions

## Executive Summary

The app has strong bones — a genuinely differentiated pedagogical engine (Feynman loop + RAG), a well-normalized data model, and meaningful AI enrichment. But it suffers from **three structural problems**: hidden depth, fragmented surfaces, and a missing feedback loop. Users who don't know what the app can do won't discover it, and users who do use it don't retain or build on what they learned.

---

## The Three Structural Problems

### 1. Hidden Depth — Most Power Is Invisible

The most valuable outputs of the ingestion pipeline are either buried or never surfaced at all:

- **Evasion analysis** (executives dodging questions) — collected, never shown
- **Misconceptions** (common misunderstandings, with corrections) — collected, never shown
- **Cross-call semantic search** — the DB supports it, there's even a `db/search.py` CLI tool, but it's not in either UI
- **Speaker behavior tracking** — schema columns exist, not wired up
- **`learning_sessions` and `concept_exercises` tables** — in the schema, completely unused in UI

The result: Tier 1/Tier 2 LLM enrichment runs on every transcript but only ~40% of those insights are shown to the user.

**Recommendation:** Add an "Analyst View" tab in the web UI. Surface what management is *avoiding* answering alongside what they're saying. Evasion patterns and misconceptions are genuinely signal-rich information for any investor or analyst — and a feature no competitor has. (See [GitHub issue #40](https://github.com/ed-mays/earnings-transcript-teacher/issues/40).)

---

### 2. Fragmented Surfaces — Two UIs Drifting Apart

Console and Streamlit are not feature-equivalent and diverge with each release:

| Feature | Console | Web |
|---|---|---|
| Beginner pre-Feynman sub-menu | ✅ | ❌ |
| Cross-ticker search | ✅ (CLI only) | ❌ |
| Token cost tracking | ✅ | Partial |
| Feynman export | ✅ | ✅ |
| Transcript browser with search | ❌ | ✅ |
| Jargon definitions | ❌ | ✅ |

Maintaining two UIs multiplies the implementation cost of every future feature. Users are also getting different products depending on how they launched the app.

**Recommendation:** Deprecate the console as a primary interface. Keep it for power-user CLI ingestion (`python3 main.py AAPL --save`) but make the web UI the one true interactive surface. Port the missing features there — particularly the Beginner pre-Feynman flow and semantic search.

---

### 3. Missing Feedback Loop — Learning Has No Memory

The Feynman loop produces a teaching note. That note goes to a markdown file. End of story.

The DB has `learning_sessions` and `concept_exercises` tables ready to go, but there is no:
- History of what you've studied
- Ability to resume a session started in a previous visit
- Spaced repetition prompt ("You learned about FX hedging 7 days ago — want a quick review?")
- Progress indicator across topics or tickers

The app treats each session as stateless. Every time a user returns, they're starting from zero.

**Recommendation:** A "My Learning" dashboard. Even a simple sidebar showing "3 Feynman sessions completed / 2 topics mastered / MSFT, AAPL, GOOGL studied" would transform the experience from a tool into a habit. The existing schema tables just need to be wired up. (See [GitHub issue #41](https://github.com/ed-mays/earnings-transcript-teacher/issues/41).)

---

## High-Impact Feature Recommendations

### Priority 1 — Remove Ingestion Friction

**Problem:** New users hit a blank slate and must know a ticker, run a download, and wait for ingestion before they can experience anything. This kills first-session retention.

**Recommendation:** Ship 3–5 pre-ingested transcripts (AAPL, MSFT, NVDA, GOOGL are obvious choices). Let users click into the Feynman loop immediately, then surface "Analyze your own transcript →" as a next step. The first five minutes should feel magical, not operational.

**Effort:** Low.

---

### Priority 2 — Surface the Evasion & Misconception Data

**Problem:** The Tier 2 pipeline generates evasion analysis and misconception corrections. They exist in the DB but appear nowhere in the UI.

**Recommendation:** Add a "⚠️ What management avoided" collapsible card in the left column of the web UI, below Key Takeaways. For an investor, this is often more useful than what *was* said. No new data collection required — just wire up existing DB rows.

**Effort:** Low. Tracked in [GitHub issue #40](https://github.com/ed-mays/earnings-transcript-teacher/issues/40).

---

### Priority 3 — Cross-Ticker Semantic Search in the Web UI

**Problem:** Cross-transcript semantic search is a hidden CLI tool (`db/search.py`). It could be the most powerful research feature in the app.

**Recommendation:** Add a global search bar to the web UI: *"Search across all transcripts…"* Results ranked by embedding similarity, showing ticker + speaker + span text. This turns the app from a single-transcript viewer into a research database.

**Effort:** Low (core logic already exists).

---

### Priority 4 — Persistent Learning State

**Problem:** No session continuity. No progress tracking.

**Recommendation:**
- Save Feynman sessions to `learning_sessions` on completion, not just markdown export
- Show a "Resume" option when returning to a ticker the user has studied before
- Simple progress sidebar: topics started, topics completed, teaching notes saved

**Effort:** Medium. Tracked in [GitHub issue #41](https://github.com/ed-mays/earnings-transcript-teacher/issues/41).

---

### Priority 5 — Cross-Call Comparison View

**Problem:** The DB stores multiple quarters per ticker but the UI only shows one at a time.

**Recommendation:** A "Trend" view that lets users ask: *"How did management's tone on AI CapEx change from Q3 to Q4?"* The embeddings and semantic search already support this. A side-by-side diff of retrieved spans from two quarters would be a genuinely novel research tool.

**Effort:** Medium.

---

## Smaller UX Improvements

**Inline jargon tooltips:** Definitions currently require clicking "Define" per term. Highlight recognised jargon terms in the transcript browser and show a hover tooltip so users can get a quick definition without losing their reading context. Tracked in [GitHub issue #42](https://github.com/ed-mays/earnings-transcript-teacher/issues/42).

**Feynman stage progress indicator:** The 5-stage indicator exists but is subtle. Make it a visible stepper (1 → 2 → 3 → 4 → 5) at the top of the chat panel so users feel forward momentum.

**Transcript browser keyboard shortcuts:** Add Enter = next match in the live search. Long transcripts are hard to orient in; a "Jump to speaker" anchor nav would also help.

**Token cost transparency:** Total ingestion cost (e.g. "This analysis cost $0.04") is tracked per model but never surfaced to the user. Showing it builds trust and helps users understand the value exchange.

**Empty state design:** When no transcript is loaded, the web UI is essentially blank. Replace with an onboarding prompt — *"Pick a company to start learning →"* — with pre-ingested examples as clickable cards.

---

## Summary Prioritisation

| Recommendation | Impact | Effort |
|---|---|---|
| Pre-ingested examples (remove ingestion friction) | High | Low |
| Surface evasion/misconception data (Analyst View) | High | Low |
| Cross-ticker semantic search in UI | High | Low |
| Persistent learning state (Learning Dashboard) | High | Medium |
| Cross-call comparison view | High | Medium |
| Deprecate console as primary UI | Medium | Medium |
| Spaced repetition / review prompts | High | High |

The top three are the quickest wins: they require no new data collection and no architectural changes — just wiring up what's already in the DB.
