# Prompt Evaluation Tooling

**Status:** Accepted
**Date:** 2026-03-27

> **Note:** This decision has **Medium confidence** in rationale reconstruction. The evaluation tooling exists in the codebase (`tools/prompt_tuner.py`, `tools/eval/dataset.json`), and the promotion workflow is documented in `docs/prompt-versioning.md`, but the depth of adoption — how consistently the evaluation harness is used before prompt changes — is unclear from the available evidence. The Alternatives Considered section reflects reasonable inferences about the decision-making process.

## Context

The three-tier LLM pipeline (ADR 0011) and prompt-as-code versioning (ADR 0015) create a need for objective prompt quality measurement. Without evaluation tooling, prompt changes are assessed subjectively ("does this output look better?"), which risks regression — a prompt that improves one transcript type may degrade another. The project needed a way to compare prompt versions quantitatively.

## Decision

Implement a local evaluation harness consisting of:

- **`tools/prompt_tuner.py`** — A script that runs side-by-side comparisons of production (`ingestion/prompts.py`) vs. candidate (`ingestion/prompts_candidates.py`) prompts on the same input data
- **`tools/eval/dataset.json`** — A golden evaluation dataset of representative transcript chunks with expected output characteristics

The evaluation loop is: edit candidate prompts → run `prompt_tuner.py` → compare outputs → promote to production if metrics improve.

The key driver was keeping the evaluation loop local and reproducible — no external service dependency, results are visible in the terminal, and the dataset is version-controlled alongside the prompts.

## Alternatives considered

1. **LangSmith** — Anthropic/LangChain's prompt evaluation and tracing platform. Offers structured evaluation runs, comparison dashboards, and dataset management. Not chosen because: (a) the evaluation needs are simple enough (compare JSON output quality on ~20 test cases) that a custom script suffices, (b) LangSmith adds an external service dependency, and (c) the dataset is small enough to run locally in seconds.

2. **Braintrust** — A prompt evaluation platform with scoring and regression detection. Similar trade-offs to LangSmith — powerful features that exceed the current evaluation complexity. Not chosen to avoid external dependencies during the rapid rewrite phase. May be worth revisiting as the evaluation dataset grows.

3. **Manual A/B testing on live transcripts** — Running both prompt versions on real ingestion requests and comparing outputs manually. Rejected because: (a) live testing is slow (requires waiting for real transcript uploads), (b) there's no controlled comparison (different transcripts have different difficulty), and (c) subjective quality assessment is inconsistent.

4. **No evaluation tooling (rely on code review)** — Assessing prompt changes purely through code review of the prompt text. Rejected because prompt changes are notoriously hard to evaluate from the text alone — small wording changes can produce large output differences that are only visible when running the prompt against real data.

## Consequences

**Easier:**
- Prompt changes can be evaluated quantitatively before merging
- The evaluation dataset is version-controlled, so regression tests run against the same data over time
- No external service to configure, authenticate, or pay for
- Evaluation runs locally in seconds, enabling rapid iteration

**Harder:**
- The golden dataset must be manually curated and maintained — its quality bounds the evaluation's usefulness
- No visualization or dashboarding — results are terminal output only
- The evaluation harness doesn't run automatically in CI (it's a manual pre-merge step)
- As the prompt complexity grows, the custom script may need significant evolution to handle multi-tier evaluation
