# Learning Path Redesign — Spike #48

*Audit and redesign of the 7-step learning path structure.*

---

## 1. Current State Audit

The current 7 steps in `ui/metadata_panel.py` (with implementation issues noted):

| Step | Label | Contents | Problems |
|------|-------|----------|----------|
| 1 | Overview | Key Takeaways + Extracted Themes | No narrative summary; takeaways and themes unlabelled as distinct |
| 2 | Tone & Speakers | Sentiment + Speaker roster | Speaker data is list-only; no dynamics (who dominated? who asked tough Qs?) |
| 3a | What management avoided | Non-Q&A evasion | **Duplicate "Step 3" label** with 3b |
| 3b | Learning Opportunities | Misconceptions/corrections | **Duplicate "Step 3" label** with 3a; no interactivity |
| 4 | Recent News | News articles (async fetch) | Educational framing is optional ("Explain relevance" is buried) |
| 5 | Competitors | Competitor list (async fetch) | Surface-level; no pedagogical structure |
| 6 | Strategic Shifts | Shift descriptions | No before/after framing; no "why it matters for investors" |
| 7 | Q&A Evasion Review | Q&A evasion analysis | **Conceptually redundant with Step 3a** — same concept, split by source |
| — | Advanced (hidden) | Financial + Industry Jargon | Gated behind a checkbox; treated as advanced when it's foundational |
| — | Feynman Loop | 5-stage Socratic loop | **Entirely disconnected** from the numbered steps; feels like a separate product |

**Root problems:**
- The step structure evolved feature-by-feature, not from a learning design perspective
- Evasion analysis is split across two steps (3a and 7) for implementation reasons the learner doesn't care about
- The Feynman Loop — the app's most valuable pedagogical tool — has no connection to the steps that precede it
- Vocabulary (jargon) is hidden as "advanced" when it's actually foundational to comprehension
- There is no "done" state; learners don't know when they've finished a transcript

---

## 2. Proposed New Step Structure

### Design principles

1. **Narrative first** — Start with what happened, before drilling into how and why
2. **Read before test** — All passive analysis steps come before the Feynman Loop
3. **One concept per step** — No duplicate labels; no split implementations of the same idea
4. **Feynman as culmination** — The loop is the payoff after completing the reading steps, not a parallel track
5. **Vocabulary is foundational** — Jargon review is a named step, not an advanced toggle

---

### Step 1 · The Story

**What it contains:**
- A 1-paragraph executive summary of the call (new — currently missing)
- Key Takeaways (with "why it matters" explanation)
- Extracted Themes

**Rationale:** Learners need a hook before they engage with detail. Without knowing "Apple beat on revenue but guided conservatively on China" they have no frame for reading anything else. The executive summary is the most important missing piece in the current UI.

**What changed from current:** Adds the summary (new content). Keeps takeaways and themes but clearly labels them as distinct things. Renamed from "Overview" to "The Story."

---

### Step 2 · Who Was In The Room

**What it contains:**
- Speaker roster: executives with titles, analysts with firms
- Sentiment analysis: overall, executive tone, analyst sentiment
- Speaker dynamics: who spoke most, which analysts asked the most probing questions (enriched — see data model section)

**Rationale:** Understanding who is on a call changes how you hear it. Knowing the CFO was unusually defensive vs. the CEO sounded confident is context that shapes interpretation of everything that follows.

**What changed from current:** Renamed from "Tone & Speakers." Reorders sentiment before speaker list (sentiment is the conclusion; speaker list is context). Adds speaker dynamics (requires ingestion pipeline change).

---

### Step 3 · What Was Said vs. Avoided

**What it contains:**
- All evasion analysis in one place: both scripted-remarks evasion (current Step 3a) and Q&A evasion (current Step 7)
- Organized by topic/theme, not by source (prepared vs Q&A)
- Each item shows: what the analyst/topic probed, how management responded, defensiveness score, what a transparent answer would have looked like

**Rationale:** From a learning perspective, evasion is evasion. The distinction between "management avoided X in their prepared remarks" and "management avoided X when asked directly" is interesting colour but not a reason to split these into two UI sections. Merging them gives the learner a coherent picture of what management was reluctant to discuss.

**What changed from current:** Merges Step 3a (non-Q&A evasion) and Step 7 (Q&A Evasion Review) into one step. **Step 7 is removed.**

**Note on misconceptions (current Step 3b):** Learning Opportunities (misconceptions/corrections) is conceptually different from evasion — it's about the learner's likely misunderstandings, not management behaviour. It belongs in the Feynman prep section as a "common traps to avoid" block, surfaced just before the learner starts a Feynman loop. It is not an independent step.

---

### Step 4 · What Changed

**What it contains:**
- Strategic shifts from prior calls
- Before/after framing: "Previously management said X; now they said Y"
- Investor significance: why does this shift matter?
- "Explain via Feynman" button (keep existing — this is a good connection)

**Rationale:** Strategic shifts are higher-signal than news or competitors — they tell you something changed in the company's story. They belong closer to the overview, before external context. The current placement (Step 6, after competitors) buries the most strategically important content.

**What changed from current:** Moved from Step 6 to Step 4. Renamed from "Strategic Shifts" to "What Changed." Adds before/after framing and investor significance (requires ingestion pipeline change).

---

### Step 5 · The Bigger Picture

**What it contains:**
- Recent news (around the call date, ranked by theme relevance)
- Competitive landscape
- Both sections load asynchronously in parallel (keep existing background thread pattern)

**Rationale:** News and competitors are both external context — they answer "what was happening around this call?" Neither requires a separate numbered step. Merging them into one "external context" step reduces the step count without losing content.

**What changed from current:** Merges Step 4 (Recent News) and Step 5 (Competitors) into one step. Uses tabs or sub-sections within the expander.

---

### Step 6 · Language Lab

**What it contains:**
- Financial jargon (term, definition, "Explain in context" button)
- Industry jargon (term, definition, "Explain in context" button)
- Top TF-IDF keywords
- Common misconceptions about this transcript's content (moved here from Step 3b)

**Rationale:** Vocabulary is not an advanced feature — it is foundational. A learner who doesn't understand "gross margin expansion," "NWC," or "TAM" cannot engage meaningfully with the Feynman Loop. Removing the `show_advanced_analysis` checkbox and making this a first-class step is one of the highest-value changes in this redesign.

**What changed from current:** Promoted from behind the `show_advanced_analysis` toggle to a named step. Added misconceptions (from current Step 3b). Renamed from "Financial/Industry Jargon" to "Language Lab."

---

### → Feynman Loop (Culmination)

**What it is:** Not a numbered step — the natural endpoint of the learning path.

**What changes:**
- At the bottom of Step 6, add a "You're ready to teach this" CTA panel that links directly to the chat pane and auto-suggests the most important topics
- Topic suggestions are prioritised: strategic shifts and evasion topics are surfaced first (they are the most educationally rich)
- Common misconceptions (from Step 6) are surfaced as "watch out for these traps" context before the learner starts
- The connection between the left panel and the chat pane is made explicit

**Rationale:** The Feynman Loop is pedagogically the most valuable part of the app. It should feel like the reward for completing the reading steps, not a separate mode you discover in the sidebar.

---

## 3. Step Mapping

| Current | New | Action |
|---------|-----|--------|
| Step 1 · Overview (Takeaways + Themes) | Step 1 · The Story | Add executive summary; keep content |
| Step 2 · Tone & Speakers | Step 2 · Who Was In The Room | Rename; add speaker dynamics |
| Step 3a · What Management Avoided (evasion) | Step 3 · What Was Said vs. Avoided | Merge with Step 7 |
| Step 3b · Learning Opportunities (misconceptions) | Step 6 · Language Lab (sub-section) | Move; not a standalone step |
| Step 4 · Recent News | Step 5 · The Bigger Picture (tab) | Merge with Step 5 |
| Step 5 · Competitors | Step 5 · The Bigger Picture (tab) | Merge with Step 4 |
| Step 6 · Strategic Shifts | Step 4 · What Changed | Reorder; enrich with before/after |
| Step 7 · Q&A Evasion Review | Step 3 · What Was Said vs. Avoided | Merge with Step 3a; step removed |
| Advanced: Financial Jargon | Step 6 · Language Lab | Promote from hidden |
| Advanced: Industry Jargon | Step 6 · Language Lab | Promote from hidden |
| Feynman Loop (separate pane) | Culmination after Step 6 | Add CTA; connect to left panel |

**Net change:** 7 steps → 6 steps. Step 7 is eliminated. Advanced jargon is promoted to a named step. Feynman Loop gains an explicit connection to the reading path.

---

## 4. Implementation Issues

These flow from the new structure and can be filed as individual issues.

### UI refactoring (no pipeline changes)

- **#A** Fix duplicate Step 3 label — quick win, should have been done already
- **#B** Rename "General Q&A" → "Ask the Transcript" in sidebar
- **#C** Remove token counts from learner-facing chat messages
- **#D** Merge Step 3a (evasion) and Step 7 (Q&A evasion) into a single expander in `metadata_panel.py`
- **#E** Merge Step 4 (Recent News) and Step 5 (Competitors) into one "The Bigger Picture" expander with tabs/sub-sections
- **#F** Reorder: move Strategic Shifts from position 6 to position 4
- **#G** Promote Language Lab: remove `show_advanced_analysis` checkbox; make it Step 6
- **#H** Move misconceptions from Step 3b into the Language Lab section
- **#I** Add "You're ready to teach this" CTA panel at the bottom of the left column that links to the Feynman Loop and surfaces prioritised topic suggestions

### Ingestion pipeline changes (new LLM calls)

- **#J** Generate executive summary during ingestion — 1 paragraph, stored in DB. Haiku is sufficient. Surface in Step 1.
- **#K** Enrich Strategic Shifts with before/after framing — modify the strategic shifts extraction prompt to output `{prior_position, current_position, investor_significance}` instead of a plain text description. Requires DB schema change.
- **#L** Speaker dynamics — count speaking turns per speaker and identify which analysts asked the most questions. Can be computed from the `spans` table at query time (no new LLM call needed).

### Data model changes

- **`call_synthesis` table:** Add `call_summary TEXT` column for the executive summary (Issue #J)
- **`call_synthesis.strategic_shifts` column:** Currently `TEXT[]` (flat strings). Change to `JSONB[]` to store `{prior, current, significance}` objects, or add a separate `strategic_shifts` table. (Issue #K)
- **No other schema changes required** — evasion merge (#D), step reordering (#F), language lab promotion (#G) are all UI-only changes

### "Done with a transcript" definition

A learner is **done** when they have:
1. Read steps 1–6 (tracked by which expanders they've opened — Streamlit session state)
2. Completed at least one Feynman loop on a topic from this transcript

Neither of these is currently tracked. Issue #M: add per-transcript completion tracking (session state + optional DB persistence in `learning_sessions`).

---

## 5. Questions Answered

**What is the ideal learning sequence for a first-time user?**

Story → Voices → Tensions (evasion) → Changes → Context → Vocabulary → Teach it back (Feynman)

**Which current steps should be merged, split, reordered, or removed?**
- **Merge:** Steps 3a + 7 (evasion) → new Step 3; Steps 4 + 5 (external context) → new Step 5
- **Reorder:** Step 6 (Strategic Shifts) moves to Step 4
- **Remove:** Step 7 (absorbed into Step 3)
- **Promote:** Advanced jargon becomes Step 6
- **Add:** Executive summary in Step 1; before/after framing in Step 4

**Are there concepts that deserve a step but currently don't?**
- Executive summary (narrative hook) — **yes, missing from Step 1**
- Vocabulary as a foundational step — **exists but hidden**
- Speaker dynamics — **exists as data, not rendered usefully**

**How should the Feynman Loop relate to the steps?**
- It is the **culmination**, not a parallel track
- Steps 1–6 are the reading phase; the Feynman Loop is the testing phase
- The left panel should end with an explicit handoff to the chat pane

**What does "done with a transcript" mean?**
- Read all 6 steps (at least opened each expander)
- Completed ≥ 1 Feynman loop on a topic from the transcript
- Currently undefined in the app — needs explicit tracking

---

## 6. Summary of New Structure

```
Step 1 · The Story           ← was: Overview + NEW executive summary
Step 2 · Who Was In The Room ← was: Tone & Speakers
Step 3 · Said vs. Avoided    ← MERGE: Step 3a + Step 7 (evasion)
Step 4 · What Changed        ← was: Step 6 (Strategic Shifts), moved earlier
Step 5 · The Bigger Picture  ← MERGE: Step 4 (News) + Step 5 (Competitors)
Step 6 · Language Lab        ← was: hidden Advanced section, PROMOTED
→ Feynman Loop               ← culmination CTA, no longer disconnected
```
