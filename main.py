import sys
import argparse
import os

from services.orchestrator import analyze
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
    
    args = parser.parse_args()

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