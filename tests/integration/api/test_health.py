"""Integration tests for GET /admin/health.

Verifies the response shape — that the endpoint composes db, env_vars,
and external_apis sections correctly through the full auth chain.
"""

import os
from contextlib import ExitStack
from unittest.mock import AsyncMock, MagicMock, patch

import jwt as pyjwt
import pytest
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives.asymmetric import rsa

from tests.conftest import TEST_ENV

# RSA key pair for this test module.
_RSA_PRIVATE_KEY = rsa.generate_private_key(
    public_exponent=65537,
    key_size=2048,
    backend=default_backend(),
)
_RSA_PUBLIC_KEY = _RSA_PRIVATE_KEY.public_key()

ADMIN_UUID = "00000000-0000-0000-0000-000000000001"


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


_ADMIN_HEADERS = {"Authorization": f"Bearer {_make_jwt(ADMIN_UUID)}"}


@pytest.fixture()
def auth_client():
    """TestClient with real JWT verification and a mocked DB (admin role).

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


class TestHealthShape:
    """GET /admin/health — response structure."""

    def test_response_has_required_shape(self, auth_client):
        """Health response includes db, env_vars, and external_apis sections."""
        mock_httpx_client = AsyncMock()
        mock_httpx_client.__aenter__ = AsyncMock(return_value=mock_httpx_client)
        mock_httpx_client.__aexit__ = AsyncMock(return_value=False)
        mock_httpx_client.head = AsyncMock()

        with (
            patch(
                "routes.admin.SchemaRepository.check_health",
                return_value=(True, None),
            ),
            patch("httpx.AsyncClient", return_value=mock_httpx_client),
        ):
            response = auth_client.get("/admin/health", headers=_ADMIN_HEADERS)

        assert response.status_code == 200
        body = response.json()
        assert "db" in body
        assert "env_vars" in body
        assert "external_apis" in body
        assert body["db"]["connected"] is True
        assert "voyage" in body["external_apis"]
        assert "perplexity" in body["external_apis"]
