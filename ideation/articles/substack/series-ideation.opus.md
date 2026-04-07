# Blog Series Ideation — Synthesized Publishing Plan
**Date:** April 7, 2026
**Basis:** Synthesis of `series-ideation.perplexity.md` and `series-ideation.sonnet.md`

---

## Context

Two prior plans exist for this article series. The Perplexity plan established the
four-track architecture and 16-article roadmap with strong source material inventory.
The Sonnet revision improved on it by phasing the track launches, front-loading the
most original material, adding a platform strategy, and introducing success metrics.

This document synthesizes both and addresses gaps in each:

1. **Reorders Phase 1 to front-load developer articles.** Diary retrospective moved out
   of the launch phase — diary entries build loyalty with existing subscribers but don't
   acquire new readers.
2. **Plans only through Article 8 in detail.** Articles 9–16 remain directional, not
   commitments. The sequence for the back half should emerge from what you learn about
   your audience in the first three months.
3. **Adds a warm-launch strategy.** Platform discovery alone won't solve the cold start
   problem on a brand-new Substack.
4. **Adds a guest post / collaboration goal.** The fastest way to reach someone else's
   audience is to appear in front of it.
5. **Reworks titles** where the originals were too insider or too generic.
6. **Keeps the Sonnet revision's best changes:** phased track launch, "LLMs in Practice"
   rename, Substack as home base, success metrics with kill criteria.

---

## The Author

Tech consultant and mentor (~30 years experience) with a background in .NET/C#,
TypeScript/React, and enterprise software. Over the past ~3 months, built an AI-native
educational app — the **Earnings Transcript Teacher** — from scratch, with no prior
experience in Python, NLP, LLM APIs, React (minimal), GitHub deployment, or AI-assisted
coding tools.

The app helps retail investors learn to analyze earnings calls. Key features:
- Transcript ingestion and parsing (speakers, Q&A segmentation, jargon extraction)
- Sentiment and evasion analysis
- Financial and industry term definitions
- Key takeaways and strategic shift identification
- Competitor and news context
- **Feynman Loop** — an interactive guided learning flow where the app pushes back on
  the user's understanding, identifies gaps, and scaffolds deeper comprehension

The project is documented in a private GitHub diary repo.

**Positioning:** The author's credibility comes from candor, not authority. Thirty years
of building software, three months of building with AI — the honest practitioner
documenting what actually happened, not the expert prescribing what you should do.

---

## Platform Strategy

### Home base: Substack

**Why Substack:**
- Built-in discovery via recommendations, Notes, and the Substack network — other writers
  can recommend you, which is the single most effective growth channel for a new technical
  newsletter.
- Free tier is generous. No paywall needed during the audience-building phase.
- You own the email list and can export it anytime — your audience is portable.
- Technical Substacks are a growing category with less saturation than Medium.

**Why not the alternatives:**
- **Medium:** Opaque algorithm, de-emphasizes technical content, you don't own the audience.
- **Ghost:** Great tool, zero built-in discovery — you'd be shouting into the void.
- **WordPress:** Maintenance burden with no network effects.
- **Dev.to / Hashnode:** Good for developer reach but weak on email capture and cross-audience appeal.

### Warm-launch strategy (before Article 1)

Platform discovery doesn't solve the cold start problem. Before Article 1 goes live:

1. **Identify 20–30 people in your professional network** — former colleagues, mentees,
   fellow consultants, people you've helped.
2. **Send personal, individual messages** (not a mass email): "I'm writing about my
   experience building with AI tools — thought you'd find this interesting."
3. **Ask each person to subscribe**, not just read. Early subscribers give Substack's
   algorithm something to work with.
4. **Set up the Substack "about" page** before any of this. Frame it as: "I've been
   building software for 30 years and I'm candidly documenting what happens when I
   throw myself into AI tools" — not a resume.
5. **Publish 3–5 Substack Notes in the week before Article 1.** Short observations from
   the build — things you noticed, questions for other builders, interesting failures.
   Notes activity primes Substack's recommendation algorithm and gives you visibility
   in the network before your first full post. Costs nothing, creates a trail for
   early discoverers to follow.

### Syndication (reach extension)

Cross-post **Building With AI** and **LLMs in Practice** articles to **Dev.to** and
**Hashnode** 3–5 days after Substack publication:
- Set canonical URL to the Substack version.
- **Cross-post on a different day of the week** from your Substack publication day
  (e.g., Tuesday Substack, Thursday Dev.to). This gives you two promotion windows per
  article instead of one.

### Amplification channels

| Channel | What to post | Why it works |
|---------|-------------|--------------|
| **LinkedIn** | Compelling excerpt + link to full piece | 30 years of consulting = an existing network. Non-Coder's Playbook articles perform especially well here. PMs and founders live on LinkedIn. |
| **Hacker News** | Selected articles (3, 6) | Specific, technical, contrarian content performs well. Treat as a lottery ticket, not a strategy. |
| **Twitter/X** | Thread versions of key insights | Build-in-public threads. Extract from existing writing, don't write for X. |

### Guest posts and collaborations (starting Phase 2)

The fastest way to reach someone else's audience is to appear in front of it. After
Articles 2–3 establish your voice:
- **Pitch guest posts** to established AI/developer newsletters. One guest post in a
  newsletter with 10,000 subscribers will do more for growth than your next 3
  self-published articles.
- **Seek podcast interviews.** Many dev podcasts are hungry for guests with real building
  stories — not product pitches, not thought leadership, but "I tried this and here's
  what happened."
- **Look for co-writing opportunities** with people who have complementary audiences
  (e.g., a PM who writes about AI adoption could collaborate on a Non-Coder's Playbook piece).

### Skip for now

- **Reddit:** Communities are hostile to self-promotion unless you're already a known
  contributor. Not worth the reputation risk at launch.
- **YouTube / Podcasts (your own):** Wrong medium for this content type now. Revisit once
  the audience asks for it.

---

## Track Architecture (Phased Launch)

All articles draw from the same project but target distinct audiences. Tracks launch
in stages rather than all at once.

| Track | Folder | Audience | Tone | Launches at | Monetization Path |
|-------|--------|----------|------|-------------|-------------------|
| **Diary** | `diary/` | Cross-audience | Warm, candid, first-person | Article 1 | Newsletter anchor, personal brand |
| **Building With AI** | `building-with-ai/` | Developers | Technical, practitioner, honest | Article 2 | CodeMentor credibility, dev newsletter |
| **LLMs in Practice** | `llms-in-practice/` | Applied AI practitioners | Deep technical, opinionated | Article 7 | Consulting, workshops, authority |
| **Non-Coder's Playbook** | `non-coders-playbook/` | PMs, founders | Accessible, practical, empowering | Article 11 | Substack growth, course/cohort product |

**Cadence:**
- Articles 1–4: **weekly** (build momentum, give Substack's algorithm enough signal)
- Articles 5+: **biweekly** (every 10–14 days, sustainable long-term)
- **Buffer rule:** Have the next article fully drafted before publishing the current one.
  A bad week shouldn't break the cadence.

**Cross-linking logic:**
- Every **LLMs in Practice** piece links to the relevant **Building With AI** piece
- Every **Non-Coder's Playbook** piece links to the relevant **Building With AI** piece
- Every **Diary** piece links forward to upcoming articles and back to the reflection prompt
- Every article's author bio links to Article 1 as the series entry point
- Every article ends with a **specific forward-looking hook** — not "subscribe for more"
  but a concrete promise of what's next (e.g., "Next week I'll show you the exact
  CLAUDE.md file that taught an AI my codebase conventions")

**Eventual free/paid boundary (not announced at launch):**

Paid subscriptions stay off until 500–1,000 free subscribers. When enabled, the track
structure has a natural split:

| Tier | Tracks | Rationale |
|------|--------|-----------|
| **Free forever** | Diary, Non-Coder's Playbook | Growth drivers. Broad audience, high shareability, LinkedIn-friendly. These attract new subscribers who may convert to paid. |
| **Paid candidates** | Building With AI, LLMs in Practice | Practitioner-value content that's hard to find elsewhere. Developers and applied AI engineers are the audiences most likely to pay for specific, experience-based technical writing. |

This means the free phase should create demand for the paid content, not satisfy the
same need. Diary and Non-Coder's pieces should reference and point toward the technical
depth in Building With AI and LLMs in Practice — establishing that the deeper material
exists and is worth subscribing for.

---

## Full Publishing Sequence

### Phase 1 — Establish (Articles 1–4, weekly cadence)
*Goal: Set up the narrative, build your voice, establish developer credibility fast.
Diary + Building With AI only. Three developer-facing articles in a row builds a clear
identity.*

| # | Track | Title | Status | Notes |
|---|-------|-------|--------|-------|
| 1 | Diary | **Why I Built an Earnings Transcript Parser to Learn AI** | Draft exists | Origin story and series anchor. Microsoft earnings call opening is vivid. "Why not just use ChatGPT?" section is well-handled. Needs: explicit teaser/invitation into the tracks. This is the only diary piece in Phase 1 — it earns its spot as the entry point to the series. |
| 2 | Building With AI | **The CLAUDE.md Pattern: Teaching an AI Your Codebase Conventions** | Not started | Concrete, specific, immediately useful. Low controversy, high shareability. **This is your breakout candidate** — it addresses a pain point that thousands of developers have right now. Give it the most promotion effort. Cross-post to Dev.to + Hashnode. |
| 3 | Building With AI | **Replacing a scikit-learn Pipeline With a Single Haiku Prompt** | Not started | Concrete before/after story. scikit-learn TF-IDF + NMF + TextRank replaced by a single Haiku call — better quality, dramatically simpler code, resolved silent JSON reliability failures. This is your "show, don't tell" proof that AI tooling changes what's possible. Cross-post to Dev.to + Hashnode. Submit to Hacker News. |
| 4 | Building With AI | **AI Memory Systems Across Sessions: Why Context Is Everything** | Not started | Deepens the developer track. Connects to the divide-and-conquer agentic pattern. Pairs naturally with the CLAUDE.md piece — both are about teaching AI your context, at different levels. |

**Why no diary piece at Article 4:** The Sonnet revision placed a retrospective diary here.
But diary articles build loyalty with existing subscribers — they don't acquire new readers.
In Phase 1 you have no existing subscribers. Three developer-facing articles in a row
(Articles 2–4) build a clear identity and give you three pieces to cross-post and promote.
The retrospective moves to Article 8, where you'll have subscribers who care about your
reflections.

### Phase 2 — Build Credibility (Articles 5–8, biweekly cadence)
*Goal: Demonstrate technical depth. Front-load your most differentiated material. Launch
the LLMs in Practice track.*

| # | Track | Title | Status | Notes |
|---|-------|-------|--------|-------|
| 5 | Building With AI | **I Asked Claude to Plan My Sprint — Then Rewrote Every Ticket** | Not started | Previously titled "When to Trust the AI and When to Push Back" — that's generic. Lead with the specific story: the horizontal → vertical slice rewrite where the LLM proposed horizontal delivery, the author knew better, and Claude rewrote every ticket for vertical slices. Secondary story: CSS layout as a persistent weak spot. The point: AI amplifies existing judgment. |
| 6 | Building With AI | **Chunk, Dispatch, Synthesize: The Pattern That Runs My App and My Development Workflow** | Not started | **Your most original insight — elevated from original position 14.** The same divide-and-conquer pattern operates at two levels simultaneously: (1) production architecture (transcript ingestion chunks text, dispatches to parallel agents, aggregates analyses) and (2) development workflow (spinning up multiple Claude Code agents to analyze different aspects of a problem in parallel). The through-line: chunk+dispatch+synthesize maps to a fundamental LLM constraint (context window) and capability (parallel inference). Submit to Hacker News. |
| 7 | LLMs in Practice | **The JSON That Broke My App: When LLM Outputs Can't Be Trusted** | Not started | **First LLMs in Practice article — launches the track.** Previously titled "Structured Output Reliability: Why Perplexity Failed and Haiku Saved Me" — reworked to lead with the problem, not the providers. Evasion investor signals feature switched from Perplexity to Claude after reliability failures. Two angles: (1) JSON output reliability as a real engineering concern, (2) provider enshittification — Gemini/Perplexity reducing quotas/reliability without warning is a reason to build provider flexibility from day one. |
| 8 | Diary | **What I Actually Learned Building With AI for Three Months** | Not started | Honest retrospective. Re-engages Article 1 readers. Establishes the candid practitioner persona. This is the right time for a diary piece — you have subscribers who followed the technical articles and now want the human story. Adapted from original Article 8; timeline adjusted to match actual elapsed time. |

### Phase 3 — Go Deeper (Articles 9–12, biweekly cadence)
*Goal: Establish technical authority. Launch the Non-Coder's Playbook track.
Differentiate from AI hype content.*

**Note:** The sequence below is directional, not a commitment. Reassess after Phase 2
based on which articles performed best and what audience you've actually built.

| # | Track | Title | Status | Notes |
|---|-------|-------|--------|-------|
| 9 | LLMs in Practice | **Model Routing in Practice: When to Use Haiku, Sonnet, and Opus** | Not started | Synthesizes real decisions from the project. The Opus/Sonnet split: Opus for planning, analysis, and issue design; Sonnet for execution. Covers cost/capability tradeoff but also trust as a routing dimension. |
| 10 | Building With AI | **TDD With an AI Co-Author: Does It Still Work?** | Not started | Opinionated, slightly contrarian. Appeals to experienced developers skeptical of AI coding tools. Draw from the test coverage 0→80% sprint. |
| 11 | Non-Coder's Playbook | **What's Actually Possible When You Build With AI as a Non-Engineer** | Not started | **First Non-Coder's Playbook article — launches the track.** Broad audience, LinkedIn-friendly. By this point you have a body of technical work to reference, which strengthens the "here's what I actually built" claim. Push hard on LinkedIn. |
| 12 | Non-Coder's Playbook | **The Real Costs of Building an LLM-Powered App** | Not started | Anchor with the concrete $0.75/transcript figure. Key nuance: subscription + API combination creates a cost structure that sneaks up on you. Counterweight to hype. High share value on LinkedIn. |

### Phase 4 — Synthesize (Articles 13–16, biweekly cadence)
*Goal: Draw on the most recent learnings. Cement a unique, practitioner perspective.*

**Note:** These are topic reservations, not specifications. By the time you reach Article
13 (~5 months in), your audience data will tell you which of these to write, which to
skip, and what new topics have emerged that you couldn't have predicted today.

| # | Track | Candidate title | Notes |
|---|-------|----------------|-------|
| 13 | Building With AI | **The AI Coding Tool Journey: From Copy-Paste to Claude Code** | Chronological evolution through four tools. Provider enshittification as cautionary note. |
| 14 | LLMs in Practice | **What Six Personas Found That One Missed: Parallel LLM Architecture Reviews** | The security gap (Next.js middleware vs. FastAPI admin routes) is a compelling anchor. Previously titled with the subtitle first — lead with the hook. |
| 15 | Non-Coder's Playbook | **Turning Business Requirements Into GitHub Issues With AI** | Practical playbook format. Include the vertical slice rewrite at PM depth. |
| 16 | Non-Coder's Playbook | **Using Claude Code for Product Management: Beyond the Code Editor** | AI amplifies existing judgment rather than replacing it. Session handoff checkpoint pattern. |

---

## Title Rework Summary

Titles should lead with the specific, surprising detail — not the category or abstraction.

| Original title | Revised title | Why |
|---------------|--------------|-----|
| When to Trust the AI and When to Push Back | **I Asked Claude to Plan My Sprint — Then Rewrote Every Ticket** | Generic → specific story. The reader wants to know what happened. |
| Structured Output Reliability: Why Perplexity Failed and Haiku Saved Me | **The JSON That Broke My App: When LLM Outputs Can't Be Trusted** | Assumes the reader cares about provider names. Lead with the problem. |
| Parallel LLM Architecture Reviews: What Six Personas Found That One Missed | **What Six Personas Found That One Missed: Parallel LLM Architecture Reviews** | Flip the title — the hook first, the method second. |
| Six Months In: What I Thought I Was Building vs. What I Actually Built | **What I Actually Learned Building With AI for Three Months** | Adjusted timeline to match reality. Simpler, more direct. |

Titles that were already strong and kept as-is: The CLAUDE.md Pattern, Replacing a
scikit-learn Pipeline With a Single Haiku Prompt, Chunk Dispatch Synthesize, Model
Routing in Practice, TDD With an AI Co-Author.

---

## Writing Workload

A good technical article takes 8–15 hours: outlining, drafting from diary source material,
editing, creating any diagrams or code samples, writing the Substack-specific intro and
CTA. At weekly cadence that's 1–2 hours per day alongside engineering work.

**Sustainability rules:**
- **Always stay one article ahead.** Have Articles 1 and 2 fully drafted before publishing
  Article 1. A bad week shouldn't break the cadence.
- **Mine the diary aggressively.** Weekly summaries (especially week-ending-2026-03-29.md
  and the executive-summary-draft.md) are already 40–50% of the way to finished articles
  for Articles 3, 6, 7, and 14.
- **Don't polish in isolation.** Share drafts with 1–2 trusted readers before publishing.
  Early feedback catches blind spots and clarifies what's interesting to someone who
  isn't you.

---

## Success Metrics

### At Article 4 (end of Phase 1, ~1 month in)
- **Subscribers:** 50+ (warm-launch contacts + organic; baseline for Substack recommendation eligibility)
- **Signal:** At least 2 articles with >50% open rate
- **Qualitative:** At least one inbound comment or share from someone you don't know
- **Action:** Decide whether to maintain weekly cadence or shift to biweekly
- **Action:** Review per-article engagement (opens, shares, comments) for Articles 2–4.
  Which topics resonated? Use this to inform Phase 2 ordering — if "Chunk, Dispatch,
  Synthesize" themes got early traction in Article 4, pull it forward; if CLAUDE.md
  drove the most shares, lean into developer tooling pieces first.
- **Early warning:** If you reach Article 4 with <20 subscribers beyond warm-launch
  contacts, diagnose before completing Phase 1 at full speed. Is it the content, the
  distribution, or the audience targeting?

### At Article 8 (end of Phase 2, ~3 months in)
- **Subscribers:** 200+
- **Signal:** Dev.to/Hashnode cross-posts generating inbound clicks to Substack
- **Qualitative:** At least one article shared by another technical writer or newsletter
- **Action:** Pitch at least one guest post to an established newsletter
- **Action:** Reassess Phase 3–4 article sequence based on what's working

### At Article 12 (end of Phase 3, ~5 months in)
- **Subscribers:** 500+
- **Signal:** LinkedIn posts for Non-Coder's Playbook articles generating engagement
- **Qualitative:** Inbound consulting inquiry or CodeMentor signup attributable to the series

### Kill criteria
- If you reach Article 8 with <50 subscribers and zero engagement from strangers, the
  audience isn't there. Pause and diagnose before continuing: is it the content, the
  distribution, or the audience targeting?

---

## Key Surprises (Source Material Across Multiple Articles)

- **LLM costs are manageable but sneaky.** ~$0.75/transcript for processing. The
  subscription + API combination adds up in ways that aren't obvious upfront.
- **Provider enshittification is real.** Gemini reduced usage quotas and extended reset
  limits without warning. Build provider flexibility in from day one.
- **Quality differences between providers are significant.** Claude has come out on top
  consistently. The evasion signals feature was switched from Perplexity to Claude after
  reliability failures.
- **Agentic divide-and-conquer is a force multiplier.** Parallel agents analyzing different
  aspects, synthesized into a final output — speeds things up and sidesteps context window
  limits. Works both as a dev workflow and as a production architecture pattern.
- **LLMs understand delivery philosophy.** The horizontal → vertical slice rewrite
  demonstrates that LLMs can reframe an entire body of work when pushed — but only because
  the human knew what to push for.
- **The Opus/Sonnet split pays off.** Opus for planning and design; Sonnet for execution.

---

## Existing Assets

| Asset | Location | Status |
|-------|----------|--------|
| Article 001 draft | `ideation/articles/diary/001-why-i-built-an-earnings-transcript-parser-to-learn-ai.md` | Strong draft, needs series-anchor ending |
| Substack setup decisions | `ideation/articles/substack/substack-setup-ideation.md` | Publication name, bio, welcome post/email |
| Track conventions | `ideation/articles/CONVENTIONS.md` | Needs update: rename `llms-in-production/` → `llms-in-practice/` |
| Diary repo | Private GitHub repo | Active; weekly summaries are rich source material |

---

## Recommended Next Steps

1. **Choose a plan** — compare all three ideation documents and decide on a sequence
2. **Draft Articles 1 and 2** — both must be ready before Article 1 publishes
3. **Set up Substack** — claim your publication name, write the "about" page (position
   as candid practitioner, not resume), configure the welcome email
4. **Build your warm-launch list** — 20–30 personal contacts to notify on launch day
5. **Update `CONVENTIONS.md`** — rename track folder from `llms-in-production/` to
   `llms-in-practice/`
6. **Mine the diary** — weekly summaries are already 40–50% of Articles 3, 6, 7, and 14
7. **After Article 3:** identify 2–3 established newsletters to pitch a guest post to
