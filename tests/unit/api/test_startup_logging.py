"""Tests that the root logger configuration wires api.main log output to caplog."""

import logging
import os
import sys
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

API_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../api"))
if API_DIR not in sys.path:
    sys.path.insert(0, API_DIR)

ENV = {
    "DATABASE_URL": "postgresql://test",
    "SUPABASE_URL": "https://test.supabase.co",
    "VOYAGE_API_KEY": "voyage-test-key",
    "PERPLEXITY_API_KEY": "pplx-test-key",
    "MODAL_TOKEN_ID": "modal-test-id",
    "ANTHROPIC_API_KEY": "anth-test-key",
}


def test_startup_pool_log_reaches_caplog(caplog):
    """INFO message from the pool startup path appears in caplog after basicConfig."""
    mock_pool = MagicMock()
    mock_pool.close = MagicMock()

    mock_psycopg_pool = MagicMock()
    mock_psycopg_pool.ConnectionPool.return_value = mock_pool

    with patch.dict(os.environ, ENV):
        with patch.dict(sys.modules, {"psycopg_pool": mock_psycopg_pool}):
            with patch("dependencies.set_pool"):
                with patch("db.analytics.drain"):
                    from fastapi.testclient import TestClient
                    from main import app

                    with caplog.at_level(logging.INFO, logger="main"):
                        with TestClient(app):
                            pass

    assert any("connection pool started" in r.message for r in caplog.records)
