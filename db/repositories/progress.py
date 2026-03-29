"""Step-progress repository for the 6-step learning path."""

import logging

import psycopg

logger = logging.getLogger(__name__)


class ProgressRepository:
    """Read/write per-step completion tracking for the 6-step learning path."""

    def __init__(self, conn_str: str):
        self.conn_str = conn_str

    def mark_step_viewed(self, ticker: str, step_number: int) -> None:
        """Record that a step has been read for a given ticker. Idempotent."""
        try:
            with psycopg.connect(self.conn_str) as conn:
                with conn.cursor() as cur:
                    cur.execute("SELECT id FROM calls WHERE ticker = %s LIMIT 1", (ticker,))
                    row = cur.fetchone()
                    if not row:
                        return
                    call_id = str(row[0])
                    cur.execute(
                        """
                        INSERT INTO transcript_progress (call_id, step_number)
                        VALUES (%s, %s)
                        ON CONFLICT (call_id, step_number) DO NOTHING
                        """,
                        (call_id, step_number),
                    )
                conn.commit()
        except Exception as e:
            logger.warning(f"Could not mark step {step_number} as viewed for {ticker}: {e}")

    def get_completed_steps(self, ticker: str) -> set[int]:
        """Return the set of step numbers the user has marked as read for a transcript."""
        try:
            with psycopg.connect(self.conn_str) as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        """
                        SELECT tp.step_number
                        FROM transcript_progress tp
                        JOIN calls c ON tp.call_id = c.id
                        WHERE c.ticker = %s
                        """,
                        (ticker,),
                    )
                    return {row[0] for row in cur.fetchall()}
        except Exception as e:
            logger.warning(f"Could not fetch progress for {ticker}: {e}")
        return set()

    def get_all_step_counts(self) -> list[tuple[str, int]]:
        """Return (ticker, steps_completed) for all transcripts with any step progress."""
        try:
            with psycopg.connect(self.conn_str) as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        """
                        SELECT c.ticker, COUNT(tp.step_number)
                        FROM transcript_progress tp
                        JOIN calls c ON tp.call_id = c.id
                        GROUP BY c.ticker
                        ORDER BY COUNT(tp.step_number) DESC
                        """
                    )
                    return [(row[0], row[1]) for row in cur.fetchall()]
        except Exception as e:
            logger.warning(f"Could not fetch step counts: {e}")
        return []
