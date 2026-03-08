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

            # 1. Insert Call
            call = result.call
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
                    f"Q? {call.ticker}",  # placeholder until we parse it from transcript
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
            for span in result.spans:
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

        # Commit the transaction explicitly.
        conn.commit()

