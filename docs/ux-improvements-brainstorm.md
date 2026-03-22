# UX Improvements Brainstorm

Product & EdTech analysis of the Earnings Transcript Teacher app. Generated 2026-03-22.

---

## ONBOARDING & DISCOVERABILITY

**1. Zero-state / empty state problem**
The app assumes you already have a transcript loaded. A first-time user who opens it with no transcripts sees nothing useful. There's no "Get Started" flow, no sample transcript, no guidance on how to ingest a ticker.

**2. No learning objectives framing**
Learners don't know what they're about to learn or why. Before diving into a transcript, a brief "What you'll be able to do after studying this call" framing would set expectations and motivate engagement.

**3. Transcript metadata is sparse at point of selection**
The sidebar dropdown shows just a ticker symbol. A learner selecting "AAPL" vs "NVDA" gets no context: what quarter? What year? What was the headline story? Was this a big beat, a miss, a guidance cut? That context matters enormously for setting up learning.

**4. No guided "where to start" path**
The 7-step learning path is labeled Step 1–7 but doesn't actually enforce or suggest an order. A beginner doesn't know whether to start with the transcript, the overview, the Feynman loop, or the chat. The UI doesn't tell them.

**5. Jargon discovery is passive, not active**
Tooltips appear on hover, but learners don't know they exist. There's no "this transcript has 12 jargon terms — want to review them first?" prompt before diving in.

---

## LEARNING FLOW & PROGRESSION

**6. The 7-step panel and the chat pane feel disconnected**
A learner could spend 30 minutes in the metadata panel and never touch the Feynman loop, or vice versa. These two learning modalities don't reinforce each other. The Feynman loop should feel like the natural culmination of reading through the left panel, not a separate thing you remember to click.

**7. No sense of overall progress or completion**
There's no "you've studied 3 of 5 recommended topics" or "you've completed this transcript" indicator. Learners don't know when they're done or what's left.

**8. Feynman topics aren't prioritized or recommended**
The topic suggestions (themes + takeaways) are listed flat. There's no guidance on which topic is the most important to understand first, which builds on another, or which is likely to challenge the learner most.

**9. The Feynman loop stages aren't explained to the learner**
The 5-stage loop is pedagogically sound but invisible to the user. A learner gets an explanation (Stage 1) without knowing that Stage 2 is coming to challenge them. This undermines buy-in and causes confusion when the AI starts asking probing questions.

**10. No cross-transcript learning path**
The app treats each transcript as a standalone. A learner studying Apple across 4 quarters has no way to track progress across calls, see how narratives evolved, or get a "what changed since last quarter" synthesis.

**11. General Q&A mode is undersold**
It's called "General Q&A" which sounds like a support chat. It's actually a powerful RAG-grounded tutoring tool. Better framing: "Ask the Transcript" or "Transcript Q&A."

**12. No structured pre-reading checklist**
Before a learner dives into a transcript, a short checklist of recommended prep steps (read the overview, scan tone & speakers, note strategic shifts) would improve engagement with the full learning path.

---

## CONTENT & INFORMATION ARCHITECTURE

**13. Step 3 is used for two different things**
"What Management Avoided" and "Learning Opportunities" (misconceptions) are both labeled Step 3. This is confusing — they're conceptually distinct and one of them should be renumbered.

**14. Evasion analysis and "What Management Avoided" are redundant**
Step 3 (evasion, non-Q&A) and Step 7 (Q&A Evasion Review) both analyze evasion. The split between them is an implementation detail the learner doesn't care about. Consider merging them into one "How Management Handled Tough Questions" section.

**15. Takeaways and themes at Step 1 are shown without distinction**
Key takeaways and extracted themes serve different purposes (one is narrative, one is topical) but are listed together without explanation. Learners need to understand what each is.

**16. The "Recent News" section lacks educational framing**
News articles are listed but the educational value isn't obvious. "Why does this matter to your learning?" framing per article would help (the "Explain relevance" button is a start, but it's buried and optional).

**17. Competitor context is surface-level**
A list of competitors with descriptions is informative, but not pedagogically structured. "What should I be thinking about when I see $NVDA mentioned in an Apple call?" is a richer framing than "here are Apple's competitors."

**18. Strategic Shifts could show before/after**
Currently just a description of what shifted. Adding "what was the prior position" and "why this matters for investors" would dramatically increase educational value.

**19. Speaker roster information is underused**
Knowing that the CFO answered the most analyst questions, or that analysts from certain firms dominated Q&A, is educationally interesting. The speaker data exists but is only displayed as a roster list.

**20. Token counts shown to the user add noise, not value**
Learners don't care about prompt/completion tokens. This is a developer debug artifact that should be removed from the learner-facing UI.

---

## ENGAGEMENT & RETENTION

**21. No spaced repetition or review system**
Feynman sessions are completed and then forgotten. A learner who mastered "supply chain risk" in October has no mechanism to review it in November. Spaced repetition is one of the most evidence-backed learning techniques.

**22. No flashcard-style review mode**
The misconceptions and Q&A evasion analysis are perfect raw material for flashcard-style active recall ("What was the analyst probing when they asked about memory chip supply?").

**23. No learning journal or notes feature**
Learners can export Feynman session markdown but there's no persistent "my notes on this transcript" feature. Annotation and note-taking are proven retention boosters.

**24. Progress is not celebrated**
Completing a Feynman loop, completing a full transcript study — none of these events produce positive feedback. Even a simple session summary or completion acknowledgment is missing.

**25. No difficulty or depth selector**
The app generates the same content regardless of whether the user is a finance novice or an equity analyst. A learner profile or difficulty setting would allow prompts to adapt to the audience.

---

## NAVIGATION & UX

**26. Two-column layout wastes space on wide screens**
On a large monitor, the transcript browser (left) and chat (right) compete for attention without clear visual hierarchy. The learning path panel is sandwiched between them and gets lost.

**27. The left column is doing too much**
Transcript browser + 7-step learning path in one column is overwhelming. These could be tabs or a step-by-step wizard to reduce cognitive load.

**28. No way to link directly to a section of analysis**
You can't share "look at Step 7, the Q&A evasion for NVDA Q3 2024" via URL. Deep links into specific analysis sections would support collaborative learning and reference.

**29. Sidebar is the only navigation**
All navigation lives in the sidebar. As the app grows (more transcripts, multi-quarter views), this won't scale. A proper transcript library / landing page would be a better starting point.

**30. No mobile/tablet experience**
The wide-layout Streamlit app is barely usable on a tablet. For a learning tool, mobile access matters — learners study on the go.

---

## PEDAGOGICAL DEPTH

**31. The Feynman loop doesn't connect back to the transcript**
During a Feynman loop on "gross margin expansion," the AI explains the concept in isolation. It should cite specific moments in the transcript: "In this call, the CFO said X — that's exactly this concept."

**32. No "test yourself" mode beyond the Feynman loop**
Multiple choice, fill-in-the-blank, or scenario-based quizzes on the call's content would diversify the assessment modalities.

**33. The misconceptions section has no interactivity**
It's purely informational. Turning misconceptions into "Do you agree or disagree? Here's the reality" prompts would create active engagement.

**34. No synthesis across topics**
After studying multiple topics via Feynman, there's no "connect the dots" prompt: "Given what you learned about X and Y, how do they interact in this company's story?"

**35. Analyst Q&A evasion is framed as observation, not lesson**
"The executive scored 7/10 on defensiveness" is interesting but not educational on its own. "What does a defensive answer like this signal to investors? What would a transparent answer look like?" would create deeper understanding.

---

## CONTENT CREATION & LIBRARY

**36. No guided ingestion flow**
Ingesting a new transcript requires running a command-line tool. A UI to enter a ticker + quarter and trigger ingestion would make the app accessible to non-technical learners.

**37. No curated starter library**
The app has no suggested "start here" transcripts. Recommending 3-5 transcripts that are pedagogically rich (e.g., "a company beating expectations," "a company guiding down," "a company navigating a crisis") would help learners build intuition across scenarios.

**38. No transcript comparison view**
Side-by-side or sequential comparison of two calls (same company, or two companies in the same industry) would be extremely valuable for teaching how narratives evolve.

---

## TRUST & CREDIBILITY

**39. No source attribution for AI-generated content**
Every takeaway, evasion analysis, and misconception is AI-generated but presented without a "this is AI analysis — verify against the transcript" caveat. Learners (especially beginners) may treat this as ground truth.

**40. Evasion scoring feels authoritative but is subjective**
A defensiveness score of "8/10" carries false precision. Adding confidence ranges or framing as "on a spectrum from forthcoming to evasive" would be more honest about the AI's uncertainty.

---

## QUICK WINS (Low effort, high value)

- Rename "General Q&A" → "Ask the Transcript"
- Remove token counts from learner-facing chat
- Fix the duplicate "Step 3" labeling
- Add a one-paragraph "What is this transcript about?" summary at top of left panel
- Show call date + quarter in the transcript selector dropdown
- Add a "Suggest a Feynman topic" button that uses AI to recommend what to study first
