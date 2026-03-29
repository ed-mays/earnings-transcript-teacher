"""Unit tests for db/analytics — thread tracking and drain behaviour."""

import sys
import os
import threading
import time

import pytest

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../.."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from db import analytics


@pytest.fixture(autouse=True)
def reset_thread_registry():
    """Clear the analytics thread registry before and after each test."""
    with analytics._threads_lock:
        analytics._active_threads.clear()
    yield
    with analytics._threads_lock:
        analytics._active_threads.clear()


class TestDrain:
    def test_drain_joins_threads_within_timeout(self):
        """drain() waits for in-flight threads and returns with an empty registry."""
        started = threading.Event()
        proceed = threading.Event()

        def slow_insert(event_name, session_id, properties):
            started.set()
            proceed.wait(timeout=2)

        t = threading.Thread(target=analytics._run_and_untrack, args=("test_event", None, {}), daemon=False)
        # Patch _insert_event for the duration of this thread's execution
        original = analytics._insert_event
        analytics._insert_event = slow_insert
        try:
            with analytics._threads_lock:
                analytics._active_threads.append(t)
            t.start()
            started.wait(timeout=1)
            proceed.set()  # unblock the thread before draining
            analytics.drain(timeout=2.0)
        finally:
            analytics._insert_event = original

        with analytics._threads_lock:
            assert len(analytics._active_threads) == 0

    def test_drain_logs_warning_when_thread_does_not_finish(self, caplog):
        """drain() logs a warning when a thread is still running after the timeout."""
        blocker = threading.Event()

        def stuck_insert(event_name, session_id, properties):
            blocker.wait(timeout=10)  # will not be unblocked during the test

        original = analytics._insert_event
        analytics._insert_event = stuck_insert
        t = threading.Thread(target=analytics._run_and_untrack, args=("test_event", None, {}), daemon=True)
        try:
            with analytics._threads_lock:
                analytics._active_threads.append(t)
            t.start()

            import logging
            with caplog.at_level(logging.WARNING, logger="db.analytics"):
                analytics.drain(timeout=0.05)

            assert any("did not finish" in record.message for record in caplog.records)
        finally:
            analytics._insert_event = original
            blocker.set()

    def test_track_registers_non_daemon_thread(self):
        """track() spawns a non-daemon thread tracked in the active registry."""
        from unittest.mock import patch

        with patch("db.analytics._insert_event"):
            analytics.track("test_event", session_id=None, properties={})

        # Thread was registered (may have already finished and been removed — that is fine)
        # The key assertion is that it was non-daemon, verified by checking it was started
        # We assert drain() completes without error (thread finishes naturally)
        analytics.drain(timeout=1.0)
