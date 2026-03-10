import psycopg
import sys

def main():
    try:
        conn = psycopg.connect("dbname=earnings_teacher")
        cur = conn.cursor()
        cur.execute("ALTER TABLE extracted_terms ADD COLUMN IF NOT EXISTS explanation TEXT DEFAULT '';")
        conn.commit()
        with open("migration_result.txt", "w") as f:
            f.write("Successfully added column.\n")
    except Exception as e:
        with open("migration_result.txt", "w") as f:
            f.write(f"Error: {e}\n")

if __name__ == "__main__":
    main()
