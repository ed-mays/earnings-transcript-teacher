# Learning Flow Design: EarningsFluency UX Ideation

_Working document for [#202](https://github.com/ed-mays/earnings-transcript-teacher/issues/202) — updated 2026-03-28 after PR #203 review (rounds 1 and 2)_

---

## Design Brief

**Learner:** Retail investor — not a finance professional, but someone actively trying to improve their ability to read and interpret earnings calls. The app is a learning tool that happens to be focused on finance; approachability and skill development are the primary design values.

**Session goal:** The learner leaves with a better interpretation of *this* call, with the meta-goal of becoming better at reading calls in general.

**Primary frame:** Skill-building — teaching a mental model for how to evaluate a call. A future "Investor Mode" could serve users focused on pure decision-making (faster signal extraction, less pedagogy), but the default experience is a learning tool.

**The central tension:** Passive reading feels like understanding but doesn't build skill. Interpretive skill comes from active engagement — forming hypotheses, noticing what's missing, explaining things in your own words. The design must create natural entry points into active engagement without imposing a rigid sequence.

**Feynman:** On-demand, not mandatory. The design should make using it feel like an obvious next step, not an optional extra. Full Feynman redesign (stage indicator, pacing controls) is deferred to a separate ideation thread.

**Scope:** Single-session design. Note where session history infrastructure would plug in naturally.

**Extensibility note:** Future learning models are planned — Socratic method is the first candidate. The information architecture should be designed so that the learning *mode* (Feynman, Socratic, self-assessment) is a layer on top of the content structure, not baked into it. The content structure should be stable regardless of which learning mode is active.

---

## Decisions Log

| Question | Decision |
|---|---|
| How much do retail investors read the transcript? | Transcript is a secondary surface. Primary flow is analysis; transcript is drill-down on demand. |
| Skill-building vs. faster decisions? | Skill-building is the primary frame. "Investor Mode" noted for future extension. |
| Direction 2 (Annotated Transcript) viable? | Dropped — inline annotations deferred. Transcript as primary surface is not the right model. |
| Chosen direction? | **Brief + Progressive Disclosure hybrid.** |
| Bigger Picture timing (pre vs. post-reading)? | Pre-reading. Context before engaging with analysis, especially for beginner learners. |
| Analytical structure? | Progressive disclosure layers map to the steps an analyst takes — not data types, not a numbered learning path. |
| Library cards? | Enrich with signal data (evasion level, sentiment, top shift) so learners can triage before opening a call. |
| Feynman redesign? | Separate ideation thread. |
| Learner level selector: manual or inferred? | Manual to start; path to inferred via session history later. |
| Where do misconceptions live? | Brief layer — at the bottom of the brief, before the learner starts the analysis. |
| Bigger Picture snapshot vs. Step 6 full section? | Same information at different zoom levels. Brief = 2–3 non-interactive bullets; Step 6 = full-fidelity with LLM buttons and drill-down. |
| Progress model: sections explored or activity log? | **Activity log** — track intentional engagement events per session, aggregate across sessions for the same transcript. No "check the boxes" progress. |
| Brief generation: ingest-time or on-demand? | Ingest-time. Latency is already a concern; consistent availability is higher priority than personalization at this stage. |
| Evasion item interaction pattern? | Reveal-card — default shows question + severity badge + topic; click reveals full analysis + "What this signals" button. |

---

## Chosen Direction: "Brief + Progressive Disclosure" Hybrid

### Philosophy

The learner should be taught an analyst's mental model, not just shown data. The experience is structured around the steps an experienced analyst takes when evaluating an earnings call — each step progressively disclosed, going only as deep as the learner chooses. Analysis is the primary surface; the transcript is available for drill-down but is not where learning begins.

The brief at entry orients the learner so they arrive at the analysis with context already loaded. Progressive disclosure prevents cognitive overload and teaches prioritization — a skill in itself.

---

### The Analyst's Evaluation Framework

This is the organizing principle for the progressive disclosure. Six steps, derived from how an experienced analyst actually thinks through a call:

| Step | Question | Analysis types mapped |
|---|---|---|
| 1. Orient | What is this call about, and what was expected? | Call brief, key takeaways, overall sentiment signal |
| 2. Read the Room | How did management sound? | Executive vs. analyst sentiment, speaker dynamics, call dynamics |
| 3. Understand the Narrative | What story did management tell? | Themes, prepared remarks, strategic shifts |
| 4. Notice What Was Avoided | What wasn't said? | Evasion — prepared remarks + Q&A by analyst |
| 5. Track What Changed | What's different from last quarter? | Strategic shifts, guidance changes |
| 6. Situate in Context | How does this fit the bigger picture? | Recent news, competitors |

Language (keywords, jargon) is threaded across all steps — available where relevant rather than isolated in its own tier. Misconceptions are surfaced in the brief layer (see below).

This framework has two benefits: it produces a learnable sequence without enforcing it, and it makes the pedagogical intent visible. The learner isn't just browsing analysis — they're being taught a transferable method.

---

### The Flow

#### 1. Call Brief (pre-reading, always visible)

The call page opens to a compact brief before any analysis is shown. This is the pre-reading layer — designed to be read in 60–90 seconds. Generated at ingest time.

- **Context line:** Company, quarter, call date, and a single sentence framing why this call matters (e.g. "First post-acquisition report — analysts focused on integration costs and margin guidance").
- **Bigger Picture snapshot:** What's happening in the company's environment right now — 2–3 non-interactive bullets drawn from recent news and competitors. Pre-reading context, not post-reading synthesis.
- **3 key takeaways:** The most important conclusions a skilled reader would draw — not summaries, but interpretations.
- **3 interpretation questions:** Things to hold in mind as you work through the analysis. E.g. "Did management's confidence on margins match the actual guidance numbers?" These seed Feynman sessions — questions the learner should be able to answer by the end of the session.
- **Overall signal strip:** Sentiment (executive vs. analyst), evasion level (low/medium/high), strategic shift flagged (yes/no).
- **Misconceptions:** 2–3 reveal-cards at the bottom of the brief. See Card Interaction Language section below. Positioned here so learners encounter them before they form incorrect assumptions during analysis.

The brief replaces the old pre-reading checklist and the adaptive start prompt banner. It is opinionated and LLM-generated rather than a mechanical checkbox list.

#### 2. Analysis: Progressive Disclosure by Analyst Step

Below the brief, the analysis is organized around the six-step analyst framework. Each step starts collapsed to a one-line summary and expands on demand.

**Step 1 · Orient** _(always expanded by default)_
- Overall sentiment summary
- Key takeaways (same as brief, expandable for more context)
- One-sentence call context

**Step 2 · Read the Room**
- Executive sentiment vs. analyst sentiment side-by-side
- Speaker list (name, title, firm)
- Call dynamics: most active executive, most active analyst, analyst firm diversity, talk-time split

**Step 3 · Understand the Narrative**
- Top themes (theme cards, each expandable with "What this signals for investors" button)
- Prepared remarks summary
- Strategic shifts (each with "Explore with Feynman" link)

**Step 4 · Notice What Was Avoided**

Evasion items use the reveal-card pattern (see Card Interaction Language below):
- **Default visible:** analyst question + severity badge (🔴/🟡/🟢) + topic label
- **On click:** full evasion analysis + "What this signals for investors" button
- Prepared remarks and Q&A evasion are shown in separate sub-sections
- Evasion index (overall level) shown at the top of the step

**Step 5 · Track What Changed**
- Strategic shifts (full detail, linked from Step 3)
- Guidance changes flagged

**Step 6 · Situate in Context**
- Recent news (headline, source, date, "Why does this matter for this call?" LLM button per article)
- Competitors: referenced in this call + other competitors
- This is the full-fidelity version of the Bigger Picture snapshot in the brief — same information, deeper zoom level.

**Language layer** (accessible throughout, surfaced at the bottom or via a persistent keywords entry point):
- Keywords
- Financial/industry jargon (define / explain / find in transcript)

Each step section has an "Explore with Feynman" entry point, pre-seeded with the step's topic.

#### 3. Transcript: Secondary, Drill-down Surface

The transcript is always accessible — a tab or "Read transcript" link from the call page. When a learner navigates to it from an analysis item (evasion entry, theme card, strategic shift), the relevant passage is scrolled into view and highlighted. This connects analysis to evidence without making the transcript the primary surface.

Client-side text search (highlight + navigation) makes it usable as a reference. "Find in transcript" from Language Lab triggers the same mechanism.

Inline annotations (evasion highlights, sentiment markers, jargon underlines) are **deferred** — a future enhancement once the primary analysis flow is solid.

---

### Card Interaction Language

A consistent interaction vocabulary across the app: a card with a badge or label signals "something here — click to investigate." The learner only has to learn this pattern once; the content of the reveal varies.

**Misconception cards (brief layer)**
- **Default visible:** the common misinterpretation, stated plainly (e.g. "Management's confidence on margins signals a strong recovery")
- **On click:** the correction — why this reading is wrong or incomplete, grounded in what the call actually said
- Mechanic: judgment-first reveal. The learner reads the claim and implicitly evaluates it before seeing the correction. The pedagogical value is in the gap between expectation and reality.
- "Expand all" toggle available if multiple misconceptions are present.

**Evasion cards (Step 4)**
- **Default visible:** analyst question + severity badge (🔴/🟡/🟢) + topic label (e.g. "margin guidance")
- **On click:** full evasion analysis (what was evaded, how) + "What this signals for investors" button
- Mechanic: curiosity-first reveal. The severity badge invites investigation; the learner chooses which items to dig into. Manages cognitive load when many evasion items are present.

**Distinction:** Misconception cards ask "do you believe this?" (judgment). Evasion cards ask "what happened here?" (investigation). Both are intentional engagement mechanics; both produce loggable events.

This pattern can extend to theme cards and strategic shift cards as those components are developed.

---

### Engagement Activity Log

Progress is not tracked as "sections completed." Instead, the app logs intentional engagement events per session and aggregates them across sessions for the same transcript. A learner who returns to a call can see what they engaged with previously — without any checkbox pressure.

**Event taxonomy — intentional engagements only (initial scope):**
- Feynman session started (topic recorded)
- "What this signals for investors" button triggered (which item)
- Definition requested for a term
- "Explain in context" requested for a term
- "Find in transcript" triggered (which term)
- Misconception card revealed (which misconception)
- Evasion card revealed (which item)

Passive navigation (opening/closing a step section, scrolling) is not logged. The event must require a deliberate action.

**Per-session view:** when a learner revisits a transcript, the activity from prior sessions is surfaced — e.g. "Last session: explored margin guidance with Feynman, revealed 2 evasion items, requested definition of 'adjusted EBITDA'." This is not a checklist; it's a memory aid that helps the learner pick up where they left off.

**Cross-session aggregation:** events from all sessions on the *same transcript* are combined. A learner who has opened AAPL Q4 three times sees a combined picture of their engagement with that call.

Cross-call aggregation (e.g. AAPL across multiple quarters) is explicitly out of scope for now — a future feature once the per-transcript model is established.

**Session history readiness:** the activity log is the foundation for session history features (resume, synthesis, revisit flow). Logging events now doesn't require building the UI; it just means the data is available when that work is prioritized.

---

### Call Library: Enriched Signal Cards

The library entry for each call surfaces a compressed version of the brief signal — enough to triage before opening:

- Evasion level (low / medium / high)
- Overall sentiment (bullish / neutral / bearish)
- Top strategic shift (one line, if present)
- Date and ticker (already present)

This allows a learner to scan the library and decide which call deserves deep attention — a skill in itself.

---

### Learner Level Selector

A manual toggle — Beginner / Intermediate / Advanced — adjusts the experience without changing the underlying data:

- **Beginner:** Brief is expanded and prominent; interpretation questions are explicit; "What this signals" framing shown by default; Feynman on-ramp is more prominent.
- **Intermediate:** Brief shown but compact; analysis without scaffolding text; signals framing available on demand.
- **Advanced:** Brief collapsed by default; raw analysis without interpretation scaffolding; Feynman available but not prompted.

Manual to start. Path to inference later via session history (how many calls has this user analyzed? how deeply do they typically engage?).

---

### Investor Mode (future extension)

A future mode — toggled in settings — would reconfigure the experience for pure signal extraction:

- Brief replaced by a compact signal dashboard
- Analysis steps accessible but not framed pedagogically
- "What this signals" buttons prominent
- Feynman de-emphasized

Content and data are identical; only framing and defaults change.

---

## Deferred Items: Resolution in the Hybrid

| Parity audit item | Resolution |
|---|---|
| Call summary | → Brief: context line + key takeaways |
| Key takeaways | → Brief: 3 key takeaways |
| Learning objectives | → Brief: interpretation questions |
| Pre-reading checklist | → Replaced by brief entirely |
| Adaptive start prompt banner | → Folded into brief (context line) |
| Misconceptions | → Brief layer: reveal-cards at bottom of brief |
| Speaker list | → Step 2: Read the Room |
| Call dynamics | → Step 2: Read the Room |
| Recent news | → Brief snapshot (2–3 bullets) + Step 6 full section |
| Competitor intelligence | → Step 6: Situate in Context |
| Q&A evasion panel | → Step 4: reveal-card pattern |
| "What this signals" button | → Step 4 (evasion); extend to themes and shifts |
| Language Lab jargon | → Language layer (threaded through all steps) |
| Jargon discovery banner | → Language layer |
| Jargon tooltips in transcript | → Deferred with inline annotations |
| Learning path header / progress | → Replaced by analyst steps structure |
| Step progress tracking | → Replaced by activity log model |
| Learning statistics | → Out of scope (cross-session) |

---

## Cross-Cutting Observations

**1. Relabel analysis around interpretation, not data type.**
The current tabs (Summary / Keywords / Themes / Evasion / Shifts) describe data. The analyst steps structure replaces this — labels should answer "what am I looking for here?" not "what data is stored here."

**2. Extend "What this signals for investors" to all major analysis types.**
This button currently exists only on evasion items in Streamlit. The pattern is the core interpretation scaffold the tool offers. It should appear on themes, strategic shifts, speaker dynamics, and sentiment — not just evasion.

**3. Misconceptions and evasion share a reveal-card interaction pattern.**
Both use the same mechanic (badge/label visible → click to reveal detail) but serve different cognitive purposes. Misconceptions: judgment-first (do you believe this?). Evasion: curiosity-first (what happened here?). The shared pattern creates a consistent vocabulary; the distinct copy and framing preserve their different pedagogical roles.

**4. Feynman needs a better on-ramp.**
"Learn" in the nav bar is too abstract. The call to action should answer "Want to test whether you actually understood this call?" Each analyst step having its own Feynman entry point is part of the solution — but the top-level nav framing also needs to change.

**5. Extensibility for future learning models.**
The analyst steps structure is content architecture, not a learning mode. Feynman, Socratic method, self-assessment — these are modes that sit on top of the same structure. When Socratic mode is built, it should be able to use the same brief + progressive disclosure flow, just with different prompting and progression mechanics.

---

## Open Questions

1. **Does the 6-step analyst framework need validation?** Does the sequence match how you'd want a beginner to approach a call? Are any steps missing, misordered, or redundant? (e.g. Steps 3 and 5 both involve strategic shifts — is there overlap that should be resolved?)

2. **What triggers the learner level selector UI?** Is it a first-launch prompt ("how familiar are you with earnings calls?"), a persistent settings control, or both?

3. **How is the activity log displayed on revisit?** A raw event list could be noisy at 20+ events. Grouping by analyst step is one option; a summary ("you explored 4 items in Step 4, started 1 Feynman session") is another. Worth designing the revisit view before the log is built.

---

## Recommended Next Steps

1. **Validate the analyst framework steps** — confirm the 6-step sequence, resolve any overlap between steps.

2. **Design the brief in detail** — the brief is the most important single component. Sketch the exact fields, their sources, LLM prompts required, and how learner level affects what's shown.

3. **Design the activity log revisit view** — decide how prior session events are grouped and displayed before implementing the logging infrastructure.

4. **Map parity items to issues** — the deferred items table above resolves most of the dropped items. Each resolved item needs to be opened as an issue (or bundled) for implementation.

5. **Start Feynman ideation thread** — now that the content architecture is settled, the Feynman redesign has a clearer context to work within.
