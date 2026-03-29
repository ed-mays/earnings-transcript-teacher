"""Unit tests for /api/calls routes."""

import sys
import os
from unittest.mock import MagicMock, patch

import pytest

# Add the api/ directory so FastAPI can resolve `routes.*` imports.
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


@pytest.fixture()
def client():
    """Return a TestClient with required env vars set and DB connections mocked."""
    with patch.dict(os.environ, ENV):
        with patch("psycopg.connect"):
            from fastapi.testclient import TestClient
            from main import app

            with TestClient(app) as c:
                yield c


class TestListCalls:
    def test_returns_call_list(self, client):
        mock_rows = [
            ("AAPL", "Apple Inc.", "2025-01-30", "Technology"),
            ("MSFT", "Microsoft Corp.", None, None),
        ]
        mock_cursor = MagicMock()
        mock_cursor.fetchall.return_value = mock_rows
        mock_conn = MagicMock()
        mock_conn.__enter__ = MagicMock(return_value=mock_conn)
        mock_conn.__exit__ = MagicMock(return_value=False)
        mock_conn.cursor.return_value.__enter__ = MagicMock(return_value=mock_cursor)
        mock_conn.cursor.return_value.__exit__ = MagicMock(return_value=False)

        with patch("psycopg.connect", return_value=mock_conn):
            response = client.get("/api/calls")

        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2
        assert data[0]["ticker"] == "AAPL"
        assert data[0]["company_name"] == "Apple Inc."
        assert data[0]["call_date"] == "2025-01-30"
        assert data[0]["industry"] == "Technology"
        assert data[1]["ticker"] == "MSFT"
        assert data[1]["call_date"] is None

    def test_empty_library(self, client):
        mock_cursor = MagicMock()
        mock_cursor.fetchall.return_value = []
        mock_conn = MagicMock()
        mock_conn.__enter__ = MagicMock(return_value=mock_conn)
        mock_conn.__exit__ = MagicMock(return_value=False)
        mock_conn.cursor.return_value.__enter__ = MagicMock(return_value=mock_cursor)
        mock_conn.cursor.return_value.__exit__ = MagicMock(return_value=False)

        with patch("psycopg.connect", return_value=mock_conn):
            response = client.get("/api/calls")

        assert response.status_code == 200
        assert response.json() == []


class TestGetCall:
    def test_404_for_unknown_ticker(self, client):
        mock_cursor = MagicMock()
        mock_cursor.fetchone.return_value = None
        mock_conn = MagicMock()
        mock_conn.__enter__ = MagicMock(return_value=mock_conn)
        mock_conn.__exit__ = MagicMock(return_value=False)
        mock_conn.cursor.return_value.__enter__ = MagicMock(return_value=mock_cursor)
        mock_conn.cursor.return_value.__exit__ = MagicMock(return_value=False)

        with patch("psycopg.connect", return_value=mock_conn):
            response = client.get("/api/calls/UNKNOWN")

        assert response.status_code == 404

    def test_returns_call_detail(self, client):
        # _ticker_exists returns True
        exists_cursor = MagicMock()
        exists_cursor.fetchone.return_value = (1,)

        with (
            patch("routes.calls._ticker_exists", return_value=True),
            patch("routes.calls.CallRepository") as MockCallRepo,
            patch("routes.calls.AnalysisRepository") as MockAnalysisRepo,
        ):
            call_repo = MockCallRepo.return_value
            call_repo.get_company_info.return_value = ("Apple Inc.", "Technology")
            call_repo.get_call_date.return_value = None

            analysis_repo = MockAnalysisRepo.return_value
            analysis_repo.get_synthesis_for_ticker.return_value = ("bullish", "confident", "neutral")
            analysis_repo.get_keywords_for_ticker.return_value = ["AI", "cloud"]
            analysis_repo.get_themes_for_ticker.return_value = ["Growth", "Margins"]
            analysis_repo.get_topics_for_ticker.return_value = [["ai", "cloud"], ["revenue"]]
            analysis_repo.get_evasion_for_ticker.return_value = [
                ("margin compression", 3, "Deflected with guidance")
            ]
            analysis_repo.get_strategic_shifts_for_ticker.return_value = [
                {"prior_position": "on-prem", "current_position": "cloud", "investor_significance": "high"}
            ]
            analysis_repo.get_speakers_for_ticker.return_value = [
                ("Tim Cook", "executive", "CEO", "Apple Inc.")
            ]

            response = client.get("/api/calls/AAPL")

        assert response.status_code == 200
        data = response.json()
        assert data["ticker"] == "AAPL"
        assert data["company_name"] == "Apple Inc."
        assert data["synthesis"]["overall_sentiment"] == "bullish"
        assert data["keywords"] == ["AI", "cloud"]
        assert len(data["evasion_analyses"]) == 1
        assert data["evasion_analyses"][0]["defensiveness_score"] == 3
        assert len(data["strategic_shifts"]) == 1
        assert len(data["speakers"]) == 1
        assert data["speakers"][0]["name"] == "Tim Cook"


class TestGetSpans:
    def test_404_for_unknown_ticker(self, client):
        with patch("routes.calls._ticker_exists", return_value=False):
            response = client.get("/api/calls/UNKNOWN/spans")
        assert response.status_code == 404

    def test_returns_paginated_spans(self, client):
        mock_cursor = MagicMock()
        mock_cursor.fetchone.return_value = (2,)
        mock_cursor.fetchall.return_value = [
            ("Tim Cook", "prepared", "Revenue grew strongly.", 1),
            ("Luca Maestri", "prepared", "Margins expanded.", 2),
        ]
        mock_conn = MagicMock()
        mock_conn.__enter__ = MagicMock(return_value=mock_conn)
        mock_conn.__exit__ = MagicMock(return_value=False)
        mock_conn.cursor.return_value.__enter__ = MagicMock(return_value=mock_cursor)
        mock_conn.cursor.return_value.__exit__ = MagicMock(return_value=False)

        with (
            patch("routes.calls._ticker_exists", return_value=True),
            patch("psycopg.connect", return_value=mock_conn),
        ):
            response = client.get("/api/calls/AAPL/spans?section=prepared&page=1&page_size=50")

        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 2
        assert data["page"] == 1
        assert len(data["spans"]) == 2
        assert data["spans"][0]["speaker"] == "Tim Cook"
        assert data["spans"][0]["sequence_order"] == 1

    def test_invalid_section_param(self, client):
        response = client.get("/api/calls/AAPL/spans?section=invalid")
        assert response.status_code == 422


class TestSearchTranscript:
    def test_404_for_unknown_ticker(self, client):
        with patch("routes.calls._ticker_exists", return_value=False):
            response = client.get("/api/calls/UNKNOWN/search?q=revenue")
        assert response.status_code == 404

    def test_503_when_voyage_key_missing(self, client):
        with (
            patch("routes.calls._ticker_exists", return_value=True),
            patch.dict(os.environ, {"VOYAGE_API_KEY": ""}, clear=False),
        ):
            # Remove VOYAGE_API_KEY if present
            env_without_voyage = {k: v for k, v in os.environ.items() if k != "VOYAGE_API_KEY"}
            with patch.dict(os.environ, env_without_voyage, clear=True):
                response = client.get("/api/calls/AAPL/search?q=revenue")

        assert response.status_code == 503

    def test_missing_query_param(self, client):
        response = client.get("/api/calls/AAPL/search")
        assert response.status_code == 422

    def test_422_when_query_exceeds_max_length(self, client):
        """Query longer than 500 chars is rejected by FastAPI before any API call."""
        response = client.get(f"/api/calls/AAPL/search?q={'x' * 501}")
        assert response.status_code == 422

    def test_429_when_search_rate_limit_exceeded(self, client):
        """Endpoint returns 429 when the per-user/IP rate limit is hit."""
        from fastapi import HTTPException

        def _raise_429(*args, **kwargs):
            raise HTTPException(status_code=429, detail="Rate limit exceeded")

        with patch("slowapi.Limiter._check_request_limit", side_effect=_raise_429):
            response = client.get("/api/calls/AAPL/search?q=revenue")
        assert response.status_code == 429
