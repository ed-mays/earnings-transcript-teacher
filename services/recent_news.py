"""Fetch recent news articles about a company around an earnings call date."""

import json
import logging
import os
from datetime import date, timedelta

import requests

from core.models import NewsItem

logger = logging.getLogger(__name__)

_SYSTEM_PROMPT = (
    "You are a financial research assistant. "
    "Return ONLY a valid JSON array, no markdown, no explanations."
)

_DATE_WINDOW_BEFORE_DAYS = 30
_DATE_WINDOW_AFTER_DAYS = 7


def fetch_recent_news(
    ticker: str,
    company_name: str,
    call_date: date,
    themes: list[str],
    max_items: int = 5,
) -> list[NewsItem]:
    """Query Perplexity for news about the company around the call date.

    Returns up to max_items NewsItems ranked by relevance to the transcript themes.
    Returns an empty list on any error so callers are never blocked.
    """
    api_key = os.environ.get("PERPLEXITY_API_KEY")
    if not api_key:
        logger.warning("PERPLEXITY_API_KEY not set — skipping news fetch")
        return []

    start_date = (call_date - timedelta(days=_DATE_WINDOW_BEFORE_DAYS)).isoformat()
    end_date = (call_date + timedelta(days=_DATE_WINDOW_AFTER_DAYS)).isoformat()
    display_name = company_name or ticker
    themes_str = ", ".join(themes[:5]) if themes else "earnings results, financial performance"

    user_prompt = (
        f"Find the {max_items} most relevant news articles about {display_name} ({ticker}) "
        f"published between {start_date} and {end_date}. "
        f"Prioritise articles related to these themes: {themes_str}. "
        f"Return ONLY a JSON array of up to {max_items} objects. "
        f'Each object must have these keys: "headline" (string), "url" (string), '
        f'"source" (publication name, string), "date" (YYYY-MM-DD string), '
        f'"summary" (1-2 sentence summary, string). '
        f"If fewer than {max_items} relevant articles exist, return what you find."
    )

    payload = {
        "model": "sonar",
        "messages": [
            {"role": "system", "content": _SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ],
        "stream": False,
    }

    try:
        response = requests.post(
            "https://api.perplexity.ai/chat/completions",
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            json=payload,
            timeout=30,
        )
        response.raise_for_status()
        content = response.json()["choices"][0]["message"]["content"].strip()
        return _parse_news_items(content)
    except Exception as e:
        logger.error("News fetch failed for %s: %s", ticker, e)
        return []


def _parse_news_items(content: str) -> list[NewsItem]:
    """Parse a JSON array from the LLM response into NewsItem objects."""
    # Strip markdown code fences if present
    if content.startswith("```json"):
        content = content[7:]
    elif content.startswith("```"):
        content = content[3:]
    if content.endswith("```"):
        content = content[:-3]
    content = content.strip()

    try:
        items = json.loads(content)
    except json.JSONDecodeError as e:
        logger.warning("Could not parse news JSON: %s. Content: %.200s", e, content)
        return []

    if not isinstance(items, list):
        logger.warning("Expected JSON array, got %s", type(items))
        return []

    result = []
    for item in items:
        if not isinstance(item, dict) or not item.get("headline"):
            continue
        result.append(
            NewsItem(
                headline=item.get("headline", ""),
                url=item.get("url", ""),
                source=item.get("source", ""),
                date=item.get("date", ""),
                summary=item.get("summary", ""),
            )
        )
    return result
