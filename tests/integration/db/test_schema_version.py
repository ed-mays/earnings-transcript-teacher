import pytest
import psycopg
import psycopg.errors
from unittest.mock import MagicMock, patch
from db.repositories import SchemaRepository, REQUIRED_SCHEMA_VERSION

def test_get_current_version_success():
    m_connect = MagicMock()
    m_cursor = MagicMock()
    m_connect.__enter__.return_value = m_connect
    m_cursor.__enter__.return_value = m_cursor
    m_connect.cursor.return_value = m_cursor
    m_cursor.fetchone.return_value = (1,)
    
    with patch('psycopg.connect', return_value=m_connect):
        repo = SchemaRepository("fake_conn")
        version = repo.get_current_version()
        
    assert version == 1

def test_get_current_version_missing_table():
    m_connect = MagicMock()
    m_cursor = MagicMock()
    m_connect.__enter__.return_value = m_connect
    m_cursor.__enter__.return_value = m_cursor
    m_connect.cursor.return_value = m_cursor
    m_cursor.execute.side_effect = psycopg.errors.UndefinedTable("Table not found")
    
    with patch('psycopg.connect', return_value=m_connect):
        repo = SchemaRepository("fake_conn")
        version = repo.get_current_version()
        
    assert version == 0

def test_check_health_ok():
    m_connect = MagicMock()
    m_cursor = MagicMock()
    m_connect.__enter__.return_value = m_connect
    m_cursor.__enter__.return_value = m_cursor
    m_connect.cursor.return_value = m_cursor
    m_cursor.fetchone.return_value = (REQUIRED_SCHEMA_VERSION,)
    
    with patch('psycopg.connect', return_value=m_connect):
        repo = SchemaRepository("fake_conn")
        is_ok, msg = repo.check_health()
    
    assert is_ok is True
    assert "up to date" in msg

def test_check_health_outdated():
    m_connect = MagicMock()
    m_cursor = MagicMock()
    m_connect.__enter__.return_value = m_connect
    m_cursor.__enter__.return_value = m_cursor
    m_connect.cursor.return_value = m_cursor
    # Explicitly set the version to 0 to trigger the "outdated" branch (if version < REQUIRED_SCHEMA_VERSION)
    m_cursor.fetchone.return_value = (0,)
    
    with patch('psycopg.connect', return_value=m_connect):
        repo = SchemaRepository("fake_conn")
        is_ok, msg = repo.check_health()
    
    assert is_ok is False
    # If version is 0 and REQUIRED_SCHEMA_VERSION is 1, it should say "missing" or "outdated" 
    # based on our logic in repositories.py:
    # if current_version < REQUIRED_SCHEMA_VERSION:
    #     if current_version == 0: msg = "... missing ..."
    assert "missing" in msg

def test_check_health_explicit_outdated():
    # Test the case where version is > 0 but < REQUIRED
    m_connect = MagicMock()
    m_cursor = MagicMock()
    m_connect.__enter__.return_value = m_connect
    m_cursor.__enter__.return_value = m_cursor
    m_connect.cursor.return_value = m_cursor
    
    # We need to temporarily mock REQUIRED_SCHEMA_VERSION to 2 to test this
    with patch('db.repositories.REQUIRED_SCHEMA_VERSION', 2):
        m_cursor.fetchone.return_value = (1,)
        with patch('psycopg.connect', return_value=m_connect):
            repo = SchemaRepository("fake_conn")
            is_ok, msg = repo.check_health()
            
    assert is_ok is False
    assert "outdated" in msg
