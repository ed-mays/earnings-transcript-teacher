## **MVP: “Single-call Feynman tutor”**

These are the **must-haves** that make the product useful to you on day one.intersog+2

## **Core ingestion and structure**

- ✅ Shell script to download transcript by ticker from API Ninjas (`download_transcript.sh`)
- ✅ Python console UI to start (`main.py`, accepts ticker symbol parameter)
- ✅ Parsing into: **Prepared Remarks** vs. **Q&A** sections (`sections.py`)
- ✅ **Speaker identification**: enriched profiles with role (executive/analyst/operator), title, and firm (`sections.py`)
- ✅ **Q&A exchange extraction**: structured question-answer threads grouped by analyst (`sections.py`)
- ✅ **Keyword extraction** (TF-IDF): top 20 salient terms and bigrams (`keywords.py`)
- ✅ **Theme extraction** (NMF): 5 topic clusters of related terms (`themes.py`)
- ✅ **Key takeaways** (TextRank): top 10 most central statements with speaker attribution (`takeaways.py`)

- Minimal metadata: company name, ticker, period entered or confirmed by the user.

## **Concept selection (Feynman step 1\)**

- Automatic extraction of 5–15 candidate “concepts” from the call (e.g., revenue guidance, margin drivers, FX headwinds).audit-ally+3

- Simple UI to pick a small subset (e.g., 3–5 concepts) for this learning session.\[[aliabdaal](https://aliabdaal.com/studying/the-feynman-technique/)\]​

## **Explanation, critique, and refinement**

- For each selected concept:
  - Input box: “Explain this as if to a smart 12‑year‑old.”\[[aliabdaal](https://aliabdaal.com/studying/the-feynman-technique/)\]​

  - AI critique that:
    - Points out missing pieces relative to the transcript.

    - Highlights jargon and suggests simpler wording.

    - Asks 2–3 follow‑up questions to expose gaps.feynmantechnique+1

  - Second‑pass explanation box, with side‑by‑side before/after comparison.

## **Lightweight testing**

- Auto-generate a small set (3–5) of concept questions per concept (mix of conceptual \+ simple numeric, nothing fancy).researchly+2

- Immediate feedback and a crude “confidence” indicator for each concept (e.g., Low/Medium/High) based on answers.

## **Minimal analyst Q\&A view**

- Q\&A section listing all questions and answers.

- Tag each question with a **theme** (e.g., demand, competition, guidance) using AI; show a count per theme.dakota+2

- Simple “What analysts cared about most” summary (top 3 themes).\[[dakota](https://www.dakota.com/resources/blog/earnings-call-intelligence-for-investors-dakotas-ai-powered-transcript-sentiment-tool)\]​

## **Learning artifacts**

- Per call:
  - One “learning summary” page containing:
    - Your final explanations per concept.

    - AI bullet summary of key call takeaways (1–2 short sections).alpha-sense+2

    - List of unanswered questions / gaps.

- Export this page as Markdown / copy-to-clipboard for notes.

## **Product basics for an MVP**

- Auth (even just email+magic link or GitHub) and a basic dashboard showing:
  - Recent calls analyzed.

  - Concepts touched per call.groovyweb+1

- A simple feedback mechanism (“What confused you?” “What didn’t work?”).complice+2

This MVP gives you: one-earnings-call-at-a-time deep learning with Feynman loops, critique, and a tangible artifact per call. It’s enough to validate UX, AI prompting, and whether the approach actually improves your understanding.glasp+3

---
