# Feature Parity Items: Confirmed for Porting

_Derived from [feature-parity-audit.md](feature-parity-audit.md) — 2026-03-28_

These are the items from the parity audit confirmed for porting to the new web UI. Items that are intentionally dropped, deferred, or already complete are excluded. This list is the input for issue creation.

---

## 1. Library Filter and Sort Controls

**Suggested issue title:** `feat: add filter and sort controls to web UI call library`
**Audit rows:** #1
**Streamlit location:** `ui/library.py`

**Description:** The Streamlit library has a text filter (by ticker/company name) and sort controls (by date, ticker, progress). The new UI currently renders a grid of cards with no filter or sort.

**Dependencies:** None — can be implemented client-side against the existing `GET /api/calls` response.

**Design notes:** Skip step-progress and Feynman session count columns for now — the meaning of "progress" will change after the upcoming UX review of the learning experience flow.

---

## 2. Chat Mode Selector (Feynman vs. Ask the Transcript)

**Suggested issue title:** `feat: port "Ask the Transcript" free-form chat mode to web UI`
**Audit rows:** #5
**Streamlit location:** `ui/sidebar.py:L56–64`, `ui/feynman.py`

**Description:** A free-form Q&A mode where users ask questions about the transcript without Feynman stage progression. Useful for quick lookups and reading comprehension outside the structured learning flow. The new UI currently supports Feynman mode only.

**Dependencies:** None — the chat API already supports non-Feynman queries.

**Design notes:** The toggle belongs on the learn page so users can switch between Feynman and Ask the Transcript.

---

## 3. Speaker List and Call Dynamics

**Suggested issue title:** `feat: render speaker list and call dynamics in web UI`
**Audit rows:** #17, #18
**Streamlit location:** `ui/metadata_panel.py:L515–545`

**Description:** Lists all speakers (executives and analysts) with name, title, and firm. Call dynamics adds: most active executive, most active analyst, analyst firm diversity count, and executive vs. analyst talk-time split.

**Dependencies:** Speaker list data already in `GET /api/calls/{ticker}`. Talk-time split and most-active stats may need to be added to the API response.

**Design notes:** Port both speaker list and call dynamics together — they live in the same Streamlit block and share the same data context.

---

## 4. Q&A Evasion Panel and "What This Signals for Investors" Button

**Suggested issue title:** `feat: add Q&A evasion panel and "What this signals for investors" button to evasion tab`
**Audit rows:** #19 (partial gap), #20
**Streamlit location:** `ui/metadata_panel.py:L560–620`

**Description:** Two related gaps bundled into one issue:
- **Q&A evasion sub-panel:** per-analyst expandable rows with severity badges (🔴/🟡/🟢) showing which analyst questions were evaded and how.
- **"What this signals for investors" button:** an LLM-generated 2–3 sentence investor framing. Applies to both prepared-remarks evasion items (row #19 partial gap) and Q&A evasion items (row #20).

**Dependencies:** Q&A evasion data needs to be in `GET /api/calls/{ticker}` response. LLM signals generation needs a new POST endpoint.

---

## 5. "Explore with Feynman" Deep-link from Strategic Shifts

**Suggested issue title:** `feat: add "Explore with Feynman" deep-link from strategic shifts to Feynman chat`
**Audit rows:** #21
**Streamlit location:** `ui/metadata_panel.py:L625–640`

**Description:** Each strategic shift card has a button that pre-populates the Feynman topic picker with the shift text and navigates to the chat page.

**Dependencies:** None — client-side navigation from `/calls/{ticker}` to `/calls/{ticker}/learn?topic=...`.

**Design notes:** Button renamed to "Explore with Feynman" (was "Explain via Feynman" in Streamlit).

---

## 6. Recent News Panel

**Suggested issue title:** `feat: port recent news panel to web UI`
**Audit rows:** #22
**Streamlit location:** `ui/metadata_panel.py:L67–120`

**Description:** Fetches recent news articles relevant to the company and call themes. Each article shows headline (linked), source, date, summary, and a "Why does this matter for this call?" LLM button.

**Dependencies:** Requires `fetch_recent_news()` service wired to a new API endpoint. Themes from the transcript are needed to provide relevance context.

---

## 7. Competitor Intelligence Panel

**Suggested issue title:** `feat: port competitor intelligence panel to web UI`
**Audit rows:** #23
**Streamlit location:** `ui/metadata_panel.py:L150–234`

**Description:** Fetches competitors split into "referenced in this call" and "other competitors". Each entry shows name, ticker, and description. Includes a refresh button.

**Dependencies:** `fetch_competitors()` service and `CompetitorRepository` already exist. Needs a new API endpoint wired.

---

## 8. Language Lab — Financial and Industry Jargon Actions

**Suggested issue title:** `feat: port Language Lab jargon actions (define / explain / find) to web UI`
**Audit rows:** #25, #41, #42, #43
**Streamlit location:** `ui/metadata_panel.py:L648–693`, `ui/term_actions.py`

**Description:** For each extracted financial/industry term in the Keywords tab, three actions:
- **Define:** LLM-generated definition.
- **Explain:** RAG + LLM contextual explanation of the term within this transcript.
- **Find in transcript:** Triggers a cross-panel text search highlighting all occurrences of the term.

Definitions and explanations persist to DB on generation.

**Dependencies:** New API endpoints for define and explain. Find-in-transcript requires the client-side text search feature (#9 below) to land first.

---

## 9. Language Lab — Misconceptions Reveal Cards

**Suggested issue title:** `feat: port misconceptions reveal-cards to web UI`
**Audit rows:** #26
**Streamlit location:** `ui/metadata_panel.py:L630–647`

**Description:** Reveal-on-click correction cards. Each card shows a common misinterpretation with the correction hidden until clicked. Includes an "Expand all" toggle. Only shown if `misconceptions` data exists for the call.

**Dependencies:** Misconceptions data must be included in `GET /api/calls/{ticker}` response.

---

## 10. Transcript Client-Side Text Search with Highlight and Navigation

**Suggested issue title:** `feat: add client-side text search with highlight and navigation to TranscriptBrowser`
**Audit rows:** #28
**Streamlit location:** `ui/transcript_browser.py:L158–206`

**Description:** Client-side text search with:
- Yellow highlight for all matches, orange for the current match
- X of Y match counter
- Up/down navigation buttons
- Enter / Shift+Enter keyboard shortcuts

Also accepts a cross-panel trigger from Language Lab's "Find in transcript" action.

**Dependencies:** Independent. Should land before or alongside Language Lab jargon actions so the "Find in transcript" flow works end-to-end.

---

## 11. Feynman Custom Topic Text Input

**Suggested issue title:** `feat: add custom topic text input to Feynman topic picker`
**Audit rows:** #32
**Streamlit location:** `ui/feynman.py:L150`

**Description:** A free-text field where users type any topic they want to explore via Feynman, in addition to the suggested topic list. In Streamlit, the topic picker also showed a star-marked recommended suggestion — that marker can be skipped (low value).

**Dependencies:** None — UI-only addition to the learn page.

---

## 12. Feynman Stage Progress Indicator and Pacing Controls

**Suggested issue title:** `feat: design and implement Feynman stage progress indicator and pacing controls`
**Audit rows:** #35, #36
**Streamlit location:** `ui/feynman.py:L200–310`

**Description:** Streamlit showed a stage header ("Step X of 5: {stage name}") above the chat with stage-specific instructional hints, plus explicit advance buttons ("I'm ready to be tested" → stage 4, "Give me my teaching note" → stage 5). Stage is tracked in the API already; there is currently no visual indicator in the new UI.

**Dependencies:** UI-only for the indicator. Advance controls may need API changes if automatic progression is reconsidered.

**Design notes:** Known problems with the Streamlit approach that the redesign must address:
- Stage header appeared above chat messages; as the conversation grew it scrolled out of view.
- Manual advance buttons were gameable — users could skip stages without engaging.
- Buttons and context were visually disconnected from the conversation.

The redesign should consider: whether the indicator is inline or persistent, how the app encourages genuine engagement before advancing, and where stage controls sit relative to the chat window. Stage data is already returned in SSE `done` events.

---

## 13. Feynman Completion Banner and Session Export

**Suggested issue title:** `feat: add Feynman completion banner and session export to web UI`
**Audit rows:** #37, #38
**Streamlit location:** `ui/feynman.py:L310–350`

**Description:** At stage 5:
- A success banner (e.g. "Session complete") acknowledging completion.
- A button to download the full session as a formatted markdown file named `{ticker}_{topic}_{timestamp}.md`.

**Dependencies:** Requires stage 5 completion state to be detectable in the UI — likely part of the stage progress indicator work (item #12 above).

---

## Summary Table

| # | Issue title | Audit rows | Dependencies |
|---|-------------|-----------|--------------|
| 1 | Library filter and sort | #1 | None |
| 2 | Ask the Transcript chat mode | #5 | None |
| 3 | Speaker list and call dynamics | #17, #18 | API may need talk-time stats added |
| 4 | Q&A evasion panel + signals button | #19 (gap), #20 | QA data in API; new POST endpoint |
| 5 | Explore with Feynman deep-link | #21 | None |
| 6 | Recent news panel | #22 | New API endpoint; `fetch_recent_news()` |
| 7 | Competitor intelligence panel | #23 | New API endpoint |
| 8 | Language Lab jargon actions | #25, #41–43 | New API endpoints; item #10 first |
| 9 | Misconceptions reveal cards | #26 | Data in `GET /api/calls/{ticker}` |
| 10 | Transcript text search | #28 | None (independent) |
| 11 | Feynman custom topic input | #32 | None |
| 12 | Feynman stage indicator + pacing | #35, #36 | Needs design consideration |
| 13 | Feynman completion banner + export | #37, #38 | Item #12 (stage 5 state) |
