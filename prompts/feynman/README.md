# Feynman Prompt Library

This directory contains the system prompts for the Feynman learning loop. Each file is a self-contained prompt that shapes the tutor's behaviour for one stage of the interaction.

## Stage mapping

| File | Stage | Role |
|------|-------|------|
| `00_beginner_jargon.md` | Beginner variant | Jargon explanation tuned for novice learners |
| `00_beginner_takeaways.md` | Beginner variant | Key takeaways framing tuned for novice learners |
| `00_general_qa.md` | General Q&A | Free-form question answering outside the Feynman loop |
| `01_initial_explanation.md` | Stage 1 | Tutor introduces the concept using analogies grounded in the transcript |
| `02_gap_analysis.md` | Stage 2 | Tutor identifies gaps in the student's understanding and probes deeper |
| `03_guided_refinement.md` | Stage 3 | Tutor provides targeted feedback to help the student refine their explanation |
| `04_understanding_test.md` | Stage 4 | Tutor tests comprehension with knowledge checks |
| `05_teaching_note.md` | Stage 5 | Student produces a teaching note as a summative assessment |
| `synthesis.md` | Post-loop | Synthesises learning across all completed stages |

## Loading mechanism (FastAPI path)

Prompts are loaded at request time by `api/routes/chat.py`:

```python
_STAGE_PROMPTS: dict[int, str] = {
    1: "01_initial_explanation.md",
    2: "02_gap_analysis.md",
    3: "03_guided_refinement.md",
    4: "04_understanding_test.md",
    5: "05_teaching_note.md",
}

def _load_prompt(stage: int) -> str:
    filename = _STAGE_PROMPTS.get(stage, "01_initial_explanation.md")
    return (_PROMPTS_DIR / filename).read_text(encoding="utf-8")
```

The `_PROMPTS_DIR` resolves to this directory (`prompts/feynman/`) relative to the repo root.

**Known gap**: `00_beginner_jargon.md`, `00_beginner_takeaways.md`, `00_general_qa.md`, and `synthesis.md` exist on disk but are not wired into `_STAGE_PROMPTS`. They were used by the Streamlit-era loader and are retained for future integration.

## Deprecated path

The Streamlit UI (`ui/feynman.py`) had an equivalent loader (`_load_prompt_file()`, `_FEYNMAN_PROMPT_FILES`). That path is no longer active — `ui/feynman.py` is part of the deprecated Streamlit stack.

## Versioning

Prompt files carry no inline version markers. Changes are tracked via git history. When making a substantive change to a prompt, include a clear commit message explaining the intent.

## Editing guidance

Files are read from disk at request time (not cached at startup), so changes take effect immediately at the next API request without a server restart.
