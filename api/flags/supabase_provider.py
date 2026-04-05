"""SupabaseFlagProvider — TTL-cached feature flag provider backed by a Postgres table."""

import logging
import os
import threading
import time
from typing import TYPE_CHECKING

import psycopg

if TYPE_CHECKING:
    pass

logger = logging.getLogger(__name__)

_TTL = 30.0  # seconds before the in-memory cache is refreshed


class SupabaseFlagProvider:
    """Thread-safe, TTL-cached feature flag provider reading from the feature_flags table.

    On cache miss or TTL expiry, all flags are loaded in a single query.
    If the DB is unavailable and a stale cache exists, the stale data is served.
    """

    _TTL = _TTL

    def __init__(self) -> None:
        """Initialise with an empty cache."""
        self._cache: dict[str, bool] | None = None
        self._cache_loaded_at: float | None = None
        self._lock = threading.Lock()

    def is_enabled(self, key: str, *, default: bool = False) -> bool:
        """Return the flag's enabled state, or default if the key is not found."""
        self._maybe_refresh()
        assert self._cache is not None
        return self._cache.get(key, default)

    def get_all(self) -> dict[str, bool]:
        """Return a copy of all flags as a {key: enabled} dict."""
        self._maybe_refresh()
        assert self._cache is not None
        return dict(self._cache)

    def invalidate_cache(self) -> None:
        """Force the next call to reload from the database."""
        with self._lock:
            self._cache = None
            self._cache_loaded_at = None

    def _maybe_refresh(self) -> None:
        """Reload the cache if it is absent or expired."""
        with self._lock:
            if self._cache is None or self._is_expired():
                self._load_cache()

    def _is_expired(self) -> bool:
        """Return True if the cache TTL has elapsed."""
        return self._cache_loaded_at is None or (
            time.monotonic() - self._cache_loaded_at > self._TTL
        )

    def _load_cache(self) -> None:
        """Query the feature_flags table and populate the in-memory cache.

        Serves stale data on DB error if a previous cache exists.
        Raises the original exception if there is no cache to fall back to.
        """
        try:
            rows = self._fetch_rows()
            self._cache = {key: enabled for key, enabled in rows}
            self._cache_loaded_at = time.monotonic()
        except Exception:
            if self._cache is not None:
                logger.warning(
                    "feature_flags DB refresh failed — serving stale cache", exc_info=True
                )
            else:
                raise

    def _fetch_rows(self) -> list[tuple[str, bool]]:
        """Fetch all rows from the feature_flags table."""
        from dependencies import _pool  # avoid circular import at module load

        if _pool is not None:
            with _pool.connection() as conn:
                return conn.execute(
                    "SELECT key, enabled FROM public.feature_flags"
                ).fetchall()
        else:
            database_url = os.environ["DATABASE_URL"]
            conn = psycopg.connect(database_url)
            try:
                return conn.execute(
                    "SELECT key, enabled FROM public.feature_flags"
                ).fetchall()
            finally:
                conn.close()
