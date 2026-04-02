# Code Coverage Improvement Plan v1

## Context

There is upcoming work to add a code coverage gate to the CI pipeline with an 80% threshold (#175). Current measured coverage is **76%** (4,425 active statements, 880 uncovered — excluding `tools/prompt_tuner.py` which is an interactive dev tool, not production code).

Phase 1 (removing deprecated code, #303) is complete — merged in PR #304. This eliminated ~2,700 lines of dead code and raised measured coverage from 57% to 76%.

With `tools/prompt_tuner.py` excluded via `pyproject.toml` omit, coverage is already **80.1%** — the gate passes immediately. However, the modules below still have meaningful gaps worth closing for code health.

---

## ~~Phase 1: Remove deprecated code~~ DONE

Completed in PR #304 (merged 2026-04-02). All deprecated CLI, Streamlit UI, and legacy entry points removed.

---

## Phase 2: Close remaining gaps

### Step 1: Add the coverage gate

Add `tools/prompt_tuner.py` to `[tool.coverage.run]` omit in `pyproject.toml` and raise `--cov-fail-under` from 50 → 80 in `scripts/run_tests.sh`. This passes immediately at 80.1%.

### Step 2: Improve coverage for code health (optional, prioritized)

Prioritized by uncovered lines. Current baseline: 76% measured, 80.1% excluding prompt_tuner.

#### Tier 1 — Largest gaps

| Module | Current | Uncovered | Notes |
|--------|---------|-----------|-------|
| `db/repositories/analysis.py` | 22% | 268 lines | Largest single gap. Many methods untested. Add unit tests with mocked cursor. |
| `ingestion/pipeline.py` | 42% | 149 lines | Critical path for data ingestion. Lines 191-349 entirely uncovered. |
| `services/llm.py` | 69% | 55 lines | Has integration tests but gaps in unit coverage. |

#### Tier 2 — Medium gaps

| Module | Current | Uncovered | Notes |
|--------|---------|-----------|-------|
| `parsing/sections.py` | 72% | 61 lines | Already partially tested, gaps in edge cases |
| `db/persistence.py` | 35% | 44 lines | Thin wrapper functions — easy to unit test |
| `db/repositories/competitors.py` | 23% | 40 lines | No tests at all. Straightforward repo logic. |
| `db/repositories/progress.py` | 22% | 29 lines | Similar pattern to other repos |
| `db/repositories/analytics.py` | 26% | 28 lines | Similar pattern to other repos |
| `api/routes/admin.py` | 76% | 26 lines | Several error paths untested |
| `db/repositories/learning.py` | 71% | 25 lines | Already well-tested, fill remaining gaps |

#### Tier 3 — Small gaps

| Module | Current | Uncovered | Notes |
|--------|---------|-----------|-------|
| `api/routes/calls.py` | 92% | 18 lines | Near-complete, a few edge cases |
| `db/repositories/schema.py` | 48% | 13 lines | Small file |
| `services/orchestrator.py` | 88% | 13 lines | Near-complete |
| `db/repositories/embeddings.py` | 61% | 12 lines | Small file |
| `core/models.py` | 91% | 12 lines | Mostly dataclass fields |
| `parsing/financial_terms.py` | 68% | 11 lines | Small file |
| `api/routes/chat.py` | 89% | 10 lines | Near-complete |

---

## Implementation approach

### For repository classes (`db/repositories/*.py`)

These all follow the same pattern: methods that take a cursor, execute SQL, return dataclasses. Test with a mocked cursor that returns canned rows. Follow the existing pattern in `tests/unit/db/test_learning_repository.py`.

### For `ingestion/pipeline.py`

The uncovered code (lines 191-349) contains the LLM-calling ingestion logic. Test with mocked LLM responses, following the pattern in `tests/services/test_llm.py`.

### For service modules

Mock external dependencies (DB, APIs) and test business logic. Follow existing patterns in `tests/unit/services/`.

---

## Verification

1. After adding the omit + raising the gate, run `pytest --cov=. --cov-report=term-missing -q` and confirm >= 80%
2. After each batch of new tests, confirm coverage is trending up
3. Confirm CI green on PR branch

---

## Execution order

1. **Add coverage gate** — omit `tools/prompt_tuner.py`, raise `--cov-fail-under` to 80 (one PR, should pass immediately)
2. **Phase 2 tests** — grouped by module area (one or more follow-up PRs, optional)
