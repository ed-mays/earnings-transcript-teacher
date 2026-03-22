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

            # v2 → v3: add competitors table
            cur.execute("""
                CREATE TABLE IF NOT EXISTS competitors (
                    id                      UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                    call_id                 UUID NOT NULL REFERENCES calls(id) ON DELETE CASCADE,
                    competitor_name         TEXT NOT NULL,
                    competitor_ticker       TEXT,
                    description             TEXT,
                    mentioned_in_transcript BOOLEAN NOT NULL DEFAULT FALSE,
                    fetched_at              TIMESTAMPTZ DEFAULT now(),
                    UNIQUE (call_id, competitor_name)
                );
            """)
            cur.execute(
                "CREATE INDEX IF NOT EXISTS idx_competitors_call ON competitors(call_id);"
            )
            cur.execute(
                "INSERT INTO schema_version (version) VALUES (3) ON CONFLICT DO NOTHING;"
            )

            # v3 → v4: convert strategic_shifts from TEXT to TEXT[]
            cur.execute(
                """
                ALTER TABLE call_synthesis
                    ALTER COLUMN strategic_shifts TYPE TEXT[]
                    USING ARRAY[strategic_shifts];
                """
            )
            cur.execute(
                "INSERT INTO schema_version (version) VALUES (4) ON CONFLICT DO NOTHING;"
            )
            # v4 → v5: add structured Q&A fields to evasion_analysis
            cur.execute(
                "ALTER TABLE evasion_analysis ADD COLUMN IF NOT EXISTS analyst_name TEXT;"
            )
            cur.execute(
                "ALTER TABLE evasion_analysis ADD COLUMN IF NOT EXISTS question_topic TEXT;"
            )
            cur.execute(
                "ALTER TABLE evasion_analysis ADD COLUMN IF NOT EXISTS question_text TEXT;"
            )
            cur.execute(
                "ALTER TABLE evasion_analysis ADD COLUMN IF NOT EXISTS answer_text TEXT;"
            )
            cur.execute(
                "INSERT INTO schema_version (version) VALUES (5) ON CONFLICT DO NOTHING;"
            )
        conn.commit()
    print("Migration successful — schema is at version 5.")
except Exception as e:
    print(f"Error during migration: {e}")
