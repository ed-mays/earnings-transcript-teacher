"""Unit tests for /admin routes."""

import os
import sys
from unittest.mock import MagicMock, patch

import pytest

API_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../api"))
if API_DIR not in sys.path:
    sys.path.insert(0, API_DIR)

# Stub modal before routes.admin imports it so the C-extension dance never happens.
MODAL_STUB = MagicMock()
sys.modules.setdefault("modal", MODAL_STUB)

from main import app  # noqa: E402  (must come after sys.modules stub)

ENV = {
    "DATABASE_URL": "postgresql://test",
    "SUPABASE_JWT_SECRET": "secret",
    "ADMIN_SECRET_TOKEN": "test-admin-token",
}


@pytest.fixture()
def client():
    """Return a TestClient with required env vars set and side-effects mocked."""
    with patch.dict(os.environ, ENV):
        with patch("psycopg.connect"):
            from fastapi.testclient import TestClient

            with TestClient(app) as c:
                yield c


@pytest.fixture(autouse=True)
def reset_modal():
    """Reset the modal stub between tests so call counts don't bleed over."""
    MODAL_STUB.reset_mock()


def test_ingest_returns_202(client):
    mock_fn = MagicMock()
    MODAL_STUB.Function.lookup.return_value = mock_fn

    resp = client.post(
        "/admin/ingest",
        json={"ticker": "AAPL"},
        headers={"X-Admin-Token": "test-admin-token"},
    )

    assert resp.status_code == 202
    body = resp.json()
    assert body["status"] == "accepted"
    assert body["ticker"] == "AAPL"
    mock_fn.spawn.assert_called_once_with("AAPL")


def test_ingest_uppercases_ticker(client):
    mock_fn = MagicMock()
    MODAL_STUB.Function.lookup.return_value = mock_fn

    resp = client.post(
        "/admin/ingest",
        json={"ticker": "aapl"},
        headers={"X-Admin-Token": "test-admin-token"},
    )

    assert resp.status_code == 202
    assert resp.json()["ticker"] == "AAPL"
    mock_fn.spawn.assert_called_once_with("AAPL")


def test_ingest_missing_token_returns_403(client):
    resp = client.post("/admin/ingest", json={"ticker": "AAPL"})
    assert resp.status_code == 403


def test_ingest_wrong_token_returns_403(client):
    resp = client.post(
        "/admin/ingest",
        json={"ticker": "AAPL"},
        headers={"X-Admin-Token": "wrong"},
    )
    assert resp.status_code == 403


def test_ingest_missing_ticker_returns_422(client):
    resp = client.post(
        "/admin/ingest",
        json={},
        headers={"X-Admin-Token": "test-admin-token"},
    )
    assert resp.status_code == 422


def test_ingest_invalid_ticker_too_short_returns_422(client):
    resp = client.post(
        "/admin/ingest",
        json={"ticker": "A"},
        headers={"X-Admin-Token": "test-admin-token"},
    )
    assert resp.status_code == 422


def test_ingest_invalid_ticker_too_long_returns_422(client):
    resp = client.post(
        "/admin/ingest",
        json={"ticker": "TOOLONG"},
        headers={"X-Admin-Token": "test-admin-token"},
    )
    assert resp.status_code == 422


def test_ingest_invalid_ticker_non_alpha_returns_422(client):
    resp = client.post(
        "/admin/ingest",
        json={"ticker": "AP1L"},
        headers={"X-Admin-Token": "test-admin-token"},
    )
    assert resp.status_code == 422


def test_ingest_looks_up_correct_modal_function(client):
    mock_fn = MagicMock()
    MODAL_STUB.Function.lookup.return_value = mock_fn

    client.post(
        "/admin/ingest",
        json={"ticker": "MSFT"},
        headers={"X-Admin-Token": "test-admin-token"},
    )

    MODAL_STUB.Function.lookup.assert_called_with("earnings-ingestion", "ingest_ticker")
