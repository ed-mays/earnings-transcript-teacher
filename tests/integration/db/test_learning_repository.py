import json
import pytest

from db.repositories.learning import LearningRepository, SYSTEM_USER_ID


def test_save_session_success(mock_psycopg_connect):
    m_connect, m_cursor = mock_psycopg_connect
    m_cursor.fetchone.return_value = ("call-uuid-1234",)

    repo = LearningRepository("fake_connection_string")
    result = repo.save_session(
        ticker="MSFT",
        session_id="session-001",
        topic="Revenue model",
        stage=2,
        messages=[{"role": "user", "content": "Explain it"}],
        completed=False,
    )

    assert result is True
    assert m_cursor.execute.call_count == 2

    first_sql = m_cursor.execute.call_args_list[0][0][0]
    assert "SELECT id FROM calls" in first_sql

    second_sql = m_cursor.execute.call_args_list[1][0][1]
    notes = json.loads(second_sql[3])
    assert notes["topic"] == "Revenue model"
    assert notes["stage"] == 2

    m_connect.commit.assert_called_once()


def test_save_session_no_call_returns_false(mock_psycopg_connect):
    m_connect, m_cursor = mock_psycopg_connect
    m_cursor.fetchone.return_value = None

    repo = LearningRepository("fake_connection_string")
    result = repo.save_session(
        ticker="UNKNOWN",
        session_id="session-002",
        topic="Cash flow",
        stage=1,
        messages=[],
        completed=False,
    )

    assert result is False
    assert m_cursor.execute.call_count == 1


def test_save_session_completed_inserts_concept_exercise(mock_psycopg_connect):
    m_connect, m_cursor = mock_psycopg_connect
    m_cursor.fetchone.return_value = ("call-uuid-1234",)

    messages = [
        {"role": "user", "content": "Explain it"},
        {"role": "assistant", "content": "Great explanation!", "feynman_stage": 5},
    ]

    repo = LearningRepository("fake_connection_string")
    result = repo.save_session(
        ticker="MSFT",
        session_id="session-003",
        topic="Operating leverage",
        stage=5,
        messages=messages,
        completed=True,
    )

    assert result is True
    assert m_cursor.execute.call_count == 3

    third_sql = m_cursor.execute.call_args_list[2][0][0]
    assert "concept_exercises" in third_sql

    m_connect.commit.assert_called_once()


def test_get_sessions_for_ticker(mock_psycopg_connect):
    m_connect, m_cursor = mock_psycopg_connect

    notes = json.dumps({"topic": "Revenue model", "stage": 3, "messages": [], "type": "feynman"})
    m_cursor.fetchall.return_value = [
        ("session-001", notes, None, "2024-01-30T10:00:00", None),
        ("session-002", notes, "2024-01-31T11:00:00", "2024-01-30T09:00:00", "Great job!"),
    ]

    repo = LearningRepository("fake_connection_string")
    sessions = repo.get_sessions_for_ticker("MSFT")

    assert len(sessions) == 2
    assert sessions[0]["id"] == "session-001"
    assert sessions[0]["topic"] == "Revenue model"
    assert sessions[0]["completed"] is False
    assert sessions[1]["completed"] is True
    assert sessions[1]["teaching_note"] == "Great job!"

    executed_sql = m_cursor.execute.call_args[0][0]
    assert "user_id" not in executed_sql


def test_get_sessions_for_ticker_user_filter(mock_psycopg_connect):
    m_connect, m_cursor = mock_psycopg_connect

    notes = json.dumps({"topic": "Margins", "stage": 1, "messages": [], "type": "feynman"})
    m_cursor.fetchall.return_value = [
        ("session-005", notes, None, "2024-02-01T08:00:00", None),
    ]

    repo = LearningRepository("fake_connection_string")
    repo.get_sessions_for_ticker("MSFT", user_id="user-xyz")

    executed_sql = m_cursor.execute.call_args[0][0]
    executed_params = m_cursor.execute.call_args[0][1]

    assert "ls.user_id = %s::uuid" in executed_sql
    assert "user-xyz" in executed_params


def test_get_session_by_id_success(mock_psycopg_connect):
    m_connect, m_cursor = mock_psycopg_connect

    notes = {"topic": "Cash flow", "stage": 1, "messages": []}
    m_cursor.fetchone.return_value = (json.dumps(notes), "user-abc")

    repo = LearningRepository("fake_connection_string")
    result = repo.get_session_by_id("session-001", "user-abc")

    assert result == notes

    executed_sql = m_cursor.execute.call_args[0][0]
    assert "SELECT notes, user_id FROM learning_sessions" in executed_sql


def test_get_session_by_id_ownership_mismatch_raises(mock_psycopg_connect):
    m_connect, m_cursor = mock_psycopg_connect

    notes = {"topic": "Cash flow", "stage": 1, "messages": []}
    m_cursor.fetchone.return_value = (json.dumps(notes), "actual-owner")

    repo = LearningRepository("fake_connection_string")

    with pytest.raises(ValueError, match="belongs to a different user"):
        repo.get_session_by_id("session-001", "different-user")
