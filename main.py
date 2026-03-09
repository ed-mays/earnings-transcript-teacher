import sys
import argparse
import os

from services.orchestrator import analyze
from cli.display import display
from cli.menu import interactive_menu

if __name__ == "__main__":
    # If run without arguments, use interactive menu
    if len(sys.argv) == 1:
        try:
            interactive_menu()
        except KeyboardInterrupt:
            print("\nGoodbye!")
            sys.exit(0)
    else:
        # Legacy CLI mode
        parser = argparse.ArgumentParser(description="Analyze an earnings transcript.")
        parser.add_argument("ticker", help="Ticker symbol (e.g., AAPL)")
        parser.add_argument("--save", action="store_true", help="Save results to Postgres")
        args = parser.parse_args()
    
        result = analyze(args.ticker)
        display(result)
    
        if args.save:
            from db.persistence import save_analysis
            conn_str = os.environ.get("DATABASE_URL", "dbname=earnings_teacher")
            print(f"\nSaving analysis to database ({conn_str})...")
            try:
                save_analysis(conn_str, result)
                print("Successfully saved to database.")
            except Exception as e:
                print(f"Error saving to database: {e}", file=sys.stderr)
                sys.exit(1)