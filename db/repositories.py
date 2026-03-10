import uuid
import logging
import psycopg
from pgvector.psycopg import register_vector
from core.models import CallAnalysis

logger = logging.getLogger(__name__)

class CallRepository:
    def __init__(self, conn_str: str):
        self.conn_str = conn_str

    def get_all_calls(self) -> list[tuple[str, str]]:
        calls = []
        try:
            with psycopg.connect(self.conn_str) as conn:
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
            logger.warning(f"Could not fetch calls: {e}")
        return calls


class EmbeddingRepository:
    def __init__(self, conn_str: str):
        self.conn_str = conn_str

    def fetch_existing_embeddings(self, ticker: str, fiscal_quarter: str) -> dict[str, list[float]]:
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


class AnalysisRepository:
    def __init__(self, conn_str: str):
        self.conn_str = conn_str

    def get_topics_for_ticker(self, ticker: str, limit: int = 5) -> list[list[str]]:
        topics = []
        try:
            with psycopg.connect(self.conn_str) as conn:
                with conn.cursor() as cur:
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
            logger.warning(f"Could not fetch topics: {e}")
        return topics

    def get_themes_for_ticker(self, ticker: str) -> list[str]:
        themes = []
        try:
            with psycopg.connect(self.conn_str) as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        """
                        SELECT cs.key_themes
                        FROM call_synthesis cs
                        JOIN calls c ON cs.call_id = c.id
                        WHERE c.ticker = %s
                        """,
                        (ticker,),
                    )
                    row = cur.fetchone()
                    if row and row[0]:
                        # key_themes is a TEXT[] array in postgres, psycopg maps it to a py list
                        themes = row[0]
        except Exception as e:
            logger.warning(f"Could not fetch themes: {e}")
        return themes

    def get_takeaways_for_ticker(self, ticker: str, limit: int = 5) -> list[tuple[str, str]]:
        takeaways = []
        try:
            with psycopg.connect(self.conn_str) as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        """
                        SELECT et.takeaway, et.why_it_matters
                        FROM extracted_takeaways et
                        JOIN calls c ON et.call_id = c.id
                        WHERE c.ticker = %s
                        ORDER BY c.created_at DESC, et.id ASC
                        LIMIT %s
                        """,
                        (ticker, limit),
                    )
                    takeaways = cur.fetchall()
        except Exception as e:
            logger.warning(f"Could not fetch takeaways: {e}")
        return takeaways

    def get_keywords_for_ticker(self, ticker: str, limit: int = 15) -> list[str]:
        keywords = []
        try:
            with psycopg.connect(self.conn_str) as conn:
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
            logger.warning(f"Could not fetch keywords: {e}")
        return keywords

    def get_extracted_terms_for_ticker(self, ticker: str, limit: int = 15) -> list[tuple[str, str, str]]:
        terms = []
        try:
            with psycopg.connect(self.conn_str) as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        """
                        SELECT et.term, et.definition, COALESCE(et.explanation, '')
                        FROM extracted_terms et
                        JOIN calls c ON et.call_id = c.id
                        WHERE c.ticker = %s
                        ORDER BY c.created_at DESC, et.term ASC
                        LIMIT %s
                        """,
                        (ticker, limit),
                    )
                    terms = cur.fetchall()
        except Exception as e:
            logger.warning(f"Could not fetch extracted terms: {e}")
        return terms

    def update_term_definition(self, ticker: str, term: str, definition: str) -> bool:
        """Update the definition for a specific term belonging to a given ticker."""
        try:
            with psycopg.connect(self.conn_str) as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        """
                        UPDATE extracted_terms
                        SET definition = %s
                        FROM calls c
                        WHERE extracted_terms.call_id = c.id
                          AND c.ticker = %s
                          AND extracted_terms.term = %s
                        """,
                        (definition, ticker, term)
                    )
                    conn.commit()
                    return cur.rowcount > 0
        except Exception as e:
            logger.warning(f"Could not update term definition: {e}")
            return False

    def update_term_explanation(self, ticker: str, term: str, explanation: str) -> bool:
        """Update the contextual explanation for a specific term belonging to a given ticker."""
        try:
            with psycopg.connect(self.conn_str) as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        """
                        UPDATE extracted_terms
                        SET explanation = %s
                        FROM calls c
                        WHERE extracted_terms.call_id = c.id
                          AND c.ticker = %s
                          AND extracted_terms.term = %s
                        """,
                        (explanation, ticker, term)
                    )
                    conn.commit()
                    return cur.rowcount > 0
        except Exception as e:
            logger.warning(f"Could not update term explanation: {e}")
            return False

    def save_analysis(self, result: CallAnalysis) -> None:
        with psycopg.connect(self.conn_str) as conn:
            register_vector(conn)
            with conn.cursor() as cur:
                self._save_call(cur, result.call)
                speaker_ids = self._save_speakers(cur, result.call.id, result.speakers)
                self._save_spans(cur, result.call.id, result.spans, result.takeaways, speaker_ids)
                self._save_topics(cur, result.call.id, result.topics)
                self._save_keywords(cur, result.call.id, result.keywords)
                self._save_qa_pairs(cur, result.call.id, result.qa_pairs)
                self._save_agentic_chunks(cur, result.call.id, getattr(result, "chunks", []))
                if getattr(result, "synthesis", None):
                    self._save_call_synthesis(cur, result.call.id, result.synthesis)
            conn.commit()

    def _save_call_synthesis(self, cur, call_id, synthesis):
        cur.execute(
            """
            INSERT INTO call_synthesis (
                id, call_id, overall_sentiment, executive_tone,
                key_themes, strategic_shifts, analyst_sentiment
            ) VALUES (%s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (call_id) DO UPDATE SET
                overall_sentiment = EXCLUDED.overall_sentiment,
                executive_tone = EXCLUDED.executive_tone,
                key_themes = EXCLUDED.key_themes,
                strategic_shifts = EXCLUDED.strategic_shifts,
                analyst_sentiment = EXCLUDED.analyst_sentiment
            """,
            (
                str(synthesis.id),
                str(call_id),
                synthesis.overall_sentiment,
                synthesis.executive_tone,
                synthesis.key_themes,
                synthesis.strategic_shifts,
                synthesis.analyst_sentiment
            )
        )

    def _save_call(self, cur, call):
        fiscal_quarter = f"Q? {call.ticker}"
        cur.execute(
            "DELETE FROM calls WHERE ticker = %s AND fiscal_quarter = %s",
            (call.ticker, fiscal_quarter)
        )
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

    def _save_speakers(self, cur, call_id, speakers) -> dict[str, str]:
        speaker_ids: dict[str, str] = {}
        for sp in speakers:
            sid = str(uuid.uuid4())
            speaker_ids[sp.name] = sid
            cur.execute(
                """
                INSERT INTO speakers (
                    id, call_id, name, role, title, firm, turn_count
                ) VALUES (%s, %s, %s, %s, %s, %s, %s)
                """,
                (sid, str(call_id), sp.name, sp.role, sp.title, sp.firm, sp.turn_count)
            )
        return speaker_ids

    def _save_spans(self, cur, call_id, spans, takeaways, speaker_ids):
        all_spans = {s.id: s for s in spans}
        for t in takeaways:
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
                    str(span.id), str(call_id), speaker_id, span.section,
                    span.span_type, span.sequence_order, span.text,
                    span.char_count, span.textrank_score, span.embedding,
                )
            )

    def _save_topics(self, cur, call_id, topics):
        for topic in topics:
            cur.execute(
                """
                INSERT INTO call_topics (
                    call_id, label, terms, weight, rank_order
                ) VALUES (%s, %s, %s, %s, %s)
                """,
                (str(call_id), topic.label, topic.terms, topic.weight, topic.rank_order)
            )

    def _save_keywords(self, cur, call_id, keywords):
        for kw in keywords:
            cur.execute(
                """
                INSERT INTO span_keywords (
                    call_id, term, score, ngram_size
                ) VALUES (%s, %s, %s, %s)
                """,
                (str(call_id), kw.term, kw.score, kw.ngram_size)
            )

    def _save_qa_pairs(self, cur, call_id, qa_pairs):
        for pair in qa_pairs:
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
                (str(call_id), pair.exchange_order, q_id, a_id)
            )

    def _save_agentic_chunks(self, cur, call_id, chunks):
        for chunk in chunks:
            cur.execute(
                """
                INSERT INTO transcript_chunks (
                    call_id, chunk_id, chunk_type, sequence_order, tier1_score, needs_deep_analysis
                ) VALUES (%s, %s, %s, %s, %s, %s)
                """,
                (
                    str(call_id), chunk.chunk_id, chunk.chunk_type,
                    chunk.sequence_order, getattr(chunk, "tier1_score", None),
                    getattr(chunk, "requires_deep_analysis", False)
                )
            )
            for term_data in getattr(chunk, "extracted_terms", []):
                term = term_data.get("term")
                if not term: continue
                cur.execute(
                    """
                    INSERT INTO extracted_terms (call_id, chunk_id, term, definition, explanation)
                    VALUES (%s, %s, %s, %s, %s)
                    """,
                    (str(call_id), chunk.chunk_id, term, term_data.get("definition") or "", term_data.get("explanation") or "")
                )
            for concept in getattr(chunk, "core_concepts", []):
                if not concept: continue
                cur.execute(
                    """
                    INSERT INTO core_concepts (call_id, chunk_id, concept)
                    VALUES (%s, %s, %s)
                    """,
                    (str(call_id), chunk.chunk_id, concept)
                )
            for takeaway_data in getattr(chunk, "takeaways", []):
                takeaway = takeaway_data.get("takeaway")
                if not takeaway: continue
                cur.execute(
                    """
                    INSERT INTO extracted_takeaways (call_id, chunk_id, takeaway, why_it_matters)
                    VALUES (%s, %s, %s, %s)
                    """,
                    (str(call_id), chunk.chunk_id, takeaway, takeaway_data.get("why_it_matters") or "")
                )
            evasion = getattr(chunk, "evasion_analysis", None)
            if evasion and evasion.get("analyst_concern"):
                cur.execute(
                    """
                    INSERT INTO evasion_analysis (
                        call_id, chunk_id, analyst_concern, defensiveness_score, evasion_explanation
                    ) VALUES (%s, %s, %s, %s, %s)
                    """,
                    (
                        str(call_id), chunk.chunk_id, evasion.get("analyst_concern"),
                        evasion.get("defensiveness_score") or 0, evasion.get("evasion_explanation") or ""
                    )
                )
            for gotcha in getattr(chunk, "misconceptions", []):
                fact = gotcha.get("fact")
                if not fact: continue
                cur.execute(
                    """
                    INSERT INTO misconceptions (
                        call_id, chunk_id, fact, misinterpretation, correction
                    ) VALUES (%s, %s, %s, %s, %s)
                    """,
                    (str(call_id), chunk.chunk_id, fact, gotcha.get("misinterpretation") or "", gotcha.get("correction") or "")
                )
