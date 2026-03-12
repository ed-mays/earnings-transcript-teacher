import csv
import re
from pathlib import Path
from typing import Dict, List

_TERMS_CSV = Path(__file__).parent / "financial-terms.csv"


def _load_terms() -> List[Dict[str, str]]:
    """Load financial terms from CSV, expanding parenthetical aliases into separate match patterns."""
    entries = []
    with open(_TERMS_CSV, newline='', encoding='utf-8') as f:
        for row in csv.DictReader(f):
            raw_term = row["term"]
            definition = row["definition"]

            # Normalise non-breaking hyphens so matching works against plain transcript text
            raw_term_norm = raw_term.replace("\u2011", "-")

            # Parse "Primary term (Alias)" → two match patterns pointing to one primary label
            alias_match = re.match(r'^(.+?)\s*\((.+?)\)\s*$', raw_term_norm)
            if alias_match:
                primary = alias_match.group(1).strip()
                alias = alias_match.group(2).strip()
                match_patterns = [primary, alias]
            else:
                primary = raw_term_norm.strip()
                match_patterns = [primary]

            entries.append({
                "term": primary,
                "definition": definition,
                "patterns": match_patterns,
            })
    return entries


# Loaded once at import time; safe because the CSV is read-only at runtime.
_FINANCIAL_TERMS = _load_terms()


def scan_chunk(text: str) -> List[Dict[str, str]]:
    """Return financial terms found in text, each with its pre-defined definition.

    Matches are case-insensitive whole-word. Duplicate primary terms are collapsed.
    Returns a list of {"term": ..., "definition": ..., "category": "financial"}.
    """
    found: Dict[str, str] = {}  # primary term → definition
    # Normalise hyphens in the source text too
    text_norm = text.replace("\u2011", "-").lower()

    for entry in _FINANCIAL_TERMS:
        if entry["term"] in found:
            continue
        for pattern in entry["patterns"]:
            regex = r'\b' + re.escape(pattern.lower()) + r'\b'
            if re.search(regex, text_norm):
                found[entry["term"]] = entry["definition"]
                break

    return [
        {"term": term, "definition": defn, "category": "financial"}
        for term, defn in found.items()
    ]
