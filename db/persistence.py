"""Persistence layer for storing analysis results in PostgreSQL.

Requires psycopg 3.1+ (installed via `pip install "psycopg[binary]"`).
"""

import sys
import psycopg
from pgvector.psycopg import register_vector

from transcript.models import CallAnalysis


def fetch_existing_embeddings(
    conn_str: str, ticker: str, fiscal_quarter: str
) -> dict[str, list[float]]:
    """Retrieve all previously computed embeddings for a given transcript.

    Args:
        conn_str: PostgreSQL connection string.
        ticker: The stock ticker (e.g. 'MSFT').
        fiscal_quarter: The fiscal quarter identifier.

    Returns:
        A dictionary mapping the exact span text to its embedding vector.
    """
    cache: dict[str, list[float]] = {}
    try:
        with psycopg.connect(conn_str) as conn:
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
                    # psycopg converts the pgvector type directly to a Python list
                    if embedding is not None:
                        cache[text] = embedding.tolist()
    except Exception as e:
        # If DB is down or table is missing, just return an empty cache
        # so the pipeline can still degraded/re-compute.
        import logging
        logging.warning(f"Could not fetch embedding cache: {e}")

    return cache


def get_all_calls(conn_str: str) -> list[tuple[str, str]]:
    """Fetch all ingested transcripts from the database.

    Args:
        conn_str: PostgreSQL connection string.

    Returns:
        A list of tuples: (ticker, fiscal_quarter)
    """
    calls = []
    try:
        with psycopg.connect(conn_str) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT ticker, fiscal_quarter
                    FROM calls
                    ORDER BY created_at DESC
                    """
                )
                calls = cur.fetchall()
    except Exception as e:
        import logging
        logging.warning(f"Could not fetch calls: {e}")
        
    return calls


def search_spans(
    conn_str: str, ticker: str, query_vector: list[float], top_k: int = 5
) -> list[str]:
    """Perform a semantic similarity search within a specific transcript.

    Args:
        conn_str: PostgreSQL connection string.
        ticker: The specific stock ticker to isolate the search to.
        query_vector: The embedded user query.
        top_k: Number of results to return.

    Returns:
        List of span texts matching the query.
    """
    results = []
    try:
        with psycopg.connect(conn_str) as conn:
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
        import logging
        logging.warning(f"Could not perform semantic search: {e}")
        
    return results


def get_topics_for_ticker(conn_str: str, ticker: str, limit: int = 5) -> list[list[str]]:
    """Retrieve the top NLP themes extracted for the latest call of a ticker."""
    topics = []
    try:
        with psycopg.connect(conn_str) as conn:
            with conn.cursor() as cur:
                # We order by calls.created_at DESC to get the latest transcript for this ticker
                cur.execute(
                    """
                    SELECT ct.terms
                    FROM call_topics ct
                    JOIN calls c ON ct.call_id = c.id
                    WHERE c.ticker = %s
                    ORDER BY c.created_at DESC, ct.rank_order ASC
                    LIMIT %s
                    """,
                    (ticker, limit),
                )
                topics = [row[0] for row in cur.fetchall()]
    except Exception as e:
        import logging
        logging.warning(f"Could not fetch topics: {e}")
    return topics


def get_takeaways_for_ticker(conn_str: str, ticker: str, limit: int = 3) -> list[str]:
    """Retrieve the top TextRank sentences extracted for the latest call of a ticker."""
    takeaways = []
    try:
        with psycopg.connect(conn_str) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT s.text
                    FROM spans s
                    JOIN calls c ON s.call_id = c.id
                    WHERE c.ticker = %s AND s.textrank_score IS NOT NULL
                    ORDER BY c.created_at DESC, s.textrank_score DESC
                    LIMIT %s
                    """,
                    (ticker, limit),
                )
                takeaways = [row[0] for row in cur.fetchall()]
    except Exception as e:
        import logging
        logging.warning(f"Could not fetch takeaways: {e}")
    return takeaways


def get_keywords_for_ticker(conn_str: str, ticker: str, limit: int = 15) -> list[str]:
    """Retrieve the top TF-IDF keywords extracted for the latest call of a ticker."""
    keywords = []
    try:
        with psycopg.connect(conn_str) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT sk.term
                    FROM span_keywords sk
                    JOIN calls c ON sk.call_id = c.id
                    WHERE c.ticker = %s
                    ORDER BY c.created_at DESC, sk.score DESC
                    LIMIT %s
                    """,
                    (ticker, limit),
                )
                keywords = [row[0] for row in cur.fetchall()]
    except Exception as e:
        import logging
        logging.warning(f"Could not fetch keywords: {e}")
    return keywords


def save_analysis(conn_str: str, result: CallAnalysis) -> None:
    """Save the full call analysis result to the database.

    All records are inserted in a single transaction.  If a call with
    the same ticker and quarter already exists, the transaction will
    fail with a unique constraint violation.

    Args:
        conn_str: PostgreSQL connection string (e.g. ``dbname=earnings_teacher``)
        result: The structured analysis output to save.
    """
    # Use context managers to auto-commit on success or rollback on error.
    with psycopg.connect(conn_str) as conn:
        register_vector(conn)
        with conn.cursor() as cur:
            call = result.call
            fiscal_quarter = f"Q? {call.ticker}"
            
            # 0. Delete any existing record for this transcript so re-ingestion is idempotent
            cur.execute(
                "DELETE FROM calls WHERE ticker = %s AND fiscal_quarter = %s",
                (call.ticker, fiscal_quarter)
            )

            # 1. Insert Call
            cur.execute(
                """
                INSERT INTO calls (
                    id, ticker, company_name, fiscal_quarter, call_date,
                    transcript_json, transcript_text, token_count,
                    prepared_len, qa_len
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """,
                (
                    str(call.id),
                    call.ticker,
                    None,  # company_name
                    fiscal_quarter,
                    None,  # call_date
                    call.transcript_json,
                    call.transcript_text,
                    call.token_count,
                    call.prepared_len,
                    call.qa_len,
                )
            )

            # 2. Insert Speakers
            # We map speaker names to UUIDs to link the spans correctly.
            speaker_ids: dict[str, str] = {}
            for sp in result.speakers:
                # generate a UUID for the speaker
                import uuid
                sid = str(uuid.uuid4())
                speaker_ids[sp.name] = sid
                cur.execute(
                    """
                    INSERT INTO speakers (
                        id, call_id, name, role, title, firm, turn_count
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s)
                    """,
                    (
                        sid,
                        str(call.id),
                        sp.name,
                        sp.role,
                        sp.title,
                        sp.firm,
                        sp.turn_count,
                    )
                )

            # 3. Insert Spans (including takeaways)
            # Takeaways might be standalone SpanRecord objects not in result.spans.
            # Combine them, using a dictionary to guarantee we don't insert duplicates if
            # modified in-place.
            all_spans = {s.id: s for s in result.spans}
            for t in result.takeaways:
                if t.id not in all_spans:
                    all_spans[t.id] = t
                    
            for span in all_spans.values():
                speaker_id = speaker_ids.get(span.speaker_name)
                cur.execute(
                    """
                    INSERT INTO spans (
                        id, call_id, speaker_id, section, span_type,
                        sequence_order, text, char_count, textrank_score, embedding
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    """,
                    (
                        str(span.id),
                        str(call.id),
                        speaker_id,
                        span.section,
                        span.span_type,
                        span.sequence_order,
                        span.text,
                        span.char_count,
                        span.textrank_score,
                        span.embedding,
                    )
                )

            # 4. Insert Topics (NMF Themes)
            for topic in result.topics:
                cur.execute(
                    """
                    INSERT INTO call_topics (
                        call_id, label, terms, weight, rank_order
                    ) VALUES (%s, %s, %s, %s, %s)
                    """,
                    (
                        str(call.id),
                        topic.label,
                        topic.terms,
                        topic.weight,
                        topic.rank_order,
                    )
                )

            # 5. Insert Keywords (TF-IDF)
            for kw in result.keywords:
                cur.execute(
                    """
                    INSERT INTO span_keywords (
                        call_id, term, score, ngram_size
                    ) VALUES (%s, %s, %s, %s)
                    """,
                    (
                        str(call.id),
                        kw.term,
                        kw.score,
                        kw.ngram_size,
                    )
                )

            # 6. Insert Q&A Pairs
            for pair in result.qa_pairs:
                # Our schema is 1-to-1 question to answer span, but the exchange
                # extractor groups multiple questions/answers. For MVP persistence,
                # we'll create a pair row for the *first* question and answer span
                # in each exchange to satisfy the schema constraints.
                if not pair.question_span_ids or not pair.answer_span_ids:
                    continue
                    
                q_id = str(pair.question_span_ids[0])
                a_id = str(pair.answer_span_ids[0])
                
                cur.execute(
                    """
                    INSERT INTO qa_pairs (
                        call_id, exchange_order, question_span_id, answer_span_id
                    ) VALUES (%s, %s, %s, %s)
                    """,
                    (
                        str(call.id),
                        pair.exchange_order,
                        q_id,
                        a_id,
                    )
                )

            # 7. Insert Agentic Pipeline Outputs (Transcript Chunks and Entities)
            for chunk in getattr(result, "chunks", []):
                cur.execute(
                    """
                    INSERT INTO transcript_chunks (
                        call_id, chunk_id, chunk_type, sequence_order, tier1_score, needs_deep_analysis
                    ) VALUES (%s, %s, %s, %s, %s, %s)
                    """,
                    (
                        str(call.id),
                        chunk.chunk_id,
                        chunk.chunk_type,
                        chunk.sequence_order,
                        getattr(chunk, "tier1_score", None),
                        getattr(chunk, "requires_deep_analysis", False)
                    )
                )

                # Tier 1: Extracted Terms
                for term_data in getattr(chunk, "extracted_terms", []):
                    cur.execute(
                        """
                        INSERT INTO extracted_terms (call_id, chunk_id, term, definition)
                        VALUES (%s, %s, %s, %s)
                        """,
                        (str(call.id), chunk.chunk_id, term_data.get("term", ""), term_data.get("definition", ""))
                    )

                # Tier 1: Core Concepts
                for concept in getattr(chunk, "core_concepts", []):
                    cur.execute(
                        """
                        INSERT INTO core_concepts (call_id, chunk_id, concept)
                        VALUES (%s, %s, %s)
                        """,
                        (str(call.id), chunk.chunk_id, concept)
                    )

                # Tier 2: Takeaways
                for takeaway_data in getattr(chunk, "takeaways", []):
                    cur.execute(
                        """
                        INSERT INTO extracted_takeaways (call_id, chunk_id, takeaway, why_it_matters)
                        VALUES (%s, %s, %s, %s)
                        """,
                        (str(call.id), chunk.chunk_id, takeaway_data.get("takeaway", ""), takeaway_data.get("why_it_matters", ""))
                    )

                # Tier 2: Evasion Analysis
                evasion = getattr(chunk, "evasion_analysis", None)
                if evasion:
                    cur.execute(
                        """
                        INSERT INTO evasion_analysis (
                            call_id, chunk_id, analyst_concern, defensiveness_score, evasion_explanation
                        ) VALUES (%s, %s, %s, %s, %s)
                        """,
                        (
                            str(call.id),
                            chunk.chunk_id,
                            evasion.get("analyst_concern", ""),
                            evasion.get("defensiveness_score", 0),
                            evasion.get("evasion_explanation", "")
                        )
                    )

                # Tier 2: Misconceptions
                for gotcha in getattr(chunk, "misconceptions", []):
                    cur.execute(
                        """
                        INSERT INTO misconceptions (
                            call_id, chunk_id, fact, misinterpretation, correction
                        ) VALUES (%s, %s, %s, %s, %s)
                        """,
                        (str(call.id), chunk.chunk_id, gotcha.get("fact", ""), gotcha.get("misinterpretation", ""), gotcha.get("correction", ""))
                    )

        # Commit the transaction explicitly.
        conn.commit()

