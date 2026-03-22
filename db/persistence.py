"""Persistence wrapper to maintain API compatibility during refactoring."""

from core.models import CallAnalysis
from db.repositories import CallRepository, EmbeddingRepository, AnalysisRepository

def fetch_existing_embeddings(
    conn_str: str, ticker: str, fiscal_quarter: str
) -> dict[str, list[float]]:
    repo = EmbeddingRepository(conn_str)
    return repo.fetch_existing_embeddings(ticker, fiscal_quarter)

def get_all_calls(conn_str: str) -> list[tuple[str, str]]:
    repo = CallRepository(conn_str)
    return repo.get_all_calls()

def search_spans(
    conn_str: str, ticker: str, query_vector: list[float], top_k: int = 5
) -> list[str]:
    repo = EmbeddingRepository(conn_str)
    return repo.search_spans(ticker, query_vector, top_k)

def get_topics_for_ticker(conn_str: str, ticker: str, limit: int = 5) -> list[list[str]]:
    repo = AnalysisRepository(conn_str)
    return repo.get_topics_for_ticker(ticker, limit)

def get_speakers_for_ticker(conn_str: str, ticker: str) -> list[tuple[str, str, str | None, str | None]]:
    repo = AnalysisRepository(conn_str)
    return repo.get_speakers_for_ticker(ticker)

def get_spans_for_ticker(conn_str: str, ticker: str) -> list[tuple[str, str, str]]:
    repo = AnalysisRepository(conn_str)
    return repo.get_spans_for_ticker(ticker)

def get_themes_for_ticker(conn_str: str, ticker: str) -> list[str]:
    repo = AnalysisRepository(conn_str)
    return repo.get_themes_for_ticker(ticker)

def get_takeaways_for_ticker(conn_str: str, ticker: str, limit: int = 5) -> list[tuple[str, str]]:
    repo = AnalysisRepository(conn_str)
    return repo.get_takeaways_for_ticker(ticker, limit)

def get_synthesis_for_ticker(conn_str: str, ticker: str) -> tuple[str, str, str] | None:
    repo = AnalysisRepository(conn_str)
    return repo.get_synthesis_for_ticker(ticker)

def get_strategic_shifts_for_ticker(conn_str: str, ticker: str) -> str | None:
    """Return the strategic_shifts analysis text for a ticker, or None if absent."""
    repo = AnalysisRepository(conn_str)
    return repo.get_strategic_shifts_for_ticker(ticker)

def get_keywords_for_ticker(conn_str: str, ticker: str, limit: int = 15) -> list[str]:
    repo = AnalysisRepository(conn_str)
    return repo.get_keywords_for_ticker(ticker, limit)

def get_evasion_for_ticker(conn_str: str, ticker: str) -> list[tuple[str, int, str]]:
    repo = AnalysisRepository(conn_str)
    return repo.get_evasion_for_ticker(ticker)

def get_misconceptions_for_ticker(conn_str: str, ticker: str) -> list[tuple[str, str, str]]:
    repo = AnalysisRepository(conn_str)
    return repo.get_misconceptions_for_ticker(ticker)

def get_extracted_terms_for_ticker(conn_str: str, ticker: str, limit: int = 15) -> list[tuple[str, str, str]]:
    repo = AnalysisRepository(conn_str)
    return repo.get_extracted_terms_for_ticker(ticker, limit)

def get_industry_terms_for_ticker(conn_str: str, ticker: str, limit: int = 30) -> list[tuple[str, str, str]]:
    repo = AnalysisRepository(conn_str)
    return repo.get_industry_terms_for_ticker(ticker, limit)

def get_financial_terms_for_ticker(conn_str: str, ticker: str) -> list[tuple[str, str, str]]:
    repo = AnalysisRepository(conn_str)
    return repo.get_financial_terms_for_ticker(ticker)

def update_term_definition(conn_str: str, ticker: str, term: str, definition: str) -> bool:
    repo = AnalysisRepository(conn_str)
    return repo.update_term_definition(ticker, term, definition)

def update_term_explanation(conn_str: str, ticker: str, term: str, explanation: str) -> bool:
    repo = AnalysisRepository(conn_str)
    return repo.update_term_explanation(ticker, term, explanation)

def save_analysis(conn_str: str, result: CallAnalysis) -> None:
    repo = AnalysisRepository(conn_str)
    repo.save_analysis(result)
