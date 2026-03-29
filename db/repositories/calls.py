"""Call metadata repository."""

import logging

import psycopg

logger = logging.getLogger(__name__)


class CallRepository:
    def __init__(self, conn_str: str):
        self.conn_str = conn_str

    def get_company_info(self, ticker: str) -> tuple[str, str]:
        """Return (company_name, industry) for a ticker, or empty strings if not found."""
        try:
            with psycopg.connect(self.conn_str) as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        "SELECT company_name, industry FROM calls WHERE ticker = %s LIMIT 1",
                        (ticker,),
                    )
                    row = cur.fetchone()
                    if row:
                        return (row[0] or "", row[1] or "")
        except Exception as e:
            logger.warning(f"Could not fetch company info for {ticker}: {e}")
        return ("", "")

    def get_call_date(self, ticker: str):
        """Return the call_date for a ticker, or None if not set."""
        try:
            with psycopg.connect(self.conn_str) as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        "SELECT call_date FROM calls WHERE ticker = %s LIMIT 1",
                        (ticker,),
                    )
                    row = cur.fetchone()
                    return row[0] if row else None
        except Exception as e:
            logger.warning(f"Could not fetch call_date for {ticker}: {e}")
            return None

    def get_all_calls(self) -> list[tuple[str, str, str | None, str | None]]:
        """Return (ticker, fiscal_quarter, company_name, call_date) for all stored calls."""
        calls = []
        try:
            with psycopg.connect(self.conn_str) as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        """
                        SELECT ticker, fiscal_quarter, company_name, call_date
                        FROM calls
                        ORDER BY created_at DESC
                        """
                    )
                    calls = cur.fetchall()
        except Exception as e:
            logger.warning(f"Could not fetch calls: {e}")
        return calls
