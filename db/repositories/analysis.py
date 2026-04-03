"""Analysis data repository: read/write NLP results, terms, and synthesis."""

import logging
import uuid
from contextlib import nullcontext

import psycopg
from pgvector.psycopg import register_vector

from core.models import CallAnalysis, TranscriptChunk

logger = logging.getLogger(__name__)


class AnalysisRepository:
    def __init__(self, conn_str: str):
        self.conn_str = conn_str

    def get_topics_for_ticker(
        self, ticker: str, limit: int = 5, conn: psycopg.Connection | None = None
    ) -> list[dict]:
        """Return structured topic dicts with label, terms, and summary."""
        topics = []
        try:
            ctx = nullcontext(conn) if conn is not None else psycopg.connect(self.conn_str)
            with ctx as c:
                with c.cursor() as cur:
                    cur.execute(
                        """
                        SELECT ct.topic_name, ct.terms, COALESCE(ct.summary, '')
                        FROM call_topics ct
                        JOIN calls c ON ct.call_id = c.id
                        WHERE c.ticker = %s
                        ORDER BY c.created_at DESC, ct.rank_order ASC
                        LIMIT %s
                        """,
                        (ticker, limit),
                    )
                    topics = [
                        {"label": row[0] or (row[1][0] if row[1] else ""), "terms": row[1], "summary": row[2]}
                        for row in cur.fetchall()
                    ]
        except Exception as e:
            logger.warning(f"Could not fetch topics: {e}")
        return topics

    def get_themes_for_ticker(
        self, ticker: str, conn: psycopg.Connection | None = None
    ) -> list[str]:
        themes = []
        try:
            ctx = nullcontext(conn) if conn is not None else psycopg.connect(self.conn_str)
            with ctx as c:
                with c.cursor() as cur:
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

    def get_synthesis_for_ticker(
        self, ticker: str, conn: psycopg.Connection | None = None
    ) -> tuple[str, str, str] | None:
        """Return (overall_sentiment, executive_tone, analyst_sentiment) for a ticker."""
        try:
            ctx = nullcontext(conn) if conn is not None else psycopg.connect(self.conn_str)
            with ctx as c:
                with c.cursor() as cur:
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

    def get_strategic_shifts_for_ticker(
        self, ticker: str, conn: psycopg.Connection | None = None
    ) -> list[dict] | None:
        """Return the strategic_shifts list for a ticker as structured dicts, or None if absent."""
        try:
            ctx = nullcontext(conn) if conn is not None else psycopg.connect(self.conn_str)
            with ctx as c:
                with c.cursor() as cur:
                    cur.execute(
                        """
                        SELECT cs.strategic_shifts
                        FROM call_synthesis cs
                        JOIN calls c ON cs.call_id = c.id
                        WHERE c.ticker = %s
                        """,
                        (ticker,),
                    )
                    row = cur.fetchone()
                    if not row or not row[0]:
                        return None
                    # Normalise: old TEXT[] rows may have been migrated; ensure list[dict]
                    shifts = []
                    for item in row[0]:
                        if isinstance(item, dict):
                            shifts.append(item)
                        else:
                            shifts.append({"prior_position": "", "current_position": str(item), "investor_significance": ""})
                    return shifts
        except Exception as e:
            logger.warning(f"Could not fetch strategic_shifts for {ticker}: {e}")
        return None

    def get_call_summary_for_ticker(self, ticker: str) -> str | None:
        """Return the call_summary paragraph for a ticker, or None if absent."""
        try:
            with psycopg.connect(self.conn_str) as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        """
                        SELECT cs.call_summary
                        FROM call_synthesis cs
                        JOIN calls c ON cs.call_id = c.id
                        WHERE c.ticker = %s
                        """,
                        (ticker,),
                    )
                    row = cur.fetchone()
                    return row[0] if row else None
        except Exception as e:
            logger.warning(f"Could not fetch call_summary for {ticker}: {e}")
        return None

    def get_speaker_dynamics(self, ticker: str) -> list[dict]:
        """Return per-speaker, per-section turn and word counts for a ticker.

        Each dict contains: speaker, role, firm, section, turn_count, word_count.
        """
        rows = []
        try:
            with psycopg.connect(self.conn_str) as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        """
                        SELECT
                            COALESCE(sp.name, 'Unknown') AS speaker,
                            COALESCE(sp.role, 'unknown') AS role,
                            COALESCE(sp.firm, '') AS firm,
                            s.section,
                            COUNT(*) AS turn_count,
                            SUM(COALESCE(
                                array_length(regexp_split_to_array(trim(s.text), '\\s+'), 1),
                                0
                            )) AS word_count
                        FROM spans s
                        JOIN calls c ON s.call_id = c.id
                        LEFT JOIN speakers sp ON s.speaker_id = sp.id
                        WHERE c.ticker = %s
                          AND s.span_type = 'turn'
                          AND s.sequence_order >= 0
                          AND (sp.role IS NULL OR sp.role != 'operator')
                        GROUP BY
                            COALESCE(sp.name, 'Unknown'),
                            COALESCE(sp.role, 'unknown'),
                            COALESCE(sp.firm, ''),
                            s.section
                        ORDER BY turn_count DESC
                        """,
                        (ticker,),
                    )
                    rows = [
                        {
                            "speaker": r[0],
                            "role": r[1],
                            "firm": r[2],
                            "section": r[3],
                            "turn_count": r[4],
                            "word_count": r[5],
                        }
                        for r in cur.fetchall()
                    ]
        except Exception as e:
            logger.warning(f"Could not fetch speaker dynamics for {ticker}: {e}")
        return rows

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

    def get_keywords_for_ticker(
        self, ticker: str, limit: int = 15, conn: psycopg.Connection | None = None
    ) -> list[str]:
        keywords = []
        try:
            ctx = nullcontext(conn) if conn is not None else psycopg.connect(self.conn_str)
            with ctx as c:
                with c.cursor() as cur:
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

    def get_speakers_for_ticker(
        self, ticker: str, conn: psycopg.Connection | None = None
    ) -> list[tuple[str, str, str | None, str | None]]:
        """Return speakers for a ticker as (name, role, title, firm) ordered by role then name."""
        rows = []
        try:
            ctx = nullcontext(conn) if conn is not None else psycopg.connect(self.conn_str)
            with ctx as c:
                with c.cursor() as cur:
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

    def get_chunks_for_ticker(
        self,
        ticker: str,
        limit: int = 10,
        quarter: str | None = None,
    ) -> list[dict]:
        """Return transcript chunks for a ticker from the transcript_chunks table.

        Optionally filter to a specific quarter using the format YYYY-QN (e.g. "2025-Q4").
        Returns a list of dicts with keys: chunk_id, chunk_type, chunk_text,
        tier1_score, needs_deep_analysis.
        """
        rows = []
        try:
            with psycopg.connect(self.conn_str) as conn:
                with conn.cursor() as cur:
                    params: list = [ticker]
                    quarter_clause = ""
                    if quarter:
                        # Parse YYYY-QN into a date range
                        year_str, q_str = quarter.split("-Q")
                        year = int(year_str)
                        q = int(q_str)
                        quarter_starts = {1: "01-01", 2: "04-01", 3: "07-01", 4: "10-01"}
                        quarter_ends = {1: "03-31", 2: "06-30", 3: "09-30", 4: "12-31"}
                        start_date = f"{year}-{quarter_starts[q]}"
                        end_date = f"{year}-{quarter_ends[q]}"
                        quarter_clause = "AND c.call_date BETWEEN %s AND %s"
                        params.extend([start_date, end_date])
                    params.append(limit)
                    cur.execute(
                        f"""
                        SELECT tc.chunk_id, tc.chunk_type, tc.chunk_text,
                               tc.tier1_score, tc.needs_deep_analysis
                        FROM transcript_chunks tc
                        JOIN calls c ON tc.call_id = c.id
                        WHERE c.ticker = %s {quarter_clause}
                        ORDER BY tc.sequence_order ASC
                        LIMIT %s
                        """,
                        params,
                    )
                    for row in cur.fetchall():
                        rows.append({
                            "chunk_id": row[0],
                            "chunk_type": row[1],
                            "chunk_text": row[2],
                            "tier1_score": row[3],
                            "needs_deep_analysis": row[4],
                        })
        except Exception as e:
            logger.warning(f"Could not fetch chunks for {ticker}: {e}")
        return rows

    def get_qa_evasion_for_ticker(self, ticker: str) -> list[tuple]:
        """Return evasion entries ordered by call sequence.

        Each row: (analyst_name, question_topic, question_text, answer_text,
                   analyst_concern, defensiveness_score, evasion_explanation)
        """
        rows = []
        try:
            with psycopg.connect(self.conn_str) as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        """
                        SELECT ea.analyst_name, ea.question_topic,
                               ea.question_text, ea.answer_text,
                               ea.analyst_concern, ea.defensiveness_score,
                               ea.evasion_explanation
                        FROM evasion_analysis ea
                        JOIN transcript_chunks tc ON ea.chunk_id = tc.chunk_id AND ea.call_id = tc.call_id
                        JOIN calls c ON ea.call_id = c.id
                        WHERE c.ticker = %s
                        ORDER BY tc.sequence_order ASC
                        """,
                        (ticker,),
                    )
                    rows = cur.fetchall()
        except Exception as e:
            logger.warning(f"Could not fetch Q&A evasion for {ticker}: {e}")
        return rows

    def get_evasion_for_ticker(
        self, ticker: str, conn: psycopg.Connection | None = None
    ) -> list[tuple[str, int, str, str | None, str | None]]:
        """Return evasion analysis entries for a ticker.

        Each row: (analyst_concern, defensiveness_score, evasion_explanation,
                   question_topic, analyst_name)
        """
        rows = []
        try:
            ctx = nullcontext(conn) if conn is not None else psycopg.connect(self.conn_str)
            with ctx as c:
                with c.cursor() as cur:
                    cur.execute(
                        """
                        SELECT ea.analyst_concern, ea.defensiveness_score, ea.evasion_explanation,
                               ea.question_topic, ea.analyst_name
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
        """Persist a full CallAnalysis to the database."""
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
                if getattr(result, "brief", None):
                    self._save_call_brief(cur, result.call.id, result.brief)
            conn.commit()

    def _save_call_synthesis(self, cur, call_id, synthesis):
        from psycopg.types.json import Jsonb

        # Serialise strategic_shifts: list[dict] → JSONB[]
        shifts = synthesis.strategic_shifts or []
        shifts_value = [
            Jsonb(s) if isinstance(s, dict)
            else Jsonb({"prior_position": "", "current_position": str(s), "investor_significance": ""})
            for s in shifts
        ]

        cur.execute(
            """
            INSERT INTO call_synthesis (
                id, call_id, overall_sentiment, executive_tone,
                key_themes, strategic_shifts, analyst_sentiment, call_summary
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (call_id) DO UPDATE SET
                overall_sentiment = EXCLUDED.overall_sentiment,
                executive_tone = EXCLUDED.executive_tone,
                key_themes = EXCLUDED.key_themes,
                strategic_shifts = EXCLUDED.strategic_shifts,
                analyst_sentiment = EXCLUDED.analyst_sentiment,
                call_summary = EXCLUDED.call_summary
            """,
            (
                str(synthesis.id),
                str(call_id),
                synthesis.overall_sentiment,
                synthesis.executive_tone,
                synthesis.key_themes,
                shifts_value,
                synthesis.analyst_sentiment,
                synthesis.call_summary,
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
                    call_id, label, terms, weight, rank_order, topic_name, summary
                ) VALUES (%s, %s, %s, %s, %s, %s, %s)
                """,
                (str(call_id), topic.label, topic.terms, topic.weight, topic.rank_order, getattr(topic, "name", ""), getattr(topic, "summary", ""))
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
                call_id, chunk_id,
                analyst_name, question_topic, question_text, answer_text,
                analyst_concern, defensiveness_score, evasion_explanation
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            """,
            (
                str(call_id), chunk.chunk_id,
                evasion.get("analyst_name"),
                evasion.get("question_topic"),
                evasion.get("question_text"),
                evasion.get("answer_text"),
                evasion.get("analyst_concern"),
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

    def _save_call_brief(self, cur, call_id, brief) -> None:
        """Upsert the call_brief row for a given call_id (used within an open transaction)."""
        from psycopg.types.json import Jsonb
        cur.execute(
            """
            INSERT INTO call_brief (call_id, context_line, bigger_picture, interpretation_questions)
            VALUES (%s, %s, %s, %s)
            ON CONFLICT (call_id) DO UPDATE SET
                context_line = EXCLUDED.context_line,
                bigger_picture = EXCLUDED.bigger_picture,
                interpretation_questions = EXCLUDED.interpretation_questions
            """,
            (
                str(call_id),
                brief.context_line,
                Jsonb(brief.bigger_picture),
                Jsonb(brief.interpretation_questions),
            ),
        )

    def save_call_brief(self, call_id, brief) -> None:
        """Upsert the call_brief row for a given call_id (opens its own connection)."""
        try:
            with psycopg.connect(self.conn_str) as conn:
                with conn.cursor() as cur:
                    self._save_call_brief(cur, call_id, brief)
                conn.commit()
        except Exception as e:
            logger.warning(f"Could not save call_brief for {call_id}: {e}")

    def get_call_brief_for_ticker(self, ticker: str) -> dict | None:
        """Return the call_brief record for a ticker, or None if absent."""
        try:
            with psycopg.connect(self.conn_str) as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        """
                        SELECT cb.context_line, cb.bigger_picture, cb.interpretation_questions
                        FROM call_brief cb
                        JOIN calls c ON cb.call_id = c.id
                        WHERE c.ticker = %s
                        ORDER BY c.created_at DESC
                        LIMIT 1
                        """,
                        (ticker,),
                    )
                    row = cur.fetchone()
                    if not row:
                        return None
                    return {
                        "context_line": row[0],
                        "bigger_picture": row[1] or [],
                        "interpretation_questions": row[2] or [],
                    }
        except Exception as e:
            logger.warning(f"Could not fetch call_brief for {ticker}: {e}")
        return None
