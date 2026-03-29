"""Schema management repository: version checks and data reset."""

import logging

import psycopg
import psycopg.errors

logger = logging.getLogger(__name__)

REQUIRED_SCHEMA_VERSION = 9


class OutdatedSchemaError(Exception):
    """Raised when the database schema version is below the required minimum."""
    pass


class RepositoryError(Exception):
    """Raised when a repository operation fails due to a database error."""
    pass


def reset_all_data(conn_str: str) -> None:
    """Delete all application data from the database, preserving the schema."""
    # Deleting from calls cascades to all dependent tables via ON DELETE CASCADE.
    # learning_sessions and concept_exercises are not linked to calls so are truncated separately.
    with psycopg.connect(conn_str) as conn:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM learning_sessions")
            cur.execute("DELETE FROM calls")
        conn.commit()


class SchemaRepository:
    def __init__(self, conn_str: str):
        self.conn_str = conn_str

    def get_current_version(self) -> int:
        """Get the current schema version from the database. Returns 0 if table missing or empty."""
        try:
            with psycopg.connect(self.conn_str) as conn:
                with conn.cursor() as cur:
                    cur.execute("SELECT version FROM schema_version ORDER BY version DESC LIMIT 1")
                    row = cur.fetchone()
                    return row[0] if row else 0
        except psycopg.errors.UndefinedTable:
            return 0
        except Exception as e:
            logger.warning(f"Error checking schema version: {e}")
            return 0

    def check_health(self) -> tuple[bool, str]:
        """Check if the database schema is up to date."""
        current_version = self.get_current_version()
        if current_version < REQUIRED_SCHEMA_VERSION:
            if current_version == 0:
                msg = "Database schema version table is missing. Re-initialize the database."
            else:
                msg = f"Database schema is outdated (current: {current_version}, required: {REQUIRED_SCHEMA_VERSION})."
            return False, f"{msg} Run 'python migrate.py' or './reset_db.sh' to update."
        return True, "Database schema is up to date."
