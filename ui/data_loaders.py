import logging

import streamlit as st

from db.persistence import (
    get_all_calls,
    get_themes_for_ticker,
    get_takeaways_for_ticker,
    get_synthesis_for_ticker,
    get_keywords_for_ticker,
    get_industry_terms_for_ticker,
    get_financial_terms_for_ticker,
    get_speakers_for_ticker,
    get_spans_for_ticker,
)

logger = logging.getLogger(__name__)


@st.cache_data
def load_transcripts(conn_str: str) -> list[str]:
    """Fetch available transcript tickers from the database."""
    calls = get_all_calls(conn_str)
    return [c[0] for c in calls] if calls else []


@st.cache_data
def load_speakers(conn_str: str, ticker: str) -> list[tuple[str, str, str | None, str | None]]:
    """Fetch enriched speaker profiles for a transcript from the database."""
    return get_speakers_for_ticker(conn_str, ticker)


@st.cache_data
def load_transcript_spans(conn_str: str, ticker: str) -> list[tuple[str, str, str]]:
    """Fetch all speaker turns for a transcript from the database."""
    return get_spans_for_ticker(conn_str, ticker)


@st.cache_data
def load_metadata(conn_str: str, ticker: str):
    """Fetch themes, takeaways, synthesis, keywords, and jargon for a transcript."""
    try:
        themes = get_themes_for_ticker(conn_str, ticker)
        takeaways = get_takeaways_for_ticker(conn_str, ticker)
        synthesis = get_synthesis_for_ticker(conn_str, ticker)
        keywords = get_keywords_for_ticker(conn_str, ticker)
        industry_terms = get_industry_terms_for_ticker(conn_str, ticker)
        financial_terms = get_financial_terms_for_ticker(conn_str, ticker)

        # Deduplicate keywords for cleaner display
        unique_keywords: list[str] = []
        seen: set[str] = set()
        for kw in keywords:
            if kw.lower() not in seen:
                unique_keywords.append(kw)
                seen.add(kw.lower())

        return themes, takeaways, synthesis, unique_keywords, industry_terms, financial_terms
    except Exception:
        logger.exception("load_metadata failed for ticker %s", ticker)
        raise
