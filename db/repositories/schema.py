"""Schema management repository: connectivity checks and data reset."""

import logging

import psycopg

logger = logging.getLogger(__name__)


class OutdatedSchemaError(Exception):
    """Raised when the database is not accessible."""
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

    def check_health(self) -> tuple[bool, str]:
        """Check that the database is reachable."""
        try:
            with psycopg.connect(self.conn_str) as conn:
                with conn.cursor() as cur:
                    cur.execute("SELECT 1")
            return True, "Database is reachable."
        except Exception as e:
            logger.warning(f"Database health check failed: {e}")
            return False, f"Database is not reachable: {e}"
