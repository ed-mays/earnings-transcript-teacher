"""Semantic search utility spanning the ingested earnings transcripts."""

import argparse
import os
import sys

# Add the project root to sys.path so we can import transcript
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import psycopg
from pgvector.psycopg import register_vector

from transcript.embedder import get_embeddings


def semantic_search(query: str, top_k: int = 5) -> None:
    """Find and print the most semantically relevant transcript spans.

    Args:
        query: The natural language search query.
        top_k: Number of results to return.
    """
    # 1. Generate the embedding vector for the query
    query_embeddings = get_embeddings([query])
    if not query_embeddings:
        print("Error: VOYAGE_API_KEY environment variable is missing.", file=sys.stderr)
        sys.exit(1)
    
    query_vector = query_embeddings[0]

    # 2. Search Postgres using vector similarity
    conn_str = os.environ.get("DATABASE_URL", "dbname=earnings_teacher")
    
    try:
        with psycopg.connect(conn_str) as conn:
            register_vector(conn)
            with conn.cursor() as cur:
                # <=> is the pgvector operator for cosine distance.
                # Lower distance = higher similarity.
                cur.execute(
                    """
                    SELECT c.ticker, c.fiscal_quarter, sp.name, s.section, s.text, 
                           1 - (s.embedding <=> %s::vector) AS similarity
                    FROM spans s
                    JOIN calls c ON s.call_id = c.id
                    JOIN speakers sp ON s.speaker_id = sp.id
                    ORDER BY s.embedding <=> %s::vector
                    LIMIT %s
                    """,
                    (query_vector, query_vector, top_k)
                )
                
                results = cur.fetchall()
                
                print(f"\nSemantic Search Results for: '{query}'")
                print("=" * 60)
                
                for i, row in enumerate(results, 1):
                    ticker, qtr, speaker, section, text, sim = row
                    print(f"\n{i}. [{ticker} {qtr}] {speaker} ({section}) — Similarity: {sim:.3f}")
                    # Print preview of text
                    preview = text if len(text) < 200 else text[:197] + "..."
                    print(f"   \"{preview}\"")
                    
    except psycopg.Error as e:
        print(f"Database error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Search earnings transcripts semantically.")
    parser.add_argument("query", help="The search query")
    parser.add_argument("-k", "--top-k", type=int, default=5, help="Number of results to return")
    args = parser.parse_args()
    
    semantic_search(args.query, args.top_k)
