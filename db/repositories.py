import uuid
import logging
import psycopg
import psycopg.errors
from pgvector.psycopg import register_vector
from core.models import CallAnalysis, TranscriptChunk

logger = logging.getLogger(__name__)

class OutdatedSchemaError(Exception):
    """Exception raised when the database schema is out of date."""
    pass

REQUIRED_SCHEMA_VERSION = 2


def reset_all_data(conn_str: str) -> None:
    """Delete all application data from the database, preserving the schema."""
    # Deleting from calls cascades to all dependent tables via ON DELETE CASCADE.
    # learning_sessions and concept_exercises are not linked to calls so are truncated separately.
    with psycopg.connect(conn_str) as conn:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM learning_sessions")
            cur.execute("DELETE FROM calls")
        conn.commit()


class SchemaRepository:
    def __init__(self, conn_str: str):
        self.conn_str = conn_str

    def get_current_version(self) -> int:
        """Get the current schema version from the database. Returns 0 if table missing or empty."""
        try:
            with psycopg.connect(self.conn_str) as conn:
                with conn.cursor() as cur:
                    cur.execute("SELECT version FROM schema_version ORDER BY installed_at DESC LIMIT 1")
                    row = cur.fetchone()
                    return row[0] if row else 0
        except psycopg.errors.UndefinedTable:
            return 0
        except Exception as e:
            logger.warning(f"Error checking schema version: {e}")
            return 0

    def check_health(self) -> tuple[bool, str]:
        """Check if the database schema is up to date."""
        current_version = self.get_current_version()
        if current_version < REQUIRED_SCHEMA_VERSION:
            if current_version == 0:
                msg = "Database schema version table is missing. Re-initialize the database."
            else:
                msg = f"Database schema is outdated (current: {current_version}, required: {REQUIRED_SCHEMA_VERSION})."
            return False, f"{msg} Run 'python migrate.py' or './reset_db.sh' to update."
        return True, "Database schema is up to date."


class CallRepository:
    def __init__(self, conn_str: str):
        self.conn_str = conn_str

    def get_company_info(self, ticker: str) -> tuple[str, str]:
        """Return (company_name, industry) for a ticker, or empty strings if not found."""
        try:
            with psycopg.connect(self.conn_str) as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        "SELECT company_name, industry FROM calls WHERE ticker = %s LIMIT 1",
                        (ticker,),
                    )
                    row = cur.fetchone()
                    if row:
                        return (row[0] or "", row[1] or "")
        except Exception as e:
            logger.warning(f"Could not fetch company info for {ticker}: {e}")
        return ("", "")

    def get_call_date(self, ticker: str):
        """Return the call_date for a ticker, or None if not set."""
        try:
            with psycopg.connect(self.conn_str) as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        "SELECT call_date FROM calls WHERE ticker = %s LIMIT 1",
                        (ticker,),
                    )
                    row = cur.fetchone()
                    return row[0] if row else None
        except Exception as e:
            logger.warning(f"Could not fetch call_date for {ticker}: {e}")
            return None

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

    def get_synthesis_for_ticker(self, ticker: str) -> tuple[str, str, str] | None:
        """Return (overall_sentiment, executive_tone, analyst_sentiment) for a ticker."""
        try:
            with psycopg.connect(self.conn_str) as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        """
                        SELECT cs.overall_sentiment, cs.executive_tone, cs.analyst_sentiment
                        FROM call_synthesis cs
                        JOIN calls c ON cs.call_id = c.id
                        WHERE c.ticker = %s
                        """,
                        (ticker,),
                    )
                    return cur.fetchone()
        except Exception as e:
            logger.warning(f"Could not fetch synthesis for {ticker}: {e}")
        return None

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

    def get_speakers_for_ticker(self, ticker: str) -> list[tuple[str, str, str | None, str | None]]:
        """Return speakers for a ticker as (name, role, title, firm) ordered by role then name."""
        rows = []
        try:
            with psycopg.connect(self.conn_str) as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        """
                        SELECT sp.name, sp.role, sp.title, sp.firm
                        FROM speakers sp
                        JOIN calls c ON sp.call_id = c.id
                        WHERE c.ticker = %s AND sp.role != 'operator'
                        ORDER BY
                            CASE sp.role WHEN 'executive' THEN 0 WHEN 'analyst' THEN 1 ELSE 2 END,
                            sp.name ASC
                        """,
                        (ticker,),
                    )
                    rows = cur.fetchall()
        except Exception as e:
            logger.warning(f"Could not fetch speakers: {e}")
        return rows

    def get_spans_for_ticker(self, ticker: str) -> list[tuple[str, str, str]]:
        """Return all speaker turns for a ticker in transcript order as (speaker, section, text) tuples."""
        rows = []
        try:
            with psycopg.connect(self.conn_str) as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        """
                        SELECT COALESCE(sp.name, 'Unknown'), s.section, s.text
                        FROM spans s
                        JOIN calls c ON s.call_id = c.id
                        LEFT JOIN speakers sp ON s.speaker_id = sp.id
                        WHERE c.ticker = %s AND s.span_type = 'turn' AND s.sequence_order >= 0
                        ORDER BY s.sequence_order ASC
                        """,
                        (ticker,),
                    )
                    rows = cur.fetchall()
        except Exception as e:
            logger.warning(f"Could not fetch spans: {e}")
        return rows

    def get_evasion_for_ticker(self, ticker: str) -> list[tuple[str, int, str]]:
        """Return evasion analysis entries for a ticker as (analyst_concern, defensiveness_score, evasion_explanation)."""
        rows = []
        try:
            with psycopg.connect(self.conn_str) as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        """
                        SELECT ea.analyst_concern, ea.defensiveness_score, ea.evasion_explanation
                        FROM evasion_analysis ea
                        JOIN calls c ON ea.call_id = c.id
                        WHERE c.ticker = %s
                        ORDER BY ea.defensiveness_score DESC
                        """,
                        (ticker,),
                    )
                    rows = cur.fetchall()
        except Exception as e:
            logger.warning(f"Could not fetch evasion analysis for {ticker}: {e}")
        return rows

    def get_misconceptions_for_ticker(self, ticker: str) -> list[tuple[str, str, str]]:
        """Return misconception entries for a ticker as (fact, misinterpretation, correction)."""
        rows = []
        try:
            with psycopg.connect(self.conn_str) as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        """
                        SELECT m.fact, m.misinterpretation, m.correction
                        FROM misconceptions m
                        JOIN calls c ON m.call_id = c.id
                        WHERE c.ticker = %s
                        ORDER BY m.id ASC
                        """,
                        (ticker,),
                    )
                    rows = cur.fetchall()
        except Exception as e:
            logger.warning(f"Could not fetch misconceptions for {ticker}: {e}")
        return rows

    def get_industry_terms_for_ticker(self, ticker: str, limit: int = 30) -> list[tuple[str, str, str]]:
        """Return deduplicated industry-specific terms for a ticker as (term, definition, explanation)."""
        terms = []
        try:
            with psycopg.connect(self.conn_str) as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        """
                        SELECT DISTINCT ON (et.term) et.term, et.definition, COALESCE(et.explanation, '')
                        FROM extracted_terms et
                        JOIN calls c ON et.call_id = c.id
                        WHERE c.ticker = %s AND et.category = 'industry'
                        ORDER BY et.term ASC
                        LIMIT %s
                        """,
                        (ticker, limit),
                    )
                    terms = cur.fetchall()
        except Exception as e:
            logger.warning(f"Could not fetch industry terms: {e}")
        return terms

    def get_financial_terms_for_ticker(self, ticker: str, limit: int = 50) -> list[tuple[str, str, str]]:
        """Return deduplicated financial terms found in a transcript as (term, definition, explanation)."""
        terms = []
        try:
            with psycopg.connect(self.conn_str) as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        """
                        SELECT DISTINCT ON (et.term) et.term, et.definition, COALESCE(et.explanation, '')
                        FROM extracted_terms et
                        JOIN calls c ON et.call_id = c.id
                        WHERE c.ticker = %s AND et.category = 'financial'
                        ORDER BY et.term ASC
                        LIMIT %s
                        """,
                        (ticker, limit),
                    )
                    terms = cur.fetchall()
        except Exception as e:
            logger.warning(f"Could not fetch financial terms: {e}")
        return terms

    def get_extracted_terms_for_ticker(self, ticker: str, limit: int = 15) -> list[tuple[str, str, str]]:
        """Return deduplicated terms of all categories for a ticker (legacy method)."""
        terms = []
        try:
            with psycopg.connect(self.conn_str) as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        """
                        SELECT DISTINCT ON (et.term) et.term, et.definition, COALESCE(et.explanation, '')
                        FROM extracted_terms et
                        JOIN calls c ON et.call_id = c.id
                        WHERE c.ticker = %s
                        ORDER BY et.term ASC
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
                id, ticker, company_name, industry, fiscal_quarter, call_date,
                transcript_json, transcript_text, token_count,
                prepared_len, qa_len
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """,
            (
                str(call.id),
                call.ticker,
                call.company_name or None,
                call.industry or None,
                fiscal_quarter,
                call.call_date or None,
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

    def _save_agentic_chunks(self, cur, call_id, chunks: list[TranscriptChunk]) -> None:
        """Persist all LLM-extracted data for each chunk."""
        for chunk in chunks:
            self._save_chunk_record(cur, call_id, chunk)
            self._save_chunk_terms(cur, call_id, chunk)
            self._save_chunk_concepts(cur, call_id, chunk)
            self._save_chunk_takeaways(cur, call_id, chunk)
            self._save_chunk_evasion(cur, call_id, chunk)
            self._save_chunk_misconceptions(cur, call_id, chunk)

    def _save_chunk_record(self, cur, call_id, chunk: TranscriptChunk) -> None:
        """Insert the transcript_chunks row for one chunk."""
        cur.execute(
            """
            INSERT INTO transcript_chunks (
                call_id, chunk_id, chunk_type, sequence_order, tier1_score, needs_deep_analysis, chunk_text
            ) VALUES (%s, %s, %s, %s, %s, %s, %s)
            """,
            (
                str(call_id), chunk.chunk_id, chunk.chunk_type,
                chunk.sequence_order, chunk.tier1_score,
                chunk.requires_deep_analysis,
                chunk.text,
            ),
        )

    def _save_chunk_terms(self, cur, call_id, chunk: TranscriptChunk) -> None:
        """Insert extracted_terms rows for one chunk."""
        for term_data in chunk.extracted_terms:
            term = term_data.get("term")
            if not term:
                continue
            cur.execute(
                """
                INSERT INTO extracted_terms (call_id, chunk_id, term, definition, explanation, category)
                VALUES (%s, %s, %s, %s, %s, %s)
                """,
                (
                    str(call_id), chunk.chunk_id, term,
                    term_data.get("definition") or "",
                    term_data.get("explanation") or "",
                    term_data.get("category") or "industry",
                ),
            )

    def _save_chunk_concepts(self, cur, call_id, chunk: TranscriptChunk) -> None:
        """Insert core_concepts rows for one chunk."""
        for concept in chunk.core_concepts:
            if not concept:
                continue
            cur.execute(
                "INSERT INTO core_concepts (call_id, chunk_id, concept) VALUES (%s, %s, %s)",
                (str(call_id), chunk.chunk_id, concept),
            )

    def _save_chunk_takeaways(self, cur, call_id, chunk: TranscriptChunk) -> None:
        """Insert extracted_takeaways rows for one chunk."""
        for takeaway_data in chunk.takeaways:
            takeaway = takeaway_data.get("takeaway")
            if not takeaway:
                continue
            cur.execute(
                """
                INSERT INTO extracted_takeaways (call_id, chunk_id, takeaway, why_it_matters)
                VALUES (%s, %s, %s, %s)
                """,
                (str(call_id), chunk.chunk_id, takeaway, takeaway_data.get("why_it_matters") or ""),
            )

    def _save_chunk_evasion(self, cur, call_id, chunk: TranscriptChunk) -> None:
        """Insert evasion_analysis row for one chunk if present."""
        evasion = chunk.evasion_analysis
        if not evasion or not evasion.get("analyst_concern"):
            return
        cur.execute(
            """
            INSERT INTO evasion_analysis (
                call_id, chunk_id, analyst_concern, defensiveness_score, evasion_explanation
            ) VALUES (%s, %s, %s, %s, %s)
            """,
            (
                str(call_id), chunk.chunk_id, evasion.get("analyst_concern"),
                evasion.get("defensiveness_score") or 0,
                evasion.get("evasion_explanation") or "",
            ),
        )

    def _save_chunk_misconceptions(self, cur, call_id, chunk: TranscriptChunk) -> None:
        """Insert misconceptions rows for one chunk."""
        for gotcha in chunk.misconceptions:
            fact = gotcha.get("fact")
            if not fact:
                continue
            cur.execute(
                """
                INSERT INTO misconceptions (
                    call_id, chunk_id, fact, misinterpretation, correction
                ) VALUES (%s, %s, %s, %s, %s)
                """,
                (
                    str(call_id), chunk.chunk_id, fact,
                    gotcha.get("misinterpretation") or "",
                    gotcha.get("correction") or "",
                ),
            )


SYSTEM_USER_ID = "00000000-0000-0000-0000-000000000001"


class LearningRepository:
    """Read/write Feynman learning sessions and concept exercises."""

    def __init__(self, conn_str: str):
        self.conn_str = conn_str

    def _get_call_id(self, cur, ticker: str) -> str | None:
        """Look up the call UUID for a ticker."""
        cur.execute("SELECT id FROM calls WHERE ticker = %s LIMIT 1", (ticker,))
        row = cur.fetchone()
        return str(row[0]) if row else None

    def save_session(
        self,
        ticker: str,
        session_id: str,
        topic: str,
        stage: int,
        messages: list[dict],
        completed: bool,
    ) -> bool:
        """Upsert a learning session. Stores full message history in notes as JSON. Returns True on success."""
        import json
        try:
            with psycopg.connect(self.conn_str) as conn:
                with conn.cursor() as cur:
                    call_id = self._get_call_id(cur, ticker)
                    if not call_id:
                        logger.warning(f"No call found for ticker {ticker}, skipping session save")
                        return False
                    notes = json.dumps({"topic": topic, "stage": stage, "messages": messages})
                    completed_at_expr = "now()" if completed else "NULL"
                    cur.execute(
                        f"""
                        INSERT INTO learning_sessions (id, user_id, call_id, notes, completed_at)
                        VALUES (%s, %s, %s, %s, {completed_at_expr})
                        ON CONFLICT (id) DO UPDATE SET
                            notes = EXCLUDED.notes,
                            completed_at = COALESCE(learning_sessions.completed_at, EXCLUDED.completed_at)
                        """,
                        (session_id, SYSTEM_USER_ID, call_id, notes),
                    )
                    if completed:
                        teaching_note = next(
                            (m["content"] for m in reversed(messages)
                             if m.get("role") == "assistant" and m.get("feynman_stage") == 5),
                            None,
                        )
                        cur.execute(
                            """
                            INSERT INTO concept_exercises (session_id, concept_label, ai_critique)
                            SELECT %s, %s, %s
                            WHERE NOT EXISTS (SELECT 1 FROM concept_exercises WHERE session_id = %s)
                            """,
                            (session_id, topic, teaching_note, session_id),
                        )
                conn.commit()
            return True
        except Exception as e:
            logger.warning(f"Could not save learning session: {e}")
            return False

    def get_sessions_for_ticker(self, ticker: str) -> list[dict]:
        """Return all sessions for a ticker, newest first. Each dict has: id, topic, stage, completed, teaching_note, started_at."""
        import json
        rows = []
        try:
            with psycopg.connect(self.conn_str) as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        """
                        SELECT ls.id, ls.notes, ls.completed_at, ls.started_at,
                               ce.ai_critique
                        FROM learning_sessions ls
                        JOIN calls c ON ls.call_id = c.id
                        LEFT JOIN concept_exercises ce ON ce.session_id = ls.id
                        WHERE c.ticker = %s
                        ORDER BY ls.started_at DESC
                        """,
                        (ticker,),
                    )
                    for row in cur.fetchall():
                        session_id, notes_json, completed_at, started_at, teaching_note = row
                        notes = json.loads(notes_json) if notes_json else {}
                        rows.append({
                            "id": str(session_id),
                            "topic": notes.get("topic", "Unknown topic"),
                            "stage": notes.get("stage", 1),
                            "messages": notes.get("messages", []),
                            "completed": completed_at is not None,
                            "teaching_note": teaching_note,
                            "started_at": started_at,
                        })
        except Exception as e:
            logger.warning(f"Could not fetch sessions for ticker {ticker}: {e}")
        return rows

    def get_learning_stats(self) -> dict:
        """Return overall learning stats: tickers_studied, total_sessions, completed_sessions."""
        stats = {"tickers_studied": 0, "total_sessions": 0, "completed_sessions": 0}
        try:
            with psycopg.connect(self.conn_str) as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        """
                        SELECT COUNT(DISTINCT c.ticker),
                               COUNT(ls.id),
                               SUM(CASE WHEN ls.completed_at IS NOT NULL THEN 1 ELSE 0 END)
                        FROM learning_sessions ls
                        JOIN calls c ON ls.call_id = c.id
                        """
                    )
                    row = cur.fetchone()
                    if row:
                        stats["tickers_studied"] = row[0] or 0
                        stats["total_sessions"] = row[1] or 0
                        stats["completed_sessions"] = int(row[2] or 0)
        except Exception as e:
            logger.warning(f"Could not fetch learning stats: {e}")
        return stats

    def get_ticker_session_counts(self) -> list[tuple[str, int, int]]:
        """Return (ticker, total_sessions, completed_sessions) for all tickers that have learning history."""
        rows = []
        try:
            with psycopg.connect(self.conn_str) as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        """
                        SELECT c.ticker,
                               COUNT(ls.id),
                               SUM(CASE WHEN ls.completed_at IS NOT NULL THEN 1 ELSE 0 END)
                        FROM learning_sessions ls
                        JOIN calls c ON ls.call_id = c.id
                        GROUP BY c.ticker
                        ORDER BY COUNT(ls.id) DESC
                        """
                    )
                    rows = [(r[0], r[1], int(r[2] or 0)) for r in cur.fetchall()]
        except Exception as e:
            logger.warning(f"Could not fetch ticker session counts: {e}")
        return rows
