"""Embedding cache and semantic search repository."""

import logging

import psycopg
from pgvector.psycopg import register_vector

logger = logging.getLogger(__name__)


class EmbeddingRepository:
    def __init__(self, conn_str: str):
        self.conn_str = conn_str

    def fetch_existing_embeddings(self, ticker: str, fiscal_quarter: str) -> dict[str, list[float]]:
        """Return cached embeddings for a ticker/quarter as {text: vector}."""
        cache: dict[str, list[float]] = {}
        try:
            with psycopg.connect(self.conn_str) as conn:
                register_vector(conn)
                with conn.cursor() as cur:
                    cur.execute(
                        """
                        SELECT s.text, s.embedding
                        FROM spans s
                        JOIN calls c ON s.call_id = c.id
                        WHERE c.ticker = %s AND c.fiscal_quarter = %s
                            AND s.embedding IS NOT NULL
                        """,
                        (ticker, fiscal_quarter),
                    )
                    for text, embedding in cur.fetchall():
                        if embedding is not None:
                            cache[text] = embedding.tolist()
        except Exception as e:
            logger.warning(f"Could not fetch embedding cache: {e}")
        return cache

    def search_spans(self, ticker: str, query_vector: list[float], top_k: int = 5) -> list[str]:
        """Return the top-k span texts most similar to query_vector for the given ticker."""
        results = []
        try:
            with psycopg.connect(self.conn_str) as conn:
                register_vector(conn)
                with conn.cursor() as cur:
                    cur.execute(
                        """
                        SELECT s.text
                        FROM spans s
                        JOIN calls c ON s.call_id = c.id
                        WHERE c.ticker = %s
                        ORDER BY s.embedding <=> %s::vector
                        LIMIT %s
                        """,
                        (ticker, query_vector, top_k),
                    )
                    results = [row[0] for row in cur.fetchall()]
        except Exception as e:
            logger.warning(f"Could not perform semantic search: {e}")
        return results
