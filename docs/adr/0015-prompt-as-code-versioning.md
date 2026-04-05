# Prompt-as-Code Versioning

**Status:** Accepted
**Date:** 2026-03-27

## Context

The three-tier LLM pipeline (ADR 0011) uses multiple prompt constants that directly control analysis quality. These prompts are iterated frequently as the pipeline is tuned. The project needed a strategy for versioning prompts — tracking what changed, when, and why — while supporting safe experimentation without affecting production analysis.

## Decision

Version prompts as Python source files in the repository:

- **`ingestion/prompts.py`** — All production prompt constants, with inline documentation of tier architecture and usage
- **`ingestion/prompts_candidates.py`** — Experimental prompt variants that are never imported by the pipeline

Git history is the version record — no database, no version numbers in filenames, no external prompt management platform. Prompts are code-reviewed in PRs, diffs are visible in git, and there is no runtime dependency on an external prompt store.

The promotion workflow (documented in `docs/prompt-versioning.md`) requires running `tools/prompt_tuner.py` to compare candidate vs. production prompts on an evaluation dataset before merging changes.

## Alternatives considered

1. **Database-stored prompts (runtime-editable)** — Storing prompts in a database table with version numbers, allowing runtime changes without deploys. Rejected because: (a) runtime prompt changes bypass code review, making it impossible to audit what prompt produced a given analysis result, (b) rollback requires database operations rather than `git revert`, and (c) the pipeline processes transcripts in batch (not real-time), so deploy-time updates are fast enough.

2. **Prompt management platform (LangSmith, Braintrust, PromptLayer)** — Using a dedicated prompt versioning and evaluation service. Rejected because: (a) adds an external service dependency for a workflow that git handles natively, (b) the evaluation loop is simple enough (compare JSON output quality) that a custom script suffices, and (c) platform lock-in for prompt storage is an unnecessary risk when the prompts are just strings in Python files.

3. **Version-numbered files (prompts_v1.py, prompts_v2.py)** — Creating a new file for each prompt version. Rejected because: (a) git history already provides the version timeline, (b) accumulating version files creates confusion about which is active, and (c) the single-file approach makes it obvious what's in production (it's in `prompts.py`).

4. **YAML/JSON prompt files with a loader** — Storing prompts in structured data files rather than Python code. Rejected because: (a) Python string constants support f-string interpolation and multi-line formatting that YAML handles awkwardly, (b) IDE support (syntax highlighting, linting) is better for Python files, and (c) the prompts contain documentation comments that are more natural in Python than YAML.

## Consequences

**Easier:**
- Every prompt change is code-reviewed in a PR with a visible diff
- `git log ingestion/prompts.py` shows the complete prompt evolution timeline
- `git revert` rolls back a bad prompt change instantly
- The candidate file (`prompts_candidates.py`) provides a safe experimentation space without import-guarding or feature flags
- The evaluation script (`tools/prompt_tuner.py`) runs locally with no external dependencies

**Harder:**
- Prompt changes require a deploy (no hot-swapping in production)
- No built-in A/B testing — the evaluation harness (ADR 0027) compares offline, not on live traffic
- Prompt metadata (who authored it, what it was tested on) is only in git commit messages — no structured metadata
- Large prompt constants in Python files can make the file hard to navigate (mitigated by inline documentation)
