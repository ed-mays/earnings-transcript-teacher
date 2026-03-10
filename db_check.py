import psycopg
conn = psycopg.connect("dbname=earnings_teacher")
cur = conn.cursor()
cur.execute("SELECT column_name FROM information_schema.columns WHERE table_name = 'extracted_terms'")
print(cur.fetchall())
