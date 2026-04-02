"""Unit tests for /api/calls routes."""

import logging
import os
from unittest.mock import MagicMock, patch

import pytest

# api_client fixture is provided by tests/conftest.py


class TestListCalls:
    def test_returns_call_list(self, api_client):
        mock_rows = [
            ("AAPL", "Apple Inc.", "2025-01-30", "Technology", "bullish", "low", "Expanding into AI hardware"),
            ("MSFT", "Microsoft Corp.", None, None, None, None, None),
        ]
        mock_cursor = MagicMock()
        mock_cursor.fetchall.return_value = mock_rows
        mock_conn = MagicMock()
        mock_conn.__enter__ = MagicMock(return_value=mock_conn)
        mock_conn.__exit__ = MagicMock(return_value=False)
        mock_conn.cursor.return_value.__enter__ = MagicMock(return_value=mock_cursor)
        mock_conn.cursor.return_value.__exit__ = MagicMock(return_value=False)

        with patch("psycopg.connect", return_value=mock_conn):
            response = api_client.get("/api/calls")

        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2
        assert data[0]["ticker"] == "AAPL"
        assert data[0]["company_name"] == "Apple Inc."
        assert data[0]["call_date"] == "2025-01-30"
        assert data[0]["industry"] == "Technology"
        assert data[0]["overall_sentiment"] == "bullish"
        assert data[0]["evasion_level"] == "low"
        assert data[0]["top_strategic_shift"] == "Expanding into AI hardware"
        assert data[1]["ticker"] == "MSFT"
        assert data[1]["call_date"] is None
        assert data[1]["evasion_level"] is None
        assert data[1]["top_strategic_shift"] is None

    def test_logs_route_entry(self, api_client, caplog):
        """list_calls() emits an INFO log on entry."""
        mock_cursor = MagicMock()
        mock_cursor.fetchall.return_value = []
        mock_conn = MagicMock()
        mock_conn.__enter__ = MagicMock(return_value=mock_conn)
        mock_conn.__exit__ = MagicMock(return_value=False)
        mock_conn.cursor.return_value.__enter__ = MagicMock(return_value=mock_cursor)
        mock_conn.cursor.return_value.__exit__ = MagicMock(return_value=False)

        with caplog.at_level(logging.INFO, logger="routes.calls"):
            with patch("psycopg.connect", return_value=mock_conn):
                api_client.get("/api/calls")

        assert any("GET /api/calls" in r.message for r in caplog.records)

    def test_empty_library(self, api_client):
        mock_cursor = MagicMock()
        mock_cursor.fetchall.return_value = []
        mock_conn = MagicMock()
        mock_conn.__enter__ = MagicMock(return_value=mock_conn)
        mock_conn.__exit__ = MagicMock(return_value=False)
        mock_conn.cursor.return_value.__enter__ = MagicMock(return_value=mock_cursor)
        mock_conn.cursor.return_value.__exit__ = MagicMock(return_value=False)

        with patch("psycopg.connect", return_value=mock_conn):
            response = api_client.get("/api/calls")

        assert response.status_code == 200
        assert response.json() == []


class TestGetCall:
    def test_404_for_unknown_ticker(self, api_client):
        mock_cursor = MagicMock()
        mock_cursor.fetchone.return_value = None
        mock_conn = MagicMock()
        mock_conn.__enter__ = MagicMock(return_value=mock_conn)
        mock_conn.__exit__ = MagicMock(return_value=False)
        mock_conn.cursor.return_value.__enter__ = MagicMock(return_value=mock_cursor)
        mock_conn.cursor.return_value.__exit__ = MagicMock(return_value=False)

        with patch("psycopg.connect", return_value=mock_conn):
            response = api_client.get("/api/calls/UNKNOWN")

        assert response.status_code == 404

    def test_logs_route_entry(self, api_client, caplog):
        """get_call() emits an INFO log with the ticker on entry."""
        with caplog.at_level(logging.INFO, logger="routes.calls"):
            with patch("routes.calls._ticker_exists", return_value=False):
                api_client.get("/api/calls/AAPL")

        assert any("AAPL" in r.message for r in caplog.records)

    def test_returns_call_detail(self, api_client):
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
                ("margin compression", 3, "Deflected with guidance", "margin guidance", "John Smith")
            ]
            analysis_repo.get_strategic_shifts_for_ticker.return_value = [
                {"prior_position": "on-prem", "current_position": "cloud", "investor_significance": "high"}
            ]
            analysis_repo.get_speakers_for_ticker.return_value = [
                ("Tim Cook", "executive", "CEO", "Apple Inc.")
            ]
            analysis_repo.get_call_brief_for_ticker.return_value = None
            analysis_repo.get_takeaways_for_ticker.return_value = []
            analysis_repo.get_misconceptions_for_ticker.return_value = []

            response = api_client.get("/api/calls/AAPL")

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
    def test_404_for_unknown_ticker(self, api_client):
        with patch("routes.calls._ticker_exists", return_value=False):
            response = api_client.get("/api/calls/UNKNOWN/spans")
        assert response.status_code == 404

    def test_logs_route_entry(self, api_client, caplog):
        """get_spans() emits an INFO log with ticker and section on entry."""
        with caplog.at_level(logging.INFO, logger="routes.calls"):
            with patch("routes.calls._ticker_exists", return_value=False):
                api_client.get("/api/calls/AAPL/spans?section=prepared")

        assert any("AAPL" in r.message and "prepared" in r.message for r in caplog.records)

    def test_returns_paginated_spans(self, api_client):
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
            response = api_client.get("/api/calls/AAPL/spans?section=prepared&page=1&page_size=50")

        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 2
        assert data["page"] == 1
        assert len(data["spans"]) == 2
        assert data["spans"][0]["speaker"] == "Tim Cook"
        assert data["spans"][0]["sequence_order"] == 1

    def test_invalid_section_param(self, api_client):
        response = api_client.get("/api/calls/AAPL/spans?section=invalid")
        assert response.status_code == 422


class TestSearchTranscript:
    def test_404_for_unknown_ticker(self, api_client):
        with patch("routes.calls._ticker_exists", return_value=False):
            response = api_client.get("/api/calls/UNKNOWN/search?q=revenue")
        assert response.status_code == 404

    def test_logs_route_entry(self, api_client, caplog):
        """search_transcript() emits an INFO log with ticker and query on entry."""
        with caplog.at_level(logging.INFO, logger="routes.calls"):
            with patch("routes.calls._ticker_exists", return_value=False):
                api_client.get("/api/calls/AAPL/search?q=revenue")

        assert any("AAPL" in r.message and "revenue" in r.message for r in caplog.records)

    def test_503_when_voyage_key_missing(self, api_client):
        with patch("routes.calls._ticker_exists", return_value=True):
            env_without_voyage = {k: v for k, v in os.environ.items() if k != "VOYAGE_API_KEY"}
            with patch.dict(os.environ, env_without_voyage, clear=True):
                response = api_client.get("/api/calls/AAPL/search?q=revenue")

        assert response.status_code == 503

    def test_missing_query_param(self, api_client):
        response = api_client.get("/api/calls/AAPL/search")
        assert response.status_code == 422

    def test_422_when_query_exceeds_max_length(self, api_client):
        """Query longer than 500 chars is rejected by FastAPI before any API call."""
        response = api_client.get(f"/api/calls/AAPL/search?q={'x' * 501}")
        assert response.status_code == 422

    def test_429_when_search_rate_limit_exceeded(self, api_client):
        """Endpoint returns 429 when the per-user/IP rate limit is hit."""
        from fastapi import HTTPException

        def _raise_429(*args, **kwargs):
            raise HTTPException(status_code=429, detail="Rate limit exceeded")

        with patch("slowapi.Limiter._check_request_limit", side_effect=_raise_429):
            response = api_client.get("/api/calls/AAPL/search?q=revenue")
        assert response.status_code == 429


class TestEvasionSignals:
    PAYLOAD = {
        "analyst_concern": "Margin guidance",
        "defensiveness_score": 7,
        "evasion_explanation": "Executive redirected to top-line growth.",
    }

    def _parse_sse(self, text: str) -> list[dict]:
        """Parse SSE response body into a list of event dicts."""
        import json
        events = []
        for block in text.split("\n\n"):
            for line in block.splitlines():
                if line.startswith("data: "):
                    events.append(json.loads(line[len("data: "):]))
        return events

    def test_404_for_unknown_ticker(self, api_client):
        with patch("routes.calls._ticker_exists", return_value=False):
            response = api_client.post("/api/calls/UNKNOWN/evasion-signals", json=self.PAYLOAD)
        assert response.status_code == 404

    def test_happy_path_streams_tokens_and_done(self, api_client):
        """When stream_investor_signals yields tokens, endpoint emits token events then done."""
        def _fake_stream(messages, system_prompt):
            yield "Investors "
            yield "should note."

        with (
            patch("routes.calls._ticker_exists", return_value=True),
            patch("services.llm.stream_investor_signals", side_effect=_fake_stream),
        ):
            response = api_client.post("/api/calls/AAPL/evasion-signals", json=self.PAYLOAD)

        assert response.status_code == 200
        events = self._parse_sse(response.text)
        token_events = [e for e in events if e["type"] == "token"]
        assert len(token_events) == 2
        assert token_events[0]["content"] == "Investors "
        assert token_events[1]["content"] == "should note."
        assert events[-1] == {"type": "done"}

    def test_no_content_emits_error_event(self, api_client):
        """When stream_investor_signals yields nothing, endpoint emits an error SSE event."""
        def _empty_stream(messages, system_prompt):
            return
            yield  # make it a generator

        with (
            patch("routes.calls._ticker_exists", return_value=True),
            patch("services.llm.stream_investor_signals", side_effect=_empty_stream),
        ):
            response = api_client.post("/api/calls/AAPL/evasion-signals", json=self.PAYLOAD)

        assert response.status_code == 200
        events = self._parse_sse(response.text)
        assert len(events) == 1
        assert events[0]["type"] == "error"
        assert "No content" in events[0]["message"]

    def test_api_exception_emits_error_event(self, api_client):
        """When stream_investor_signals raises, endpoint emits an error SSE event."""
        def _failing_stream(messages, system_prompt):
            raise RuntimeError("upstream API error")
            yield  # make it a generator

        with (
            patch("routes.calls._ticker_exists", return_value=True),
            patch("services.llm.stream_investor_signals", side_effect=_failing_stream),
        ):
            response = api_client.post("/api/calls/AAPL/evasion-signals", json=self.PAYLOAD)

        assert response.status_code == 200
        events = self._parse_sse(response.text)
        assert len(events) == 1
        assert events[0]["type"] == "error"


class TestGetAdjacentCalls:
    def test_404_for_unknown_ticker(self, api_client):
        with patch("routes.calls._ticker_exists", return_value=False):
            response = api_client.get("/api/calls/UNKNOWN/adjacent")
        assert response.status_code == 404

    def test_returns_prev_and_next(self, api_client):
        with (
            patch("routes.calls._ticker_exists", return_value=True),
            patch("routes.calls.CallRepository") as MockCallRepo,
        ):
            MockCallRepo.return_value.get_adjacent_calls.return_value = {
                "prev": {
                    "ticker": "MSFT",
                    "fiscal_quarter": "Q3 2024",
                    "company_name": "Microsoft Corp.",
                    "call_date": "2024-07-30",
                },
                "next": {
                    "ticker": "GOOGL",
                    "fiscal_quarter": "Q3 2024",
                    "company_name": "Alphabet Inc.",
                    "call_date": "2024-07-31",
                },
            }
            response = api_client.get("/api/calls/AAPL/adjacent")

        assert response.status_code == 200
        data = response.json()
        assert data["prev"]["ticker"] == "MSFT"
        assert data["prev"]["call_date"] == "2024-07-30"
        assert data["next"]["ticker"] == "GOOGL"

    def test_returns_null_when_no_adjacent(self, api_client):
        """When at the boundary, prev or next is None."""
        with (
            patch("routes.calls._ticker_exists", return_value=True),
            patch("routes.calls.CallRepository") as MockCallRepo,
        ):
            MockCallRepo.return_value.get_adjacent_calls.return_value = {
                "prev": None,
                "next": None,
            }
            response = api_client.get("/api/calls/AAPL/adjacent")

        assert response.status_code == 200
        data = response.json()
        assert data["prev"] is None
        assert data["next"] is None
