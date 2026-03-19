"""Database migration script. Run this before starting the app."""
import os
import psycopg

conn_str = os.environ.get("DATABASE_URL", "dbname=earnings_teacher")

try:
    with psycopg.connect(conn_str) as conn:
        with conn.cursor() as cur:
            # Ensure schema_version table exists
            cur.execute("""
                CREATE TABLE IF NOT EXISTS schema_version (
                    version      INTEGER PRIMARY KEY,
                    installed_at TIMESTAMPTZ DEFAULT now()
                );
            """)

            # v1 → v2: add explanation column to extracted_terms
            cur.execute(
                "ALTER TABLE extracted_terms ADD COLUMN IF NOT EXISTS explanation TEXT DEFAULT '';"
            )

            cur.execute(
                "INSERT INTO schema_version (version) VALUES (2) ON CONFLICT DO NOTHING;"
            )
        conn.commit()
    print("Migration successful — schema is at version 2.")
except Exception as e:
    print(f"Error during migration: {e}")
