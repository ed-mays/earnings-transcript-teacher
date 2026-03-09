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

def get_takeaways_for_ticker(conn_str: str, ticker: str, limit: int = 5) -> list[tuple[str, str]]:
    repo = AnalysisRepository(conn_str)
    return repo.get_takeaways_for_ticker(ticker, limit)

def get_keywords_for_ticker(conn_str: str, ticker: str, limit: int = 15) -> list[str]:
    repo = AnalysisRepository(conn_str)
    return repo.get_keywords_for_ticker(ticker, limit)

def get_extracted_terms_for_ticker(conn_str: str, ticker: str, limit: int = 15) -> list[tuple[str, str]]:
    repo = AnalysisRepository(conn_str)
    return repo.get_extracted_terms_for_ticker(ticker, limit)

def save_analysis(conn_str: str, result: CallAnalysis) -> None:
    repo = AnalysisRepository(conn_str)
    repo.save_analysis(result)
