"""Competitor cache repository."""

import logging
from datetime import datetime, timezone, timedelta

import psycopg

from core.models import Competitor

logger = logging.getLogger(__name__)

_COMPETITOR_CACHE_TTL_DAYS = 30


class CompetitorRepository:
    """Read/write cached competitors for a given ticker."""

    def __init__(self, conn_str: str):
        self.conn_str = conn_str

    def _get_call_id(self, cur, ticker: str) -> str | None:
        """Return the call UUID for a ticker, or None if not found."""
        cur.execute("SELECT id FROM calls WHERE ticker = %s LIMIT 1", (ticker,))
        row = cur.fetchone()
        return str(row[0]) if row else None

    def get(self, ticker: str) -> list[Competitor]:
        """Return cached competitors for a ticker if still within TTL, else empty list."""
        rows = []
        try:
            with psycopg.connect(self.conn_str) as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        """
                        SELECT co.competitor_name, co.competitor_ticker,
                               co.description, co.mentioned_in_transcript, co.fetched_at
                        FROM competitors co
                        JOIN calls c ON co.call_id = c.id
                        WHERE c.ticker = %s
                        ORDER BY co.competitor_name ASC
                        """,
                        (ticker,),
                    )
                    rows = cur.fetchall()
        except Exception as e:
            logger.warning("Could not fetch competitors for %s: %s", ticker, e)
            return []

        if not rows:
            return []

        # Check TTL against the oldest fetched_at in the set
        cutoff = datetime.now(timezone.utc) - timedelta(days=_COMPETITOR_CACHE_TTL_DAYS)
        fetched_at = rows[0][4]
        if fetched_at and fetched_at < cutoff:
            return []

        return [
            Competitor(
                name=row[0],
                ticker=row[1] or "",
                description=row[2] or "",
                mentioned_in_transcript=bool(row[3]),
            )
            for row in rows
        ]

    def save(self, ticker: str, competitors: list[Competitor]) -> None:
        """Delete existing competitors for a ticker and insert the new list."""
        try:
            with psycopg.connect(self.conn_str) as conn:
                with conn.cursor() as cur:
                    call_id = self._get_call_id(cur, ticker)
                    if not call_id:
                        logger.warning("No call found for ticker %s — skipping competitor save", ticker)
                        return
                    cur.execute("DELETE FROM competitors WHERE call_id = %s", (call_id,))
                    for c in competitors:
                        cur.execute(
                            """
                            INSERT INTO competitors (
                                call_id, competitor_name, competitor_ticker,
                                description, mentioned_in_transcript
                            ) VALUES (%s, %s, %s, %s, %s)
                            ON CONFLICT (call_id, competitor_name) DO UPDATE SET
                                competitor_ticker = EXCLUDED.competitor_ticker,
                                description = EXCLUDED.description,
                                mentioned_in_transcript = EXCLUDED.mentioned_in_transcript,
                                fetched_at = now()
                            """,
                            (call_id, c.name, c.ticker or None, c.description, c.mentioned_in_transcript),
                        )
                conn.commit()
        except Exception as e:
            logger.warning("Could not save competitors for %s: %s", ticker, e)

    def delete(self, ticker: str) -> None:
        """Remove all cached competitors for a ticker (forces re-fetch)."""
        try:
            with psycopg.connect(self.conn_str) as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        """
                        DELETE FROM competitors
                        USING calls
                        WHERE competitors.call_id = calls.id AND calls.ticker = %s
                        """,
                        (ticker,),
                    )
                conn.commit()
        except Exception as e:
            logger.warning("Could not delete competitors for %s: %s", ticker, e)
