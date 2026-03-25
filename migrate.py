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

            # v5 → v6: add call_summary to call_synthesis
            cur.execute(
                "ALTER TABLE call_synthesis ADD COLUMN IF NOT EXISTS call_summary TEXT;"
            )
            cur.execute(
                "INSERT INTO schema_version (version) VALUES (6) ON CONFLICT DO NOTHING;"
            )

            # v6 → v7: convert strategic_shifts from TEXT[] to JSONB[]
            # Uses a new-column+UPDATE+rename approach because PostgreSQL does not
            # allow subqueries in ALTER COLUMN TYPE ... USING.
            # The block is written to be safe to re-run after a partial failure:
            #   - inspect actual column state before each step
            #   - only execute steps that have not already completed
            cur.execute("""
                SELECT column_name, udt_name
                FROM information_schema.columns
                WHERE table_name = 'call_synthesis'
                  AND column_name IN ('strategic_shifts', 'strategic_shifts_new')
            """)
            existing = {row[0]: row[1] for row in cur.fetchall()}

            shifts_type = existing.get("strategic_shifts")        # '_text', '_jsonb', or None
            shifts_new_exists = "strategic_shifts_new" in existing

            if shifts_type == "_jsonb":
                # Already migrated — nothing to do
                pass
            else:
                if not shifts_new_exists:
                    cur.execute(
                        "ALTER TABLE call_synthesis ADD COLUMN strategic_shifts_new JSONB[] DEFAULT '{}';"
                    )
                if shifts_type == "_text":
                    # Populate from the TEXT[] column
                    cur.execute(
                        """
                        UPDATE call_synthesis
                        SET strategic_shifts_new = (
                            SELECT array_agg(
                                jsonb_build_object(
                                    'prior_position', '',
                                    'current_position', s,
                                    'investor_significance', ''
                                )
                            )
                            FROM unnest(strategic_shifts) AS s
                        )
                        WHERE strategic_shifts IS NOT NULL
                          AND array_length(strategic_shifts, 1) > 0;
                        """
                    )
                    cur.execute("ALTER TABLE call_synthesis DROP COLUMN strategic_shifts;")
                cur.execute(
                    "ALTER TABLE call_synthesis RENAME COLUMN strategic_shifts_new TO strategic_shifts;"
                )
            cur.execute(
                "INSERT INTO schema_version (version) VALUES (7) ON CONFLICT DO NOTHING;"
            )
            # v7 → v8: add transcript_progress table for per-step completion tracking
            cur.execute("""
                CREATE TABLE IF NOT EXISTS transcript_progress (
                    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                    call_id     UUID NOT NULL REFERENCES calls(id) ON DELETE CASCADE,
                    step_number INTEGER NOT NULL CHECK (step_number BETWEEN 1 AND 6),
                    viewed_at   TIMESTAMPTZ NOT NULL DEFAULT now(),
                    UNIQUE (call_id, step_number)
                );
            """)
            cur.execute(
                "CREATE INDEX IF NOT EXISTS idx_transcript_progress_call ON transcript_progress(call_id);"
            )
            cur.execute(
                "INSERT INTO schema_version (version) VALUES (8) ON CONFLICT DO NOTHING;"
            )
            # v8 → v9: add topic_name column to call_topics for Haiku NLP synthesis
            cur.execute(
                "ALTER TABLE call_topics ADD COLUMN IF NOT EXISTS topic_name TEXT DEFAULT '';"
            )
            cur.execute(
                "INSERT INTO schema_version (version) VALUES (9) ON CONFLICT DO NOTHING;"
            )

        conn.commit()
    print("Migration successful — schema is at version 9.")
except Exception as e:
    print(f"Error during migration: {e}")
