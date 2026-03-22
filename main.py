import sys
import argparse
import os

from services.orchestrator import analyze, OutdatedSchemaError
from cli.display import display
from cli.menu import interactive_menu

if __name__ == "__main__":
    # Setup argparse to handle both GUI and CLI modes
    parser = argparse.ArgumentParser(description="Earnings Transcript Teacher")
    parser.add_argument("--mode", choices=["cli", "gui"], default="cli",
                        help="Choose the interface mode (default: cli)")
    
    # Optional positional argument for the legacy CLI direct-analysis mode
    parser.add_argument("ticker", nargs="?", help="Ticker symbol (e.g., AAPL)")
    parser.add_argument("--save", action="store_true", help="Save results to Postgres")
    parser.add_argument("--reset-db", action="store_true",
                        help="Delete all database data (schema is preserved, transcripts on disk are preserved). For a full schema reset, use ./reset_db.sh")

    args = parser.parse_args()

    if args.reset_db:
        conn_str = os.environ.get("DATABASE_URL", "dbname=earnings_teacher")
        print("This will permanently delete all data from the database.")
        print("Downloaded transcript files will not be affected.")
        confirm = input("Type 'yes' to confirm: ").strip().lower()
        if confirm == "yes":
            from db.repositories import reset_all_data
            reset_all_data(conn_str)
            print("Database reset complete.")
        else:
            print("Aborted.")
        sys.exit(0)

    if args.mode == "gui":
        print("Launching Earnings Transcript Teacher GUI...")
        import subprocess
        # Run streamlit pointing to app.py
        subprocess.run(["streamlit", "run", "app.py"])
        sys.exit(0)

    # If run without arguments (and mode is cli), use interactive menu
    if not args.ticker:
        try:
            interactive_menu()
        except KeyboardInterrupt:
            print("\nGoodbye!")
            sys.exit(0)
    else:
        # Legacy CLI direct-analysis mode
    
        try:
            result = analyze(args.ticker)
            display(result)
        except OutdatedSchemaError as e:
            print(f"\n❌ ERROR: {e}", file=sys.stderr)
            sys.exit(1)
    
        if args.save:
            from db.persistence import save_analysis
            from db.repositories import CompetitorRepository
            from services.competitors import fetch_competitors
            conn_str = os.environ.get("DATABASE_URL", "dbname=earnings_teacher")
            print(f"\nSaving analysis to database ({conn_str})...")
            try:
                save_analysis(conn_str, result)
                print("Successfully saved to database.")
                print("Pre-caching competitors...")
                competitors = fetch_competitors(
                    ticker=result.call.ticker,
                    company_name=result.call.company_name,
                    industry=result.call.industry,
                    transcript_text=result.call.transcript_text,
                )
                if competitors:
                    CompetitorRepository(conn_str).save(result.call.ticker, competitors)
                    print(f"Cached {len(competitors)} competitors.")
            except Exception as e:
                print(f"Error saving to database: {e}", file=sys.stderr)
                sys.exit(1)