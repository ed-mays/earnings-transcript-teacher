"""Analytics event tracking — fire-and-forget inserts into analytics_events."""

import logging
import os
import threading
import time
from typing import Any

import psycopg

logger = logging.getLogger(__name__)

_active_threads: list[threading.Thread] = []
_threads_lock = threading.Lock()


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


def _run_and_untrack(event_name: str, session_id: str | None, properties: dict[str, Any] | None) -> None:
    """Run the DB insert and remove this thread from the active registry when done."""
    try:
        _insert_event(event_name, session_id, properties)
    finally:
        with _threads_lock:
            try:
                _active_threads.remove(threading.current_thread())
            except ValueError:
                pass


def track(
    event_name: str,
    session_id: str | None = None,
    properties: dict[str, Any] | None = None,
) -> None:
    """Record an analytics event without blocking the caller.

    Spawns a non-daemon thread to perform the DB insert. Logs a warning on failure
    and never raises — safe to call on any code path.
    """
    t = threading.Thread(target=_run_and_untrack, args=(event_name, session_id, properties), daemon=False)
    with _threads_lock:
        _active_threads.append(t)
    t.start()


def drain(timeout: float = 5.0) -> None:
    """Join all in-flight analytics threads up to the given timeout.

    Called from the lifespan shutdown path. Logs a warning if any threads
    do not finish within the allotted time.
    """
    with _threads_lock:
        threads = list(_active_threads)
    deadline = time.monotonic() + timeout
    for t in threads:
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            break
        t.join(timeout=remaining)
    with _threads_lock:
        still_running = len(_active_threads)
    if still_running:
        logger.warning(
            "analytics.drain: %d thread(s) did not finish within %.1fs timeout",
            still_running,
            timeout,
        )
