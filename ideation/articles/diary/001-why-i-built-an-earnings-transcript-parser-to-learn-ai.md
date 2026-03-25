# Why I Built an Earnings Transcript Parser to Learn AI

**Track:** Diary
**Sequence:** 1
**Status:** Pre-draft

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

It started with a casual piece of advice that quietly exposed a gap in my business acumen: *"You should really listen to more earnings calls."*

My colleague was right. As a technical consultant and mentor with nearly thirty years of experience in technology and management, I had spent my career mastering complex systems and architectures. Yet, when it came to the enterprise-scale financial machinery that actually governs strategic business decisions, I was missing a crucial piece of the puzzle. Earnings calls are the unfiltered pulse of the corporate world. They signal strategic shifts, reveal underlying health, and dictate market movements.

So, I tried listening to them. And it was brutal.

Earnings transcripts are a dense thicket of unfamiliar vocabulary, arcane industry context, and carefully constructed corporate speak. For an experienced financial analyst, these transcripts are rich with signal. They can scan the text, instantly extract the salient points, read between the lines to detect subtle shifts in tone or deliberate deflections, and synthesize the information in minutes.

But for a learner? It's an exhausting exercise in information overload. Trying to digest that volume of specialized data all at once required an immense amount of cognitive energy. I wasn't just struggling to understand the words; I was struggling to find the *story*. 

I realized I needed a better way to consume this information—a tool that didn't just summarize a document, but actively helped me learn how to read it. 

### 2. The Builder's Dilemma (Why Not Just ChatGPT?)

The obvious question, especially in today's generative AI landscape, is: *Why not just drop the PDF into ChatGPT or Claude and ask it to summarize?*

As a technical consultant and mentor with nearly thirty years of experience, I knew that approach wouldn't cut it. A standard chatbot is a generalist. It will happily summarize an earnings call, but it does so passively. If you don't know the right questions to ask, or if you don't even know what you don't know, a chat interface won't save you. 

I didn't want a passive summarizer; I wanted an active learning tool. My goal was to build something specifically for learners, like retail investors, who need a guided path to understanding. I needed to isolate the AI's behavior exclusively to the finance domain and take strict control over its inference. 

More importantly, true learning requires iteration. I wanted to implement a Feynman learning loop—a structured, interactive flow where the user is prompted to explain concepts back and fill gaps in their knowledge. Orchestrating that kind of continuous, guided state machine is nearly impossible to achieve consistently in a standard off-the-shelf chat interface. I needed to build a custom application to pull it off.

### 3. The App & Its "Magic"

The Earnings Transcript Teacher isn't just a reader; it's a fully automated ingestion and analysis pipeline. Give it a stock ticker and a quarter, and it downloads the raw transcript, parses it, and ingests it into local storage. 

During that process, it systematically tears the document down to its structural components. It identifies the prepared remarks, segments the Q&A sessions, profiles the speakers, and extracts both financial and industry-specific jargon. A deeper LLM-driven analysis pinpoints core takeaways, strategic shifts, and even relevant news from the time period surrounding the call.

But the real "magic" happens in the GUI. Instead of staring at a multi-page wall of text, learners get a cohesive visual representation of the call's concepts enabling rapid exploration and review. The application surfaces the "hidden" signals that an experienced analyst would catch naturally—sentiment shifts across speakers, changes in tone, and subtle cues buried in the dialogue that are difficult for learners to detect.

You can also drill down into the extracted concepts, for example defining a financial term or concept, or exploring the strategic implications of a particular statement within the context of the call.

Rather than reading passively, you can also engage with the transcript through an interactive Feynman learning loop. The app prompts you to explain what you've just read, analyzes your understanding, and helps you fill in the gaps through a guided, open-ended discussion. The transcript goes from a daunting block of text to a dynamic educational engine.

### 4. Facing the Learning Curve (Honesty & Vulnerability)

I won't pretend this was an easy build. Before writing a single line of code, the imposter syndrome hit hard. Questions like *"Will this actually be useful for real enterprise-level finance, or am I just building an expensive summarization toy?"* and *"What happens if the LLM hallucinates and gives me terrible financial insights?"* were constant companions. Add to that the overwhelming technical question: *"How do I even begin to wire together Python, Streamlit, and LLM APIs when the landscape changes every week?"*

The reality of building an AI-native application is that it's an avalanche of new technology. It wasn't just about learning Python or building a UI with Streamlit. I had to simultaneously wrap my head around AI model selection, prompt engineering, complex data ingestion pipelines, product development, and the very new world of AI-assisted coding flows. It was overwhelming, and there were days when the learning curve felt more like a brick wall.

Beyond the technical hurdles, there was a very practical fear: cost. An interactive application, especially one driving a continuous Feynman learning loop, makes a *lot* of LLM requests. I had to learn on the fly how to manage tokens, optimize inference, and balance capability with potential for runaway API bills. It forced me to treat every prompt not just as an instruction, but as a unit of economics.

### 5. Conclusion: A New Lens on AI and Finance

What started as an attempt to close a gap in my business acumen became a full-fledged journey into modern AI application development. The Earnings Transcript Teacher solved my immediate problem: it gave me a structured, visually coherent, and interactive way to consume complex financial transcripts without the cognitive overload.

Crucially, while the core features are in place, the application isn't finished. Right now, it's a well-fleshed-out prototype. It's not yet hardened for production—it lacks multi-user support, a scalable web UI, proper deployment pipelines, and robust observability. But that's exactly the point. Building this prototype didn't just teach me how to read an earnings report; it laid the foundation for learning how to *productionize* AI applications, design non-linear user flows, and collaborate with AI to write code.

This diary entry is just the beginning. Over the next few months, I'll be unpacking the technical architecture, prompt strategies, and the hard-won lessons of moving from prototype to production. If you're a developer curious about how to guide an AI codebase, watch for the **Building With AI** track. If you're looking for deep dives into structured output reliability, deployment, and "productionizing" these tools, follow the **LLMs in Production** track.

I built this parser to learn. Let's explore what it can teach us.
