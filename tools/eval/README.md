# Prompt Evaluation Harness

This directory contains the tools for measuring whether a prompt change is an improvement before it reaches production.

## What this harness is

The ingestion pipeline depends on LLM prompts for three extraction phases (Tier 1, 2, 3). Prompt changes are the primary lever for improving analysis quality. Without a structured evaluation process, it is impossible to know whether a change made things better, worse, or had no effect.

This harness provides:
- A CLI runner that executes production and candidate prompts against real transcript data
- Scorers that measure quality differences objectively
- A dataset of labeled examples to score against
- A promotion workflow that updates `prompts.py` when a candidate wins

## How to run a comparison

First, add a candidate variant to `ingestion/prompts_candidates.py` following the naming convention in the module docstring. Then:

```bash
# Compare production vs a Tier 1 candidate on 10 MSFT chunks
python tools/prompt_tuner.py \
  --phase tier1 \
  --ticker MSFT \
  --variant TIER_1_v2_few_shot_examples

# Run on more chunks, or filter to a specific quarter
python tools/prompt_tuner.py \
  --phase tier1 \
  --ticker AAPL \
  --variant TIER_1_v2_few_shot_examples \
  --chunks 20 \
  --quarter 2025-Q4
```

The tuner prints a side-by-side comparison for each chunk and a metrics summary at the end. Raw results are saved to `tools/eval/results/` for offline review.

For Tier 2, a `--judge-model` flag controls which Claude model acts as the quality judge (default: `claude-haiku-4-5-20251001`):

```bash
python tools/prompt_tuner.py \
  --phase tier2 \
  --ticker MSFT \
  --variant TIER_2_v1_verbatim_quotes \
  --judge-model claude-haiku-4-5-20251001
```

## How to label examples for dataset.json

`tools/eval/dataset.json` is the ground-truth file for Tier 1 and Tier 2 scoring. It is committed to the repo and versioned with Git.

To add a new labeled chunk:

1. Find a representative chunk in the database. Use the Supabase SQL Editor to query `transcript_chunks JOIN calls ON call_id = calls.id`.
2. Copy the `chunk_id` (UUID) and a 300-character preview of `chunk_text`.
3. Add a labeled entry to the appropriate tier array in `dataset.json`:

```json
{
  "chunk_id": "<uuid from DB>",
  "ticker": "MSFT",
  "chunk_text_preview": "<first 300 chars>",
  "tier1_labels": {
    "good_terms": ["Copilot stack", "Azure Arc", "intelligent cloud"],
    "bad_terms": ["pleased to report", "on a year-over-year basis"],
    "expected_score": 8
  }
}
```

**Labeling criteria for Tier 1:**
- `good_terms`: genuine domain jargon or company-specific language a learner should understand
- `bad_terms`: generic filler phrases that the prompt should NOT surface as terms
- `expected_score`: honest 1–10 assessment of how educationally valuable this chunk is

The dataset should cover high (8–10), medium (4–7), and low (1–3) scoring chunks across at least 3 tickers.

For Tier 2, add `evasion_verbatim_expected: true/false` to indicate whether evasion items in this chunk should quote verbatim:

```json
{
  "chunk_id": "<uuid>",
  "ticker": "MSFT",
  "chunk_text_preview": "...",
  "tier2_labels": {
    "evasion_verbatim_expected": true
  }
}
```

## Promotion workflow

When a candidate outperforms production on the labeled dataset, the tuner walks you through promotion:

1. The tuner prints a metrics comparison table (production vs. candidate).
2. If the candidate wins, it prompts `Promote candidate to production? [y/N]`.
3. Confirming `y` does three things:
   - Replaces the production constant in `ingestion/prompts.py` with the candidate text
   - Removes the candidate constant from `ingestion/prompts_candidates.py`
   - Prints a suggested Git commit message

4. Review the diff, then commit manually:

```bash
git diff ingestion/prompts.py ingestion/prompts_candidates.py
git add ingestion/prompts.py ingestion/prompts_candidates.py
git commit -m "Promote TIER_1_v2_few_shot: +13% term precision on 18-chunk sample"
```

The commit message IS the version record. No external database, no version fields in filenames.

See `docs/prompt-versioning.md` for the full conventions.
