"""Unit tests for CallRepository.get_adjacent_calls."""

from unittest.mock import MagicMock, patch

import pytest

from db.repositories import CallRepository

CONN_STR = "dbname=test"


@pytest.fixture()
def mock_conn():
    """Return a mocked psycopg connection and cursor."""
    m_conn = MagicMock()
    m_conn.__enter__ = MagicMock(return_value=m_conn)
    m_conn.__exit__ = MagicMock(return_value=False)
    m_cur = MagicMock()
    m_cur.__enter__ = MagicMock(return_value=m_cur)
    m_cur.__exit__ = MagicMock(return_value=False)
    m_conn.cursor.return_value = m_cur
    return m_conn, m_cur


class TestGetAdjacentCalls:
    def test_returns_prev_and_next(self, mock_conn):
        m_conn, m_cur = mock_conn
        m_cur.fetchone.side_effect = [
            ("MSFT", "Q3 2024", "Microsoft Corp.", "2024-07-30"),
            ("GOOGL", "Q3 2024", "Alphabet Inc.", "2024-07-31"),
        ]

        with patch("psycopg.connect", return_value=m_conn):
            repo = CallRepository(CONN_STR)
            result = repo.get_adjacent_calls("AAPL")

        assert result["prev"] == {
            "ticker": "MSFT",
            "fiscal_quarter": "Q3 2024",
            "company_name": "Microsoft Corp.",
            "call_date": "2024-07-30",
        }
        assert result["next"] == {
            "ticker": "GOOGL",
            "fiscal_quarter": "Q3 2024",
            "company_name": "Alphabet Inc.",
            "call_date": "2024-07-31",
        }

    def test_returns_none_when_no_prev(self, mock_conn):
        """First call in history — no previous call exists."""
        m_conn, m_cur = mock_conn
        m_cur.fetchone.side_effect = [
            None,
            ("GOOGL", "Q3 2024", "Alphabet Inc.", "2024-07-31"),
        ]

        with patch("psycopg.connect", return_value=m_conn):
            repo = CallRepository(CONN_STR)
            result = repo.get_adjacent_calls("AAPL")

        assert result["prev"] is None
        assert result["next"]["ticker"] == "GOOGL"

    def test_returns_none_when_no_next(self, mock_conn):
        """Most recent call — no next call exists."""
        m_conn, m_cur = mock_conn
        m_cur.fetchone.side_effect = [
            ("MSFT", "Q3 2024", "Microsoft Corp.", "2024-07-30"),
            None,
        ]

        with patch("psycopg.connect", return_value=m_conn):
            repo = CallRepository(CONN_STR)
            result = repo.get_adjacent_calls("AAPL")

        assert result["prev"]["ticker"] == "MSFT"
        assert result["next"] is None

    def test_returns_empty_on_db_error(self, mock_conn):
        """DB failure returns graceful fallback — no exception raised."""
        m_conn, m_cur = mock_conn
        m_cur.fetchone.side_effect = Exception("connection refused")

        with patch("psycopg.connect", return_value=m_conn):
            repo = CallRepository(CONN_STR)
            result = repo.get_adjacent_calls("AAPL")

        assert result == {"prev": None, "next": None}
