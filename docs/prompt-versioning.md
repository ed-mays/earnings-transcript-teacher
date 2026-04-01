# Prompt Versioning

This document describes the conventions for managing and evolving the LLM prompts in the ingestion pipeline.

## Two-file convention

Production prompts live in `ingestion/prompts.py` as named module-level constants. This is the only file imported by the pipeline.

Candidate prompts live in `ingestion/prompts_candidates.py`. This file is **never imported by the pipeline** — it is only used by `tools/prompt_tuner.py` during evaluation.

```
ingestion/
  prompts.py             ← production (pipeline imports this)
  prompts_candidates.py  ← experiment space (tuner imports this, pipeline does not)
```

## Git is the version store

There is no database, no version number in filenames, and no `v1`/`v2` suffix on production constants. The version record is the Git commit history of `ingestion/prompts.py`.

When a candidate wins an evaluation, it is promoted by replacing the production constant in `prompts.py` in a single, descriptive Git commit. The commit message is the version record.

## Commit message format for promotions

```
Promote <CONSTANT_NAME>: <metric delta> on <N>-chunk sample
```

Examples:

```
Promote TIER_1_v2_few_shot: +13% term precision on 20-chunk sample
Promote TIER_2_v1_verbatim: +0.18 avg specificity, +9pp verbatim rate on 12-chunk sample
```

The `<metric delta>` should describe the most meaningful improvement. For Tier 1, that is usually precision. For Tier 2, specificity or verbatim rate. Use the tuner's suggested commit message as a starting point.

## Naming convention for candidate variants

```
<PHASE>_v<N>_<short_hypothesis>
```

Examples: `TIER_1_v2_few_shot_examples`, `TIER_2_v1_verbatim_quotes`, `TIER_1_v3_no_generic_filter`

The `<N>` is a local counter — it only needs to be unique within `prompts_candidates.py` at any point in time, not globally unique across history.

## Rules

1. **Only promote when the tuner shows improvement** on the labeled dataset (`tools/eval/dataset.json`). Do not promote based on qualitative impressions alone.

2. **Delete losing variants immediately.** When a candidate does not win, remove it from `prompts_candidates.py`. Dead experiments must not accumulate.

3. **One promotion per commit.** Each promotion is its own Git commit with a descriptive message. Do not bundle multiple promotions.

4. **Do not modify `prompts.py` directly for experiments.** All experimental text goes in `prompts_candidates.py` first. If you want to test the current production prompt as a baseline, it is already in `prompts.py` — the tuner runs it automatically.

5. **Keep the dataset current.** When you add a new ticker to the pipeline, add labeled chunks for that ticker to `tools/eval/dataset.json` before tuning prompts against it.

## Running an evaluation

See `tools/eval/README.md` for step-by-step instructions on running the tuner, labeling examples, and completing the promotion flow.
