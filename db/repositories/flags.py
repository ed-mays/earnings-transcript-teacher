"""Feature flag repository — data-access layer for the feature_flags table."""

import logging
from typing import Any

import psycopg
import psycopg.types.json

logger = logging.getLogger(__name__)

_COLUMNS = "key, enabled, description, category, metadata, created_at, updated_at"


class FlagRepository:
    """Data-access class for the feature_flags table.

    Accepts an open psycopg connection to integrate with FastAPI's DbDep pattern.
    """

    def __init__(self, conn: psycopg.Connection) -> None:
        """Bind to an open psycopg connection."""
        self._conn = conn

    def list_all(self) -> list[tuple]:
        """Return all flag rows ordered by key."""
        return self._conn.execute(
            f"SELECT {_COLUMNS} FROM public.feature_flags ORDER BY key"
        ).fetchall()

    def create(
        self,
        key: str,
        enabled: bool,
        description: str,
        category: str,
        metadata: dict[str, Any],
    ) -> tuple:
        """Insert a new flag and return the created row. Raises UniqueViolation on duplicate key."""
        return self._conn.execute(
            f"INSERT INTO public.feature_flags (key, enabled, description, category, metadata)"
            f" VALUES (%s, %s, %s, %s, %s)"
            f" RETURNING {_COLUMNS}",
            (key, enabled, description, category, psycopg.types.json.Jsonb(metadata)),
        ).fetchone()

    def update(self, key: str, fields: dict[str, Any]) -> tuple | None:
        """Update the given fields on an existing flag. Returns the updated row, or None if not found."""
        updates = []
        params: list[Any] = []
        for field, value in fields.items():
            updates.append(f"{field} = %s")
            if field == "metadata":
                params.append(psycopg.types.json.Jsonb(value))
            else:
                params.append(value)
        params.append(key)
        return self._conn.execute(
            f"UPDATE public.feature_flags SET {', '.join(updates)}"
            f" WHERE key = %s"
            f" RETURNING {_COLUMNS}",
            params,
        ).fetchone()

    def delete(self, key: str) -> int:
        """Delete a flag by key. Returns the number of rows deleted (0 or 1)."""
        return self._conn.execute(
            "DELETE FROM public.feature_flags WHERE key = %s", (key,)
        ).rowcount
