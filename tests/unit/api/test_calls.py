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
            analysis_repo.get_call_brief_for_ticker.return_value = None
            analysis_repo.get_takeaways_for_ticker.return_value = []
            analysis_repo.get_misconceptions_for_ticker.return_value = []
            analysis_repo.get_signal_strip_flags_for_ticker.return_value = ("low", True)

            response = api_client.get("/api/calls/AAPL")

        assert response.status_code == 200
        data = response.json()
        assert data["ticker"] == "AAPL"
        assert data["company_name"] == "Apple Inc."
        assert "synthesis" not in data
        assert "keywords" not in data
        assert "speakers" not in data
        assert "evasion_analyses" not in data
        assert "strategic_shifts" not in data
        assert "topics" not in data
        assert "themes" not in data
        assert "news_items" not in data
        assert "competitors" not in data

    def test_signal_strip_uses_flags_from_repo(self, api_client):
        """signal_strip is built from get_signal_strip_flags_for_ticker, not full evasion data."""
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
            analysis_repo.get_call_brief_for_ticker.return_value = None
            analysis_repo.get_takeaways_for_ticker.return_value = []
            analysis_repo.get_misconceptions_for_ticker.return_value = []
            analysis_repo.get_signal_strip_flags_for_ticker.return_value = ("high", True)

            response = api_client.get("/api/calls/AAPL")

        assert response.status_code == 200
        strip = response.json()["signal_strip"]
        assert strip["evasion_level"] == "high"
        assert strip["strategic_shift_flagged"] is True


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


class TestNewsContext:
    PAYLOAD = {
        "headline": "Apple beats Q1 estimates",
        "summary": "Revenue grew 10% YoY driven by services.",
        "source": "Reuters",
        "date": "2025-01-31",
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
            response = api_client.post("/api/calls/UNKNOWN/news-context", json=self.PAYLOAD)
        assert response.status_code == 404

    def test_happy_path_streams_tokens_and_done(self, api_client):
        """When stream_investor_signals yields tokens, endpoint emits token events then done."""
        def _fake_stream(messages, system_prompt):
            yield "This news "
            yield "is relevant."

        with (
            patch("routes.calls._ticker_exists", return_value=True),
            patch("routes.calls.CallRepository") as MockCallRepo,
            patch("services.llm.stream_investor_signals", side_effect=_fake_stream),
        ):
            MockCallRepo.return_value.get_company_info.return_value = ("Apple Inc.", "Technology")
            MockCallRepo.return_value.get_call_date.return_value = None
            response = api_client.post("/api/calls/AAPL/news-context", json=self.PAYLOAD)

        assert response.status_code == 200
        events = self._parse_sse(response.text)
        token_events = [e for e in events if e["type"] == "token"]
        assert len(token_events) == 2
        assert token_events[0]["content"] == "This news "
        assert events[-1] == {"type": "done"}

    def test_no_content_emits_error_event(self, api_client):
        def _empty_stream(messages, system_prompt):
            return
            yield  # make it a generator

        with (
            patch("routes.calls._ticker_exists", return_value=True),
            patch("routes.calls.CallRepository") as MockCallRepo,
            patch("services.llm.stream_investor_signals", side_effect=_empty_stream),
        ):
            MockCallRepo.return_value.get_company_info.return_value = ("Apple Inc.", "Technology")
            MockCallRepo.return_value.get_call_date.return_value = None
            response = api_client.post("/api/calls/AAPL/news-context", json=self.PAYLOAD)

        assert response.status_code == 200
        events = self._parse_sse(response.text)
        assert len(events) == 1
        assert events[0]["type"] == "error"

    def test_api_exception_emits_error_event(self, api_client):
        def _failing_stream(messages, system_prompt):
            raise RuntimeError("upstream API error")
            yield  # make it a generator

        with (
            patch("routes.calls._ticker_exists", return_value=True),
            patch("routes.calls.CallRepository") as MockCallRepo,
            patch("services.llm.stream_investor_signals", side_effect=_failing_stream),
        ):
            MockCallRepo.return_value.get_company_info.return_value = ("Apple Inc.", "Technology")
            MockCallRepo.return_value.get_call_date.return_value = None
            response = api_client.post("/api/calls/AAPL/news-context", json=self.PAYLOAD)

        assert response.status_code == 200
        events = self._parse_sse(response.text)
        assert len(events) == 1
        assert events[0]["type"] == "error"


class TestGetCallTopics:
    def test_404_for_unknown_ticker(self, api_client):
        with patch("routes.calls._ticker_exists", return_value=False):
            response = api_client.get("/api/calls/UNKNOWN/topics")
        assert response.status_code == 404

    def test_returns_topics_and_themes(self, api_client):
        with (
            patch("routes.calls._ticker_exists", return_value=True),
            patch("routes.calls.AnalysisRepository") as MockAnalysisRepo,
        ):
            repo = MockAnalysisRepo.return_value
            repo.get_topics_for_ticker.return_value = [
                {"label": "AI & Cloud", "terms": ["ai", "cloud"], "summary": "Adoption accelerating."},
            ]
            repo.get_themes_for_ticker.return_value = ["Growth", "Margins"]
            response = api_client.get("/api/calls/AAPL/topics")

        assert response.status_code == 200
        data = response.json()
        assert len(data["topics"]) == 1
        assert data["topics"][0]["label"] == "AI & Cloud"
        assert data["themes"] == ["Growth", "Margins"]

    def test_empty_state(self, api_client):
        with (
            patch("routes.calls._ticker_exists", return_value=True),
            patch("routes.calls.AnalysisRepository") as MockAnalysisRepo,
        ):
            repo = MockAnalysisRepo.return_value
            repo.get_topics_for_ticker.return_value = []
            repo.get_themes_for_ticker.return_value = []
            response = api_client.get("/api/calls/AAPL/topics")

        assert response.status_code == 200
        data = response.json()
        assert data["topics"] == []
        assert data["themes"] == []


class TestThemeSignals:
    PAYLOAD = {
        "label": "AI & Cloud",
        "summary": "Management repeatedly emphasised AI-driven efficiency gains.",
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
            response = api_client.post("/api/calls/UNKNOWN/theme-signals", json=self.PAYLOAD)
        assert response.status_code == 404

    def test_happy_path_streams_tokens_and_done(self, api_client):
        """When stream_investor_signals yields tokens, endpoint emits token events then done."""
        def _fake_stream(messages, system_prompt):
            yield "This theme "
            yield "signals intent."

        with (
            patch("routes.calls._ticker_exists", return_value=True),
            patch("services.llm.stream_investor_signals", side_effect=_fake_stream),
        ):
            response = api_client.post("/api/calls/AAPL/theme-signals", json=self.PAYLOAD)

        assert response.status_code == 200
        events = self._parse_sse(response.text)
        token_events = [e for e in events if e["type"] == "token"]
        assert len(token_events) == 2
        assert token_events[0]["content"] == "This theme "
        assert token_events[1]["content"] == "signals intent."
        assert events[-1] == {"type": "done"}

    def test_no_content_emits_error_event(self, api_client):
        def _empty_stream(messages, system_prompt):
            return
            yield  # make it a generator

        with (
            patch("routes.calls._ticker_exists", return_value=True),
            patch("services.llm.stream_investor_signals", side_effect=_empty_stream),
        ):
            response = api_client.post("/api/calls/AAPL/theme-signals", json=self.PAYLOAD)

        assert response.status_code == 200
        events = self._parse_sse(response.text)
        assert len(events) == 1
        assert events[0]["type"] == "error"
        assert "No content" in events[0]["message"]

    def test_api_exception_emits_error_event(self, api_client):
        def _failing_stream(messages, system_prompt):
            raise RuntimeError("upstream API error")
            yield  # make it a generator

        with (
            patch("routes.calls._ticker_exists", return_value=True),
            patch("services.llm.stream_investor_signals", side_effect=_failing_stream),
        ):
            response = api_client.post("/api/calls/AAPL/theme-signals", json=self.PAYLOAD)

        assert response.status_code == 200
        events = self._parse_sse(response.text)
        assert len(events) == 1
        assert events[0]["type"] == "error"


class TestShiftSignals:
    PAYLOAD = {
        "prior_position": "Focused on hardware margins.",
        "current_position": "Pivoting to services-led revenue mix.",
        "investor_significance": "Services carry ~70% gross margin vs ~35% for hardware.",
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
            response = api_client.post("/api/calls/UNKNOWN/shift-signals", json=self.PAYLOAD)
        assert response.status_code == 404

    def test_happy_path_streams_tokens_and_done(self, api_client):
        """When stream_investor_signals yields tokens, endpoint emits token events then done."""
        def _fake_stream(messages, system_prompt):
            yield "This shift "
            yield "changes the thesis."

        with (
            patch("routes.calls._ticker_exists", return_value=True),
            patch("services.llm.stream_investor_signals", side_effect=_fake_stream),
        ):
            response = api_client.post("/api/calls/AAPL/shift-signals", json=self.PAYLOAD)

        assert response.status_code == 200
        events = self._parse_sse(response.text)
        token_events = [e for e in events if e["type"] == "token"]
        assert len(token_events) == 2
        assert token_events[0]["content"] == "This shift "
        assert token_events[1]["content"] == "changes the thesis."
        assert events[-1] == {"type": "done"}

    def test_no_content_emits_error_event(self, api_client):
        def _empty_stream(messages, system_prompt):
            return
            yield  # make it a generator

        with (
            patch("routes.calls._ticker_exists", return_value=True),
            patch("services.llm.stream_investor_signals", side_effect=_empty_stream),
        ):
            response = api_client.post("/api/calls/AAPL/shift-signals", json=self.PAYLOAD)

        assert response.status_code == 200
        events = self._parse_sse(response.text)
        assert len(events) == 1
        assert events[0]["type"] == "error"
        assert "No content" in events[0]["message"]

    def test_api_exception_emits_error_event(self, api_client):
        def _failing_stream(messages, system_prompt):
            raise RuntimeError("upstream API error")
            yield  # make it a generator

        with (
            patch("routes.calls._ticker_exists", return_value=True),
            patch("services.llm.stream_investor_signals", side_effect=_failing_stream),
        ):
            response = api_client.post("/api/calls/AAPL/shift-signals", json=self.PAYLOAD)

        assert response.status_code == 200
        events = self._parse_sse(response.text)
        assert len(events) == 1
        assert events[0]["type"] == "error"


class TestGetCallEvasion:
    def test_404_for_unknown_ticker(self, api_client):
        with patch("routes.calls._ticker_exists", return_value=False):
            response = api_client.get("/api/calls/UNKNOWN/evasion")
        assert response.status_code == 404

    def test_returns_evasion_analyses_with_level(self, api_client):
        with (
            patch("routes.calls._ticker_exists", return_value=True),
            patch("routes.calls.AnalysisRepository") as MockAnalysisRepo,
        ):
            MockAnalysisRepo.return_value.get_evasion_for_ticker.return_value = [
                ("margin guidance", 7, "Deflected to top-line", "margins", "John Smith", "deflect_to_forward_looking"),
                ("capex outlook", 8, "Vague non-answer", "capex", "Jane Doe", "verbose_non_answer"),
            ]
            response = api_client.get("/api/calls/AAPL/evasion")

        assert response.status_code == 200
        data = response.json()
        assert len(data["evasion_analyses"]) == 2
        assert data["evasion_analyses"][0]["defensiveness_score"] == 7
        assert data["evasion_level"] == "high"

    def test_empty_state_returns_null_level(self, api_client):
        with (
            patch("routes.calls._ticker_exists", return_value=True),
            patch("routes.calls.AnalysisRepository") as MockAnalysisRepo,
        ):
            MockAnalysisRepo.return_value.get_evasion_for_ticker.return_value = []
            response = api_client.get("/api/calls/AAPL/evasion")

        assert response.status_code == 200
        data = response.json()
        assert data["evasion_analyses"] == []
        assert data["evasion_level"] is None


class TestGetCallStrategicShifts:
    def test_404_for_unknown_ticker(self, api_client):
        with patch("routes.calls._ticker_exists", return_value=False):
            response = api_client.get("/api/calls/UNKNOWN/strategic-shifts")
        assert response.status_code == 404

    def test_returns_strategic_shifts(self, api_client):
        with (
            patch("routes.calls._ticker_exists", return_value=True),
            patch("routes.calls.AnalysisRepository") as MockAnalysisRepo,
        ):
            MockAnalysisRepo.return_value.get_strategic_shifts_for_ticker.return_value = [
                {"prior_position": "on-prem", "current_position": "cloud", "investor_significance": "high"},
            ]
            response = api_client.get("/api/calls/AAPL/strategic-shifts")

        assert response.status_code == 200
        data = response.json()
        assert len(data["strategic_shifts"]) == 1
        assert data["strategic_shifts"][0]["current_position"] == "cloud"

    def test_empty_state(self, api_client):
        with (
            patch("routes.calls._ticker_exists", return_value=True),
            patch("routes.calls.AnalysisRepository") as MockAnalysisRepo,
        ):
            MockAnalysisRepo.return_value.get_strategic_shifts_for_ticker.return_value = []
            response = api_client.get("/api/calls/AAPL/strategic-shifts")

        assert response.status_code == 200
        assert response.json()["strategic_shifts"] == []


class TestGetCallCompetitors:
    def test_404_for_unknown_ticker(self, api_client):
        with patch("routes.calls._ticker_exists", return_value=False):
            response = api_client.get("/api/calls/UNKNOWN/competitors")
        assert response.status_code == 404

    def test_returns_cached_competitors(self, api_client):
        from core.models import Competitor

        with (
            patch("routes.calls._ticker_exists", return_value=True),
            patch("routes.calls.CallRepository"),
            patch("routes.calls.CompetitorRepository") as MockCompRepo,
        ):
            MockCompRepo.return_value.get.return_value = [
                Competitor(name="Google", ticker="GOOGL", description="Search.", mentioned_in_transcript=True)
            ]
            response = api_client.get("/api/calls/AAPL/competitors")

        assert response.status_code == 200
        data = response.json()
        assert len(data["competitors"]) == 1
        assert data["competitors"][0]["name"] == "Google"
        assert data["competitors"][0]["mentioned_in_transcript"] is True

    def test_lazy_hydration_on_cache_miss(self, api_client):
        """When cache is empty, fetch_competitors is called and result is returned."""
        from core.models import Competitor

        fetched = [Competitor(name="Microsoft", ticker="MSFT", description="Cloud.", mentioned_in_transcript=False)]

        with (
            patch("routes.calls._ticker_exists", return_value=True),
            patch("routes.calls.CallRepository") as MockCallRepo,
            patch("routes.calls.CompetitorRepository") as MockCompRepo,
            patch("routes.calls.fetch_competitors", return_value=fetched) as mock_fetch,
        ):
            MockCallRepo.return_value.get_company_info.return_value = ("Apple Inc.", "Technology")
            MockCallRepo.return_value.get_transcript_text.return_value = "transcript text"
            MockCompRepo.return_value.get.return_value = []
            response = api_client.get("/api/calls/AAPL/competitors")

        assert response.status_code == 200
        mock_fetch.assert_called_once()
        data = response.json()
        assert len(data["competitors"]) == 1
        assert data["competitors"][0]["ticker"] == "MSFT"


class TestGetCallNews:
    def test_404_for_unknown_ticker(self, api_client):
        with patch("routes.calls._ticker_exists", return_value=False):
            response = api_client.get("/api/calls/UNKNOWN/news")
        assert response.status_code == 404

    def test_returns_cached_news(self, api_client):
        from core.models import NewsItem

        with (
            patch("routes.calls._ticker_exists", return_value=True),
            patch("routes.calls.CallRepository"),
            patch("routes.calls.AnalysisRepository"),
            patch("routes.calls.NewsRepository") as MockNewsRepo,
        ):
            MockNewsRepo.return_value.get.return_value = [
                NewsItem(headline="Apple beats Q1", url="https://example.com", source="Reuters", date="2025-01-31", summary="Strong quarter.")
            ]
            response = api_client.get("/api/calls/AAPL/news")

        assert response.status_code == 200
        data = response.json()
        assert len(data["news_items"]) == 1
        assert data["news_items"][0]["headline"] == "Apple beats Q1"

    def test_lazy_hydration_skipped_when_call_date_none(self, api_client):
        """When cache is empty and call_date is None, fetch_recent_news is not called."""
        with (
            patch("routes.calls._ticker_exists", return_value=True),
            patch("routes.calls.CallRepository") as MockCallRepo,
            patch("routes.calls.AnalysisRepository") as MockAnalysisRepo,
            patch("routes.calls.NewsRepository") as MockNewsRepo,
            patch("routes.calls.fetch_recent_news") as mock_fetch,
        ):
            MockCallRepo.return_value.get_company_info.return_value = ("Apple Inc.", "Technology")
            MockCallRepo.return_value.get_call_date.return_value = None
            MockAnalysisRepo.return_value.get_themes_for_ticker.return_value = []
            MockNewsRepo.return_value.get.return_value = []
            response = api_client.get("/api/calls/AAPL/news")

        assert response.status_code == 200
        mock_fetch.assert_not_called()
        assert response.json()["news_items"] == []


class TestGetCallSynthesis:
    def test_404_for_unknown_ticker(self, api_client):
        with patch("routes.calls._ticker_exists", return_value=False):
            response = api_client.get("/api/calls/UNKNOWN/synthesis")
        assert response.status_code == 404

    def test_returns_synthesis(self, api_client):
        with (
            patch("routes.calls._ticker_exists", return_value=True),
            patch("routes.calls.AnalysisRepository") as MockAnalysisRepo,
        ):
            MockAnalysisRepo.return_value.get_synthesis_for_ticker.return_value = (
                "bullish", "confident", "neutral"
            )
            response = api_client.get("/api/calls/AAPL/synthesis")

        assert response.status_code == 200
        data = response.json()
        assert data["synthesis"]["overall_sentiment"] == "bullish"
        assert data["synthesis"]["executive_tone"] == "confident"
        assert data["synthesis"]["analyst_sentiment"] == "neutral"

    def test_returns_null_synthesis_when_none(self, api_client):
        with (
            patch("routes.calls._ticker_exists", return_value=True),
            patch("routes.calls.AnalysisRepository") as MockAnalysisRepo,
        ):
            MockAnalysisRepo.return_value.get_synthesis_for_ticker.return_value = None
            response = api_client.get("/api/calls/AAPL/synthesis")

        assert response.status_code == 200
        assert response.json()["synthesis"] is None


class TestGetLearnAnnotations:
    def test_404_for_unknown_ticker(self, api_client):
        with patch("routes.calls._ticker_exists", return_value=False):
            response = api_client.get("/api/calls/UNKNOWN/learn-annotations")
        assert response.status_code == 404

    def test_returns_composed_annotations(self, api_client):
        with (
            patch("routes.calls._ticker_exists", return_value=True),
            patch("routes.calls.AnalysisRepository") as MockAnalysisRepo,
        ):
            MockAnalysisRepo.return_value.get_learn_annotations_for_ticker.return_value = {
                "terms": [
                    {
                        "term": "ARR",
                        "definition": "Annual recurring revenue",
                        "explanation": "Revenue from subscriptions normalized to one year.",
                        "category": "financial",
                    },
                    {
                        "term": "Data center GPU",
                        "definition": "Specialized compute hardware",
                        "explanation": "Used for AI workloads.",
                        "category": "industry",
                    },
                ],
                "evasion": [
                    {
                        "analyst_name": "Jane Doe",
                        "question_topic": "Margins",
                        "question_text": "Why did gross margin compress?",
                        "answer_text": "We're investing in growth.",
                        "analyst_concern": "Dodging margin question",
                        "defensiveness_score": 7,
                        "evasion_explanation": "Deflected to growth narrative.",
                    }
                ],
                "takeaways": [
                    {"takeaway": "Q4 revenue beat guidance", "why_it_matters": "Confirms demand."}
                ],
                "misconceptions": [
                    {"fact": "CapEx rose 30%", "misinterpretation": "Growth slowing", "correction": "Scaling capacity."}
                ],
                "synthesis": {
                    "overall_sentiment": "bullish",
                    "executive_tone": "confident",
                    "analyst_sentiment": "neutral",
                },
            }
            response = api_client.get("/api/calls/NVDA/learn-annotations")

        assert response.status_code == 200
        data = response.json()
        assert len(data["terms"]) == 2
        assert data["terms"][0]["term"] == "ARR"
        assert data["terms"][0]["category"] == "financial"
        assert len(data["evasion"]) == 1
        assert data["evasion"][0]["defensiveness_score"] == 7
        assert data["evasion"][0]["analyst_name"] == "Jane Doe"
        assert len(data["takeaways"]) == 1
        assert data["takeaways"][0]["takeaway"] == "Q4 revenue beat guidance"
        assert len(data["misconceptions"]) == 1
        assert data["misconceptions"][0]["fact"] == "CapEx rose 30%"
        assert data["synthesis"]["overall_sentiment"] == "bullish"
        assert data["synthesis"]["executive_tone"] == "confident"
        assert data["synthesis"]["analyst_sentiment"] == "neutral"

    def test_empty_state(self, api_client):
        with (
            patch("routes.calls._ticker_exists", return_value=True),
            patch("routes.calls.AnalysisRepository") as MockAnalysisRepo,
        ):
            MockAnalysisRepo.return_value.get_learn_annotations_for_ticker.return_value = {
                "terms": [],
                "evasion": [],
                "takeaways": [],
                "misconceptions": [],
                "synthesis": None,
            }
            response = api_client.get("/api/calls/EMPTY/learn-annotations")

        assert response.status_code == 200
        data = response.json()
        assert data["terms"] == []
        assert data["evasion"] == []
        assert data["takeaways"] == []
        assert data["misconceptions"] == []
        assert data["synthesis"] is None


class TestGetCallSpeakers:
    def test_404_for_unknown_ticker(self, api_client):
        with patch("routes.calls._ticker_exists", return_value=False):
            response = api_client.get("/api/calls/UNKNOWN/speakers")
        assert response.status_code == 404

    def test_returns_speakers(self, api_client):
        with (
            patch("routes.calls._ticker_exists", return_value=True),
            patch("routes.calls.AnalysisRepository") as MockAnalysisRepo,
        ):
            MockAnalysisRepo.return_value.get_speakers_for_ticker.return_value = [
                ("Tim Cook", "executive", "CEO", "Apple Inc."),
                ("Luca Maestri", "executive", "CFO", "Apple Inc."),
            ]
            response = api_client.get("/api/calls/AAPL/speakers")

        assert response.status_code == 200
        data = response.json()
        assert len(data["speakers"]) == 2
        assert data["speakers"][0]["name"] == "Tim Cook"
        assert data["speakers"][0]["title"] == "CEO"
        assert data["speakers"][1]["name"] == "Luca Maestri"

    def test_empty_state(self, api_client):
        with (
            patch("routes.calls._ticker_exists", return_value=True),
            patch("routes.calls.AnalysisRepository") as MockAnalysisRepo,
        ):
            MockAnalysisRepo.return_value.get_speakers_for_ticker.return_value = []
            response = api_client.get("/api/calls/AAPL/speakers")

        assert response.status_code == 200
        assert response.json()["speakers"] == []


class TestGetCallKeywords:
    def test_404_for_unknown_ticker(self, api_client):
        with patch("routes.calls._ticker_exists", return_value=False):
            response = api_client.get("/api/calls/UNKNOWN/keywords")
        assert response.status_code == 404

    def test_returns_keywords(self, api_client):
        with (
            patch("routes.calls._ticker_exists", return_value=True),
            patch("routes.calls.AnalysisRepository") as MockAnalysisRepo,
        ):
            MockAnalysisRepo.return_value.get_keywords_for_ticker.return_value = ["AI", "cloud", "margin"]
            response = api_client.get("/api/calls/AAPL/keywords")

        assert response.status_code == 200
        assert response.json()["keywords"] == ["AI", "cloud", "margin"]

    def test_empty_state(self, api_client):
        with (
            patch("routes.calls._ticker_exists", return_value=True),
            patch("routes.calls.AnalysisRepository") as MockAnalysisRepo,
        ):
            MockAnalysisRepo.return_value.get_keywords_for_ticker.return_value = []
            response = api_client.get("/api/calls/AAPL/keywords")

        assert response.status_code == 200
        assert response.json()["keywords"] == []


class TestTrackSection:
    PAYLOAD = {"section": "understand-the-narrative", "open": True}

    def test_returns_ok(self, api_client):
        with patch("routes.calls.track") as mock_track:
            response = api_client.post("/api/calls/AAPL/track", json=self.PAYLOAD)
        assert response.status_code == 200
        assert response.json() == {"ok": True}

    def test_calls_track_with_correct_properties(self, api_client):
        with patch("routes.calls.track") as mock_track:
            api_client.post("/api/calls/AAPL/track", json=self.PAYLOAD)
        mock_track.assert_called_once_with(
            "section_toggled",
            properties={"ticker": "AAPL", "section": "understand-the-narrative", "open": True},
        )

    def test_tracks_close_event(self, api_client):
        with patch("routes.calls.track") as mock_track:
            api_client.post("/api/calls/AAPL/track", json={"section": "orient", "open": False})
        mock_track.assert_called_once_with(
            "section_toggled",
            properties={"ticker": "AAPL", "section": "orient", "open": False},
        )
