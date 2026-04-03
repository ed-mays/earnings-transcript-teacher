"""Unit tests for NewsRepository."""

from unittest.mock import MagicMock, call, patch

import pytest

from core.models import NewsItem
from db.repositories.news import NewsRepository

CONN_STR = "dbname=test"

_ITEM_A = NewsItem(
    headline="Apple beats Q1 estimates",
    url="https://example.com/apple-q1",
    source="Reuters",
    date="2025-01-31",
    summary="Revenue grew 10% YoY driven by services.",
)
_ITEM_B = NewsItem(
    headline="iPhone demand resilient in China",
    url="https://example.com/iphone-china",
    source="Bloomberg",
    date="2025-01-28",
    summary="Sell-through data shows stable demand.",
)


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


class TestNewsRepositoryGet:
    def test_returns_empty_when_no_rows(self, mock_conn):
        m_conn, m_cur = mock_conn
        m_cur.fetchall.return_value = []

        with patch("psycopg.connect", return_value=m_conn):
            repo = NewsRepository(CONN_STR)
            result = repo.get("AAPL")

        assert result == []

    def test_returns_news_items(self, mock_conn):
        m_conn, m_cur = mock_conn
        m_cur.fetchall.return_value = [
            (_ITEM_A.headline, _ITEM_A.url, _ITEM_A.source, _ITEM_A.date, _ITEM_A.summary),
            (_ITEM_B.headline, _ITEM_B.url, _ITEM_B.source, _ITEM_B.date, _ITEM_B.summary),
        ]

        with patch("psycopg.connect", return_value=m_conn):
            repo = NewsRepository(CONN_STR)
            result = repo.get("AAPL")

        assert len(result) == 2
        assert result[0].headline == _ITEM_A.headline
        assert result[0].url == _ITEM_A.url
        assert result[0].source == _ITEM_A.source
        assert result[1].headline == _ITEM_B.headline

    def test_returns_empty_on_db_error(self, mock_conn):
        m_conn, m_cur = mock_conn
        m_cur.fetchall.side_effect = Exception("DB unavailable")

        with patch("psycopg.connect", return_value=m_conn):
            repo = NewsRepository(CONN_STR)
            result = repo.get("AAPL")

        assert result == []


class TestNewsRepositorySave:
    def test_skips_save_when_no_call_found(self, mock_conn):
        """When _get_call_id returns None, save returns without inserting."""
        m_conn, m_cur = mock_conn
        m_cur.fetchone.return_value = None  # no call_id found

        with patch("psycopg.connect", return_value=m_conn):
            repo = NewsRepository(CONN_STR)
            repo.save("AAPL", [_ITEM_A])

        # Only the call_id SELECT should have been executed, no DELETE or INSERT
        executed_sqls = [str(c.args[0]).strip().lower() for c in m_cur.execute.call_args_list]
        assert not any("insert" in sql for sql in executed_sqls)

    def test_deletes_then_inserts(self, mock_conn):
        """save() deletes existing rows then inserts new items."""
        m_conn, m_cur = mock_conn
        call_id = "test-uuid-1234"
        m_cur.fetchone.return_value = (call_id,)

        with patch("psycopg.connect", return_value=m_conn):
            repo = NewsRepository(CONN_STR)
            repo.save("AAPL", [_ITEM_A, _ITEM_B])

        executed_sqls = [str(c.args[0]).lower() for c in m_cur.execute.call_args_list]
        assert any("delete" in sql for sql in executed_sqls)
        assert sum("insert" in sql for sql in executed_sqls) == 2
        m_conn.commit.assert_called_once()

    def test_handles_db_error_gracefully(self, mock_conn):
        """save() logs and swallows DB errors rather than raising."""
        m_conn, m_cur = mock_conn
        m_cur.execute.side_effect = Exception("connection lost")

        with patch("psycopg.connect", return_value=m_conn):
            repo = NewsRepository(CONN_STR)
            # should not raise
            repo.save("AAPL", [_ITEM_A])
