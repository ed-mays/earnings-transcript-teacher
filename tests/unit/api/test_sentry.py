"""Tests for Sentry SDK initialisation in api/main.py."""

import logging
import os
import sys
from unittest.mock import MagicMock, patch

import pytest

API_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../api"))
if API_DIR not in sys.path:
    sys.path.insert(0, API_DIR)

_MOCK_POOL = MagicMock()
_MOCK_POOL.close = MagicMock()
_MOCK_PSYCOPG_POOL = MagicMock()
_MOCK_PSYCOPG_POOL.ConnectionPool.return_value = _MOCK_POOL

# Import main once (with sentry_sdk.init patched so the module-level call is a no-op).
with patch("sentry_sdk.init"):
    with patch.dict(sys.modules, {"psycopg_pool": _MOCK_PSYCOPG_POOL}):
        with patch("dependencies.set_pool"):
            with patch("db.analytics.drain"):
                import main  # noqa: E402


def test_sentry_warning_logged_when_dsn_absent(caplog: pytest.LogCaptureFixture) -> None:
    """A WARNING is emitted when SENTRY_DSN is not set."""
    env = {"SENTRY_DSN": ""}  # absent / empty

    with patch.dict(os.environ, env):
        with patch("sentry_sdk.init") as mock_init:
            with caplog.at_level(logging.WARNING):
                main._configure_sentry()

    mock_init.assert_not_called()
    assert any("SENTRY_DSN" in r.message for r in caplog.records)


def test_sentry_init_called_when_dsn_present() -> None:
    """sentry_sdk.init is called with the correct DSN and environment when SENTRY_DSN is set."""
    env = {"SENTRY_DSN": "https://abc@sentry.io/123", "ENV": "staging"}

    with patch.dict(os.environ, env):
        with patch("sentry_sdk.init") as mock_init:
            main._configure_sentry()

    mock_init.assert_called_once()
    call_kwargs = mock_init.call_args.kwargs
    assert call_kwargs["dsn"] == "https://abc@sentry.io/123"
    assert call_kwargs["environment"] == "staging"
