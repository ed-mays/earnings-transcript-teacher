# Learning Flow Design: EarningsFluency UX Ideation

_Working document for [#202](https://github.com/ed-mays/earnings-transcript-teacher/issues/202) — 2026-03-28_

---

## Design Brief

**Learner:** Retail investor — not a finance professional, but someone actively trying to improve their ability to read and interpret earnings calls.

**Session goal:** The learner leaves with a better interpretation of *this* call, with the meta-goal of becoming better at reading calls in general.

**The central tension:** Passive reading feels like understanding but doesn't build skill. Interpretive skill comes from active engagement — forming hypotheses, noticing what's missing, explaining things in your own words. The design must create natural entry points into active engagement without imposing a rigid sequence.

**Feynman:** On-demand, not mandatory. But the design should make using it feel like an obvious next step, not an optional extra.

**Scope:** Single-session design. Note where session history infrastructure would plug in naturally — this primes the architecture without building it yet.

---

## Direction 1: "Orient Then Dive"

### Philosophy

A retail investor landing on an earnings call is walking into a room mid-conversation. Before they can interpret anything, they need to know who's speaking, what's at stake, and what questions to hold in mind as they read. This direction front-loads orientation — then gets out of the way.

### The Flow

**1. Call Brief (before transcript)**

The call page opens to a compact brief rather than the transcript. This replaces the old pre-reading checklist with something more opinionated and less mechanical:

- **Context line:** Company, quarter, call date, and a single sentence on why this call mattered (e.g. "First post-acquisition report; analysts focused on integration costs and margin guidance.")
- **3 key takeaways:** The most important things that were said — not summaries, but conclusions a skilled reader would draw.
- **3 interpretation questions:** Framed as things to watch for as you read. E.g.: "Did management's confidence on margin recovery match the actual numbers?" / "Which analyst questions were deflected, and what topic did they share?" / "What changed in tone from last quarter?" These are the Feynman entry points — they seed the questions a learner should be able to answer.
- **Overall signal:** Sentiment summary (executive vs. analyst), evasion level (low/medium/high), and whether any major strategic shift was flagged.

The brief is designed to be read in 60–90 seconds. It gives the learner a mental frame before they encounter the density of the transcript.

**2. Transcript + Analysis Panel (main experience)**

After the brief, the learner moves into the familiar two-panel layout — but the analysis panel is reorganized around interpretation rather than data type.

Current tab grouping (data-typed):
- Summary / Keywords / Themes / Evasion / Shifts

Proposed grouping (interpretation-oriented):
- **What they said** — key themes, prepared remarks summary, strategic shifts
- **What they avoided** — evasion panel (prepared remarks + Q&A), signals button
- **Who was in the room** — speaker list, call dynamics, analyst firm breakdown
- **The bigger picture** — recent news, competitors
- **Language** — keywords, jargon, misconceptions

This grouping mirrors how an experienced investor actually thinks through a call. It also makes the Feynman entry points more obvious: each tab maps to a topic category a learner could explore.

**3. Feynman — on demand, everywhere**

A persistent "Explore with Feynman" entry point is available from:
- Any analysis tab (explore this topic)
- Any interpretation question from the brief (surface this question in chat)
- The "Explore with Feynman" button on strategic shifts (already planned)

**Deferred items and where they land:**

| Deferred item | Resolution in this direction |
|---|---|
| Call summary | → Brief: context line + key takeaways |
| Key takeaways | → Brief: top 3 takeaways |
| Learning objectives | → Brief: interpretation questions |
| Pre-reading checklist | → Replaced by the brief entirely |
| Adaptive start prompt banner | → Folded into brief (surfaces what kind of call this is) |
| Jargon discovery banner | → Surfaced in the Language tab after reading |
| Learning path header / progress | → Dropped: no mandatory sequence |
| Step progress tracking | → Dropped: no mandatory sequence |

**Trade-offs:**

- **Does well:** Low cognitive load entry; teaches learners to read actively by giving them questions before they start; fits a retail investor's limited attention.
- **Gives up:** No connection between analysis and specific transcript passages. The transcript is still a wall of text. Learners who read without the interpretation questions in mind won't benefit from the brief.
- **Risk:** The brief could become a substitute for reading — learners consume the takeaways and skip the transcript entirely. The interpretation questions need to require genuine engagement with the transcript to answer.

---

## Direction 2: "Annotated Transcript"

### Philosophy

The transcript is the primary learning artifact — not the analysis panel. Every finding (evasion, sentiment, themes, jargon) should be visible *within* the text, not just in a separate panel. Analysis becomes a layer on top of the transcript, not a separate destination. The learner reads the call as an annotated document and arrives at interpretation naturally.

### The Flow

**1. The transcript as the primary surface**

The call page leads with the transcript. The analysis panel is secondary — a reference layer, not the main event.

The transcript is annotated inline:

- **Evasion highlights:** Passages flagged as evasive are highlighted in a warm amber. A tooltip shows the evasion label ("non-answer," "redirected to guidance," "deflection with optimism"). This is the evasiveness heat map extended to the full Q&A.
- **Sentiment markers:** Segments are colored by tone — confident (green), hedging (yellow), defensive (red). Subtle enough to not be distracting; visible enough to create a pattern across the call.
- **Speaker role differentiation:** Executive responses and analyst questions are visually distinct (color band or label at left margin). This makes the back-and-forth legible at a glance.
- **Theme tags:** Passages linked to a theme (e.g. "margin guidance," "integration costs") carry an inline tag. Clicking the tag surfaces the theme analysis in the side panel.
- **Jargon underlines:** Financial/industry terms are underlined. Hover triggers a tooltip definition; click opens the full jargon panel (define / explain / find).

**2. Analysis panel as reference**

The panel on the right doesn't change on tab selection — it responds to what the learner clicks in the transcript. Click an evasion highlight → panel shows evasion detail for that passage. Click a theme tag → panel shows that theme's analysis. Click a jargon term → panel shows term actions.

For learners who prefer to browse analysis rather than start from the transcript, the panel can also be browsed directly, with highlights in the transcript updating to reflect the selected analysis item.

**3. Feynman as a passage-level entry point**

Any annotated passage has a "Explore with Feynman" micro-action. This starts a Feynman session pre-seeded with the passage and its context — not just a topic name, but a specific thing the management said and what it might mean. This is a more grounded Feynman entry point than a topic picker.

**4. Pre-reading layer (lighter version of Direction 1's brief)**

A small "before you start" summary is available as a collapsible at the top — not a full brief, just enough to orient: overall sentiment signal, evasion level, and the single most important strategic shift. The learner can expand it or skip it.

**Deferred items and where they land:**

| Deferred item | Resolution in this direction |
|---|---|
| Call summary | → Collapsible pre-reading banner (compact) |
| Key takeaways | → Collapsible pre-reading banner |
| Learning objectives | → Not present — the annotations are the pedagogy |
| Pre-reading checklist | → Replaced by the collapsible banner |
| Jargon tooltips in transcript | → Core to this direction — inline underlines with hover |
| Jargon discovery banner | → Inline underlines replace the banner |
| Learning path header / progress | → Dropped |
| Step progress tracking | → Dropped |

**Trade-offs:**

- **Does well:** Creates genuine engagement with the transcript; the annotations teach the learner to notice things they would have missed; jargon, evasion, and sentiment become visible rather than requiring a tab switch.
- **Gives up:** Requires significant new infrastructure — passage-level metadata linking analysis to specific transcript segments. The current data model likely stores analysis at the call level, not the passage level. This direction has the highest data/backend lift.
- **Risk:** Annotation density could create visual noise that feels overwhelming for a retail investor who just wants to read. Requires careful visual design to keep the annotations helpful rather than distracting.
- **Session history readiness:** Passage-level annotations naturally support highlighting "passages you've already engaged with" or "topics you've explored with Feynman" — a future session history feature plugs in naturally here.

---

## Direction 3: "Progressive Disclosure"

### Philosophy

Not every retail investor wants to read a full earnings call. Many want to understand what happened — the key signals, what management emphasized, what they avoided — without committing to the transcript. This direction makes the analysis the primary surface and positions the transcript as an on-demand reference. The learner progresses from high-level signal to granular detail, going as deep as they choose.

### The Flow

**1. Signal Dashboard (entry point)**

The call page opens to a compact dashboard — the highest-signal summary of the call:

- **Sentiment at a glance:** A 3-part bar or grid: overall, executive, analyst. Color-coded (bullish/neutral/bearish).
- **Top 3 themes:** The most prominent topics, each with a one-line description and an expand action.
- **Evasion index:** A single evasion level (low/medium/high) with a count of flagged exchanges. Tap to expand.
- **Strategic shift:** If a shift was detected, it's called out here with one sentence. Tap to expand.
- **Key takeaways:** 3 bullets below the main indicators — the call in plain language.

This dashboard is scannable in under a minute. It answers: "What happened on this call?"

**2. Expandable analysis layers**

Each dashboard element expands in place to reveal the full analysis:

- Expand a theme → see the full theme card with associated passages (links to transcript)
- Expand evasion → see the evasion panel: prepared remarks + Q&A by analyst, with severity badges and the "What this signals for investors" button
- Expand a strategic shift → see the full shift card with "Explore with Feynman" link
- Expand key takeaways → see the full call summary with additional context

**3. "Go deeper" layer**

Below the dashboard, a secondary tier surfaces contextual information the learner might want after understanding the signal:

- **Who was in the room** — speaker list and call dynamics
- **The bigger picture** — recent news and competitors (framed as: "What else should you know about this call?")
- **Language** — keywords, jargon, misconceptions

**4. Transcript as reference**

The transcript is always one tap away, but it's positioned as "read the full call" rather than the starting point. When the learner navigates to the transcript from an expanded analysis item, the relevant section is scrolled into view and highlighted. This creates a natural path from signal → evidence.

**5. Feynman per topic**

Every expanded analysis item has a "Explore with Feynman" entry. Because the learner has already formed a view at the signal level, the Feynman session starts with more context — they know what they think; now they test whether they can explain it.

**Deferred items and where they land:**

| Deferred item | Resolution in this direction |
|---|---|
| Call summary | → Signal dashboard: key takeaways bullets |
| Key takeaways | → Signal dashboard |
| Learning objectives | → Not present — learner self-directs depth |
| Pre-reading checklist | → Replaced by dashboard (it's the checklist, made visual) |
| Adaptive start prompt banner | → Dashboard serves this function |
| Jargon discovery banner | → Surface in the Language tier |
| Learning path header / progress | → Replaced by which dashboard sections the learner has expanded |
| Step progress tracking | → Could become: "sections explored" count in the dashboard header |

**Trade-offs:**

- **Does well:** Very low barrier to entry; retail investors who are time-poor or new to earnings calls get value immediately; expandable layers prevent overwhelming anyone who doesn't want depth.
- **Gives up:** Risks becoming a news-summary product rather than a learning tool. If the learner can get everything from the dashboard, they may never engage deeply with the transcript or with Feynman — which undercuts the skill-building goal.
- **Risk:** Optimizing for shallow engagement. The design needs deliberate friction that nudges learners toward the transcript and toward Feynman, rather than treating the dashboard as the terminal destination.
- **Session history readiness:** "Sections explored" state maps directly to session history. Returning learners could see which parts of a call they've already engaged with.

---

## Cross-Cutting Observations

These apply regardless of which direction is chosen:

**1. The analysis panel tab labels are currently invisible to skill-building.**
"Summary / Keywords / Themes / Evasion / Shifts" describes data types. An investor trying to build interpretation skill needs labels that describe what to *look for*, not what data is present. Even small reframing helps: "What they avoided" is more learnable than "Evasion."

**2. The "What this signals for investors" LLM button is underused.**
It currently appears only on evasion items. This pattern — "here's what this means for you as an investor" — is the core interpretation scaffold the tool should offer. Every major analysis type (themes, shifts, speaker dynamics, sentiment) could have a signals framing, not just evasion.

**3. Feynman needs an obvious on-ramp, not just a navigation link.**
"Learn" in the navigation bar is too abstract. Learners don't know what Feynman mode is or why they'd want it. The entry point should answer: "Want to test whether you actually understood this call?" That question is motivating in a way "Learn" is not.

**4. Misconceptions are underrated.**
Reveal-on-click misconception cards are a high-value active learning mechanic — learners form a judgment, then see the correction. This could be elevated rather than tucked into a tab. A "Common mistakes about this call" surface at a visible position in any direction could generate genuine engagement.

**5. The Feynman stage indicator is a design problem in all three directions.**
The Streamlit approach (stage header above chat) failed because it scrolled out of view. In all three directions, the stage indicator needs to be persistent and legible. A sticky progress bar at the top of the chat window — or stage-aware framing within the chat itself (the AI surfaces the current stage in its prompts) — are two approaches worth evaluating separately.

---

## Deferred Items: Summary Resolution

| Parity audit item | Direction 1 | Direction 2 | Direction 3 |
|---|---|---|---|
| Call summary / key takeaways | Brief (primary) | Collapsible banner | Dashboard (primary) |
| Learning objectives | Interpretation questions | Not present | Not present |
| Pre-reading checklist | Replaced by brief | Replaced by banner | Replaced by dashboard |
| Adaptive start prompt | Folded into brief | Not present | Dashboard |
| Jargon discovery banner | Language tab | Inline underlines | Language tier |
| Jargon tooltips in transcript | Incidental | Core mechanic | Via transcript links |
| Learning path / progress | Dropped | Dropped | "Sections explored" state |
| Step progress tracking | Dropped | Dropped | Lightweight dashboard state |

---

## Open Questions

1. **How much do retail investors actually read the full transcript?** The right answer for Direction 2 vs. 3 depends heavily on this. If most users don't read the transcript in full, making it the primary surface (Direction 2) is a mismatch.

2. **Is "skill-building" the right frame for a retail investor, or is "faster/better decisions" more motivating?** These lead to different designs. Skill-building → learning objectives, progression indicators, Feynman prompts. Better decisions → signal dashboards, signals buttons, "what does this mean for me."

3. **What does the call library page need to do?** If the brief / dashboard concept is right, the library entry for a call could surface a compressed version of the same signal — evasion level, sentiment, top shift — so learners can triage which calls deserve deep attention before opening one.

4. **Should the "Bigger Picture" features (news, competitors) be pre-reading context or post-reading synthesis?** Both are defensible. Pre-reading: context before engaging with the call. Post-reading: situate what you just learned in the broader environment.

---

## Recommended Next Steps

1. **React to the three directions** — which philosophy resonates, which feels wrong, which elements from different directions could be combined?

2. **Clarify the transcript question** — how much reading do you expect a retail investor to actually do? That determines whether Direction 2 is viable or over-engineered.

3. **Develop a hybrid if appropriate** — Direction 1's brief + Direction 3's progressive disclosure in the analysis panel + Direction 2's inline annotations (as a later enhancement) may be the right combination.

4. **Identify which deferred items the chosen direction restores** — the decisions in the table above will directly inform which of the dropped parity items get reopened as issues.

5. **Separate the Feynman redesign** — the stage indicator and pacing controls problem is substantial enough to warrant its own ideation thread, informed by whichever direction is chosen here.
