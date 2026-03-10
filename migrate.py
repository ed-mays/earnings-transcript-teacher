import psycopg

conn_str = "dbname=earnings_teacher"
try:
    with psycopg.connect(conn_str) as conn:
        with conn.cursor() as cur:
            cur.execute("ALTER TABLE extracted_terms ADD COLUMN IF NOT EXISTS explanation TEXT DEFAULT '';")
        conn.commit()
    print("Migration successful")
except Exception as e:
    print(f"Error during migration: {e}")
