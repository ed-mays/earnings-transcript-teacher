"""Unit tests for LearningRepository session methods."""

import json
import uuid
from unittest.mock import MagicMock, call, patch

import pytest

from db.repositories import LearningRepository, SYSTEM_USER_ID

CONN_STR = "dbname=test"
TICKER = "AAPL"
SESSION_ID = str(uuid.uuid4())
CALL_ID = str(uuid.uuid4())
USER_ID = "550e8400-e29b-41d4-a716-446655440000"
OTHER_USER_ID = "660e8400-e29b-41d4-a716-446655440001"


@pytest.fixture()
def mock_conn():
    """Return a mocked psycopg connection context manager."""
    m_conn = MagicMock()
    m_conn.__enter__ = MagicMock(return_value=m_conn)
    m_conn.__exit__ = MagicMock(return_value=False)
    m_cur = MagicMock()
    m_cur.__enter__ = MagicMock(return_value=m_cur)
    m_cur.__exit__ = MagicMock(return_value=False)
    m_conn.cursor.return_value = m_cur
    return m_conn, m_cur


class TestSaveSession:
    def test_uses_provided_user_id(self, mock_conn):
        """save_session writes the caller-supplied user_id to the DB."""
        m_conn, m_cur = mock_conn
        m_cur.fetchone.return_value = (CALL_ID,)

        with patch("psycopg.connect", return_value=m_conn):
            repo = LearningRepository(CONN_STR)
            result = repo.save_session(
                ticker=TICKER,
                session_id=SESSION_ID,
                topic="free cash flow",
                stage=1,
                messages=[],
                completed=False,
                user_id=USER_ID,
            )

        assert result is True
        insert_call = m_cur.execute.call_args_list[-1]
        params = insert_call[0][1]
        assert params[1] == USER_ID

    def test_falls_back_to_system_user_id_by_default(self, mock_conn):
        """save_session defaults to SYSTEM_USER_ID when user_id is omitted."""
        m_conn, m_cur = mock_conn
        m_cur.fetchone.return_value = (CALL_ID,)

        with patch("psycopg.connect", return_value=m_conn):
            repo = LearningRepository(CONN_STR)
            result = repo.save_session(
                ticker=TICKER,
                session_id=SESSION_ID,
                topic="margins",
                stage=2,
                messages=[],
                completed=False,
            )

        assert result is True
        insert_call = m_cur.execute.call_args_list[-1]
        params = insert_call[0][1]
        assert params[1] == SYSTEM_USER_ID

    def test_returns_false_when_ticker_not_found(self, mock_conn):
        """save_session returns False when no call row exists for the ticker."""
        m_conn, m_cur = mock_conn
        m_cur.fetchone.return_value = None

        with patch("psycopg.connect", return_value=m_conn):
            repo = LearningRepository(CONN_STR)
            result = repo.save_session(
                ticker="UNKNOWN",
                session_id=SESSION_ID,
                topic="topic",
                stage=1,
                messages=[],
                completed=False,
            )

        assert result is False


class TestGetSessionsForTicker:
    def _make_row(self, topic: str = "revenue") -> tuple:
        notes = json.dumps({"topic": topic, "stage": 1, "messages": [], "type": "feynman"})
        return (SESSION_ID, notes, None, "2024-01-01", None)

    def test_no_user_id_filter_omits_user_clause(self, mock_conn):
        """Without user_id, the query uses only the ticker WHERE clause."""
        m_conn, m_cur = mock_conn
        m_cur.fetchall.return_value = [self._make_row()]

        with patch("psycopg.connect", return_value=m_conn):
            repo = LearningRepository(CONN_STR)
            rows = repo.get_sessions_for_ticker(TICKER)

        assert len(rows) == 1
        sql = m_cur.execute.call_args[0][0]
        assert "user_id" not in sql
        params = m_cur.execute.call_args[0][1]
        assert params == (TICKER,)

    def test_with_user_id_adds_user_filter(self, mock_conn):
        """With user_id, the query adds an AND ls.user_id = %s::uuid clause."""
        m_conn, m_cur = mock_conn
        m_cur.fetchall.return_value = [self._make_row()]

        with patch("psycopg.connect", return_value=m_conn):
            repo = LearningRepository(CONN_STR)
            rows = repo.get_sessions_for_ticker(TICKER, user_id=USER_ID)

        assert len(rows) == 1
        sql = m_cur.execute.call_args[0][0]
        assert "user_id" in sql
        params = m_cur.execute.call_args[0][1]
        assert params == (TICKER, USER_ID)

    def test_returns_empty_list_on_db_error(self, mock_conn):
        """DB errors are swallowed and an empty list is returned."""
        m_conn, m_cur = mock_conn
        m_cur.fetchall.side_effect = Exception("connection refused")

        with patch("psycopg.connect", return_value=m_conn):
            repo = LearningRepository(CONN_STR)
            rows = repo.get_sessions_for_ticker(TICKER, user_id=USER_ID)

        assert rows == []


class TestGetSessionById:
    def _notes_json(self) -> str:
        return json.dumps({"topic": "margins", "stage": 2, "messages": []})

    def test_returns_notes_for_correct_owner(self, mock_conn):
        """Returns parsed notes dict when session belongs to the requesting user."""
        m_conn, m_cur = mock_conn
        m_cur.fetchone.return_value = (self._notes_json(), USER_ID)

        with patch("psycopg.connect", return_value=m_conn):
            repo = LearningRepository(CONN_STR)
            result = repo.get_session_by_id(SESSION_ID, USER_ID)

        assert result is not None
        assert result["topic"] == "margins"

    def test_returns_none_when_session_not_found(self, mock_conn):
        """Returns None when no session row matches the given ID."""
        m_conn, m_cur = mock_conn
        m_cur.fetchone.return_value = None

        with patch("psycopg.connect", return_value=m_conn):
            repo = LearningRepository(CONN_STR)
            result = repo.get_session_by_id(SESSION_ID, USER_ID)

        assert result is None

    def test_raises_on_ownership_mismatch(self, mock_conn):
        """Raises ValueError when the session belongs to a different user."""
        m_conn, m_cur = mock_conn
        m_cur.fetchone.return_value = (self._notes_json(), OTHER_USER_ID)

        with patch("psycopg.connect", return_value=m_conn):
            repo = LearningRepository(CONN_STR)
            with pytest.raises(ValueError, match="different user"):
                repo.get_session_by_id(SESSION_ID, USER_ID)

    def test_returns_none_on_db_error(self, mock_conn):
        """DB errors are swallowed and None is returned."""
        m_conn, m_cur = mock_conn
        m_cur.fetchone.side_effect = Exception("db down")

        with patch("psycopg.connect", return_value=m_conn):
            repo = LearningRepository(CONN_STR)
            result = repo.get_session_by_id(SESSION_ID, USER_ID)

        assert result is None
