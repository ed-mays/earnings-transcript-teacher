"""Integration tests for POST /api/calls/{ticker}/chat.

Covers: auth rejection (missing JWT), unknown-ticker 404, and the SSE
streaming response shape for a new session with a mocked LLM.
"""

import json
import os
from contextlib import ExitStack
from unittest.mock import MagicMock, patch

import jwt as pyjwt
import pytest
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives.asymmetric import rsa

from factories.perplexity import stream_response
from tests.conftest import TEST_ENV

# RSA key pair for this test module.
_RSA_PRIVATE_KEY = rsa.generate_private_key(
    public_exponent=65537,
    key_size=2048,
    backend=default_backend(),
)
_RSA_PUBLIC_KEY = _RSA_PRIVATE_KEY.public_key()

USER_UUID = "00000000-0000-0000-0000-000000000001"


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


_AUTH_HEADERS = {"Authorization": f"Bearer {_make_jwt(USER_UUID)}"}


@pytest.fixture()
def auth_client():
    """TestClient with real JWT verification and a mocked DB.

    Does NOT override get_current_user — the full auth chain runs.
    """
    mock_conn = MagicMock()
    with ExitStack() as stack:
        stack.enter_context(patch.dict(os.environ, TEST_ENV))
        stack.enter_context(
            patch("dependencies._get_jwks_client", return_value=_mock_jwks_client())
        )
        stack.enter_context(patch("psycopg.connect", return_value=mock_conn))
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


class TestChatAuth:
    """Auth and pre-condition checks before the stream begins."""

    def test_missing_auth_returns_401(self, auth_client):
        """get_current_user raises 401 when no Authorization header is sent."""
        response = auth_client.post(
            "/api/calls/AAPL/chat", json={"message": "Explain the results"}
        )
        assert response.status_code == 401

    def test_unknown_ticker_returns_404(self, auth_client):
        """Returns 404 when the ticker has no call record."""
        with patch("routes.chat._ticker_exists", return_value=False):
            response = auth_client.post(
                "/api/calls/UNKN/chat",
                json={"message": "What happened?"},
                headers=_AUTH_HEADERS,
            )
        assert response.status_code == 404


class TestChatStreaming:
    """SSE response shape for a new session with a mocked LLM."""

    def test_streaming_response_shape(self, auth_client):
        """Response contains at least one token event and a final done event."""
        with (
            patch("routes.chat._ticker_exists", return_value=True),
            patch("services.llm.stream_chat", return_value=stream_response("Hello world")),
            patch("routes.chat._upsert_session"),
            patch("db.analytics.track"),
        ):
            response = auth_client.post(
                "/api/calls/AAPL/chat",
                json={"message": "Explain the earnings"},
                headers=_AUTH_HEADERS,
            )

        assert response.status_code == 200

        events = []
        for line in response.text.splitlines():
            if line.startswith("data: "):
                events.append(json.loads(line[len("data: "):]))

        token_events = [e for e in events if e.get("type") == "token"]
        done_events = [e for e in events if e.get("type") == "done"]

        assert len(token_events) >= 1, "Expected at least one token event"
        assert len(done_events) == 1, "Expected exactly one done event"
        assert "session_id" in done_events[0]
        assert all("content" in e for e in token_events)
