You already capture structure, people, topics, and “central” statements. The next useful layer is _how_ things are said: intent, certainty, quality of answers, and explicit forward‑looking content.[1][2][3]

Below is a menu of additional signals that would give your Feynman‑style LLM maximal context.

## 1. Management communication signals

These are sentence/turn‑level tags on executive speech, especially in Q&A.

- Forward‑looking vs historical
  - Tag sentences as historical (reporting past KPIs) vs forward‑looking (plans, projections, assumptions).[4][5][6]
  - Add subtype labels: guidance (numeric ranges), strategic plans, qualitative outlook.

- Hedging and uncertainty language
  - Detect hedges/softeners (“we believe”, “too early to tell”, “we’re cautiously optimistic”) and uncertainty markers.[5][6]
  - You can aggregate a “hedge density” per answer, topic, or quarter.

- Commitment strength
  - Classify statements by commitment: strong (“we will”), moderate (“we expect”), weak (“we hope”, “we’ll see”).[6][5]
  - This lets the LLM reason about management conviction when explaining the call.

- Evasiveness in Q&A
  - Label answers as direct, partially evasive, or evasive, based on semantic alignment between question and answer and cues like verbosity, topic shifts, and hedging.[3][7][8][9]
  - Recent work shows evasiveness is distinct from sentiment and veracity, so it’s a valuable separate channel.[9][3]

## 2. Content and information‑density signals

These help the LLM gauge “how much substance” is in a passage.

- Metric and specificity tagging
  - Detect explicit numbers (growth rates, margins, dollar amounts) and qualifiers (exact timing, cohorts, geographies).
  - For each answer/remark, compute a simple specificity score: count of metrics, concrete nouns, and time references.

- Risk and driver taxonomy
  - Classify spans into drivers like demand, pricing, costs, margins, capex, competition, regulation, labor, FX, etc., similar to how commercial NLP systems score key drivers.[2][10]
  - Also tag explicit risks vs opportunities and mitigation actions.

- Novelty vs boilerplate
  - Identify sentences that are highly similar to prior calls (e.g., safe‑harbor and standard intros) vs genuinely new content.[10][1]
  - A novelty flag lets the LLM focus explanations on what changed this quarter.

## 3. Q&A interaction quality

You already have structured question–answer threads; you can enrich them.

- Question type and quality
  - Classify analyst questions as: housekeeping, clarification, drill‑down, model‑building, challenge/critical, or speculative.[2][10]
  - This lets your tutor ask, “Was this a good modeling question or just housekeeping?”

- Answer responsiveness
  - Tag whether the answer: directly addresses the core question, partially addresses it, or pivots away, leveraging the evasiveness taxonomy.[7][8][3][9]
  - You can annotate if follow‑ups were needed, or if the analyst accepted an evasive answer.

- Turn‑level sentiment and stance
  - Apply finance‑tuned sentiment (e.g., FinBERT‑style) for each answer and question to capture optimism/pessimism by topic and by speaker.[11][12]
  - This supports explanations like “management is positive on demand but cautious on margins.”

## 4. Cross‑call and identity features

These make the LLM’s reasoning more longitudinal and company‑aware.

- Per‑speaker history
  - Maintain speaker‑level profiles across calls: typical tone, hedge density, evasiveness rate, and topic focus.[13][10]
  - The tutor can then say, “Relative to their usual style, the CFO sounds more cautious here.”

- Theme and sentiment trajectories
  - Track topic prevalence and sentiment over time for the same company (e.g., supply chain mentions and tone across 6 quarters).[1][10][13]
  - These trajectories are ideal context for Feynman‑style prompts about “what changed and why.”

- Market‑response hooks (if you join with price data)
  - Even without modeling, annotate each call with post‑earnings return/volatility buckets so the LLM can ground explanations in “how the market reacted.”[14][15][10][11]

## 5. How this helps your Feynman LLM

With these extra features, your tutor can:

- Localize explanations
  - Point to specific high‑hedge, forward‑looking, or evasive answers when teaching “how to read between the lines.”

- Compare styles and quarters
  - Use commitment strength, risk mentions, and topic sentiment trajectories to explain changes in tone or strategy across time.[10][13][1]

- Run richer “what to notice” drills
  - Ask the learner to explain why a specific high‑evasion answer, high‑novelty risk disclosure, or strongly committed guidance statement matters.

If you had to prioritize just 2–3 new layers _today_ for your learning tool, I’d start with: (1) forward‑looking vs historical tagging, (2) hedging/commitment strength, and (3) Q&A evasiveness labels. These three alone give your LLM a much richer handle on “how honest, clear, and confident is this management team?”[8][3][5][7][9]

Are you primarily optimizing for helping users judge management quality, or for helping them build a better financial model off the call?

Sources
[1] Extracting key insights from earnings call transcript via ... https://www.sciencedirect.com/science/article/abs/pii/S0306457324003571
[2] 7 Use Cases for NLP in Large Hedge Funds https://symphony.com/insights/blog/7-use-cases-for-nlp-in-large-hedge-funds/
[3] Evasive Answers in Financial Q\&A: Earnings Calls vs. FOMC Press Conferences https://neurips.cc/virtual/2025/loc/san-diego/132563
[4] Forward-Looking Information in Financial Disclosures — Necessary ... https://blogs.cfainstitute.org/marketintegrity/2014/11/17/forward-looking-information-in-financial-disclosures-necessary-to-disclosure-effectiveness/
[5] Forward-Looking Information: A Necessary Consideration in the SEC’s Review on Disclosure Effectiveness: Investor Perspectives https://rpc.cfainstitute.org/sites/default/files/-/media/documents/article/position-paper/forward-looking-information-a-necessary-consideration-in-sec-review.pdf
[6] Forward-Looking Statements: Safe Harbors Compliance https://www.venable.com/insights/publications/2024/09/forward-looking-statements-safe-harbors-comp
[7] EvasionBench: A Large-Scale Benchmark for Detecting Managerial Evasion in Earnings Call Q&A https://arxiv.org/abs/2601.09142
[8] EvasionBench: Detecting Evasive Answers in Financial Q&A via ... https://huggingface.co/papers/2601.09142
[9] Evasive Answers in Financial Q\&A: Earnings Calls vs. FOMC Press... https://openreview.net/forum?id=A1FDpZ0Kdg
[10] Financial NLP Solutions | S&P Global Textual Data & AI Tools https://www.spglobal.com/market-intelligence/en/solutions/natural-language-processing
[11] Advanced Deep Learning Techniques for Analyzing Earnings Call ... https://arxiv.org/abs/2503.01886
[12] Advanced Deep Learning Techniques for Analyzing Earnings Call ... https://arxiv.org/html/2503.01886v1
[13] Same Company, Same Signal: The Role of Identity in Earnings Call ... https://arxiv.org/html/2412.18029v1
[14] Earnings Call Scripts Generation With Large Language Models ... https://onlinelibrary.wiley.com/doi/full/10.1002/ail2.110
[15] [PDF] Forecasting Earnings Surprises from Conference Call ... https://aclanthology.org/2023.findings-acl.520.pdf
