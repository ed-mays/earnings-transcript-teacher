"""Learning session and concept exercise repository."""

import json
import logging

import psycopg

logger = logging.getLogger(__name__)

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
        session_type: str = "feynman",
        user_id: str = SYSTEM_USER_ID,
    ) -> bool:
        """Upsert a learning session. Stores full message history in notes as JSON. Returns True on success."""
        try:
            with psycopg.connect(self.conn_str) as conn:
                with conn.cursor() as cur:
                    call_id = self._get_call_id(cur, ticker)
                    if not call_id:
                        logger.warning(f"No call found for ticker {ticker}, skipping session save")
                        return False
                    notes = json.dumps({"topic": topic, "stage": stage, "messages": messages, "type": session_type})
                    completed_at_expr = "now()" if completed else "NULL"
                    cur.execute(
                        f"""
                        INSERT INTO learning_sessions (id, user_id, call_id, notes, completed_at)
                        VALUES (%s, %s::uuid, %s, %s, {completed_at_expr})
                        ON CONFLICT (id) DO UPDATE SET
                            notes = EXCLUDED.notes,
                            completed_at = COALESCE(learning_sessions.completed_at, EXCLUDED.completed_at)
                        """,
                        (session_id, user_id, call_id, notes),
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

    def get_sessions_for_ticker(self, ticker: str, user_id: str | None = None) -> list[dict]:
        """Return all sessions for a ticker, newest first. Each dict has: id, topic, stage, completed, teaching_note, started_at.

        When user_id is provided only sessions belonging to that user are returned.
        """
        rows = []
        try:
            with psycopg.connect(self.conn_str) as conn:
                with conn.cursor() as cur:
                    if user_id is not None:
                        cur.execute(
                            """
                            SELECT ls.id, ls.notes, ls.completed_at, ls.started_at,
                                   ce.ai_critique
                            FROM learning_sessions ls
                            JOIN calls c ON ls.call_id = c.id
                            LEFT JOIN concept_exercises ce ON ce.session_id = ls.id
                            WHERE c.ticker = %s AND ls.user_id = %s::uuid
                            ORDER BY ls.started_at DESC
                            """,
                            (ticker, user_id),
                        )
                    else:
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
                            "session_type": notes.get("type", "feynman"),
                        })
        except Exception as e:
            logger.warning(f"Could not fetch sessions for ticker {ticker}: {e}")
        return rows

    def get_session_by_id(self, session_id: str, user_id: str) -> dict | None:
        """Return session data for the given session_id if it belongs to user_id.

        Returns None if not found. Raises ValueError if the session belongs to a different user.
        """
        try:
            with psycopg.connect(self.conn_str) as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        "SELECT notes, user_id FROM learning_sessions WHERE id = %s LIMIT 1",
                        (session_id,),
                    )
                    row = cur.fetchone()
            if not row:
                return None
            notes_json, owner_id = row
            if str(owner_id) != user_id:
                raise ValueError(f"Session {session_id!r} belongs to a different user")
            return json.loads(notes_json) if notes_json else {}
        except ValueError:
            raise
        except Exception as e:
            logger.warning(f"Could not fetch session {session_id}: {e}")
            return None

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
