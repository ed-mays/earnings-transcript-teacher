"""Backfill call briefs for existing calls that have synthesis data but no brief yet.

Usage:
    python scripts/backfill_briefs.py                  # process all missing briefs
    python scripts/backfill_briefs.py --dry-run        # show which calls would be processed
    python scripts/backfill_briefs.py --ticker MSFT    # process a single ticker
"""

import argparse
import json
import logging
import os
import sys

# Allow running from project root
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv

load_dotenv("api/.env")

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
logger = logging.getLogger(__name__)


def find_tickers_missing_briefs(conn_str: str, ticker_filter: str | None = None) -> list[tuple[str, str]]:
    """Return [(ticker, call_id)] for calls with synthesis data but no brief."""
    import psycopg

    query = """
        SELECT c.ticker, c.id::text
        FROM calls c
        JOIN call_synthesis cs ON cs.call_id = c.id
        LEFT JOIN call_brief cb ON cb.call_id = c.id
        WHERE cb.call_id IS NULL
    """
    params: list = []
    if ticker_filter:
        query += " AND c.ticker = %s"
        params.append(ticker_filter.upper())
    query += " ORDER BY c.created_at DESC"

    with psycopg.connect(conn_str) as conn:
        with conn.cursor() as cur:
            cur.execute(query, params)
            return cur.fetchall()


def fetch_synthesis_for_call(conn_str: str, call_id: str) -> dict | None:
    """Return synthesis data for a call_id."""
    import psycopg

    with psycopg.connect(conn_str) as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT overall_sentiment, executive_tone, analyst_sentiment,
                       key_themes, strategic_shifts, call_summary
                FROM call_synthesis
                WHERE call_id = %s
                """,
                (call_id,),
            )
            row = cur.fetchone()
            if not row:
                return None
            return {
                "overall_sentiment": row[0] or "",
                "executive_tone": row[1] or "",
                "analyst_sentiment": row[2] or "",
                "key_themes": row[3] or [],
                "strategic_shifts": row[4] or [],
                "call_summary": row[5] or "",
            }


def generate_brief(synthesis: dict) -> dict:
    """Call the brief synthesis LLM step and return the result dict."""
    from services.llm import AgenticExtractor

    extractor = AgenticExtractor()
    payload = {
        "call_summary": synthesis["call_summary"],
        "overall_sentiment": synthesis["overall_sentiment"],
        "executive_tone": synthesis["executive_tone"],
        "analyst_sentiment": synthesis["analyst_sentiment"],
        "key_themes": synthesis["key_themes"],
        "strategic_shifts": synthesis["strategic_shifts"],
        "recent_news": [],
        "competitors": [],
    }
    result = extractor.extract_brief_synthesis(json.dumps(payload, indent=2))
    result.pop("_usage_stats", None)
    return result


def save_brief(conn_str: str, call_id: str, brief_data: dict) -> None:
    """Upsert the call_brief row for a call_id."""
    import psycopg
    from psycopg.types.json import Jsonb

    with psycopg.connect(conn_str) as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO call_brief (call_id, context_line, bigger_picture, interpretation_questions)
                VALUES (%s, %s, %s, %s)
                ON CONFLICT (call_id) DO UPDATE SET
                    context_line = EXCLUDED.context_line,
                    bigger_picture = EXCLUDED.bigger_picture,
                    interpretation_questions = EXCLUDED.interpretation_questions
                """,
                (
                    call_id,
                    brief_data.get("context_line", ""),
                    Jsonb(brief_data.get("bigger_picture", [])),
                    Jsonb(brief_data.get("interpretation_questions", [])),
                ),
            )
        conn.commit()


def main() -> None:
    parser = argparse.ArgumentParser(description="Backfill call briefs for existing calls.")
    parser.add_argument("--dry-run", action="store_true", help="Show affected calls without making changes.")
    parser.add_argument("--ticker", metavar="TICKER", help="Process a single ticker only.")
    args = parser.parse_args()

    conn_str = os.environ.get("DATABASE_URL")
    if not conn_str:
        logger.error("DATABASE_URL environment variable is not set.")
        sys.exit(1)

    missing = find_tickers_missing_briefs(conn_str, ticker_filter=args.ticker)

    if not missing:
        logger.info("No calls missing a brief. Nothing to do.")
        return

    logger.info("Found %d call(s) missing a brief: %s", len(missing), [t for t, _ in missing])

    if args.dry_run:
        logger.info("Dry run — no changes made.")
        return

    success = 0
    failed = 0
    for ticker, call_id in missing:
        logger.info("Processing %s (call_id=%s)...", ticker, call_id)
        try:
            synthesis = fetch_synthesis_for_call(conn_str, call_id)
            if not synthesis:
                logger.warning("No synthesis found for %s — skipping.", ticker)
                failed += 1
                continue
            brief_data = generate_brief(synthesis)
            save_brief(conn_str, call_id, brief_data)
            logger.info("  ✓ Brief saved for %s", ticker)
            success += 1
        except Exception as e:
            logger.error("  ✗ Failed for %s: %s", ticker, e)
            failed += 1

    logger.info("Done. %d succeeded, %d failed.", success, failed)


if __name__ == "__main__":
    main()
