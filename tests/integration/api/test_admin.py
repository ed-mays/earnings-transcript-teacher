"""Integration tests for POST /admin/ingest.

Covers the full auth chain: JWT decode → require_admin → DB role query.
Complements tests/unit/api/test_admin.py which mocks individual components;
these tests let the whole chain run together.
"""

import os
from contextlib import ExitStack
from unittest.mock import AsyncMock, MagicMock, patch

import jwt as pyjwt
import pytest
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives.asymmetric import rsa

from tests.conftest import TEST_ENV

# RSA key pair for this test module — private signs JWTs, public goes into the mock JWKS client.
_RSA_PRIVATE_KEY = rsa.generate_private_key(
    public_exponent=65537,
    key_size=2048,
    backend=default_backend(),
)
_RSA_PUBLIC_KEY = _RSA_PRIVATE_KEY.public_key()

ADMIN_UUID = "00000000-0000-0000-0000-000000000001"
LEARNER_UUID = "00000000-0000-0000-0000-000000000002"


def _make_jwt(user_id: str) -> str:
    """Sign a test JWT with this module's RSA private key."""
    return pyjwt.encode(
        {"sub": user_id, "aud": "authenticated"},
        _RSA_PRIVATE_KEY,
        algorithm="RS256",
    )


def _mock_jwks_client() -> MagicMock:
    """Return a mock PyJWKClient that accepts JWTs signed with _RSA_PRIVATE_KEY."""
    mock_key = MagicMock()
    mock_key.key = _RSA_PUBLIC_KEY
    mock_client = MagicMock()
    mock_client.get_signing_key_from_jwt.return_value = mock_key
    return mock_client


def _admin_conn() -> MagicMock:
    """Mock psycopg connection whose execute().fetchone() returns ('admin',)."""
    conn = MagicMock()
    conn.execute.return_value.fetchone.return_value = ("admin",)
    return conn


def _learner_conn() -> MagicMock:
    """Mock psycopg connection whose execute().fetchone() returns ('learner',)."""
    conn = MagicMock()
    conn.execute.return_value.fetchone.return_value = ("learner",)
    return conn


def _mock_modal_fn() -> MagicMock:
    """Return a mock Modal Function with spawn.aio as an AsyncMock."""
    fn = MagicMock()
    fn.spawn = MagicMock()
    fn.spawn.aio = AsyncMock()
    return fn


_ADMIN_HEADERS = {"Authorization": f"Bearer {_make_jwt(ADMIN_UUID)}"}
_LEARNER_HEADERS = {"Authorization": f"Bearer {_make_jwt(LEARNER_UUID)}"}


@pytest.fixture()
def auth_client():
    """TestClient with real JWT verification and a mocked DB (admin role by default).

    Does NOT override get_current_user or require_admin — the full auth chain runs.
    """
    with ExitStack() as stack:
        stack.enter_context(patch.dict(os.environ, TEST_ENV))
        stack.enter_context(
            patch("dependencies._get_jwks_client", return_value=_mock_jwks_client())
        )
        stack.enter_context(patch("psycopg.connect", return_value=_admin_conn()))
        try:
            stack.enter_context(
                patch(
                    "psycopg_pool.ConnectionPool",
                    side_effect=Exception("no pool in integration tests"),
                )
            )
        except ModuleNotFoundError:
            pass
        from fastapi.testclient import TestClient
        from main import app

        with TestClient(app) as c:
            yield c

    import routes.admin as _admin_mod
    _admin_mod._ingest_last_request.clear()


class TestIngestAuthChain:
    """End-to-end auth + validation paths for POST /admin/ingest."""

    def test_valid_admin_returns_202(self, auth_client):
        """Full chain: valid JWT → admin role in DB → modal dispatch → 202."""
        with patch("routes.admin.modal.Function.from_name", return_value=_mock_modal_fn()):
            response = auth_client.post(
                "/admin/ingest", json={"ticker": "AAPL"}, headers=_ADMIN_HEADERS
            )
        assert response.status_code == 202
        body = response.json()
        assert body["status"] == "accepted"
        assert body["ticker"] == "AAPL"

    def test_invalid_ticker_returns_422(self, auth_client):
        """Pydantic rejects a ticker that doesn't match the 2–5 alpha-char pattern."""
        with patch("routes.admin.modal.Function.from_name", return_value=_mock_modal_fn()):
            response = auth_client.post(
                "/admin/ingest", json={"ticker": "1NVALID!!!"}, headers=_ADMIN_HEADERS
            )
        assert response.status_code == 422

    def test_missing_authorization_returns_401(self, auth_client):
        """get_current_user raises 401 when no Authorization header is present."""
        response = auth_client.post("/admin/ingest", json={"ticker": "AAPL"})
        assert response.status_code == 401

    def test_non_admin_role_returns_403(self, auth_client):
        """require_admin raises 403 when the DB returns a non-admin role."""
        with patch("psycopg.connect", return_value=_learner_conn()):
            response = auth_client.post(
                "/admin/ingest", json={"ticker": "AAPL"}, headers=_LEARNER_HEADERS
            )
        assert response.status_code == 403
