"""Integration tests for GET /api/calls and GET /api/calls/{ticker}.

Verifies response shape and empty state — paths that unit tests can't reach
because they mock the repository layer rather than letting the route build
the full Pydantic response from raw DB rows.
"""

from unittest.mock import MagicMock, patch


def _list_conn(rows: list) -> MagicMock:
    """Return a mock psycopg connection whose cursor.fetchall() returns rows.

    list_calls uses the context-manager form:
        with psycopg.connect(...) as conn:
            with conn.cursor() as cur:
                cur.fetchall()
    """
    mock_cursor = MagicMock()
    mock_cursor.__enter__ = MagicMock(return_value=mock_cursor)
    mock_cursor.__exit__ = MagicMock(return_value=False)
    mock_cursor.fetchall.return_value = rows

    mock_conn = MagicMock()
    mock_conn.__enter__ = MagicMock(return_value=mock_conn)
    mock_conn.__exit__ = MagicMock(return_value=False)
    mock_conn.cursor.return_value = mock_cursor

    return mock_conn


# One row matching the 7-column SELECT in list_calls:
# (ticker, company_name, call_date, industry, overall_sentiment, evasion_level, top_strategic_shift)
_SAMPLE_ROW = ("AAPL", "Apple Inc.", "2025-01-30", "Technology", "bullish", "low", "Focus on AI")


class TestListCalls:
    """GET /api/calls — shape and empty state."""

    def test_returns_expected_shape(self, api_client):
        """Response list items contain all required CallSummary fields."""
        with patch("psycopg.connect", return_value=_list_conn([_SAMPLE_ROW])):
            response = api_client.get("/api/calls")
        assert response.status_code == 200
        items = response.json()
        assert len(items) == 1
        item = items[0]
        assert item["ticker"] == "AAPL"
        assert item["company_name"] == "Apple Inc."
        assert item["call_date"] == "2025-01-30"
        assert item["industry"] == "Technology"
        assert item["overall_sentiment"] == "bullish"
        assert item["evasion_level"] == "low"
        assert item["top_strategic_shift"] == "Focus on AI"

    def test_empty_state_returns_empty_list(self, api_client):
        """Returns [] when no calls exist in the database."""
        with patch("psycopg.connect", return_value=_list_conn([])):
            response = api_client.get("/api/calls")
        assert response.status_code == 200
        assert response.json() == []


class TestGetCall:
    """GET /api/calls/{ticker} — 404 path."""

    def test_unknown_ticker_returns_404(self, api_client):
        """Returns 404 when the ticker has no call record."""
        with patch("routes.calls._ticker_exists", return_value=False):
            response = api_client.get("/api/calls/UNKN")
        assert response.status_code == 404
