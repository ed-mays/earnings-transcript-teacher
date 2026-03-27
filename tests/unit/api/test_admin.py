"""Unit tests for /admin routes."""

import os
import sys
from unittest.mock import AsyncMock, MagicMock, patch

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


# ---------------------------------------------------------------------------
# GET /admin/health
# ---------------------------------------------------------------------------

def _make_healthy_httpx_mock():
    """Return a mock httpx module with AsyncClient that succeeds on HEAD."""
    mock_response = MagicMock(status_code=200)
    mock_http_client = AsyncMock()
    mock_http_client.head = AsyncMock(return_value=mock_response)
    mock_cm = AsyncMock()
    mock_cm.__aenter__ = AsyncMock(return_value=mock_http_client)
    mock_cm.__aexit__ = AsyncMock(return_value=False)
    mock_httpx = MagicMock()
    mock_httpx.AsyncClient.return_value = mock_cm
    return mock_httpx


def _make_schema_repo_mock(version: int = 9):
    """Return a patched SchemaRepository class whose instance returns `version`."""
    mock_repo = MagicMock()
    mock_repo.get_current_version.return_value = version
    mock_cls = MagicMock(return_value=mock_repo)
    return mock_cls


def test_health_returns_200_with_valid_token(client):
    with patch("routes.admin.SchemaRepository", _make_schema_repo_mock()), \
         patch("routes.admin.httpx", _make_healthy_httpx_mock()):
        resp = client.get(
            "/admin/health",
            headers={"X-Admin-Token": "test-admin-token"},
        )
    assert resp.status_code == 200


def test_health_missing_token_returns_403(client):
    resp = client.get("/admin/health")
    assert resp.status_code == 403


def test_health_wrong_token_returns_403(client):
    resp = client.get(
        "/admin/health",
        headers={"X-Admin-Token": "wrong"},
    )
    assert resp.status_code == 403


def test_health_response_has_expected_keys(client):
    with patch("routes.admin.SchemaRepository", _make_schema_repo_mock()), \
         patch("routes.admin.httpx", _make_healthy_httpx_mock()):
        resp = client.get(
            "/admin/health",
            headers={"X-Admin-Token": "test-admin-token"},
        )
    body = resp.json()
    assert "db" in body
    assert "env_vars" in body
    assert "external_apis" in body
    assert "connected" in body["db"]
    assert "schema_version" in body["db"]
    assert {"VOYAGE_API_KEY", "PERPLEXITY_API_KEY", "MODAL_TOKEN_ID", "SUPABASE_JWT_SECRET"} == set(
        body["env_vars"].keys()
    )
    assert "voyage" in body["external_apis"]
    assert "perplexity" in body["external_apis"]


def test_health_db_connected_when_version_nonzero(client):
    with patch("routes.admin.SchemaRepository", _make_schema_repo_mock(version=9)), \
         patch("routes.admin.httpx", _make_healthy_httpx_mock()):
        resp = client.get(
            "/admin/health",
            headers={"X-Admin-Token": "test-admin-token"},
        )
    body = resp.json()
    assert body["db"]["connected"] is True
    assert body["db"]["schema_version"] == 9


def test_health_db_disconnected_when_version_zero(client):
    with patch("routes.admin.SchemaRepository", _make_schema_repo_mock(version=0)), \
         patch("routes.admin.httpx", _make_healthy_httpx_mock()):
        resp = client.get(
            "/admin/health",
            headers={"X-Admin-Token": "test-admin-token"},
        )
    body = resp.json()
    assert body["db"]["connected"] is False
    assert body["db"]["schema_version"] == 0


def test_health_env_vars_present_when_set(client):
    extra_env = {
        "VOYAGE_API_KEY": "vk",
        "PERPLEXITY_API_KEY": "pk",
        "MODAL_TOKEN_ID": "mk",
        "SUPABASE_JWT_SECRET": "sk",
    }
    with patch.dict(os.environ, extra_env), \
         patch("routes.admin.SchemaRepository", _make_schema_repo_mock()), \
         patch("routes.admin.httpx", _make_healthy_httpx_mock()):
        resp = client.get(
            "/admin/health",
            headers={"X-Admin-Token": "test-admin-token"},
        )
    body = resp.json()
    assert all(body["env_vars"].values())


def test_health_external_apis_unreachable_on_exception(client):
    mock_http_client = AsyncMock()
    mock_http_client.head = AsyncMock(side_effect=Exception("connection refused"))
    mock_cm = AsyncMock()
    mock_cm.__aenter__ = AsyncMock(return_value=mock_http_client)
    mock_cm.__aexit__ = AsyncMock(return_value=False)
    mock_httpx = MagicMock()
    mock_httpx.AsyncClient.return_value = mock_cm

    with patch("routes.admin.SchemaRepository", _make_schema_repo_mock()), \
         patch("routes.admin.httpx", mock_httpx):
        resp = client.get(
            "/admin/health",
            headers={"X-Admin-Token": "test-admin-token"},
        )
    body = resp.json()
    assert body["external_apis"]["voyage"]["reachable"] is False
    assert body["external_apis"]["perplexity"]["reachable"] is False
