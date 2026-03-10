import psycopg

conn_str = "dbname=earnings_teacher"
try:
    with psycopg.connect(conn_str) as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT et.term, et.definition, COALESCE(et.explanation, '')
                FROM extracted_terms et
                JOIN calls c ON et.call_id = c.id
                WHERE c.ticker = 'TSLA'
                LIMIT 1
            """)
            result = cur.fetchall()
            with open("test_query_out.txt", "w") as f:
                f.write(f"Query successful! {result}\n")
except Exception as e:
    with open("test_query_out.txt", "w") as f:
        f.write(f"Error test query: {e}\n")
