# Feature Parity Audit: Streamlit UI vs. New Web UI

_Generated for [#201](https://github.com/ed-mays/earnings-transcript-teacher/issues/201) — 2026-03-28_

---

## Summary

The new web UI (Next.js + FastAPI) covers the core reading and metadata experience well — transcript browsing, the five metadata analysis tabs, and the Feynman chat backbone are all present. Authentication and the admin layer are new additions with no Streamlit equivalent.

The gaps are concentrated in three areas:

1. **The structured learning path** — the 6-step framework, progress tracking, pre-reading checklist, and mark-as-read mechanics have no equivalent in the new UI. The new UI presents analysis as a flat tab panel rather than a pedagogical sequence.

2. **Language Lab (Step 6)** — the most interactive metadata feature (define/explain/find for jargon terms, misconceptions) is entirely absent.

3. **Feynman session management** — session history, resume, synthesis sessions, manual stage-advance buttons, and export are all missing. The new UI supports a single live session only.

**Overall:** ~30% of Streamlit features are fully ported, ~25% are partial, and ~45% are not yet ported. The new UI is a solid foundation but needs significant work before the Streamlit layer can be deprecated.

---

## Feature Parity Table

| # | Feature | Streamlit location | New UI location | Status | Notes |
|---|---|---|---|---|---|
| 1 | Transcript library | `ui/library.py` | `web/app/page.tsx` | ⚠️ Partial | New UI uses grid cards. Filter/sort to be ported. Progress columns deferred — will change after UX review of learning experience flow |
| 2 | Authentication | — (none) | `web/app/auth/sign-in/page.tsx` | ✅ Complete | New feature — Google OAuth not present in Streamlit |
| 3 | Navigation bar | `ui/sidebar.py:L39` (Library button) | `web/app/layout.tsx` | ✅ Complete | Equivalent home link + sign-out; admin links are new |
| 4 | Transcript selection dropdown | `ui/sidebar.py:L22–85` | — | 🚫 Intentionally dropped | New UI uses separate pages per ticker (`/calls/[ticker]`) |
| 5 | Chat mode selector (Feynman vs Ask the Transcript) | `ui/sidebar.py:L56–64` | — | ❌ Not ported | Confirmed to port. New UI needs both modes with a toggle on the learn page |
| 6 | Reload data button | `ui/sidebar.py:L67` | — | 🚫 Intentionally dropped | No server-side cache in Next.js; not applicable |
| 7 | Learning statistics expander | `ui/sidebar.py:L71–83` | — | 🚫 Intentionally dropped | Tied to 6-step learning path; will be reworked in future UX review |
| 8 | Adaptive start prompt banner | `app.py:L138–156` | — | 🚫 Intentionally dropped | Tied to 6-step learning path; will be reworked in future UX review |
| 9 | Jargon discovery banner | `app.py:L178–191` | — | 🚫 Intentionally dropped | Tied to Step 6 of learning path; will be reworked in future UX review |
| 10 | Learning path header + progress bar | `ui/metadata_panel.py:L422` | — | 🚫 Intentionally dropped | Core of 6-step structure being reworked in future UX review |
| 11 | Pre-reading checklist | `ui/metadata_panel.py:L430` | — | 🚫 Intentionally dropped | Tied to 6-step learning path; will be reworked in future UX review |
| 12 | Learning objectives expander | `ui/metadata_panel.py:L443` | — | 🚫 Intentionally dropped | Tied to 6-step learning path; will be reworked in future UX review |
| 13 | Step 1 · Overview — call summary | `ui/metadata_panel.py:L470` | — | 🚫 Deferred | Data will be kept in DB and API response; raw display deferred to UX review |
| 14 | Step 1 · Overview — key takeaways | `ui/metadata_panel.py:L478` | — | 🚫 Deferred | Data will be kept in DB and API response; raw display deferred to UX review |
| 15 | Step 1 · Overview — extracted themes | `ui/metadata_panel.py:L487` | `web/components/transcript/MetadataPanel.tsx` (Themes tab) | ⚠️ Partial | Themes tab shows topic clusters; missing numbered display format from Step 1 context |
| 16 | Step 2 · Tone & Speakers — sentiment | `ui/metadata_panel.py:L501` | `web/components/transcript/MetadataPanel.tsx` (Summary tab) | ✅ Complete | Overall, executive, and analyst sentiment all present |
| 17 | Step 2 · Tone & Speakers — speaker list | `ui/metadata_panel.py:L515` | — | ❌ Not ported | Confirmed to port. Data already in API response — UI-only gap |
| 18 | Step 2 · Tone & Speakers — call dynamics | `ui/metadata_panel.py:L530` | — | ❌ Not ported | Confirmed to port alongside speaker list |
| 19 | Step 3 · Said vs. Avoided — prepared remarks | `ui/metadata_panel.py:L560` | `web/components/transcript/MetadataPanel.tsx` (Evasion tab) | ⚠️ Partial | Confirmed to port. Missing: "What this signals for investors" LLM button |
| 20 | Step 3 · Said vs. Avoided — Q&A evasion | `ui/metadata_panel.py:L590` | — | ❌ Not ported | Confirmed to port. Per-analyst expandable rows + "What this signals" button for Q&A evasion |
| 21 | Step 4 · What Changed — strategic shifts | `ui/metadata_panel.py:L625` | `web/components/transcript/MetadataPanel.tsx` (Shifts tab) | ⚠️ Partial | Confirmed to port. Button will be renamed "Explore with Feynman". Links to `/calls/{ticker}/learn?topic=...` |
| 22 | Step 5 · The Bigger Picture — recent news | `ui/metadata_panel.py:L67` | — | ❌ Not ported | Confirmed to port. Requires `fetch_recent_news()` wired to new API endpoint |
| 23 | Step 5 · The Bigger Picture — competitors | `ui/metadata_panel.py:L150` | — | ❌ Not ported | Confirmed to port. Backend service and CompetitorRepository already exist |
| 24 | Step 6 · Language Lab — keywords | `ui/metadata_panel.py:L694` | `web/components/transcript/MetadataPanel.tsx` (Keywords tab) | ✅ Complete | Keywords displayed in both UIs |
| 25 | Step 6 · Language Lab — financial/industry jargon | `ui/metadata_panel.py:L648` | — | ❌ Not ported | Confirmed to port all 3 actions: Define / Explain / Find in transcript |
| 26 | Step 6 · Language Lab — misconceptions | `ui/metadata_panel.py:L630` | — | ❌ Not ported | Confirmed to port |
| 27 | Step progress tracking (mark as read) | `ui/metadata_panel.py` (each step) | — | 🚫 Intentionally dropped | Tied to 6-step learning path; will be reworked in future UX review |
| 28 | Transcript viewer — client-side text search | `ui/transcript_browser.py:L158` | — | ❌ Not ported | Confirmed to port. Complements semantic search; required for "Find in transcript" from Language Lab |
| 29 | Transcript viewer — semantic search | — (not in Streamlit) | `web/components/transcript/TranscriptBrowser.tsx` | ✅ Complete | New feature — debounced with similarity scores |
| 30 | Transcript viewer — section/speaker filters | `ui/transcript_browser.py` (section toggle) | `web/components/transcript/TranscriptBrowser.tsx` | ✅ Complete | All/Prepared/Q&A + speaker dropdown in both |
| 31 | Transcript viewer — jargon tooltips | `ui/transcript_browser.py` | — | 🚫 Deferred | Deferred — will consider better UX approach during future Language Lab work |
| 32 | Feynman topic picker — suggested topics + custom input | `ui/feynman.py:L150` | `web/components/chat/ChatThread.tsx` | ⚠️ Partial | Custom topic text input to be ported. Session history deferred to later UX review |
| 33 | Feynman topic picker — previous sessions | `ui/feynman.py:L120` | — | 🚫 Deferred | Deferred — will be part of a broader Feynman UX review |
| 34 | Feynman topic picker — synthesis session | `ui/feynman.py:L175` | — | 🚫 Deferred | Deferred — depends on session history work |
| 35 | Feynman stage progress indicator and hints | `ui/feynman.py:L200` | — | ❌ Not ported | Confirmed oversight. Needs redesign — Streamlit approach was awkward (header scrolled out of view as chat grew). Implementation approach TBD |
| 36 | Feynman manual stage advance buttons | `ui/feynman.py:L280` | — | ❌ Not ported | Needs redesign alongside stage indicator. Streamlit buttons were gameable (advance without engaging) and UX was confusing. Revisit as part of stage indicator design |
| 37 | Feynman completion banner | `ui/feynman.py:L310` | — | ❌ Not ported | Confirmed to port. Stage 5 success state |
| 38 | Feynman session export | `ui/feynman.py:L320` | — | ❌ Not ported | Confirmed to port. Download session as markdown file |
| 39 | Feynman new session button | `ui/feynman.py` (reset) | `web/app/calls/[ticker]/learn/page.tsx` | ✅ Complete | Both UIs have a reset/new-session control |
| 40 | Feynman streaming chat | `ui/feynman.py:L400` | `web/components/chat/ChatThread.tsx` | ✅ Complete | SSE streaming in new UI; spinner in Streamlit |
| 41 | Define term (LLM) | `ui/term_actions.py` | — | ❌ Not ported | Confirmed to port. Part of Language Lab jargon actions |
| 42 | Explain term in context (RAG+LLM) | `ui/term_actions.py` | — | ❌ Not ported | Confirmed to port. Part of Language Lab jargon actions |
| 43 | Find term in transcript | `ui/term_actions.py` | — | ❌ Not ported | Confirmed to port. Requires client-side text search (#28) to land first |
| 44 | Admin analytics dashboard | — (none) | `web/app/admin/page.tsx` | ✅ Complete | New feature — sessions, costs, chat, Feynman funnel, ingestions |
| 45 | Admin system health | — (none) | `web/app/admin/health/page.tsx` | ✅ Complete | New feature — DB, env vars, external APIs |
| 46 | Admin ingest | — (none) | `web/app/admin/ingest/page.tsx` | ✅ Complete | New feature — dispatch ticker to Modal pipeline |

---

## Unported Features (structured list for issue creation)

### Chat Mode: Ask the Transcript

**Streamlit location:** `ui/sidebar.py:L56–64`, `ui/feynman.py`
**Status:** Not ported — confirmed to port
**Description:** A free-form Q&A mode where users ask questions about the transcript without Feynman stage progression. Useful for quick lookups and reading comprehension outside the structured learning flow.
**Gap:** No equivalent in the new UI — only Feynman mode is available.
**Decision:** Port this mode with a toggle on the learn page so users can switch between Feynman and Ask the Transcript.
**Suggested issue title:** `feat: port "Ask the Transcript" free-form chat mode to web UI`
**Dependencies:** None — the chat API already supports non-Feynman queries.

---

### Learning Statistics / Learning Path Structure / Progress Tracking

**Streamlit locations:** `ui/sidebar.py:L71–83`, `ui/metadata_panel.py:L422–707`, per-step mark-as-read buttons
**Status:** Intentionally dropped
**Decision:** These features are all tied to the 6-step learning path structure, which is being reworked in a future UX review. No issues to create. Revisit when the new learning experience design is defined.

---

### Call Summary and Key Takeaways (Step 1)

**Streamlit location:** `ui/metadata_panel.py:L470–495`
**Status:** Deferred
**Description:** The `call_summary` long-form text and `key_takeaways` list (each with a "why it matters" field) are displayed in Step 1. They orient the user before they read the transcript.
**Decision:** Keep data in DB and ensure it is included in the `GET /api/calls/{ticker}` response, but do not surface in the UI in raw form. How to present this data will be decided during the UX review of the learning experience flow. No issue to create now.

---

### Speaker List and Call Dynamics

**Streamlit location:** `ui/metadata_panel.py:L515–545`
**Status:** Not ported — confirmed to port
**Description:** Lists all speakers (executives and analysts) with name/title/firm, plus call dynamics: most active executive, most active analyst, analyst firm diversity count, and executive vs. analyst talk-time split.
**Decision:** Port both the speaker list and call dynamics together.
**Suggested issue title:** `feat: render speaker list and call dynamics in web UI`
**Dependencies:** Speaker list data already in `GET /api/calls/{ticker}`. Talk-time split and most-active stats may need to be added to the API response.

---

### Q&A Evasion Panel + "What This Signals for Investors" Button (Step 3)

**Streamlit location:** `ui/metadata_panel.py:L575–620`
**Status:** Not ported — confirmed to port both gaps together
**Description:** Two related gaps: (1) a Q&A evasion sub-panel with per-analyst expandable rows and severity badges (🔴/🟡/🟢); (2) a "What this signals for investors" LLM button generating a 2–3 sentence investor framing, shown on both prepared-remarks and Q&A evasion items.
**Decision:** Port both. Bundle into one issue since the LLM button applies to both sub-panels.
**Suggested issue title:** `feat: add Q&A evasion panel and "What this signals for investors" button to evasion tab`
**Dependencies:** QA evasion data needs to be in `GET /api/calls/{ticker}` response; LLM signals generation needs a new POST endpoint.

---

### "Explore with Feynman" Link on Strategic Shifts (Step 4)

**Streamlit location:** `ui/metadata_panel.py:L625–640`
**Status:** Partial — confirmed to port
**Description:** Each strategic shift card has a button that pre-populates the Feynman topic picker with the shift text and navigates to the chat page.
**Decision:** Port with a renamed button: "Explore with Feynman" (was "Explain via Feynman" in Streamlit).
**Suggested issue title:** `feat: add "Explore with Feynman" deep-link from strategic shifts to Feynman chat`
**Dependencies:** None — client-side navigation from `/calls/{ticker}` to `/calls/{ticker}/learn?topic=...`.

---

### Step 5 · The Bigger Picture — Recent News

**Streamlit location:** `ui/metadata_panel.py:L67–120`
**Status:** Not ported — confirmed to port
**Description:** Fetches recent news articles relevant to the company and call themes. Each article shows headline (linked), source, date, summary, and a "Why does this matter for this call?" LLM button.
**Suggested issue title:** `feat: port recent news panel to web UI`
**Dependencies:** Requires `fetch_recent_news()` service wired to a new API endpoint; themes from transcript needed for relevance context.

---

### Step 5 · The Bigger Picture — Competitor Intelligence

**Streamlit location:** `ui/metadata_panel.py:L150–234`
**Status:** Not ported — confirmed to port
**Description:** Fetches competitors split into "referenced in this call" and "other competitors". Each entry shows name, ticker, and description. Includes a refresh button.
**Suggested issue title:** `feat: port competitor intelligence panel to web UI`
**Dependencies:** `fetch_competitors()` service and CompetitorRepository already exist; needs new API endpoint wired.

---

### Language Lab — Financial and Industry Jargon

**Streamlit location:** `ui/metadata_panel.py:L648–693`, `ui/term_actions.py`
**Status:** Not ported — confirmed to port all three actions
**Description:** For each extracted financial and industry term: Define (LLM-generated definition), Explain (RAG + LLM contextual explanation), and Find in transcript (cross-panel search trigger). Definitions and explanations persist to DB on generation.
**Suggested issue title:** `feat: port Language Lab jargon actions (define / explain / find) to web UI`
**Dependencies:** Requires new API endpoints for define and explain. Find-in-transcript requires client-side text search (#28) to land first.

---

### Language Lab — Misconceptions

**Streamlit location:** `ui/metadata_panel.py:L630–647`
**Status:** Not ported — confirmed to port
**Description:** Reveal-on-click correction cards. Each shows a common misinterpretation with the correction hidden until clicked. "Expand all" toggle. Only shown if `misconceptions` data exists for the call.
**Suggested issue title:** `feat: port misconceptions reveal-cards to web UI`
**Dependencies:** Misconceptions data must be included in `GET /api/calls/{ticker}` response.

---

### Transcript Text Search with Highlight and Navigation

**Streamlit location:** `ui/transcript_browser.py:L158–206`
**Status:** Not ported — confirmed to port
**Description:** Client-side text search with yellow highlight for all matches, orange for current match, X/Y counter, ⬆/⬇ navigation, Enter/Shift+Enter keyboard shortcuts. Also accepts a cross-panel trigger from Language Lab's "Find in transcript" button.
**Suggested issue title:** `feat: add client-side text search with highlight and navigation to TranscriptBrowser`
**Dependencies:** Independent. Should land before or alongside Language Lab jargon actions so "Find in transcript" works end-to-end.

---

### Jargon Tooltips in Transcript

**Streamlit location:** `ui/transcript_browser.py` (custom HTML component)
**Status:** Deferred
**Decision:** Deferred — will consider a better UX approach during future Language Lab work. The Streamlit implementation used a custom HTML/CSS component; the new UI should find a more native approach.

---

### Feynman Topic Picker — Custom Topic Input

**Streamlit location:** `ui/feynman.py:L150`
**Status:** Partial — custom input confirmed to port
**Description:** A free-text field where users type any topic they want to explore via Feynman. In Streamlit, the topic picker also showed a star-marked recommended suggestion.
**Decision:** Port the custom topic text input. The recommended-star marker on suggestions can be skipped — low value. Session history and synthesis deferred (see below).
**Suggested issue title:** `feat: add custom topic text input to Feynman topic picker`
**Dependencies:** None — UI-only addition to the learn page.

---

### Feynman Session History, Resume, and Synthesis

**Streamlit location:** `ui/feynman.py:L120–195`
**Status:** Deferred
**Description:** The topic picker showed in-progress/completed sessions, resume and review flows, and a synthesis session (cross-topic connection) when ≥2 sessions are complete.
**Decision:** All three deferred — will be part of a broader Feynman UX review. Sessions are already persisted in DB so no data is lost.

---

### Feynman Stage Progress Indicator, Hints, and Stage Advance

**Streamlit location:** `ui/feynman.py:L200–310`
**Status:** Not ported — confirmed oversight, needs redesign
**Description:** Streamlit showed a stage header ("Step X of 5: {stage name}") above the chat with a stage-specific instructional hint, plus explicit advance buttons ("I'm ready to be tested" → stage 4, "Give me my teaching note" → stage 5).
**Gap:** Stage tracked in API but no visual indicator or hint in the new UI. Users have no way to control progression.
**Known problems with the Streamlit approach:**
- Stage header appeared above chat messages; as conversation grew, it scrolled out of view
- Manual advance buttons were gameable — users could skip stages without engaging
- UX was confusing: buttons and context were disconnected from the conversation
**Decision:** Confirmed to port, but the implementation approach needs design consideration. Stage data is already returned in SSE `done` events. The redesign should address visibility (indicator inline or persistent), pacing (how the app encourages genuine engagement before advancing), and the awkward position of stage controls relative to the chat window.
**Suggested issue title:** `feat: design and implement Feynman stage progress indicator and pacing controls`
**Dependencies:** UI-only for the indicator; advance controls may need API changes if automatic progression is reconsidered.

---

### Feynman Completion Banner and Session Export

**Streamlit location:** `ui/feynman.py:L310–350`
**Status:** Not ported — confirmed to port
**Description:** At stage 5: a success banner ("🎉 Session complete") and a button to download the full session as a formatted markdown file named `{ticker}_{topic}_{timestamp}.md`.
**Suggested issue title:** `feat: add Feynman completion banner and session export to web UI`
**Dependencies:** Requires stage 5 completion state to be detectable in the UI (part of stage progress indicator work).

---

### Library Filter and Sort

**Streamlit location:** `ui/library.py`
**Status:** Partial — filter/sort confirmed to port; progress columns deferred
**Description:** Streamlit library has a text filter by ticker/company name and sort controls (date, ticker, progress).
**Decision:** Port filter and sort. Skip step-progress and Feynman session count columns for now — the meaning of "progress" will change after the upcoming UX review of the learning experience flow.
**Suggested issue title:** `feat: add filter and sort controls to web UI call library`
**Dependencies:** Filter and sort can be implemented client-side against the existing `GET /api/calls` response.
