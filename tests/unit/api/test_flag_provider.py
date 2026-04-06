"""Unit tests for the FeatureFlagProvider (SupabaseFlagProvider)."""

import os
import sys
import threading
import time
from unittest.mock import MagicMock, patch

import pytest

API_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../api"))
if API_DIR not in sys.path:
    sys.path.insert(0, API_DIR)


def _make_mock_conn(rows: list[tuple]) -> MagicMock:
    """Return a mock psycopg connection returning the given rows from fetchall()."""
    mock_conn = MagicMock()
    mock_conn.execute.return_value.fetchall.return_value = rows
    return mock_conn


def _make_pool(rows: list[tuple]) -> MagicMock:
    """Return a mock pool whose connection() context manager yields a conn with given rows."""
    mock_conn = _make_mock_conn(rows)
    mock_pool = MagicMock()
    mock_pool.connection.return_value.__enter__ = MagicMock(return_value=mock_conn)
    mock_pool.connection.return_value.__exit__ = MagicMock(return_value=False)
    return mock_pool


@pytest.fixture(autouse=True)
def fresh_provider():
    """Import a fresh SupabaseFlagProvider for each test."""
    # Only remove the flags package modules, not unrelated modules that contain 'flags' as a substring.
    _flags_mods = {"flags", "flags.provider", "flags.supabase_provider"}
    for mod in _flags_mods:
        sys.modules.pop(mod, None)
    yield
    for mod in _flags_mods:
        sys.modules.pop(mod, None)


def _make_provider(rows: list[tuple], use_pool: bool = True):
    """Create a SupabaseFlagProvider with a mocked pool or connection."""
    from flags.supabase_provider import SupabaseFlagProvider

    provider = SupabaseFlagProvider()
    if use_pool:
        import dependencies
        dependencies._pool = _make_pool(rows)
    else:
        import dependencies
        dependencies._pool = None
    return provider


# --- Cache loading ---

def test_get_all_loads_from_db():
    """get_all() returns all flags as a {key: bool} dict."""
    rows = [("chat_enabled", True), ("ingestion_enabled", True), ("beta_feature", False)]
    with patch.dict(os.environ, {"DATABASE_URL": "postgresql://test"}):
        provider = _make_provider(rows)
        result = provider.get_all()
    assert result == {"chat_enabled": True, "ingestion_enabled": True, "beta_feature": False}


def test_get_all_returns_copy():
    """Mutating the result of get_all() doesn't affect the cache."""
    rows = [("chat_enabled", True)]
    with patch.dict(os.environ, {"DATABASE_URL": "postgresql://test"}):
        provider = _make_provider(rows)
        result = provider.get_all()
        result["injected"] = True
        assert "injected" not in provider.get_all()


# --- is_enabled ---

def test_is_enabled_returns_true_for_enabled_flag():
    rows = [("chat_enabled", True)]
    with patch.dict(os.environ, {"DATABASE_URL": "postgresql://test"}):
        provider = _make_provider(rows)
        assert provider.is_enabled("chat_enabled") is True


def test_is_enabled_returns_false_for_disabled_flag():
    rows = [("beta_feature", False)]
    with patch.dict(os.environ, {"DATABASE_URL": "postgresql://test"}):
        provider = _make_provider(rows)
        assert provider.is_enabled("beta_feature") is False


def test_is_enabled_returns_default_false_for_missing_key():
    rows = [("chat_enabled", True)]
    with patch.dict(os.environ, {"DATABASE_URL": "postgresql://test"}):
        provider = _make_provider(rows)
        assert provider.is_enabled("nonexistent") is False


def test_is_enabled_returns_explicit_default_for_missing_key():
    """When default=True and key missing, returns True (kill switch pattern)."""
    rows = []
    with patch.dict(os.environ, {"DATABASE_URL": "postgresql://test"}):
        provider = _make_provider(rows)
        assert provider.is_enabled("chat_enabled", default=True) is True


def test_is_enabled_flag_value_overrides_default():
    """Explicit flag value in DB overrides the default argument."""
    rows = [("chat_enabled", False)]
    with patch.dict(os.environ, {"DATABASE_URL": "postgresql://test"}):
        provider = _make_provider(rows)
        assert provider.is_enabled("chat_enabled", default=True) is False


# --- TTL caching ---

def test_cache_not_refreshed_within_ttl():
    """Second call within TTL reuses the cache without hitting the DB."""
    rows = [("chat_enabled", True)]
    with patch.dict(os.environ, {"DATABASE_URL": "postgresql://test"}):
        provider = _make_provider(rows)
        provider.get_all()  # First call — loads cache
        import dependencies
        pool = dependencies._pool
        call_count_after_first = pool.connection.call_count
        provider.get_all()  # Second call — should use cache
        assert pool.connection.call_count == call_count_after_first


def test_cache_refreshed_after_ttl():
    """Cache is reloaded after TTL expires."""
    rows = [("chat_enabled", True)]
    with patch.dict(os.environ, {"DATABASE_URL": "postgresql://test"}):
        provider = _make_provider(rows)
        provider.get_all()  # First load

        # Expire the cache by backdating the loaded_at timestamp
        provider._cache_loaded_at = time.monotonic() - provider._TTL - 1

        import dependencies
        pool = dependencies._pool
        call_count_before = pool.connection.call_count
        provider.get_all()
        assert pool.connection.call_count > call_count_before


# --- Stale-on-error ---

def test_stale_cache_returned_on_db_error():
    """If DB fails and cache exists, returns stale data without raising."""
    rows = [("chat_enabled", True)]
    with patch.dict(os.environ, {"DATABASE_URL": "postgresql://test"}):
        provider = _make_provider(rows)
        provider.get_all()  # Populate cache

        # Expire cache and break the DB
        provider._cache_loaded_at = time.monotonic() - provider._TTL - 1
        import dependencies
        dependencies._pool.connection.side_effect = Exception("DB is down")

        # Should return stale data instead of raising
        result = provider.get_all()
        assert result == {"chat_enabled": True}


def test_no_stale_cache_on_error_raises():
    """If DB fails and no cache exists, the error propagates."""
    with patch.dict(os.environ, {"DATABASE_URL": "postgresql://test"}):
        import dependencies
        dependencies._pool = MagicMock()
        dependencies._pool.connection.side_effect = Exception("DB is down")

        from flags.supabase_provider import SupabaseFlagProvider
        provider = SupabaseFlagProvider()

        with pytest.raises(Exception, match="DB is down"):
            provider.get_all()


# --- invalidate_cache ---

def test_invalidate_cache_forces_reload():
    """invalidate_cache() causes the next call to reload from DB."""
    rows = [("chat_enabled", True)]
    with patch.dict(os.environ, {"DATABASE_URL": "postgresql://test"}):
        provider = _make_provider(rows)
        provider.get_all()  # Populate cache

        import dependencies
        pool = dependencies._pool
        call_count_after_first = pool.connection.call_count

        provider.invalidate_cache()
        provider.get_all()  # Should reload
        assert pool.connection.call_count > call_count_after_first


def test_invalidate_cache_clears_state():
    """invalidate_cache() sets cache to None."""
    rows = [("chat_enabled", True)]
    with patch.dict(os.environ, {"DATABASE_URL": "postgresql://test"}):
        provider = _make_provider(rows)
        provider.get_all()
        assert provider._cache is not None

        provider.invalidate_cache()
        assert provider._cache is None
        assert provider._cache_loaded_at is None


# --- Pool fallback ---

def test_falls_back_to_direct_connection_when_no_pool():
    """Uses psycopg.connect() directly when no pool is configured."""
    rows = [("chat_enabled", True)]
    mock_conn = _make_mock_conn(rows)

    with patch.dict(os.environ, {"DATABASE_URL": "postgresql://test"}):
        import dependencies
        dependencies._pool = None

        with patch("psycopg.connect", return_value=mock_conn) as mock_connect:
            from flags.supabase_provider import SupabaseFlagProvider
            provider = SupabaseFlagProvider()
            result = provider.get_all()

        mock_connect.assert_called_once_with("postgresql://test")
    assert result == {"chat_enabled": True}


# --- Thread safety ---

def test_concurrent_calls_dont_corrupt_cache():
    """Concurrent is_enabled() calls all return correct values."""
    rows = [("chat_enabled", True), ("beta_feature", False)]
    errors = []

    with patch.dict(os.environ, {"DATABASE_URL": "postgresql://test"}):
        provider = _make_provider(rows)

        def check_flags():
            try:
                assert provider.is_enabled("chat_enabled") is True
                assert provider.is_enabled("beta_feature") is False
                assert provider.is_enabled("missing", default=True) is True
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=check_flags) for _ in range(20)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

    assert errors == [], f"Thread errors: {errors}"
