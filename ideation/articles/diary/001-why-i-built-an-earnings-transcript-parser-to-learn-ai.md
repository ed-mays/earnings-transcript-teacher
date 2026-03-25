# Why I Built an Earnings Transcript Parser to Learn AI

**Track:** Diary
**Sequence:** 1
**Status:** Draft

---

## Notes

**Why:** Opens the whole series and anchors all future cross-links. Must establish motivation, project scope, and the parallel tracks without naming them formally.

**Three motivations to weave together:**
1. Improve understanding of finance at enterprise scale
2. Learn AI-driven app development beyond basic chat interfaces
3. Explore AI use cases for non-technical roles
4. Build a tool that helps people learn

**Reader feeling at end:** Curious and inspired.

**Voice:** Warmest of the four tracks — first person, candid, honest about what you didn't know going in. Neutral and professional overall, with slight shifts per track.

**Opening hook:**
- Lead with the domain: more surprising, less likely to read as another AI tools article; broader reach

---

## Rough Draft Outline

### 1. The Catalyst (The "Why" - Domain Focus)
- **The Gap:** A colleague pointed out a gap in my business acumen and suggested listening to earnings calls.
- **The Problem:** Earnings transcripts are brutal for learners. They are filled with unfamiliar vocabulary, dense industry context, and subtle cues (tone, deflection). 
- **The Contrast:** While an experienced analyst parses these quickly, the information overload is exhausting for a learner.

### 2. The Builder's Dilemma (Why Not Just ChatGPT?)
- **My Background:** As a tech consultant and mentor with ~30 years of experience, I knew a generic chatbot wouldn't cut it.
- **The Need for Control:** I needed to augment the LLM's behavior and isolate it exclusively to the finance domain.
- **The Goal:** Build a tool specifically for learners (like retail investors). This requires a guided flow (like the Feynman technique) that is impossible to orchestrate consistently in a standard chat interface.

### 3. The App & Its "Magic"
- **What It Does:** Downloads, parses, and ingests transcripts into local storage identifying features like Q&A, speakers, jargon, and key takeaways. Deeper analysis also identifies topics like strategic shifts, relevant news from the call's time period.
- **The Magic:** A cohesive visual representation of these concepts in a GUI, enabling rapid exploration and review. The app also helps surface "hidden" information like sentiment shifts, changes in tone, and other subtle cues that are difficult for learners to detect.
- **The Interactive Learning Loop:** Features a Feynman learning flow for open-ended discussion, which is the core educational engine.

### 4. Facing the Learning Curve (Honesty & Vulnerability)
- **The Imposter Syndrome:** "What if it doesn't work at all?", "What if *I* can't figure out how to make it work?"
- **The Avalanche of New Tech:** Addressing the overwhelming learning curve of combining Python, Streamlit, AI models, product development, prompt engineering, and AI-assisted coding flows all at once.
- **The Practical Fear:** Managing costs, especially the LLM request volumes driven by a highly interactive UI.

### 5. Conclusion / Teaser for the Series
- Tying it all back together: How building this tool not only closed the gap in my business acumen but opened up a new world of AI development.
- Tease the upcoming articles in the "Building With AI" and "LLMs in Production" tracks.

---

## Draft

## The Advice That Exposed a Gap

It started with a casual piece of advice that quietly exposed a gap in my business acumen: *"You should really listen to more earnings calls."*

My colleague was right. As a technical consultant and mentor with nearly thirty years of experience in technology and management, I had spent my career mastering complex systems and architectures. Yet, when it came to the enterprise-scale financial machinery that actually governs strategic business decisions, I was missing a crucial piece of the puzzle. Earnings calls are the unfiltered pulse of the corporate world. They signal strategic shifts, reveal underlying health, and dictate market movements.

The first one I tried was Microsoft's. I sat with the transcript open alongside the audio and felt two things arrive in quick succession: first, the sheer volume — the density, the pace, the relentless forward motion of financial language I had no way to anchor. Then, right behind it, the more discouraging realization: without prior context, nothing had a foothold. I recognized the feeling. I'd watched it cross the faces of technical mentees encountering a complex codebase for the first time. I could read every word and still lose the thread, because I didn't yet know which words mattered.

Earnings transcripts are a dense thicket of unfamiliar vocabulary, arcane industry context, and carefully constructed corporate speak. For an experienced financial analyst, these transcripts are rich with signal. They can scan the text, instantly extract the salient points, read between the lines to detect subtle shifts in tone or deliberate deflections, and synthesize the information in minutes.

But for a learner? It's an exhausting exercise in information overload. Trying to digest that volume of specialized data all at once required an immense amount of cognitive energy. I wasn't just struggling to understand the words; I was struggling to find the *story*. 

I realized I needed a better way to consume this information—a tool that didn't just summarize a document, but actively helped me learn how to read it. 

## Why a Chatbot Wasn't Enough

The obvious question, especially in today's generative AI landscape, is: *Why not just drop the PDF into ChatGPT or Claude and ask it to summarize?*

I knew that approach wouldn't cut it. A standard chatbot is a generalist. It will happily summarize an earnings call, but it does so passively. I didn't know the right questions to ask — and I didn't know what I didn't know. A chat interface wasn't going to surface that. 

I didn't want a passive summarizer; I wanted an active learning tool. My goal was to build something specifically for learners, like retail investors, who need a guided path to understanding. I needed to isolate the AI's behavior exclusively to the finance domain and take strict control over its inference. 

More importantly, true learning requires iteration. I wanted to implement a Feynman learning loop — think of it as an interactive form of rubber ducking, except instead of a silent duck, you have an AI that actually pushes back and identifies the gaps in your understanding. It's a structured flow where I'm prompted to explain concepts back and fill gaps in my knowledge. Orchestrating that kind of continuous, guided learning loop is nearly impossible to achieve consistently in a standard off-the-shelf chat interface. I needed to build a custom application to pull it off.

## From Wall of Text to Learning Engine

The first time I ran a transcript through the pipeline, the interface was a simple console application — no GUI, no AI, just Python and scikit-learn doing statistical analysis and primitive classification. I expected the output to be sparse. Instead, the terminal filled with structure: speakers segmented, Q&A separated from prepared remarks, jargon extracted, key phrases surfaced. It worked. More than that, the sheer volume of signal already embedded in the document's structure — before a single AI call — surprised me.

That was the foundation. The GUI came later. The AI-powered analysis layer came after that, adding depth that statistical methods alone couldn't reach: core takeaways, strategic shifts, and relevant news from the period surrounding the call. Each layer made the transcript less of a document and more of a map.

But the real shift came with the GUI. Instead of a wall of text, the transcript becomes navigable — the structure visible at a glance. More importantly, the application surfaces what I used to miss entirely: sentiment shifts across speakers, the difference in tone between prepared remarks and Q&A, the subtle deflections buried in the dialogue that an experienced analyst reads instinctively. Getting those signals into the interface was the difference between building a summarizer and building something that actually teaches you how to read.

I can drill down into the extracted concepts, for example defining a financial term, or exploring the strategic implications of a particular statement within the context of the call.

Rather than reading passively, I can also engage with the transcript through an interactive Feynman learning loop. The app prompts me to explain what I've just read, analyzes my understanding, and helps me fill in the gaps through a guided, open-ended discussion. The transcript goes from a daunting block of text to a dynamic educational engine.

What I had, though, was a well-fleshed-out prototype — not yet hardened for production, not ready for multi-user scale, but functional enough to prove the concept. Getting there was another matter entirely.

## The Part Nobody Talks About

Before I wrote a single line of code, the imposter syndrome had already arrived. Questions like *"Will this actually be useful for real enterprise-level finance, or am I just building an expensive summarization toy?"* and *"What happens if the LLM hallucinates and gives me terrible financial insights?"* were constant companions. Then came the technical reality: *"How do I even begin to wire together Python, Streamlit, and LLM APIs when the landscape changes every week?"*

The reality of building an AI-native application is that it's an avalanche of new technology. It wasn't just about learning Python or building a UI with Streamlit. I had to simultaneously wrap my head around AI model selection, prompt engineering, complex data ingestion pipelines, product development, and the very new world of AI-assisted coding flows. It was overwhelming, and there were days when I felt completely buried under it.

Beyond the technical hurdles, there was a practical fear: cost. An interactive application, especially one driving a continuous Feynman learning loop, makes a *lot* of LLM requests. I had to learn on the fly how to manage tokens, optimize inference, and balance capability with potential for runaway API bills. It forced me to treat every prompt not just as an instruction, but as a unit of economics.

The moment the project stopped feeling like a prototype was when I added the Feynman flow. Before that, it was a sophisticated analysis tool — useful, but passive. The moment it could push back, ask me to explain something, and identify where my understanding broke down, it became something closer to what I'd originally imagined: a learning partner. That shift changed what I thought I was building.

## What It Taught Me

What started as an attempt to close a gap in my business acumen became a full-fledged journey into modern AI application development. The Earnings Transcript Teacher solved my immediate problem: it gave me a structured, visually coherent, and interactive way to consume complex financial transcripts without the cognitive overload.

I started this project trying to understand earnings calls. I ended it with a much harder problem: how do you take something that works on your laptop and turn it into something that works for anyone? That's the question I'll be working through next.

I built this parser to learn. It's still teaching me.
