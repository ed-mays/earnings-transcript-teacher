import pytest
import numpy as np
from unittest.mock import MagicMock
from db.repositories import CallRepository, EmbeddingRepository, AnalysisRepository

@pytest.fixture
def mock_psycopg_connect(mocker):
    # m_connect will be returned by psycopg.connect()
    m_connect = MagicMock()
    # The 'with' context manager behavior
    m_connect.__enter__.return_value = m_connect
    
    # m_cursor will be returned by conn.cursor()
    m_cursor = MagicMock()
    m_cursor.__enter__.return_value = m_cursor
    m_connect.cursor.return_value = m_cursor
    
    # Mock psycopg.connect to return m_connect
    mocker.patch('psycopg.connect', return_value=m_connect)
    return m_connect, m_cursor


def test_get_all_calls(mock_psycopg_connect):
    m_connect, m_cursor = mock_psycopg_connect
    
    # Mock the results of fetchall()
    m_cursor.fetchall.return_value = [("MSFT", "Q1 2024 MSFT"), ("AAPL", "Q2 2024 AAPL")]
    
    repo = CallRepository("fake_connection_string")
    calls = repo.get_all_calls()
    
    # Verify the SQL was executed
    m_cursor.execute.assert_called_once_with(
        """
                        SELECT ticker, fiscal_quarter
                        FROM calls
                        ORDER BY created_at DESC
                        """
    )
    
    # Verify the return value
    assert len(calls) == 2
    assert calls[0] == ("MSFT", "Q1 2024 MSFT")


def test_fetch_existing_embeddings(mock_psycopg_connect, mocker):
    mocker.patch('db.repositories.register_vector')
    
    m_connect, m_cursor = mock_psycopg_connect
    
    # pgvector returns numpy arrays which have a .tolist() method
    emb1 = np.array([0.1, 0.2, 0.3])
    emb2 = np.array([0.4, 0.5, 0.6])
    
    m_cursor.fetchall.return_value = [
        ("Some text span", emb1),
        ("Another span", emb2)
    ]
    
    repo = EmbeddingRepository("fake_connection_string")
    cache = repo.fetch_existing_embeddings("MSFT", "Q1 2024 MSFT")
    
    assert "Some text span" in cache
    assert cache["Another span"] == [0.4, 0.5, 0.6]

def test_get_topics_for_ticker(mock_psycopg_connect):
    m_connect, m_cursor = mock_psycopg_connect
    
    m_cursor.fetchall.return_value = [
        (["cloud", "azure", "growth"],),
        (["ai", "copilot", "chat"],)
    ]
    
    repo = AnalysisRepository("fake_connection_string")
    topics = repo.get_topics_for_ticker("MSFT")
    
    assert len(topics) == 2
    assert topics[0] == ["cloud", "azure", "growth"]

def test_get_synthesis_for_ticker(mock_psycopg_connect):
    m_connect, m_cursor = mock_psycopg_connect
    
    m_cursor.fetchone.return_value = ("Positive", "Confident", "Bullish")
    
    repo = AnalysisRepository("fake_connection_string")
    synthesis = repo.get_synthesis_for_ticker("MSFT")
    
    assert synthesis == ("Positive", "Confident", "Bullish")
    m_cursor.execute.assert_called_once()
    assert "call_synthesis" in m_cursor.execute.call_args[0][0]
