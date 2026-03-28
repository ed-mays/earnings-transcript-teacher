"""Unit tests for /admin routes."""

import os
import sys
from unittest.mock import MagicMock, patch

import jwt as pyjwt
import pytest
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives.asymmetric import rsa

API_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../api"))
if API_DIR not in sys.path:
    sys.path.insert(0, API_DIR)

# Stub modal before routes.admin imports it so the C-extension dance never happens.
MODAL_STUB = MagicMock()
sys.modules.setdefault("modal", MODAL_STUB)

from main import app  # noqa: E402  (must come after sys.modules stub)

ENV = {
    "DATABASE_URL": "postgresql://test",
    "SUPABASE_URL": "https://test.supabase.co",
}

# RSA key pair used to sign and verify test JWTs.
_RSA_PRIVATE_KEY = rsa.generate_private_key(
    public_exponent=65537,
    key_size=2048,
    backend=default_backend(),
)
_RSA_PUBLIC_KEY = _RSA_PRIVATE_KEY.public_key()

ADMIN_UUID = "00000000-0000-0000-0000-000000000001"
LEARNER_UUID = "00000000-0000-0000-0000-000000000002"


def _make_jwt(user_id: str) -> str:
    """Sign a test JWT with the RSA private key."""
    return pyjwt.encode(
        {"sub": user_id, "aud": "authenticated"},
        _RSA_PRIVATE_KEY,
        algorithm="RS256",
    )


def _mock_jwks_client() -> MagicMock:
    """Return a mock PyJWKClient that verifies tokens signed with _RSA_PRIVATE_KEY."""
    mock_key = MagicMock()
    mock_key.key = _RSA_PUBLIC_KEY
    mock_client = MagicMock()
    mock_client.get_signing_key_from_jwt.return_value = mock_key
    return mock_client


ADMIN_AUTH = {"Authorization": f"Bearer {_make_jwt(ADMIN_UUID)}"}
LEARNER_AUTH = {"Authorization": f"Bearer {_make_jwt(LEARNER_UUID)}"}


def _make_mock_conn(role: str = "admin") -> MagicMock:
    """Return a mock psycopg connection whose execute().fetchone() returns the given role."""
    mock_conn = MagicMock()
    mock_conn.execute.return_value.fetchone.return_value = (role,)
    return mock_conn


@pytest.fixture()
def client():
    """Return a TestClient with required env vars set and the DB mocked for an admin user."""
    with patch.dict(os.environ, ENV):
        with patch("dependencies._get_jwks_client", return_value=_mock_jwks_client()):
            with patch("psycopg.connect", return_value=_make_mock_conn("admin")):
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
        headers=ADMIN_AUTH,
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
        headers=ADMIN_AUTH,
    )

    assert resp.status_code == 202
    assert resp.json()["ticker"] == "AAPL"
    mock_fn.spawn.assert_called_once_with("AAPL")


def test_ingest_missing_auth_returns_401(client):
    resp = client.post("/admin/ingest", json={"ticker": "AAPL"})
    assert resp.status_code == 401


def test_ingest_invalid_jwt_returns_401(client):
    resp = client.post(
        "/admin/ingest",
        json={"ticker": "AAPL"},
        headers={"Authorization": "Bearer not-a-real-jwt"},
    )
    assert resp.status_code == 401


def test_ingest_learner_role_returns_403(client):
    with patch("psycopg.connect", return_value=_make_mock_conn("learner")):
        resp = client.post(
            "/admin/ingest",
            json={"ticker": "AAPL"},
            headers=LEARNER_AUTH,
        )
    assert resp.status_code == 403


def test_ingest_missing_ticker_returns_422(client):
    resp = client.post(
        "/admin/ingest",
        json={},
        headers=ADMIN_AUTH,
    )
    assert resp.status_code == 422


def test_ingest_invalid_ticker_too_short_returns_422(client):
    resp = client.post(
        "/admin/ingest",
        json={"ticker": "A"},
        headers=ADMIN_AUTH,
    )
    assert resp.status_code == 422


def test_ingest_invalid_ticker_too_long_returns_422(client):
    resp = client.post(
        "/admin/ingest",
        json={"ticker": "TOOLONG"},
        headers=ADMIN_AUTH,
    )
    assert resp.status_code == 422


def test_ingest_invalid_ticker_non_alpha_returns_422(client):
    resp = client.post(
        "/admin/ingest",
        json={"ticker": "AP1L"},
        headers=ADMIN_AUTH,
    )
    assert resp.status_code == 422


def test_ingest_looks_up_correct_modal_function(client):
    mock_fn = MagicMock()
    MODAL_STUB.Function.lookup.return_value = mock_fn

    client.post(
        "/admin/ingest",
        json={"ticker": "MSFT"},
        headers=ADMIN_AUTH,
    )

    MODAL_STUB.Function.lookup.assert_called_with("earnings-ingestion", "ingest_ticker")


# ---------------------------------------------------------------------------
# GET /admin/health
# ---------------------------------------------------------------------------

def _make_healthy_httpx_mock():
    """Return a mock httpx module with AsyncClient that succeeds on HEAD."""
    from unittest.mock import AsyncMock
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


def test_health_returns_200(client):
    with patch("routes.admin.SchemaRepository", _make_schema_repo_mock()), \
         patch("routes.admin.httpx", _make_healthy_httpx_mock()):
        resp = client.get("/admin/health", headers=ADMIN_AUTH)
    assert resp.status_code == 200


def test_health_missing_auth_returns_401(client):
    resp = client.get("/admin/health")
    assert resp.status_code == 401


def test_health_invalid_jwt_returns_401(client):
    resp = client.get(
        "/admin/health",
        headers={"Authorization": "Bearer not-a-real-jwt"},
    )
    assert resp.status_code == 401


def test_health_learner_role_returns_403(client):
    with patch("psycopg.connect", return_value=_make_mock_conn("learner")):
        resp = client.get("/admin/health", headers=LEARNER_AUTH)
    assert resp.status_code == 403


def test_health_response_has_expected_keys(client):
    with patch("routes.admin.SchemaRepository", _make_schema_repo_mock()), \
         patch("routes.admin.httpx", _make_healthy_httpx_mock()):
        resp = client.get("/admin/health", headers=ADMIN_AUTH)
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
        resp = client.get("/admin/health", headers=ADMIN_AUTH)
    body = resp.json()
    assert body["db"]["connected"] is True
    assert body["db"]["schema_version"] == 9


def test_health_db_disconnected_when_version_zero(client):
    with patch("routes.admin.SchemaRepository", _make_schema_repo_mock(version=0)), \
         patch("routes.admin.httpx", _make_healthy_httpx_mock()):
        resp = client.get("/admin/health", headers=ADMIN_AUTH)
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
        resp = client.get("/admin/health", headers=ADMIN_AUTH)
    body = resp.json()
    assert all(body["env_vars"].values())


def test_health_external_apis_unreachable_on_exception(client):
    from unittest.mock import AsyncMock
    mock_http_client = AsyncMock()
    mock_http_client.head = AsyncMock(side_effect=Exception("connection refused"))
    mock_cm = AsyncMock()
    mock_cm.__aenter__ = AsyncMock(return_value=mock_http_client)
    mock_cm.__aexit__ = AsyncMock(return_value=False)
    mock_httpx = MagicMock()
    mock_httpx.AsyncClient.return_value = mock_cm

    with patch("routes.admin.SchemaRepository", _make_schema_repo_mock()), \
         patch("routes.admin.httpx", mock_httpx):
        resp = client.get("/admin/health", headers=ADMIN_AUTH)
    body = resp.json()
    assert body["external_apis"]["voyage"]["reachable"] is False
    assert body["external_apis"]["perplexity"]["reachable"] is False
