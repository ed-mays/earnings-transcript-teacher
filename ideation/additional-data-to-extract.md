You can turn your extracted fields into “handles” that drive spaced repetition, pattern recognition, and deliberate practice on real earnings calls. I’ll assume your learning tool’s goal is to help someone get better at understanding, analyzing, and comparing earnings calls over time.[1][2]

Because I couldn’t load your specific markdown file, I’ll speak in terms of typical items people extract from earnings transcripts (speakers, sections, sentiment, topics, Q&A pairs, metrics mentioned, guidance language, etc.) and how to use them, then suggest additional fields commonly used in earnings‑call NLP projects.[2][3][4][1]

## 1. Using your existing extracted data in a learning tool

Here are concrete learning experiences your current data can power:

- Speaker‑aware drills
  - Use speaker labels (CEO, CFO, analyst) to let learners practice: “Summarize the CEO’s opening remarks,” or “Compare CEO vs CFO tone on guidance.”[3][1]
  - Build exercises where a learner identifies which speaker likely made a given statement (management vs sell‑side) based on style and content.

- Section‑by‑section comprehension
  - If you split calls into prepared remarks vs Q&A, you can create tasks like: “Highlight three concrete metrics in prepared remarks and three in Q&A; which feel more forward‑looking?”[1][3]
  - Let users practice summarizing each section separately (business overview, segment performance, outlook, risk) and then stitch into a one‑paragraph thesis.

- Sentiment and tone calibration
  - Use sentence‑ or segment‑level sentiment to create labeling tasks: show a passage and ask learners to rate the tone and then reveal the model’s score and expert commentary.[4][3]
  - Track how sentiment changes from opening remarks to Q&A and ask: “Why might management sound more cautious here?”

- Topic and concept recognition
  - If you already extract topics/themes (e.g., demand, pricing, margins, supply chain, regulation), turn them into tagging exercises: “Tag each excerpt with relevant themes.”[2][3][1]
  - Build “theme timelines” across quarters so learners can visually see how often a topic appears and answer reflection questions like “What has management talked about more over the last four quarters and why might that matter?”

- Q&A pair learning
  - Use question–answer pairs to train people on how analysts ask questions and how good/bad answers sound.[3][2]
  - Exercises: “Rewrite this analyst question to make it more precise,” or “What did management _not_ answer in this response?”

- Metric extraction for sanity checks
  - If you extract numbers (revenue, growth rates, margins, guidance), build quick‑check tasks: “Match each metric to its context,” or “Which of these numbers belongs to guidance vs historical performance?”[5][6][1]
  - Ask learners to compute simple relationships from extracted metrics (e.g., y/y growth, margin deltas) and reconcile them with management’s narrative.

- Cross‑call comparison modules
  - Use metadata (company, ticker, date, sector) plus aggregated features (overall sentiment, theme counts) to let users compare two companies’ calls side by side.[5][1][3]
  - Design tasks like: “Compare how these two companies discuss competition” or “Which management team is more explicit about risks this quarter?”

## 2. Additional information worth extracting

Based on how earnings‑call analysis tools and research projects work, here are useful fields you may not be capturing yet.[7][8][4][1][2][3]

- Hedging, uncertainty, and obfuscation language
  - Explicitly flag hedges (“we hope,” “we believe,” “too early to tell”), uncertainty markers, and vague language.[8][4][3]
  - In a learning tool, you can ask: “Highlight hedging phrases in this answer; what are they signaling?”

- Forward‑looking vs backward‑looking statements
  - Tag sentences as historical reporting vs guidance or forward‑looking commentary.[9][8][3]
  - This supports drills like: “Separate what actually happened from what management says will happen.”

- Risk and opportunity frames
  - Detect explicit mentions of risk factors, headwinds, tailwinds, opportunities, and mitigation strategies.[8][1][3]
  - Then create tasks: “List three risks and three mitigations mentioned in this call.”

- Explicit vs implicit guidance quality
  - Extract whether guidance is given (yes/no), its form (numeric range, qualitative only), and whether it was raised, lowered, reaffirmed relative to prior statements.[6][1][5][8]
  - Learners can practice classifying guidance language as clear, vague, or evasive and link that to later realized results.

- Commitment strength and accountability signals
  - Tag phrases that indicate commitments (“we will,” “we are committed to”) and references back to prior promises.[4][3][8]
  - Use this to train learners to track whether management follows through over multiple quarters.

- Question quality and type
  - Classify analyst questions by type (clarification, drill‑down, model‑building, challenge, softball) and by topic.[2][3][4]
  - This enables exercises where users rate question quality, rewrite questions, or design better follow‑ups.

- Answer quality and responsiveness
  - Score answers on directness (did they actually answer the question?), specificity (metrics, timeframes), and spin.[3][4][8]
  - Turn this into rubrics where learners grade answers and compare their grades with the tool’s assessment.

- Emotional and rhetorical signals
  - Beyond sentiment, capture intensity (excitement vs flat), emphasis (repetition, “let me be clear”), and rhetorical devices (lists of three, analogies).[4][3]
  - In the learning tool, highlight these and ask: “How is management trying to shape perception here?”

- Comparative and benchmarking language
  - Extract mentions of competitors, market share, and relative performance (“outperform,” “gaining share,” “in line with peers”).[6][1][5]
  - Then learners can practice inferring competitive positioning from the commentary.

- Temporal references and timelines
  - Tag future time frames (next quarter, fiscal year, multi‑year horizon) attached to each promise or risk.[3][4]
  - This supports spaced‑repetition style follow‑ups: months later, prompt the learner to check whether a specific future claim played out.

- Structure and discourse markers
  - Extract section markers and discourse cues (“first,” “second,” “in summary,” “to your question”) to help learners see the structure of answers.[1][3]
  - Build tasks like: “Re‑outline this answer into bullet points based on its implicit structure.”

- Style and complexity metrics
  - Track readability, sentence length, jargon density by speaker and over time.[4][3]
  - Let learners see when simplicity increases or decreases, and what that might indicate (e.g., over‑complex answers around problematic topics).

## 3. Designing higher‑level learning experiences

Once you have these richer annotations, you can build more advanced modules:

- “Call clinic” mode
  - Pick a single call, show auto‑extracted themes, risks, guidance, sentiment, and a short summary, then ask the learner to write their own thesis and compare.[5][1][3]

- Longitudinal “trust the management team” module
  - Use historical extractions (commitments, guidance changes, sentiment trends) to let learners track whether management earns or loses credibility over several quarters.[6][1][5][3]

- Sector and macro pattern recognition
  - Aggregate theme frequencies and sentiment by sector/period and ask learners what macro story they infer from calls in a given quarter.[8][1][5][3]

- Structured note‑taking training
  - Provide an interactive notepad seeded with extracted metrics, themes, and risks, and ask learners to organize them into a standard template (thesis, key drivers, risks, questions).[1][2][3]

To give you more concrete advice, it would help to know: what is the primary outcome you want learners to achieve (e.g., writing better post‑call notes, building models, or improving qualitative judgment about management)?

Sources
[1] GitHub - theouterlimitz/Earnings-Call-NLP-Analysis: Using NLP and Transformer models to analyze corporate earnings call transcripts for sentiment and key insights. https://github.com/theouterlimitz/Earnings-Call-NLP-Analysis
[2] GitHub - korkridake/MSDS-DTSA-5714-EarningsCall: Earning Call Analytics is a solution that helps you extract insights from earnings calls transcripts. It saves you time and errors in analyzing these documents and helps you invest wisely in the stock market 📈 https://github.com/korkridake/msds-dtsa-5714-earningscall
[3] Earnings Call Transcript Database and Analysis with NLTK in Python https://github.com/Tingting0618/Earnings_Call_Transcript_Database_Analysis_NLTK
[4] NLP-Sentiment-Analysis-of-Earnings-Call-Transcripts/README.md at main · amberwalker-ds/NLP-Sentiment-Analysis-of-Earnings-Call-Transcripts https://github.com/amberwalker-ds/NLP-Sentiment-Analysis-of-Earnings-Call-Transcripts/blob/main/README.md
[5] GitHub - lcsrodriguez/earnings: Equity earnings Python package (confirmed calendar, news articles, earnings transcripts, ...) https://github.com/lcsrodriguez/earnings
[6] Earnings Call Themes &... https://fintool.com/app/research/companies/MAYS/earnings/Q3%202025
[7] Earnings Lens - Earnigs call transcripts with AI and API https://www.earningslens.com
[8] Earnings Call Analyzer | AI-Powered Investment Intelligence https://www.earningscallanalyzer.com
[9] How to do Sentiment Analysis of Earnings Call Transcript using TextBlob & FMP API ✅ https://www.youtube.com/watch?v=RkUtuHPTMq0
[10] [PDF] Examining the Teacher Pipeline: Will They Stay or Will They Go? https://files.eric.ed.gov/fulltext/EJ1225311.pdf
[11] CME Group Inc. (CME) Q4 2025 Earnings Call Transcript https://seekingalpha.com/article/4865794-cme-group-inc-cme-q4-2025-earnings-call-transcript
[12] Integrated Genomic Selection for Accelerating Breeding Programs of ... https://pmc.ncbi.nlm.nih.gov/articles/PMC10380062/
[13] GitHub - carstonhernke/scrape-earnings-transcripts: A simple python script for scraping earnings transcripts from Seeking Alpha https://github.com/carstonhernke/scrape-earnings-transcripts
[14] EXTREME NETWORKS INC https://www.stockinsights.ai/us/EXTR/earnings-transcript/fy25-q1-eaa0
[15] Datasette of earning call transcripts from the Motley Fool - GitHub https://github.com/jeremiak/motley-fool-earning-transcripts
