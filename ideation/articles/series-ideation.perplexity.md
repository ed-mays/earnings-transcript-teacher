# Blog Series Ideation — Session Summary
**Date:** April 7, 2026

---

## Context

The author is a tech consultant and mentor (~30 years experience) with a background
in .NET/C#, TypeScript/React, and enterprise software. Over the past ~3 months, they
built an AI-native educational app — the **Earnings Transcript Teacher** — from scratch,
with no prior experience in Python, NLP, LLM APIs, React (minimal), GitHub deployment,
or AI-assisted coding tools.

The app helps retail investors learn to analyze earnings calls. Key features:
- Transcript ingestion and parsing (speakers, Q&A segmentation, jargon extraction)
- Sentiment and evasion analysis
- Financial and industry term definitions
- Key takeaways and strategic shift identification
- Competitor and news context
- **Feynman Loop** — an interactive guided learning flow where the app pushes back on
  the user's understanding, identifies gaps, and scaffolds deeper comprehension

The project is documented in a GitHub diary repo:
https://github.com/ed-mays/earnings-transcript-teacher-diary

An article ideation folder already exists in the main repo:
https://github.com/ed-mays/earnings-transcript-teacher/tree/main/ideation/articles

---

## The Four-Track Architecture

All articles draw from the same project but target distinct audiences.

| Track | Folder | Audience | Tone | Monetization Path |
|-------|--------|----------|------|-------------------|
| **Diary** | `diary/` | Cross-audience | Warm, candid, first-person | Newsletter anchor, personal brand |
| **Building With AI** | `building-with-ai/` | Developers | Technical, practitioner, honest | CodeMentor credibility, dev newsletter |
| **LLMs in Production** | `llms-in-production/` | Applied AI engineers | Deep technical, opinionated | Consulting, workshops, authority |
| **Non-Coder's Playbook** | `non-coders-playbook/` | PMs, founders | Accessible, practical, empowering | Substack growth, course/cohort product |

**Cadence:** One article every 10–14 days (~6–7 months for 16 articles).

**Cross-linking logic:**
- Every **LLMs in Production** piece links to the relevant **Building With AI** piece
- Every **Non-Coder's Playbook** piece links to the relevant **Building With AI** piece
- Every **Diary** piece links forward to upcoming articles and back to the reflection prompt
- Every article's author bio links to Article 1 as the series entry point

---

## Full Publishing Sequence

### Phase 1 — Establish (Articles 1–4)
*Goal: Set up the narrative, build your voice, get reps in.*

| # | Track | Title | Status | Notes |
|---|-------|-------|--------|-------|
| 1 | Diary | **Why I Built an Earnings Transcript Parser to Learn AI** | Draft exists | Strong bones. Microsoft earnings call opening is vivid. "Why not just use ChatGPT?" section is well-handled. Ending needs slight update: add a more explicit teaser/invitation into the four tracks so the article functions as a series anchor. |
| 2 | Building With AI | **The CLAUDE.md Pattern: Teaching an AI Your Codebase Conventions** | Not started | Concrete, specific, immediately useful. Low controversy, high shareability. First developer-facing piece. |
| 3 | Non-Coder's Playbook | **What's Actually Possible When You Build With AI as a Non-Engineer** | Not started | Broad audience, LinkedIn-friendly. Links back to Article 1 for backstory. |
| 4 | Building With AI | **AI Memory Systems Across Sessions: Why Context Is Everything** | Not started | Deepens the developer track. Connects to the divide-and-conquer agentic pattern discovered during development. |

### Phase 2 — Build Credibility (Articles 5–8)
*Goal: Demonstrate technical depth. Start earning the LLMs in Production audience.*

| # | Track | Title | Status | Notes |
|---|-------|-------|--------|-------|
| 5 | LLMs in Production | **Replacing a scikit-learn Pipeline With a Single Haiku Prompt** | Not started | Concrete before/after story. scikit-learn TF-IDF + NMF + TextRank replaced by a single Haiku call — better quality, dramatically simpler code, resolved silent JSON reliability failures. Accessible to Track 1 readers too. |
| 6 | Non-Coder's Playbook | **The Real Costs of Building an LLM-Powered App** | Not started | Anchor with the concrete $0.75/transcript figure. Key nuance: per-call cost is manageable, but subscription + API combination creates a cost structure that sneaks up on you. Counterweight to hype. High share value. |
| 7 | Building With AI | **When to Trust the AI and When to Push Back** | Not started | Opinion piece. More personal voice. Establishes the honest practitioner persona. |
| 8 | Diary | **Six Months In: What I Thought I Was Building vs. What I Actually Built** | Not started | Mid-series reflection. Re-engages early readers. Good newsletter anchor. |

### Phase 3 — Go Deeper (Articles 9–12)
*Goal: Establish technical authority. Differentiate from AI hype content.*

| # | Track | Title | Status | Notes |
|---|-------|-------|--------|-------|
| 9 | LLMs in Production | **Structured Output Reliability: Why Perplexity Failed and Haiku Saved Me** | Not started | Evasion investor signals feature switched from Perplexity to Claude after reliability failures. Two angles: (1) JSON output reliability as a real engineering concern, (2) provider enshittification — Gemini/Perplexity reducing quotas/reliability without warning is a reason to build provider flexibility in from day one. |
| 10 | Building With AI | **TDD With an AI Co-Author: Does It Still Work?** | Not started | Opinionated, slightly contrarian. Appeals to experienced developers skeptical of AI coding tools. Draw from the test coverage 0→80% sprint and Vitest component test work. |
| 11 | Non-Coder's Playbook | **Turning Business Requirements Into GitHub Issues With AI** | Not started | Practical playbook format. High LinkedIn share value. Include the horizontal→vertical slice rewrite story (see Article 16 notes — this story could appear in both, at different depth levels). |
| 12 | LLMs in Production | **Model Routing in Practice: When to Use Haiku, Sonnet, and Opus** | Not started | Synthesizes real decisions from the project. The Opus/Sonnet split: Opus for planning, analysis, and issue design; Sonnet for execution. Issue quality from Opus-drafted specs noticeably reduced back-and-forth. CSS layout work remained a weak spot for Sonnet — Opus needed to finish it. Covers cost/capability tradeoff but also trust as a routing dimension. |

### Phase 4 — Synthesize (Articles 13–16)
*Goal: Draw on the most recent learnings. Cement a unique, practitioner perspective.*

| # | Track | Title | Status | Notes |
|---|-------|-------|--------|-------|
| 13 | Building With AI | **The AI Coding Tool Journey: From Copy-Paste to Claude Code** | Not started | Chronological evolution: Perplexity chat window (copy-paste, low friction entry point) → PyCharm + Junie (existing JetBrains subscription, IDE-native) → Antigravity (Gemini-backed, existing subscription) → Claude Code (settled workflow). Include `everything-claude-code` and Garry Tan's `gstack` toolkit extensions. Provider enshittification (Gemini reducing quotas without warning) is a cautionary note here. Quality differences between providers — Claude on top in author's experience. |
| 14 | LLMs in Production | **Chunk, Dispatch, Synthesize: The Pattern That Runs My App and My Development Workflow** | Not started | **Key insight: divide-and-conquer operates at two levels simultaneously.** (1) Production architecture: transcript ingestion chunks the text, dispatches to parallel agents, aggregates analyses — handles documents too large for a single context window. (2) Development workflow: spinning up multiple Claude Code agents to analyze different aspects of a problem in parallel, then synthesizing — solves both speed and context window constraints. The through-line: chunk+dispatch+synthesize is a general pattern for working with LLMs at scale, transferable across contexts because it maps to a fundamental LLM constraint (context window) and capability (parallel inference). Note: moved from Building With AI to LLMs in Production because the architectural depth warrants it. |
| 15 | LLMs in Production | **Parallel LLM Architecture Reviews: What Six Personas Found That One Missed** | Not started | Six concurrent LLM passes with defined personas for the architecture review. Found a security issue invisible to single-pass review: any authenticated user could invoke admin API endpoints directly because Next.js middleware only guarded page routes, not `/api/admin/*`. Required simultaneously reading Next.js middleware and FastAPI dependency to notice the gap. A single-pass review would not have caught it. Practical technique: define scoped personas (security, performance, scalability, etc.) and run in parallel. |
| 16 | Non-Coder's Playbook | **Using Claude Code for Product Management: Beyond the Code Editor** | Not started | PM functions performed with Claude Code: issue ideation, writing/creating issues, backlog analysis and reconciliation. **Centerpiece story:** LLM proposed implementing a body of work in horizontal slices (data layer → logic → UI). Author asked it to rethink in vertical slices so users could see incremental progress. LLM rewrote all tickets for vertical delivery. **Framing note:** the author had to know enough about delivery philosophy to push back in the first place. AI amplifies existing judgment rather than replacing it. Also include: session handoff checkpoint pattern — when a Claude Code session limit hits mid-task, write executable `gh issue create` commands to a handoff file; next session runs the file with no reorientation needed. PR-as-ideation-canvas: open a PR for the design document, use inline comments to anchor decisions to specific paragraphs. |

---

## Key Surprises (Source Material Across Multiple Articles)

- **LLM costs are manageable but sneaky.** ~$0.75/transcript for processing. The subscription + API combination (Claude Code subscription + feature API usage) adds up in ways that aren't obvious upfront.
- **Provider enshittification is real.** Gemini reduced usage quotas and extended reset limits without warning. Build provider flexibility in from day one.
- **Quality differences between providers are significant.** Claude has come out on top consistently in the author's experience. The evasion signals feature was switched from Perplexity to Claude after reliability failures.
- **Agentic divide-and-conquer is a force multiplier.** Parallel agents analyzing different aspects, synthesized into a final output — speeds things up and sidesteps context window limits. Works both as a dev workflow and as a production architecture pattern.
- **LLMs understand delivery philosophy.** The horizontal→vertical slice rewrite demonstrates that LLMs can reframe an entire body of work when pushed — but only because the human knew what to push for.
- **The Opus/Sonnet split pays off.** Opus for planning and design; Sonnet for execution. CSS layout was a recurring weak spot for Sonnet.

---

## Existing Assets

| Asset | Location | Status |
|-------|----------|--------|
| Article 001 draft | `ideation/articles/diary/001-why-i-built-an-earnings-transcript-parser-to-learn-ai.md` | Strong draft, needs series-anchor ending |
| Publishing sequence | `ideation/articles/publishing-sequence.proposed.md` | Covers Articles 1–12; needs Phase 4 additions |
| Track conventions | `ideation/articles/CONVENTIONS.md` | Complete, no changes needed |
| Diary repo | https://github.com/ed-mays/earnings-transcript-teacher-diary | Active; weekly summaries are rich source material |

---

## Recommended Next Steps

1. **Update `publishing-sequence.proposed.md`** to add Phase 4 (Articles 13–16) and the retitled Article 14
2. **Revise Article 001 ending** to add a clearer series invitation/teaser for the four tracks
3. **Draft Article 002** — the CLAUDE.md pattern is the highest-value, most immediately publishable next piece
4. **Mine the diary** — weekly summaries (especially week-ending-2026-03-29.md and the executive-summary-draft.md) are already halfway to blog posts for Articles 9, 10, 14, and 15