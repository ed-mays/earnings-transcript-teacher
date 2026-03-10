import psycopg
with open("db_out.txt", "w") as f:
    try:
        conn = psycopg.connect("dbname=earnings_teacher")
        cur = conn.cursor()
        cur.execute("SELECT column_name FROM information_schema.columns WHERE table_name = 'extracted_terms'")
        cols = cur.fetchall()
        f.write("Columns: " + str(cols) + "\n")
        
        # Try to do the migration again just in case
        cur.execute("ALTER TABLE extracted_terms ADD COLUMN IF NOT EXISTS explanation TEXT DEFAULT '';")
        conn.commit()
        f.write("Migration command executed.\n")
        
    except Exception as e:
        f.write(f"Error: {e}\n")
