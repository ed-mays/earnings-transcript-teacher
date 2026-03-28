# Learning Flow Design: EarningsFluency UX Ideation

_Working document for [#202](https://github.com/ed-mays/earnings-transcript-teacher/issues/202) — updated 2026-03-28 after PR #203 review_

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

## Decisions from PR #203 Review

| Question | Decision |
|---|---|
| How much do retail investors read the transcript? | Transcript is a secondary surface. Primary flow is analysis; transcript is drill-down on demand. |
| Skill-building vs. faster decisions? | Skill-building is the primary frame. "Investor Mode" noted for future extension. |
| Direction 2 (Annotated Transcript) viable? | Dropped — inline annotations deferred. Transcript as primary surface is not the right model. |
| Chosen direction? | **Brief + Progressive Disclosure hybrid.** |
| Bigger Picture timing (pre vs. post-reading)? | Pre-reading. Context before engaging with analysis, especially for beginner learners. |
| Analytical structure? | Progressive disclosure layers should map to the steps an analyst takes — not data types, not a numbered learning path. |
| Library cards? | Enrich with signal data (evasion level, sentiment, top shift) so learners can triage before opening a call. |
| Feynman redesign? | Separate ideation thread. |

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
| 2. Read the room | How did management sound? | Executive vs. analyst sentiment, speaker dynamics, call dynamics |
| 3. Understand the narrative | What story did management tell? | Themes, prepared remarks, strategic shifts |
| 4. Notice what was avoided | What wasn't said? | Evasion — prepared remarks + Q&A by analyst |
| 5. Track what changed | What's different from last quarter? | Strategic shifts, guidance changes |
| 6. Situate in context | How does this fit the bigger picture? | Recent news, competitors |

Language (keywords, jargon, misconceptions) is threaded across all steps — available where relevant rather than isolated in its own tier.

This framework has two benefits: it produces a learnable sequence without enforcing it, and it makes the pedagogical intent visible. The learner isn't just browsing analysis — they're being taught a transferable method.

---

### The Flow

#### 1. Call Brief (pre-reading, always visible)

The call page opens to a compact brief before any analysis is shown. This is the pre-reading layer — designed to be read in 60–90 seconds:

- **Context line:** Company, quarter, call date, and a single sentence framing why this call matters (e.g. "First post-acquisition report — analysts focused on integration costs and margin guidance").
- **Bigger Picture snapshot:** What's happening in the company's environment right now — 2–3 bullets drawn from recent news and competitors. Pre-reading, not post-reading, because a learner can't interpret a call without this context, especially a beginner.
- **3 key takeaways:** The most important conclusions a skilled reader would draw — not summaries, but interpretations.
- **3 interpretation questions:** Things to hold in mind as you work through the analysis. E.g. "Did management's confidence on margins match the actual guidance numbers?" These are Feynman seeds — questions the learner should be able to answer by the end of the session.
- **Overall signal strip:** Sentiment (executive vs. analyst), evasion level (low/medium/high), strategic shift flagged (yes/no). At-a-glance orientation before the learner dives in.

The brief is the replacement for the old pre-reading checklist and the adaptive start prompt banner. It's opinionated and LLM-generated rather than a mechanical checkbox list.

#### 2. Analysis: Progressive Disclosure by Analyst Step

Below the brief, the analysis is organized around the six-step analyst framework. Each step is a section that starts collapsed to a one-line summary and expands on demand:

**Step 1 · Orient** _(always expanded by default)_
- Overall sentiment summary
- Key takeaways (expandable from brief)
- One-sentence context

**Step 2 · Read the Room**
- Executive sentiment vs. analyst sentiment side-by-side
- Speaker list (name, title, firm)
- Call dynamics: most active executive, most active analyst, analyst firm diversity, talk-time split

**Step 3 · Understand the Narrative**
- Top themes (theme cards, each expandable)
- Prepared remarks summary
- Strategic shifts (each with "Explore with Feynman" link)

**Step 4 · Notice What Was Avoided**
- Prepared remarks evasion items with "What this signals for investors" button
- Q&A evasion: per-analyst expandable rows with severity badges (🔴/🟡/🟢), "What this signals" button per item
- Evasion index: overall evasion level contextualized

**Step 5 · Track What Changed**
- Strategic shifts (full detail, linked from Step 3)
- Guidance changes flagged

**Step 6 · Situate in Context**
- Recent news (headline, source, date, "Why does this matter for this call?" LLM button per article)
- Competitors: referenced in this call + other competitors

**Language layer** (available throughout, surfaced at the bottom of the analysis or accessible via keywords):
- Keywords
- Financial/industry jargon (define / explain / find)
- Misconceptions (reveal-on-click cards — see note below)

Each step section has a "Explore with Feynman" entry point, pre-seeded with the step's topic.

#### 3. Transcript: Secondary, Drill-down Surface

The transcript is always accessible — a tab or "Read transcript" link from the call page. When a learner navigates to the transcript from an analysis item (e.g. an evasion entry, a theme card, a strategic shift), the relevant passage is scrolled into view and highlighted. This "drill down" mechanic connects analysis back to evidence without making the transcript the primary surface.

Client-side text search (with highlight and navigation) makes the transcript usable as a reference. "Find in transcript" from Language Lab triggers the same mechanism.

Inline annotations (evasion highlights, sentiment markers, jargon underlines in the transcript body) are **deferred** — a future enhancement once the primary analysis flow is solid.

---

### Call Library: Enriched Signal Cards

The library entry for each call surfaces a compressed version of the signal dashboard — enough to triage before opening:

- Evasion level (low / medium / high)
- Overall sentiment (bullish / neutral / bearish)
- Top strategic shift (one line, if present)
- Date and ticker (already present)

This allows a learner to scan the library and decide which call deserves deep attention — a skill in itself (not every call is equally informative).

---

### Learner Level Selector (new idea)

A "learner level" toggle — Beginner / Intermediate / Advanced — could adjust the experience without changing the underlying data:

- **Beginner:** Brief is expanded and prominent; interpretation questions are explicit; "What this signals for investors" framing is shown by default on analysis items; Feynman on-ramp is more prominent.
- **Intermediate:** Brief is shown but compact; analysis is shown without scaffolding text; signals framing is available on demand.
- **Advanced:** Brief is collapsed by default; raw analysis without interpretation scaffolding; Feynman available but not prompted.

This also provides an extensibility hook: the learner level could eventually adapt based on session history (how many calls has this user analyzed? how far do they typically go?).

Whether this is a manual selector or inferred is an open question.

---

### Investor Mode (future extension)

A future "Investor Mode" — toggled in settings or as a view option — would reconfigure the experience for pure signal extraction rather than skill development:

- Brief replaced by a compact signal dashboard
- Analysis steps accessible but not framed pedagogically
- "What this signals for investors" buttons prominent
- Feynman de-emphasized

The content and data are identical; only the framing and defaults change. This keeps the learning tool as the primary experience while accommodating users who already have the mental model.

---

## Deferred Items: Resolution in the Hybrid

| Parity audit item | Resolution |
|---|---|
| Call summary | → Brief: context line + key takeaways |
| Key takeaways | → Brief: 3 key takeaways |
| Learning objectives | → Brief: interpretation questions |
| Pre-reading checklist | → Replaced by brief entirely |
| Adaptive start prompt banner | → Folded into brief (context line) |
| Speaker list | → Step 2: Read the Room |
| Call dynamics | → Step 2: Read the Room |
| Recent news | → Step 6 pre-reading brief snapshot + Situate in Context section |
| Competitor intelligence | → Step 6: Situate in Context |
| Q&A evasion panel | → Step 4: Notice What Was Avoided |
| "What this signals" button | → Step 4 (evasion items); extend to themes and shifts |
| Language Lab jargon | → Language layer (threaded through all steps) |
| Misconceptions | → Language layer (elevated — see note below) |
| Jargon discovery banner | → Language layer |
| Jargon tooltips in transcript | → Deferred with inline annotations |
| Learning path header / progress | → Replaced by analyst steps structure |
| Step progress tracking | → "Sections explored" lightweight state (session history readiness) |
| Learning statistics | → Out of scope (cross-session) |

---

## Cross-Cutting Observations

**1. Relabel analysis around interpretation, not data type.**
The current tabs (Summary / Keywords / Themes / Evasion / Shifts) describe data. The analyst steps structure replaces this — but the relabeling principle applies everywhere: labels should answer "what am I looking for here?" not "what data is stored here."

**2. Extend "What this signals for investors" to all major analysis types.**
This button currently exists only on evasion items in Streamlit. The pattern — "here's what this means, framed for the investor" — is the core interpretation scaffold the tool offers. It should appear on themes, strategic shifts, speaker dynamics, and sentiment — not just evasion.

**3. Elevate misconceptions.**
Reveal-on-click misconception cards are a high-value active learning mechanic — the learner forms a judgment, then sees the correction. This should not be buried in a language tab. A "Common mistakes about this call" surface in a visible position (perhaps at the bottom of the brief, or after Step 3) could drive genuine engagement.

**4. Feynman needs a better on-ramp.**
"Learn" in the nav bar is too abstract. The call to action should answer: "Want to test whether you actually understood this call?" Each analyst step having its own "Explore with Feynman" entry point is part of the solution — but the top-level nav framing also needs to change.

**5. Extensibility for future learning models.**
The analyst steps structure is content architecture, not a learning mode. Feynman, Socratic method, self-assessment — these are modes that sit on top of the same content. The design should keep these layers clean. When the Socratic mode is built, it should be able to use the same brief + progressive disclosure structure, just with different prompting and progression mechanics.

---

## Open Questions

1. **Is the learner level selector manual (the user picks) or inferred (the app adapts)?** Manual is simpler to build; inferred is more powerful but requires session history. Could start as manual with a path to inference later.

2. **Where do misconceptions live?** They're currently a language layer item but are pedagogically closer to the brief (pre-reading, set expectations) or to the evasion step (common misinterpretations are often about what management avoided). Worth deciding placement deliberately.

3. **How does the "Bigger Picture" snapshot in the brief differ from the full Step 6 section?** The brief snapshot should be extremely compact (2–3 bullets, no interaction). Step 6 is full-fidelity with drill-down. Needs to be designed so they feel like the same information at different zoom levels, not redundant.

4. **What triggers a "sections explored" state?** Does opening a step count, or does some active engagement (expanding a card, clicking a signals button, starting a Feynman session) need to happen? This decision defines what "progress" means and shapes the session history model.

5. **How does the call brief get generated — at ingest time or on-demand?** If at ingest, it's always available instantly. If on-demand, it could be personalized (e.g. adaptive to learner level) but adds latency. Ingest-time generation is simpler and more consistent.

---

## Recommended Next Steps

1. **Validate the analyst framework steps** — does the 6-step sequence match how you'd want a beginner to approach a call? Are any steps missing, misordered, or redundant?

2. **Design the brief in detail** — the brief is the entry point and the most important single component. Worth sketching the exact fields, their sources, and how they're generated before any other design work.

3. **Decide on learner level selector** — manual or inferred, and what it actually changes in the experience.

4. **Map parity items to issues** — the deferred items table above resolves most of the dropped items. Each resolved item needs to be reopened as an issue (or bundled with related items) for implementation.

5. **Start Feynman ideation thread** — now that the content architecture is settled, the Feynman redesign has a clearer context to design within.
