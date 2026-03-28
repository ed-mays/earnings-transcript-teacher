"""Analytics event tracking — fire-and-forget inserts into analytics_events."""

import logging
import os
import threading
from typing import Any

import psycopg

logger = logging.getLogger(__name__)


def _insert_event(event_name: str, session_id: str | None, properties: dict[str, Any] | None) -> None:
    """Execute the DB insert; run in a background thread."""
    try:
        db_url = os.environ.get("DATABASE_URL", "dbname=earnings_teacher")
        with psycopg.connect(db_url) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO analytics_events (event_name, session_id, properties)
                    VALUES (%s, %s::uuid, %s::jsonb)
                    """,
                    (event_name, session_id, psycopg.types.json.Jsonb(properties or {})),
                )
            conn.commit()
    except Exception as exc:
        logger.warning("analytics.track failed for event=%r: %s", event_name, exc)


def track(
    event_name: str,
    session_id: str | None = None,
    properties: dict[str, Any] | None = None,
) -> None:
    """Record an analytics event without blocking the caller.

    Spawns a daemon thread to perform the DB insert. Logs a warning on failure
    and never raises — safe to call on any code path.
    """
    t = threading.Thread(target=_insert_event, args=(event_name, session_id, properties), daemon=True)
    t.start()
