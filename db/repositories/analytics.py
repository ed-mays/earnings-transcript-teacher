"""Analytics events repository — admin dashboard queries."""

import logging

import psycopg

logger = logging.getLogger(__name__)


class AnalyticsRepository:
    """Read analytics_events for the admin dashboard."""

    def __init__(self, conn_str: str):
        self.conn_str = conn_str

    def get_daily_session_starts(self, days: int = 30) -> list[dict]:
        """Return daily session_start counts for the last N days."""
        with psycopg.connect(self.conn_str) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT DATE(created_at) AS date, COUNT(*) AS count
                    FROM analytics_events
                    WHERE event_name = 'session_start'
                      AND created_at >= NOW() - INTERVAL '%s days'
                    GROUP BY date
                    ORDER BY date
                    """,
                    (days,),
                )
                return [{"date": str(row[0]), "count": row[1]} for row in cur.fetchall()]

    def get_daily_chat_turns(self, days: int = 30) -> dict:
        """Return daily chat_turn counts and average turns per session for the last N days."""
        with psycopg.connect(self.conn_str) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT DATE(created_at) AS date, COUNT(*) AS turns
                    FROM analytics_events
                    WHERE event_name = 'chat_turn'
                      AND created_at >= NOW() - INTERVAL '%s days'
                    GROUP BY date
                    ORDER BY date
                    """,
                    (days,),
                )
                daily = [{"date": str(row[0]), "turns": row[1]} for row in cur.fetchall()]

                cur.execute(
                    """
                    SELECT AVG(turns_per_session)
                    FROM (
                        SELECT session_id, COUNT(*) AS turns_per_session
                        FROM analytics_events
                        WHERE event_name = 'chat_turn'
                          AND created_at >= NOW() - INTERVAL '%s days'
                        GROUP BY session_id
                    ) sub
                    """,
                    (days,),
                )
                row = cur.fetchone()
                avg = round(float(row[0]), 1) if row and row[0] is not None else 0.0

        return {"daily": daily, "avg_turns_per_session": avg}

    def get_costs_by_service(self, days: int = 30) -> dict:
        """Return token totals grouped by service for the last N days."""
        with psycopg.connect(self.conn_str) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT
                        properties->>'service' AS service,
                        SUM((properties->>'input_tokens')::int) AS input_tokens,
                        SUM((properties->>'output_tokens')::int) AS output_tokens
                    FROM analytics_events
                    WHERE event_name = 'api_call_completed'
                      AND created_at >= NOW() - INTERVAL '%s days'
                    GROUP BY service
                    ORDER BY service
                    """,
                    (days,),
                )
                by_service = {
                    row[0]: {"input_tokens": row[1] or 0, "output_tokens": row[2] or 0}
                    for row in cur.fetchall()
                    if row[0]
                }
        return {"by_service": by_service}

    def get_feynman_by_stage(self, days: int = 30) -> dict:
        """Return feynman_stage_completed counts grouped by stage for the last N days."""
        with psycopg.connect(self.conn_str) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT (properties->>'stage')::int AS stage, COUNT(*) AS count
                    FROM analytics_events
                    WHERE event_name = 'feynman_stage_completed'
                      AND created_at >= NOW() - INTERVAL '%s days'
                    GROUP BY stage
                    ORDER BY stage
                    """,
                    (days,),
                )
                by_stage = [{"stage": row[0], "count": row[1]} for row in cur.fetchall() if row[0]]
        return {"by_stage": by_stage}

    def get_recent_ingestions(self, limit: int = 100) -> dict:
        """Return ingestion_requested events ordered by recency."""
        with psycopg.connect(self.conn_str) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT properties->>'ticker', created_at
                    FROM analytics_events
                    WHERE event_name = 'ingestion_requested'
                    ORDER BY created_at DESC
                    LIMIT %s
                    """,
                    (limit,),
                )
                ingestions = [
                    {"ticker": row[0], "requested_at": row[1].isoformat()}
                    for row in cur.fetchall()
                    if row[0]
                ]
        return {"ingestions": ingestions}
