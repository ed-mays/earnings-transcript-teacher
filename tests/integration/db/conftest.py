import pytest
from unittest.mock import MagicMock


@pytest.fixture
def mock_psycopg_connect(mocker):
    """Patch psycopg.connect and return (mock_connection, mock_cursor)."""
    m_connect = MagicMock()
    m_connect.__enter__.return_value = m_connect

    m_cursor = MagicMock()
    m_cursor.__enter__.return_value = m_cursor
    m_connect.cursor.return_value = m_cursor

    mocker.patch('psycopg.connect', return_value=m_connect)
    return m_connect, m_cursor
