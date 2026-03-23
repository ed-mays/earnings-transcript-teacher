import logging

import streamlit as st

from core.models import Competitor, NewsItem  # Competitor used by load_competitors return type
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
    get_evasion_for_ticker,
    get_misconceptions_for_ticker,
    get_strategic_shifts_for_ticker,
    get_qa_evasion_for_ticker,
    get_call_summary_for_ticker,
    get_speaker_dynamics,
)

from db.repositories import CallRepository, CompetitorRepository, ProgressRepository
from services.competitors import fetch_competitors
from services.recent_news import fetch_recent_news

logger = logging.getLogger(__name__)


@st.cache_data
def load_transcripts(conn_str: str) -> list[tuple[str, str, str | None, str | None]]:
    """Fetch available transcripts from the database as (ticker, fiscal_quarter, company_name, call_date)."""
    calls = get_all_calls(conn_str)
    return [(c[0], c[1], c[2], c[3]) for c in calls] if calls else []


@st.cache_data
def load_speakers(conn_str: str, ticker: str) -> list[tuple[str, str, str | None, str | None]]:
    """Fetch enriched speaker profiles for a transcript from the database."""
    return get_speakers_for_ticker(conn_str, ticker)


@st.cache_data
def load_transcript_spans(conn_str: str, ticker: str) -> list[tuple[str, str, str]]:
    """Fetch all speaker turns for a transcript from the database."""
    return get_spans_for_ticker(conn_str, ticker)


@st.cache_data
def load_analyst_view(conn_str: str, ticker: str) -> tuple[list, list]:
    """Fetch evasion analysis and misconceptions for a transcript."""
    evasion = get_evasion_for_ticker(conn_str, ticker)
    misconceptions = get_misconceptions_for_ticker(conn_str, ticker)
    return evasion, misconceptions


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


@st.cache_data
def load_competitors(conn_str: str, ticker: str) -> list[Competitor]:
    """Return competitors for a ticker, using the DB cache when fresh.

    Falls back to a live Perplexity fetch when the cache is empty or stale (>30 days).
    Returns an empty list if the ticker is unknown or the fetch fails.
    """
    if not ticker:
        return []

    repo = CompetitorRepository(conn_str)
    cached = repo.get(ticker)
    if cached:
        return cached

    call_repo = CallRepository(conn_str)
    company_name, industry = call_repo.get_company_info(ticker)

    # We need the transcript text to flag mentions — fetch from the spans table.
    from db.persistence import get_spans_for_ticker
    spans = get_spans_for_ticker(conn_str, ticker)
    transcript_text = " ".join(text for _, _, text in spans)

    competitors = fetch_competitors(
        ticker=ticker,
        company_name=company_name,
        industry=industry,
        transcript_text=transcript_text,
    )
    if competitors:
        repo.save(ticker, competitors)
    return competitors


@st.cache_data
def load_qa_evasion(conn_str: str, ticker: str) -> list[tuple[str, int, str]]:
    """Fetch Q&A evasion entries ordered by call sequence."""
    if not ticker:
        return []
    return get_qa_evasion_for_ticker(conn_str, ticker)


@st.cache_data
def load_strategic_shifts(conn_str: str, ticker: str) -> list[dict] | None:
    """Fetch the strategic shifts list for a transcript as structured dicts."""
    if not ticker:
        return None
    return get_strategic_shifts_for_ticker(conn_str, ticker)


@st.cache_data
def load_call_summary(conn_str: str, ticker: str) -> str | None:
    """Fetch the executive summary paragraph for a transcript."""
    if not ticker:
        return None
    return get_call_summary_for_ticker(conn_str, ticker)


@st.cache_data
def load_speaker_dynamics(conn_str: str, ticker: str) -> list[dict]:
    """Fetch per-speaker turn and word counts for a transcript."""
    if not ticker:
        return []
    return get_speaker_dynamics(conn_str, ticker)


@st.cache_data
def load_step_progress(conn_str: str, ticker: str) -> frozenset[int]:
    """Return the set of step numbers the user has completed for a transcript."""
    if not ticker:
        return frozenset()
    return frozenset(ProgressRepository(conn_str).get_completed_steps(ticker))


@st.cache_data
def load_all_step_counts(conn_str: str) -> dict[str, int]:
    """Return a dict mapping ticker → steps_completed for all transcripts with progress."""
    return dict(ProgressRepository(conn_str).get_all_step_counts())


@st.cache_data
def load_recent_news(conn_str: str, ticker: str, themes: tuple[str, ...]) -> list[NewsItem]:
    """Fetch recent news articles around the earnings call date.

    themes is a tuple (not list) so it is hashable for st.cache_data.
    Returns an empty list if call_date is unknown or the fetch fails.
    """
    if not ticker:
        return []

    repo = CallRepository(conn_str)
    call_date = repo.get_call_date(ticker)
    if not call_date:
        logger.info("No call_date for %s — skipping news fetch", ticker)
        return []

    company_name, _ = repo.get_company_info(ticker)
    return fetch_recent_news(
        ticker=ticker,
        company_name=company_name,
        call_date=call_date,
        themes=list(themes),
    )
