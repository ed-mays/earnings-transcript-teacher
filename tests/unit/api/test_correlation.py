"""Tests for correlation ID middleware and slow-query threshold."""

import logging
import os
import sys
import time
from unittest.mock import MagicMock, patch

import pytest

API_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../api"))
if API_DIR not in sys.path:
    sys.path.insert(0, API_DIR)

DB_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../.."))
if DB_DIR not in sys.path:
    sys.path.insert(0, DB_DIR)

ENV = {
    "DATABASE_URL": "postgresql://test",
    "SUPABASE_URL": "https://test.supabase.co",
    "VOYAGE_API_KEY": "voyage-test-key",
    "PERPLEXITY_API_KEY": "pplx-test-key",
    "MODAL_TOKEN_ID": "modal-test-id",
    "ANTHROPIC_API_KEY": "anth-test-key",
}


@pytest.fixture()
def client():
    """TestClient with env vars set and connection pool mocked.

    Uses sys.modules.setdefault to inject the psycopg_pool mock without
    patch.dict(sys.modules) — that would remove all modules imported during
    the fixture on teardown, breaking subsequent test setups.
    """
    mock_pool = MagicMock()
    mock_pool.close = MagicMock()
    mock_psycopg_pool = MagicMock()
    mock_psycopg_pool.ConnectionPool.return_value = mock_pool
    sys.modules.setdefault("psycopg_pool", mock_psycopg_pool)

    with patch.dict(os.environ, ENV):
        with patch("dependencies.set_pool"):
            with patch("db.analytics.drain"):
                from fastapi.testclient import TestClient
                import main

                with TestClient(main.app) as c:
                    yield c


def test_request_id_in_log_output(client, caplog):
    """The timing middleware INFO line must appear in caplog with a UUID request_id."""
    with caplog.at_level(logging.INFO, logger="main"):
        response = client.get("/health")

    assert response.status_code == 200
    timing_records = [r for r in caplog.records if "completed" in r.message and "/health" in r.message]
    assert timing_records, "Expected timing log line from CorrelationTimingMiddleware"
    # request_id is embedded in the message as [request_id=<uuid>]
    assert any("request_id=" in r.message for r in timing_records)


def test_custom_request_id_forwarded(client, caplog):
    """A custom X-Request-ID header is echoed in the response and appears in logs."""
    custom_id = "test-abc-123"
    with caplog.at_level(logging.INFO, logger="main"):
        response = client.get("/health", headers={"X-Request-ID": custom_id})

    assert response.status_code == 200
    assert response.headers.get("X-Request-ID") == custom_id
    timing_records = [r for r in caplog.records if "completed" in r.message and "/health" in r.message]
    assert timing_records, "Expected timing log line"
    assert any(custom_id in r.message for r in timing_records)


def test_slow_query_threshold_triggers_warning(caplog):
    """_insert_event logs a WARNING when the DB insert exceeds LOG_SLOW_QUERY_THRESHOLD_MS."""
    with patch.dict(os.environ, ENV):
        import importlib
        import db.analytics as analytics_mod

        # Reload to pick up any module-level imports freshly
        importlib.reload(analytics_mod)

        # Patch LOG_SLOW_QUERY_THRESHOLD_MS to a very low value so the mock insert triggers it
        with patch.object(analytics_mod, "LOG_SLOW_QUERY_THRESHOLD_MS", 0):
            # Mock psycopg.connect so the "insert" completes but takes non-zero time
            mock_cur = MagicMock()
            mock_conn = MagicMock()
            mock_conn.__enter__ = MagicMock(return_value=mock_conn)
            mock_conn.__exit__ = MagicMock(return_value=False)
            mock_conn.cursor.return_value.__enter__ = MagicMock(return_value=mock_cur)
            mock_conn.cursor.return_value.__exit__ = MagicMock(return_value=False)

            with patch("psycopg.connect", return_value=mock_conn):
                with caplog.at_level(logging.WARNING, logger="db.analytics"):
                    analytics_mod._insert_event("test_event", None, {})

    warning_records = [r for r in caplog.records if "slow query" in r.message]
    assert warning_records, "Expected slow query WARNING from _insert_event"
