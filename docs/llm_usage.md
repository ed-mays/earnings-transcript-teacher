# LLM Usage in Earnings Transcript Teacher

This document outlines the Large Language Models (LLMs) used within the application, their specific models, and their roles in the analysis and learning pipeline.

---

## 1. Anthropic (Claude)

Anthropic's Claude models power the "Agentic Ingestion Pipeline," performing deep structured extraction and synthesis of earnings transcripts.

*   **Models Used:**
    *   **`claude-haiku-4-5-20251001`**: Used for fast, cost-effective processing of "Tier 1" tasks (glossary extraction, core concept identification, and complexity scoring) and "Tier 3" synthesis (global strategic summary). Also serves as a fallback for Q&A section detection when deterministic methods fail.
    *   **`claude-sonnet-4-5`**: Used for "Tier 2" tasks that require deeper reasoning, such as identifying key takeaways, analyzing executive evasion, and flagging common investor misconceptions.
*   **Purpose:** Structured data extraction, pedagogical analysis, and strategic synthesis.
*   **Implementation:** See `services/llm.py` (`AgenticExtractor`) and `ingestion/pipeline.py`.
*   **Prompt architecture:** The five prompt constants driving Claude-powered ingestion (`TIER_1_SYSTEM_PROMPT`, `TIER_2_SYSTEM_PROMPT`, `TIER_3_SYNTHESIS_PROMPT`, `HAIKU_NLP_SYNTHESIS_PROMPT`, `QA_DETECTION_SYSTEM_PROMPT`) are defined in `ingestion/prompts.py`. See the module docstring there for tier responsibilities and which model runs each pass.

---

## 2. Perplexity AI

Perplexity AI's online models are used for interactive elements and real-time grounding of financial concepts.

*   **Model Used:** **`sonar-pro`**
*   **Purpose:** 
    *   **Interactive Chat**: Powers the Streamlit chat interface for "General Q&A" and the "Feynman Loop" tutor.
    *   **On-Demand Definitions**: Generates concise, company-grounded definitions for financial and industry-specific jargon found in the transcript.
    *   **On-Demand Explanations**: Provides contextual explanations of terms using RAG (Retrieval Augmented Generation) based on specific transcript snippets.
*   **Implementation:** See `services/llm.py` (`stream_chat`) and `api/routes/chat.py`.

---

## 3. Voyage AI

Voyage AI provides specialized vector embeddings to enable semantic search and Retrieval Augmented Generation (RAG).

*   **Model Used:** **`voyage-finance-2`**
*   **Purpose:** 
    *   **Financial Embeddings**: Generates high-quality vector representations of transcript "spans" (speaker turns). These embeddings allow the system to find the most relevant context in the transcript when answering user questions or explaining terms.
*   **Implementation:** See `nlp/embedder.py` and `services/orchestrator.py`.

---

## Summary Table

| Provider | Model | Primary Use Case |
| :--- | :--- | :--- |
| **Anthropic** | `claude-haiku-4.5` | Fast extraction, Q&A detection, global synthesis. |
| **Anthropic** | `claude-sonnet-4.5` | Deep reasoning, evasion analysis, misconceptions. |
| **Perplexity** | `sonar-pro` | Interactive chat, grounded definitions, RAG explanations. |
| **Voyage AI** | `voyage-finance-2` | Specialized financial embeddings for semantic search. |
