"""Unit tests for /api/calls/{ticker}/chat route."""

import sys
import os
import json
from unittest.mock import MagicMock, patch

import pytest

# Add api/ directory so FastAPI can resolve `routes.*` imports.
API_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../api"))
if API_DIR not in sys.path:
    sys.path.insert(0, API_DIR)

# Add project root so routes can import from services/, db/, etc.
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../.."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

ENV = {
    "DATABASE_URL": "postgresql://test",
    "SUPABASE_JWT_SECRET": "secret",
    "PERPLEXITY_API_KEY": "pplx-test",
}

# A minimal valid JWT signed with "secret" for subject "user-uuid-001"
# Generated with: jwt.encode({"sub": "user-uuid-001"}, "secret", algorithm="HS256")
VALID_TOKEN = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJ1c2VyLXV1aWQtMDAxIn0.RYKzCziAC_ylbXw8-VyzeO4Rd-3zNXpXgTUskpjnzgk"
AUTH_HEADER = f"Bearer {VALID_TOKEN}"
USER_ID = "user-uuid-001"


@pytest.fixture()
def client():
    """Return a TestClient with env vars set and DB connections mocked."""
    with patch.dict(os.environ, ENV):
        with patch("psycopg.connect"):
            from fastapi.testclient import TestClient
            from main import app

            with TestClient(app) as c:
                yield c


class TestChatAuth:
    def test_401_without_auth_header(self, client):
        response = client.post("/api/calls/AAPL/chat", json={"message": "explain revenue"})
        assert response.status_code == 401

    def test_401_with_malformed_token(self, client):
        response = client.post(
            "/api/calls/AAPL/chat",
            json={"message": "explain revenue"},
            headers={"Authorization": "Bearer not-a-jwt"},
        )
        assert response.status_code == 401


class TestChatErrors:
    def test_404_for_unknown_ticker(self, client):
        with patch("routes.chat._ticker_exists", return_value=False):
            response = client.post(
                "/api/calls/UNKNOWN/chat",
                json={"message": "explain revenue"},
                headers={"Authorization": AUTH_HEADER},
            )
        assert response.status_code == 404

    def test_503_when_perplexity_key_missing(self, client):
        with (
            patch("routes.chat._ticker_exists", return_value=True),
            patch.dict(os.environ, {}, clear=False),
        ):
            env_without_key = {k: v for k, v in os.environ.items() if k != "PERPLEXITY_API_KEY"}
            with patch.dict(os.environ, env_without_key, clear=True):
                response = client.post(
                    "/api/calls/AAPL/chat",
                    json={"message": "explain revenue"},
                    headers={"Authorization": AUTH_HEADER},
                )
        assert response.status_code == 503

    def test_404_when_session_id_not_found(self, client):
        with (
            patch("routes.chat._ticker_exists", return_value=True),
            patch("routes.chat._load_session", return_value=None),
        ):
            response = client.post(
                "/api/calls/AAPL/chat",
                json={"message": "continue", "session_id": "nonexistent-session-id"},
                headers={"Authorization": AUTH_HEADER},
            )
        assert response.status_code == 404

    def test_403_when_session_owned_by_different_user(self, client):
        from fastapi import HTTPException, status

        def raise_403(*args, **kwargs):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Session belongs to a different user")

        with (
            patch("routes.chat._ticker_exists", return_value=True),
            patch("routes.chat._load_session", side_effect=raise_403),
        ):
            response = client.post(
                "/api/calls/AAPL/chat",
                json={"message": "continue", "session_id": "other-users-session"},
                headers={"Authorization": AUTH_HEADER},
            )
        assert response.status_code == 403


class TestChatStreaming:
    def test_new_session_streams_tokens(self, client):
        """New session: no session_id → creates session and streams SSE tokens."""
        mock_chunks = ["Hello", " world", {"model": "sonar-pro", "usage": {}}]

        with (
            patch("routes.chat._ticker_exists", return_value=True),
            patch("routes.chat._load_prompt", return_value="You are a Feynman tutor."),
            patch("routes.chat._upsert_session"),
            patch("services.llm.stream_chat", return_value=iter(mock_chunks)),
        ):
            response = client.post(
                "/api/calls/AAPL/chat",
                json={"message": "explain free cash flow"},
                headers={"Authorization": AUTH_HEADER},
            )

        assert response.status_code == 200
        assert "text/event-stream" in response.headers["content-type"]

        lines = [ln for ln in response.text.strip().split("\n\n") if ln]
        events = [json.loads(ln.removeprefix("data: ")) for ln in lines if ln.startswith("data: ")]

        token_events = [e for e in events if e["type"] == "token"]
        done_events = [e for e in events if e["type"] == "done"]

        assert len(token_events) == 2
        assert token_events[0]["content"] == "Hello"
        assert token_events[1]["content"] == " world"
        assert len(done_events) == 1
        assert "session_id" in done_events[0]

    def test_existing_session_resumes_history(self, client):
        """Existing session: session_id → loads history and streams continuation."""
        session_notes = {
            "topic": "cloud revenue",
            "stage": 2,
            "messages": [
                {"role": "user", "content": "explain cloud revenue"},
                {"role": "assistant", "content": "Cloud revenue is..."},
            ],
        }
        mock_chunks = ["Got it!"]

        with (
            patch("routes.chat._ticker_exists", return_value=True),
            patch("routes.chat._load_session", return_value=session_notes),
            patch("routes.chat._load_prompt", return_value="Stage 2 prompt."),
            patch("routes.chat._upsert_session"),
            patch("services.llm.stream_chat", return_value=iter(mock_chunks)) as mock_stream,
        ):
            response = client.post(
                "/api/calls/AAPL/chat",
                json={"message": "can you clarify?", "session_id": "existing-session-uuid"},
                headers={"Authorization": AUTH_HEADER},
            )

        assert response.status_code == 200

        # Verify stream_chat received 3 messages (2 history + 1 new user turn)
        call_args = mock_stream.call_args
        messages_passed = call_args[0][0]
        assert len(messages_passed) == 3
        assert messages_passed[-1] == {"role": "user", "content": "can you clarify?"}

    def test_load_prompt_uses_stage_from_session(self, client):
        """Stage from stored session is passed to _load_prompt, not the request body."""
        session_notes = {"topic": "margins", "stage": 3, "messages": []}
        mock_chunks = ["Response."]

        with (
            patch("routes.chat._ticker_exists", return_value=True),
            patch("routes.chat._load_session", return_value=session_notes),
            patch("routes.chat._load_prompt", return_value="Stage 3 prompt.") as mock_prompt,
            patch("routes.chat._upsert_session"),
            patch("services.llm.stream_chat", return_value=iter(mock_chunks)),
        ):
            client.post(
                "/api/calls/AAPL/chat",
                json={"message": "go on", "session_id": "some-session", "stage": 1},
                headers={"Authorization": AUTH_HEADER},
            )

        mock_prompt.assert_called_once_with(3)
