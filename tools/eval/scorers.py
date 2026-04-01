"""
Evaluation scorers for the prompt tuning harness.

Provides:
  score_tier1(outputs, labels_list)  — precision, bad_term_rate, score_mae for Tier 1
  score_tier2(output, chunk_text)    — takeaway specificity, verbatim rate, completeness for Tier 2
  validate_output_schema(outputs, phase) — structural conformance check for any phase
"""

import logging
import re
import string
from typing import Any

import anthropic

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Tier 1 scorer
# ---------------------------------------------------------------------------

def score_tier1(
    outputs: list[dict[str, Any]],
    labels_list: list[dict[str, Any]],
) -> dict[str, Any]:
    """Score Tier 1 extraction outputs against a labeled dataset.

    Args:
        outputs:     List of Tier 1 LLM output dicts (one per chunk).
        labels_list: List of label dicts matching outputs in order.
                     Each label dict has keys: good_terms, bad_terms, expected_score.

    Returns a dict with:
        term_precision  — fraction of returned terms that are "good" terms
        bad_term_rate   — fraction of returned terms that are "bad" terms
        score_mae       — mean absolute error between returned score and expected score
        n_chunks        — number of chunks scored
    """
    if not outputs or not labels_list:
        return {"term_precision": 0.0, "bad_term_rate": 0.0, "score_mae": 0.0, "n_chunks": 0}

    precision_sum = 0.0
    bad_rate_sum = 0.0
    mae_sum = 0.0
    n = 0

    for output, labels in zip(outputs, labels_list):
        if "error" in output:
            continue  # skip errored chunks

        returned_terms: list[str] = [
            t.lower().strip() for t in output.get("extracted_terms", []) if t
        ]
        good_terms = {t.lower().strip() for t in labels.get("good_terms", [])}
        bad_terms = {t.lower().strip() for t in labels.get("bad_terms", [])}
        expected_score = labels.get("expected_score", 5)
        returned_score = output.get("relevance_score", output.get("tier1_score", 5))

        total = len(returned_terms)
        if total > 0:
            good_count = sum(1 for t in returned_terms if t in good_terms)
            bad_count = sum(1 for t in returned_terms if t in bad_terms)
            precision_sum += good_count / total
            bad_rate_sum += bad_count / total
        else:
            # No terms returned: precision is 0, bad rate is 0
            precision_sum += 0.0
            bad_rate_sum += 0.0

        mae_sum += abs(float(returned_score) - float(expected_score))
        n += 1

    if n == 0:
        return {"term_precision": 0.0, "bad_term_rate": 0.0, "score_mae": 0.0, "n_chunks": 0}

    return {
        "term_precision": round(precision_sum / n, 4),
        "bad_term_rate": round(bad_rate_sum / n, 4),
        "score_mae": round(mae_sum / n, 4),
        "n_chunks": n,
    }


# ---------------------------------------------------------------------------
# Tier 2 scorer
# ---------------------------------------------------------------------------

def _strip_punct(text: str) -> str:
    """Remove punctuation and lower-case for verbatim comparison."""
    return text.translate(str.maketrans("", "", string.punctuation)).lower()


def score_tier2(
    output: dict[str, Any],
    chunk_text: str,
    judge_model: str = "claude-haiku-4-5-20251001",
) -> dict[str, Any]:
    """Score one Tier 2 extraction output.

    Args:
        output:      Tier 2 LLM output dict for a single chunk.
        chunk_text:  The original transcript chunk text.
        judge_model: Claude model to use as the LLM quality judge for takeaways.

    Returns a dict with:
        takeaway_specificity_avg — average 1–5 score from LLM judge across takeaways
        evasion_verbatim_rate    — fraction of evasion items whose quotes appear in chunk_text
        completeness_rate        — fraction of required fields that are present and non-empty
        n_chunks                 — always 1 (scored per-chunk; caller averages across chunks)
        judge_model              — model used for judging
    """
    if "error" in output:
        return {
            "takeaway_specificity_avg": 0.0,
            "evasion_verbatim_rate": 0.0,
            "completeness_rate": 0.0,
            "n_chunks": 1,
            "judge_model": judge_model,
        }

    # --- Metric 1: Takeaway specificity (LLM judge) ---
    takeaways = output.get("takeaways", [])
    specificity_scores = []
    if takeaways:
        try:
            client = anthropic.Anthropic()
            for takeaway in takeaways:
                takeaway_text = (
                    takeaway.get("takeaway", "") if isinstance(takeaway, dict) else str(takeaway)
                )
                if not takeaway_text:
                    continue
                judge_prompt = (
                    "You are evaluating the quality of a financial analysis takeaway.\n"
                    "Score it 1–5 on specificity:\n"
                    "  5 = Specific, grounded in the text, non-obvious, useful to a learner\n"
                    "  3 = Partially specific but could apply to many companies\n"
                    "  1 = Generic filler (\"the company discussed guidance\", \"management was cautious\")\n\n"
                    f"Transcript excerpt:\n{chunk_text[:500]}\n\n"
                    f"Takeaway:\n{takeaway_text}\n\n"
                    "Respond with a single integer 1–5 and nothing else."
                )
                try:
                    message = client.messages.create(
                        model=judge_model,
                        max_tokens=10,
                        messages=[{"role": "user", "content": judge_prompt}],
                    )
                    score_text = message.content[0].text.strip()
                    score = int(re.search(r"[1-5]", score_text).group())
                    specificity_scores.append(score)
                except Exception as e:
                    logger.warning("LLM judge call failed for takeaway: %s", e)
        except Exception as e:
            logger.warning("LLM judge setup failed: %s", e)

    specificity_avg = (
        sum(specificity_scores) / len(specificity_scores) if specificity_scores else 0.0
    )

    # --- Metric 2: Evasion verbatim accuracy ---
    evasion_items = output.get("evasion", [])
    verbatim_count = 0
    chunk_stripped = _strip_punct(chunk_text)
    for item in evasion_items:
        if not isinstance(item, dict):
            continue
        q_text = item.get("question_text", "")
        a_text = item.get("answer_text", "")
        q_match = bool(q_text) and (_strip_punct(q_text) in chunk_stripped)
        a_match = bool(a_text) and (_strip_punct(a_text) in chunk_stripped)
        if q_match and a_match:
            verbatim_count += 1

    verbatim_rate = (
        verbatim_count / len(evasion_items) if evasion_items else 1.0
    )

    # --- Metric 3: Field completeness ---
    required_fields = ["takeaways", "evasion", "misconceptions", "speakers"]
    complete_count = sum(
        1 for f in required_fields
        if output.get(f) is not None and output.get(f) != [] and output.get(f) != ""
    )
    completeness = complete_count / len(required_fields)

    return {
        "takeaway_specificity_avg": round(specificity_avg, 4),
        "evasion_verbatim_rate": round(verbatim_rate, 4),
        "completeness_rate": round(completeness, 4),
        "n_chunks": 1,
        "judge_model": judge_model,
    }


# ---------------------------------------------------------------------------
# Schema validator
# ---------------------------------------------------------------------------

# Phase schemas: maps phase → {field_name: expected_type_or_types}
_TIER1_SCHEMA: dict[str, Any] = {
    "relevance_score": (int, float),
    "extracted_terms": list,
    "chunk_category": str,
}

_TIER2_SCHEMA: dict[str, Any] = {
    "takeaways": list,
    "evasion": list,
    "misconceptions": list,
    "speakers": list,
}
_TIER2_EVASION_FIELDS = ["question_text", "answer_text", "evasion_type"]

_TIER3_SCHEMA: dict[str, Any] = {
    "themes": list,
    "strategic_shifts": list,
    "summary": str,
}

_SCHEMAS = {
    "tier1": _TIER1_SCHEMA,
    "tier2": _TIER2_SCHEMA,
    "tier3": _TIER3_SCHEMA,
}


def validate_output_schema(
    outputs: list[dict[str, Any]],
    phase: str,
) -> dict[str, Any]:
    """Check that a list of LLM outputs conform to the expected schema for the given phase.

    Args:
        outputs: List of output dicts (one per chunk). Each dict may include an "error" key
                 if the LLM call failed — those chunks are skipped.
        phase:   One of "tier1", "tier2", "tier3".

    Returns a dict with:
        schema_pass_rate — fraction of records with zero violations
        violations       — list of {chunk_id, field, violation, prompt} dicts
                           (prompt is "production" or "candidate"; caller must set after the fact)
    """
    schema = _SCHEMAS.get(phase)
    if schema is None:
        return {"schema_pass_rate": 1.0, "violations": []}

    violations: list[dict[str, Any]] = []
    pass_count = 0
    total = 0

    for i, output in enumerate(outputs):
        if "error" in output:
            continue  # skip errored chunks; don't count as violations

        chunk_id = output.get("chunk_id", f"chunk_{i}")
        chunk_violations: list[dict[str, Any]] = []

        for field, expected_type in schema.items():
            value = output.get(field)

            # Missing field
            if value is None:
                chunk_violations.append({
                    "chunk_id": chunk_id,
                    "field": field,
                    "violation": "missing",
                    "prompt": "",
                })
                continue

            # Wrong type
            if not isinstance(value, expected_type):
                chunk_violations.append({
                    "chunk_id": chunk_id,
                    "field": field,
                    "violation": f"expected {expected_type if isinstance(expected_type, type) else [t.__name__ for t in expected_type]}, got {type(value).__name__}",
                    "prompt": "",
                })
                continue

            # Numeric range check for relevance_score
            if field == "relevance_score" and isinstance(value, (int, float)):
                if not (1 <= value <= 10):
                    chunk_violations.append({
                        "chunk_id": chunk_id,
                        "field": field,
                        "violation": f"out of range: {value} (expected 1–10)",
                        "prompt": "",
                    })

        # Tier 2: nested evasion field check
        if phase == "tier2":
            for j, item in enumerate(output.get("evasion", [])):
                if not isinstance(item, dict):
                    chunk_violations.append({
                        "chunk_id": chunk_id,
                        "field": f"evasion[{j}]",
                        "violation": f"expected dict, got {type(item).__name__}",
                        "prompt": "",
                    })
                    continue
                for nested_field in _TIER2_EVASION_FIELDS:
                    if nested_field not in item or item[nested_field] is None:
                        chunk_violations.append({
                            "chunk_id": chunk_id,
                            "field": f"evasion[{j}].{nested_field}",
                            "violation": "missing",
                            "prompt": "",
                        })

        violations.extend(chunk_violations)
        if not chunk_violations:
            pass_count += 1
        total += 1

    pass_rate = pass_count / total if total > 0 else 1.0
    return {
        "schema_pass_rate": round(pass_rate, 4),
        "violations": violations,
    }
