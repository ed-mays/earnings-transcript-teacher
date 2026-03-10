import os
import sys
import traceback

def safe_print(msg):
    with open('log.txt', 'a') as f:
        f.write(msg + '\n')

def main():
    try:
        from services.orchestrator import analyze
        from db.persistence import save_analysis
        ticker = "MMM"
        safe_print(f"Analyzing {ticker}...")
        analysis = analyze(ticker)
        safe_print("Analysis complete. Saving...")
        conn_str = os.environ.get("DATABASE_URL", "dbname=earnings_teacher")
        safe_print(f"Conn str: {conn_str}")
        save_analysis(conn_str, analysis)
        safe_print("Save complete.")
    except Exception as e:
        safe_print(f"FAILED: {e}")
        safe_print(traceback.format_exc())

if __name__ == "__main__":
    main()
