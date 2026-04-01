"""
Prompt Tuner CLI — compare a candidate prompt against production for a given pipeline phase.

Usage:
    python tools/prompt_tuner.py --phase tier1 --ticker MSFT --variant TIER_1_v2_few_shot
    python tools/prompt_tuner.py --phase tier2 --ticker AAPL --variant TIER_2_v1_bar --chunks 5
    python tools/prompt_tuner.py --phase tier1 --ticker MSFT --variant TIER_1_v2_few_shot \\
        --chunks 20 --quarter 2025-Q4

Results are saved to tools/eval/results/<phase>_<variant>_<timestamp>.json.
"""

import argparse
import importlib
import json
import logging
import os
import re
import sys
import textwrap
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import anthropic

# Allow running from repo root: python tools/prompt_tuner.py
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from db.repositories.analysis import AnalysisRepository
from db.repositories.calls import CallRepository
from ingestion.prompts import (
    TIER_1_SYSTEM_PROMPT,
    TIER_2_SYSTEM_PROMPT,
    TIER_3_SYNTHESIS_PROMPT,
)

logger = logging.getLogger(__name__)

# Models mirror AgenticExtractor defaults
_TIER1_MODEL = "claude-sonnet-4-5"
_TIER2_MODEL = "claude-sonnet-4-5"
_TIER3_MODEL = "claude-haiku-4-5-20251001"

RESULTS_DIR = Path(__file__).resolve().parent / "eval" / "results"


# ---------------------------------------------------------------------------
# Prompt loading
# ---------------------------------------------------------------------------

def _load_production_prompt(phase: str) -> str:
    """Return the current production system prompt for the given phase."""
    mapping = {
        "tier1": TIER_1_SYSTEM_PROMPT,
        "tier2": TIER_2_SYSTEM_PROMPT,
        "tier3": TIER_3_SYNTHESIS_PROMPT,
    }
    return mapping[phase]


def _load_candidate_prompt(variant: str) -> str:
    """Load a named constant from ingestion/prompts_candidates.py.

    Exits with a clear error if the constant is not found.
    """
    try:
        module = importlib.import_module("ingestion.prompts_candidates")
    except ImportError as e:
        print(f"Error: could not import ingestion.prompts_candidates: {e}", file=sys.stderr)
        sys.exit(1)

    prompt = getattr(module, variant, None)
    if prompt is None:
        print(
            f"Error: Variant '{variant}' not found in ingestion/prompts_candidates.py",
            file=sys.stderr,
        )
        sys.exit(1)
    return prompt


# ---------------------------------------------------------------------------
# LLM call helpers — replicate AgenticExtractor call pattern without modifying it
# ---------------------------------------------------------------------------

def _parse_response(message: anthropic.types.Message) -> dict[str, Any]:
    """Parse JSON from an Anthropic message response."""
    content = message.content[0].text.strip()
    if content.startswith("```json"):
        end = content.rfind("```", 7)
        content = (content[7:end] if end != -1 else content[7:]).strip()
    elif content.startswith("```"):
        end = content.rfind("```", 3)
        content = (content[3:end] if end != -1 else content[3:]).strip()
    try:
        return json.loads(content)
    except json.JSONDecodeError:
        try:
            result, _ = json.JSONDecoder().raw_decode(content)
            return result
        except json.JSONDecodeError as e:
            raise ValueError(f"LLM returned malformed JSON: {e}") from e


def _run_tier1(
    text: str,
    chunk_type: str,
    company_context: str,
    system_prompt: str,
    client: anthropic.Anthropic,
) -> dict[str, Any]:
    """Run one Tier 1 extraction call with the given system prompt."""
    company_header = f"### Company: {company_context}\n" if company_context else ""
    user_prompt = (
        f"{company_header}### Chunk Type: {chunk_type}\n"
        f"### Transcript Text:\n{text}\n\n"
        "Extract the requested JSON metadata."
    )
    message = client.messages.create(
        model=_TIER1_MODEL,
        max_tokens=4096,
        system=system_prompt,
        messages=[{"role": "user", "content": user_prompt}],
    )
    return _parse_response(message)


def _run_tier2(
    text: str,
    chunk_type: str,
    system_prompt: str,
    client: anthropic.Anthropic,
) -> dict[str, Any]:
    """Run one Tier 2 extraction call with the given system prompt."""
    user_prompt = (
        f"### Chunk Type: {chunk_type}\n"
        f"### Transcript Text:\n{text}\n\n"
        "Extract the requested pedagogical JSON metadata."
    )
    message = client.messages.create(
        model=_TIER2_MODEL,
        max_tokens=8192,
        system=system_prompt,
        messages=[{"role": "user", "content": user_prompt}],
    )
    return _parse_response(message)


def _run_tier3(
    aggregated_text: str,
    system_prompt: str,
    client: anthropic.Anthropic,
) -> dict[str, Any]:
    """Run one Tier 3 synthesis call with the given system prompt."""
    user_prompt = (
        f"### Aggregated Output from All Chunks:\n{aggregated_text}\n\n"
        "Produce the final pedagogical strategic synthesis."
    )
    message = client.messages.create(
        model=_TIER3_MODEL,
        max_tokens=4096,
        system=system_prompt,
        messages=[{"role": "user", "content": user_prompt}],
    )
    return _parse_response(message)


def _run_phase_for_chunk(
    phase: str,
    chunk: dict,
    company_context: str,
    system_prompt: str,
    client: anthropic.Anthropic,
) -> dict[str, Any]:
    """Dispatch to the appropriate phase runner."""
    text = chunk["chunk_text"]
    chunk_type = chunk.get("chunk_type", "turn")
    if phase == "tier1":
        return _run_tier1(text, chunk_type, company_context, system_prompt, client)
    if phase == "tier2":
        return _run_tier2(text, chunk_type, system_prompt, client)
    if phase == "tier3":
        return _run_tier3(text, system_prompt, client)
    raise ValueError(f"Unknown phase: {phase}")


# ---------------------------------------------------------------------------
# Display helpers
# ---------------------------------------------------------------------------

def _truncate(text: str, length: int = 200) -> str:
    """Truncate text and append ellipsis if needed."""
    if len(text) <= length:
        return text
    return text[:length] + "…"


def _print_chunk_comparison(
    index: int,
    chunk: dict,
    production_output: dict | str,
    candidate_output: dict | str,
) -> None:
    """Print a side-by-side comparison for one chunk."""
    print(f"\n{'='*70}")
    print(f"Chunk {index + 1}  [{chunk.get('chunk_type', '?')}]  id={chunk['chunk_id']}")
    print(f"  {_truncate(chunk['chunk_text'].strip())}")
    print()
    print("  PRODUCTION:")
    if isinstance(production_output, dict):
        print(textwrap.indent(json.dumps(production_output, indent=2), "    "))
    else:
        print(f"    ERROR: {production_output}")
    print()
    print("  CANDIDATE:")
    if isinstance(candidate_output, dict):
        print(textwrap.indent(json.dumps(candidate_output, indent=2), "    "))
    else:
        print(f"    ERROR: {candidate_output}")


def _print_metrics_table(
    phase: str,
    production_metrics: dict,
    candidate_metrics: dict,
) -> None:
    """Print a formatted metrics comparison table."""
    if not production_metrics:
        return
    print(f"\n{'='*70}")
    print(f"Metrics summary ({phase.upper()}):")
    print(f"  {'Metric':<30} {'Production':>14} {'Candidate':>14}")
    print(f"  {'-'*58}")

    all_keys = set(production_metrics) | set(candidate_metrics)
    skip_keys = {"n_chunks", "judge_model", "schema_pass_rate", "violations"}
    for key in sorted(all_keys - skip_keys):
        prod_val = production_metrics.get(key, "—")
        cand_val = candidate_metrics.get(key, "—")
        fmt_prod = f"{prod_val:.3f}" if isinstance(prod_val, float) else str(prod_val)
        fmt_cand = f"{cand_val:.3f}" if isinstance(cand_val, float) else str(cand_val)
        print(f"  {key:<30} {fmt_prod:>14} {fmt_cand:>14}")

    n = production_metrics.get("n_chunks", "?")
    print(f"\n  Chunks evaluated: {n}")

    # Schema metrics
    if "schema_pass_rate" in production_metrics:
        print(f"\n  Schema pass rate:  production={production_metrics['schema_pass_rate']:.2f}"
              f"  candidate={candidate_metrics.get('schema_pass_rate', 0):.2f}")


# ---------------------------------------------------------------------------
# Promotion helpers
# ---------------------------------------------------------------------------

def _promote_candidate(
    production_constant_name: str,
    candidate_constant_name: str,
    candidate_prompt_text: str,
    production_metrics: dict,
    candidate_metrics: dict,
) -> None:
    """Replace the production constant and remove the candidate from candidates file."""
    # Build a summary delta string for the suggested commit message
    delta_parts = []
    for key in ["term_precision", "bad_term_rate", "score_mae", "takeaway_specificity_avg",
                "evasion_verbatim_rate", "completeness_rate"]:
        if key in production_metrics and key in candidate_metrics:
            delta = candidate_metrics[key] - production_metrics[key]
            sign = "+" if delta >= 0 else ""
            delta_parts.append(f"{sign}{delta:.2f} {key}")
    n = production_metrics.get("n_chunks", "?")
    delta_str = ", ".join(delta_parts) if delta_parts else "see results"

    # Update prompts.py — replace the constant value
    prompts_path = Path(__file__).resolve().parent.parent / "ingestion" / "prompts.py"
    prompts_text = prompts_path.read_text()

    # Match: CONSTANT_NAME = """...""" or CONSTANT_NAME = '...' style
    # Use a simple approach: find the assignment, replace everything up to the next
    # top-level constant or end-of-string
    pattern = re.compile(
        rf'^({re.escape(production_constant_name)}\s*=\s*""")(.*?)(""")',
        re.DOTALL | re.MULTILINE,
    )
    match = pattern.search(prompts_text)
    if not match:
        print(
            f"Warning: Could not find triple-quoted constant '{production_constant_name}' "
            "in ingestion/prompts.py. Manual promotion required.",
            file=sys.stderr,
        )
        return

    new_prompts_text = pattern.sub(
        rf'\g<1>{candidate_prompt_text}\g<3>',
        prompts_text,
        count=1,
    )
    prompts_path.write_text(new_prompts_text)
    print(f"  Updated ingestion/prompts.py: {production_constant_name} replaced.")

    # Update prompts_candidates.py — remove the candidate constant block
    candidates_path = Path(__file__).resolve().parent.parent / "ingestion" / "prompts_candidates.py"
    candidates_text = candidates_path.read_text()
    # Remove lines that are part of this candidate's assignment (comment + assignment block)
    cand_pattern = re.compile(
        r'(#[^\n]*\n)*'  # leading comment lines (optional)
        rf'{re.escape(candidate_constant_name)}\s*=\s*""".*?"""\s*\n?',
        re.DOTALL,
    )
    new_candidates_text = cand_pattern.sub("", candidates_text)
    candidates_path.write_text(new_candidates_text)
    print(f"  Updated ingestion/prompts_candidates.py: {candidate_constant_name} removed.")

    print(f"\nSuggested commit message:")
    print(f'  git commit -m "Promote {candidate_constant_name}: {delta_str} on {n}-chunk sample"')


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def _build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Compare a candidate prompt variant against production for a pipeline phase.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument(
        "--phase",
        required=True,
        choices=["tier1", "tier2", "tier3"],
        help="Pipeline phase to evaluate.",
    )
    parser.add_argument(
        "--ticker",
        required=True,
        help="Ticker symbol to pull chunks from the DB (e.g. MSFT).",
    )
    parser.add_argument(
        "--variant",
        required=True,
        help="Name of a constant in ingestion/prompts_candidates.py.",
    )
    parser.add_argument(
        "--chunks",
        type=int,
        default=10,
        help="Number of chunks to run (default: 10).",
    )
    parser.add_argument(
        "--quarter",
        default=None,
        help="Filter to a specific quarter in YYYY-QN format (e.g. 2025-Q4).",
    )
    parser.add_argument(
        "--judge-model",
        default="claude-haiku-4-5-20251001",
        dest="judge_model",
        help="Claude model to use as LLM judge for Tier 2 scoring (default: claude-haiku-4-5-20251001).",
    )
    return parser


def main() -> None:
    logging.basicConfig(level=logging.WARNING)
    parser = _build_arg_parser()
    args = parser.parse_args()

    conn_str = os.environ.get("DATABASE_URL")
    if not conn_str:
        print("Error: DATABASE_URL environment variable is not set.", file=sys.stderr)
        sys.exit(1)

    # Load prompts
    production_prompt = _load_production_prompt(args.phase)
    candidate_prompt = _load_candidate_prompt(args.variant)

    # Load chunks from DB
    analysis_repo = AnalysisRepository(conn_str)
    calls_repo = CallRepository(conn_str)

    chunks = analysis_repo.get_chunks_for_ticker(
        ticker=args.ticker.upper(),
        limit=args.chunks,
        quarter=args.quarter,
    )
    if not chunks:
        print(
            f"Error: No chunks found for ticker '{args.ticker.upper()}'"
            + (f" in quarter {args.quarter}" if args.quarter else "")
            + ".",
            file=sys.stderr,
        )
        sys.exit(1)

    company_name, industry = calls_repo.get_company_info(args.ticker.upper())
    company_context = f"{company_name} ({industry})" if company_name else args.ticker.upper()

    client = anthropic.Anthropic()

    print(f"\nPrompt Tuner — phase={args.phase}  ticker={args.ticker.upper()}  variant={args.variant}")
    print(f"Running {len(chunks)} chunk(s) with production and candidate prompts...")

    results = []
    for i, chunk in enumerate(chunks):
        chunk_id = chunk["chunk_id"]
        prod_out: dict | str
        cand_out: dict | str
        try:
            prod_out = _run_phase_for_chunk(
                args.phase, chunk, company_context, production_prompt, client
            )
        except Exception as e:
            prod_out = f"LLM error: {e}"

        try:
            cand_out = _run_phase_for_chunk(
                args.phase, chunk, company_context, candidate_prompt, client
            )
        except Exception as e:
            cand_out = f"LLM error: {e}"

        _print_chunk_comparison(i, chunk, prod_out, cand_out)
        results.append({
            "chunk_id": chunk_id,
            "chunk_text_preview": _truncate(chunk["chunk_text"].strip()),
            "production_output": prod_out if isinstance(prod_out, dict) else {"error": prod_out},
            "candidate_output": cand_out if isinstance(cand_out, dict) else {"error": cand_out},
        })

    # --- Run schema validation (always runs, issues #288) ---
    production_schema: dict = {}
    candidate_schema: dict = {}
    try:
        from tools.eval.scorers import validate_output_schema
        prod_outputs = [r["production_output"] for r in results]
        cand_outputs = [r["candidate_output"] for r in results]
        production_schema = validate_output_schema(prod_outputs, args.phase)
        candidate_schema = validate_output_schema(cand_outputs, args.phase)
        # Attach schema_pass_rate to outputs for metrics table
        production_schema["schema_pass_rate"] = production_schema.get("schema_pass_rate", 1.0)
        candidate_schema["schema_pass_rate"] = candidate_schema.get("schema_pass_rate", 1.0)
    except ImportError:
        pass  # scorers.py not yet available (pre-#288)
    except Exception as e:
        print(f"\nWarning: schema validation failed: {e}", file=sys.stderr)

    # --- Run phase-specific scorer (issues #286/#287) ---
    production_metrics: dict = {}
    candidate_metrics: dict = {}
    try:
        from tools.eval import scorers
        dataset_path = Path(__file__).resolve().parent / "eval" / "dataset.json"
        if args.phase == "tier1" and hasattr(scorers, "score_tier1") and dataset_path.exists():
            dataset = json.loads(dataset_path.read_text())
            labeled = {e["chunk_id"]: e["tier1_labels"] for e in dataset.get("tier1", [])}
            if labeled:
                prod_for_scoring = [
                    (r["production_output"], labeled[r["chunk_id"]])
                    for r in results if r["chunk_id"] in labeled
                ]
                cand_for_scoring = [
                    (r["candidate_output"], labeled[r["chunk_id"]])
                    for r in results if r["chunk_id"] in labeled
                ]
                if prod_for_scoring:
                    production_metrics = scorers.score_tier1(
                        [o for o, _ in prod_for_scoring],
                        [l for _, l in prod_for_scoring],
                    )
                    candidate_metrics = scorers.score_tier1(
                        [o for o, _ in cand_for_scoring],
                        [l for _, l in cand_for_scoring],
                    )
        elif args.phase == "tier2" and hasattr(scorers, "score_tier2"):
            prod_scored = [
                scorers.score_tier2(
                    r["production_output"],
                    chunks[i]["chunk_text"],
                    judge_model=args.judge_model,
                )
                for i, r in enumerate(results)
            ]
            cand_scored = [
                scorers.score_tier2(
                    r["candidate_output"],
                    chunks[i]["chunk_text"],
                    judge_model=args.judge_model,
                )
                for i, r in enumerate(results)
            ]
            # Average across chunks
            def _avg_metrics(scored_list: list[dict]) -> dict:
                if not scored_list:
                    return {}
                keys = [k for k in scored_list[0] if k not in ("n_chunks", "judge_model")]
                return {
                    k: sum(s.get(k, 0) for s in scored_list) / len(scored_list)
                    for k in keys
                } | {"n_chunks": len(scored_list), "judge_model": args.judge_model}

            production_metrics = _avg_metrics(prod_scored)
            candidate_metrics = _avg_metrics(cand_scored)
    except ImportError:
        pass  # scorers not yet available

    # Merge schema pass rates into metrics dicts
    if production_schema:
        production_metrics["schema_pass_rate"] = production_schema.get("schema_pass_rate", 1.0)
        candidate_metrics["schema_pass_rate"] = candidate_schema.get("schema_pass_rate", 1.0)

    if production_metrics:
        _print_metrics_table(args.phase, production_metrics, candidate_metrics)

    # --- Schema regression warning ---
    prod_spr = production_schema.get("schema_pass_rate", 1.0) if production_schema else None
    cand_spr = candidate_schema.get("schema_pass_rate", 1.0) if candidate_schema else None
    schema_regression = (
        prod_spr is not None
        and cand_spr is not None
        and cand_spr < prod_spr
    )
    if schema_regression:
        violations = candidate_schema.get("violations", [])
        print(f"\n⚠  Schema regression detected:")
        print(f"   Production schema pass rate: {prod_spr:.2f}")
        print(f"   Candidate schema pass rate:  {cand_spr:.2f}")
        print(f"   {len(violations)} violation(s) found in candidate output (see results file for details).")
        print("   Proceeding with promotion is not recommended.")

    # --- Save results ---
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    results_file = RESULTS_DIR / f"{args.phase}_{args.variant}_{timestamp}.json"
    output = {
        "meta": {
            "phase": args.phase,
            "ticker": args.ticker.upper(),
            "variant": args.variant,
            "timestamp": timestamp,
            "chunks_run": len(chunks),
        },
        "metrics": {
            "production": {**production_metrics, **({} if not production_schema else {"schema": production_schema})},
            "candidate": {**candidate_metrics, **({} if not candidate_schema else {"schema": candidate_schema})},
        },
        "results": results,
    }
    results_file.write_text(json.dumps(output, indent=2))
    print(f"\nResults saved to {results_file}")

    # --- Promotion flow ---
    if production_metrics and candidate_metrics:
        promote_prompt = "\nPromote candidate to production? [y/N] "
        if schema_regression:
            promote_prompt = "\nPromote anyway? [y/N] "
        try:
            answer = input(promote_prompt).strip().lower()
        except (EOFError, KeyboardInterrupt):
            answer = "n"
        if answer == "y":
            # Determine the production constant name for this phase
            const_map = {
                "tier1": "TIER_1_SYSTEM_PROMPT",
                "tier2": "TIER_2_SYSTEM_PROMPT",
                "tier3": "TIER_3_SYNTHESIS_PROMPT",
            }
            _promote_candidate(
                production_constant_name=const_map[args.phase],
                candidate_constant_name=args.variant,
                candidate_prompt_text=candidate_prompt,
                production_metrics=production_metrics,
                candidate_metrics=candidate_metrics,
            )
        else:
            print("Promotion declined. Candidate remains in prompts_candidates.py.")


if __name__ == "__main__":
    main()
