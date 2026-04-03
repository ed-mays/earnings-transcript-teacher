"""News items cache repository."""

import logging

import psycopg

from core.models import NewsItem

logger = logging.getLogger(__name__)


class NewsRepository:
    """Read/write cached news items for a given ticker."""

    def __init__(self, conn_str: str):
        self.conn_str = conn_str

    def _get_call_id(self, cur: psycopg.Cursor, ticker: str) -> str | None:
        """Return the call UUID for a ticker, or None if not found."""
        cur.execute("SELECT id FROM calls WHERE ticker = %s LIMIT 1", (ticker,))
        row = cur.fetchone()
        return str(row[0]) if row else None

    def get(self, ticker: str) -> list[NewsItem]:
        """Return cached news items for a ticker, or empty list if none."""
        try:
            with psycopg.connect(self.conn_str) as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        """
                        SELECT ni.headline, ni.url, ni.source, ni.date, ni.summary
                        FROM news_items ni
                        JOIN calls c ON ni.call_id = c.id
                        WHERE c.ticker = %s
                        ORDER BY ni.date DESC
                        """,
                        (ticker,),
                    )
                    rows = cur.fetchall()
        except Exception as e:
            logger.warning("Could not fetch news items for %s: %s", ticker, e)
            return []

        return [
            NewsItem(
                headline=row[0],
                url=row[1],
                source=row[2],
                date=row[3],
                summary=row[4],
            )
            for row in rows
        ]

    def save(self, ticker: str, items: list[NewsItem]) -> None:
        """Delete existing news items for a ticker and insert the new list."""
        try:
            with psycopg.connect(self.conn_str) as conn:
                with conn.cursor() as cur:
                    call_id = self._get_call_id(cur, ticker)
                    if not call_id:
                        logger.warning("No call found for ticker %s — skipping news save", ticker)
                        return
                    cur.execute("DELETE FROM news_items WHERE call_id = %s", (call_id,))
                    for item in items:
                        cur.execute(
                            """
                            INSERT INTO news_items (call_id, headline, url, source, date, summary)
                            VALUES (%s, %s, %s, %s, %s, %s)
                            ON CONFLICT (call_id, headline) DO UPDATE SET
                                url = EXCLUDED.url,
                                source = EXCLUDED.source,
                                date = EXCLUDED.date,
                                summary = EXCLUDED.summary,
                                fetched_at = now()
                            """,
                            (call_id, item.headline, item.url, item.source, item.date, item.summary),
                        )
                conn.commit()
        except Exception as e:
            logger.warning("Could not save news items for %s: %s", ticker, e)
