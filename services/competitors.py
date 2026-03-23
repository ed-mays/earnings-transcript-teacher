"""Fetch competitors for a company via Claude Haiku and detect transcript mentions."""

import json
import logging

import anthropic

from core.models import Competitor

logger = logging.getLogger(__name__)

_SYSTEM_PROMPT = (
    "You are a financial research assistant. "
    "Return ONLY a valid JSON array, no markdown, no explanations."
)

_MAX_COMPETITORS = 8


def fetch_competitors(
    ticker: str,
    company_name: str,
    industry: str,
    transcript_text: str,
    max_items: int = _MAX_COMPETITORS,
) -> list[Competitor]:
    """Query Claude Haiku for direct competitors of the company.

    Returns up to max_items Competitor objects with mention flags set.
    Returns an empty list on any error so callers are never blocked.
    """
    display_name = company_name or ticker
    industry_str = industry or "their industry"

    user_prompt = (
        f"List the top {max_items} direct competitors of {display_name} ({ticker}) "
        f"in the {industry_str} sector. "
        f"Return ONLY a JSON array of up to {max_items} objects. "
        f'Each object must have these keys: "name" (company name, string), '
        f'"ticker" (stock ticker symbol or empty string if unknown, string), '
        f'"description" (one sentence describing the company and why it competes, string). '
        f"Focus on publicly traded direct competitors. "
        f"If fewer than {max_items} exist, return what you find."
    )

    try:
        client = anthropic.Anthropic()
        message = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=1024,
            system=_SYSTEM_PROMPT,
            messages=[{"role": "user", "content": user_prompt}],
        )
        content = message.content[0].text.strip()
        competitors = _parse_competitors(content)
        return _flag_transcript_mentions(competitors, transcript_text)
    except Exception as e:
        logger.error("Competitors fetch failed for %s: %s", ticker, e)
        return []


def _parse_competitors(content: str) -> list[Competitor]:
    """Parse a JSON array from the LLM response into Competitor objects."""
    if content.startswith("```json"):
        end = content.rfind("```", 7)
        content = (content[7:end] if end != -1 else content[7:]).strip()
    elif content.startswith("```"):
        end = content.rfind("```", 3)
        content = (content[3:end] if end != -1 else content[3:]).strip()
    else:
        content = content.strip()

    try:
        items = json.loads(content)
    except json.JSONDecodeError as e:
        logger.warning("Could not parse competitors JSON: %s. Content: %.200s", e, content)
        return []

    if not isinstance(items, list):
        logger.warning("Expected JSON array for competitors, got %s", type(items))
        return []

    result = []
    for item in items:
        if not isinstance(item, dict) or not item.get("name"):
            continue
        result.append(
            Competitor(
                name=item.get("name", ""),
                ticker=item.get("ticker", "") or "",
                description=item.get("description", ""),
            )
        )
    return result


def _flag_transcript_mentions(
    competitors: list[Competitor], transcript_text: str
) -> list[Competitor]:
    """Return a new list of Competitors with mentioned_in_transcript set via string search."""
    text_lower = transcript_text.lower()
    result = []
    for c in competitors:
        mentioned = False
        if c.name and c.name.lower() in text_lower:
            mentioned = True
        elif c.ticker and c.ticker.upper() in transcript_text.upper():
            mentioned = True
        result.append(
            Competitor(
                name=c.name,
                ticker=c.ticker,
                description=c.description,
                mentioned_in_transcript=mentioned,
            )
        )
    return result
