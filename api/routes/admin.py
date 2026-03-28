"""Admin routes — protected ingestion dispatch."""

import asyncio
import logging
import os
import re
from datetime import UTC, datetime

import httpx
import modal
import psycopg
from fastapi import APIRouter, Depends
from pydantic import BaseModel, field_validator

from db.analytics import track
from db.repositories import SchemaRepository
from dependencies import RequireAdminDep

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/admin", tags=["admin"])

_TICKER_RE = re.compile(r"^[A-Z]{2,5}$")


class IngestRequest(BaseModel):
    ticker: str

    @field_validator("ticker")
    @classmethod
    def validate_ticker(cls, v: str) -> str:
        """Uppercase and validate ticker format (2–5 alpha chars)."""
        upper = v.upper()
        if not _TICKER_RE.match(upper):
            raise ValueError("ticker must be 2–5 alphabetic characters")
        return upper


_HEALTH_ENV_VARS = ["VOYAGE_API_KEY", "PERPLEXITY_API_KEY", "MODAL_TOKEN_ID", "SUPABASE_JWT_SECRET"]
_VOYAGE_URL = "https://api.voyageai.com"
_PERPLEXITY_URL = "https://api.perplexity.ai"


@router.get("/health")
async def system_health(_: RequireAdminDep) -> dict:
    """Return system health: DB connection, env var presence, and external API reachability."""
    db_url = os.environ.get("DATABASE_URL", "")
    repo = SchemaRepository(db_url)
    version: int = await asyncio.to_thread(repo.get_current_version)

    env_vars = {key: bool(os.environ.get(key)) for key in _HEALTH_ENV_VARS}

    voyage_reachable = False
    perplexity_reachable = False
    async with httpx.AsyncClient(timeout=5.0) as client:
        try:
            await client.head(_VOYAGE_URL)
            voyage_reachable = True
        except Exception:
            pass
        try:
            await client.head(_PERPLEXITY_URL)
            perplexity_reachable = True
        except Exception:
            pass

    return {
        "db": {
            "connected": version > 0,
            "schema_version": version,
        },
        "env_vars": env_vars,
        "external_apis": {
            "voyage": {"reachable": voyage_reachable},
            "perplexity": {"reachable": perplexity_reachable},
        },
    }


def _db_url() -> str:
    """Return the database connection URL from environment."""
    return os.environ.get("DATABASE_URL", "dbname=earnings_teacher")


@router.get("/analytics/sessions")
def analytics_sessions(_: RequireAdminDep) -> list[dict]:
    """Return daily session_start counts for the last 30 days."""
    with psycopg.connect(_db_url()) as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT DATE(created_at) AS date, COUNT(*) AS count
                FROM analytics_events
                WHERE event_name = 'session_start'
                  AND created_at >= NOW() - INTERVAL '30 days'
                GROUP BY date
                ORDER BY date
                """
            )
            return [{"date": str(row[0]), "count": row[1]} for row in cur.fetchall()]


@router.get("/analytics/chat")
def analytics_chat(_: RequireAdminDep) -> dict:
    """Return daily chat_turn counts and average turns per session for the last 30 days."""
    with psycopg.connect(_db_url()) as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT DATE(created_at) AS date, COUNT(*) AS turns
                FROM analytics_events
                WHERE event_name = 'chat_turn'
                  AND created_at >= NOW() - INTERVAL '30 days'
                GROUP BY date
                ORDER BY date
                """
            )
            daily = [{"date": str(row[0]), "turns": row[1]} for row in cur.fetchall()]

            cur.execute(
                """
                SELECT AVG(turns_per_session)
                FROM (
                    SELECT session_id, COUNT(*) AS turns_per_session
                    FROM analytics_events
                    WHERE event_name = 'chat_turn'
                      AND created_at >= NOW() - INTERVAL '30 days'
                    GROUP BY session_id
                ) sub
                """
            )
            row = cur.fetchone()
            avg = round(float(row[0]), 1) if row and row[0] is not None else 0.0

    return {"daily": daily, "avg_turns_per_session": avg}


@router.post("/ingest", status_code=202)
async def trigger_ingestion(body: IngestRequest, _: RequireAdminDep) -> dict:
    """Dispatch ticker to the Modal ingestion pipeline and return 202 immediately."""
    fn = modal.Function.lookup("earnings-ingestion", "ingest_ticker")
    fn.spawn(body.ticker)
    logger.info("Ingestion dispatched: ticker=%s at=%s", body.ticker, datetime.now(UTC).isoformat())
    return {
        "status": "accepted",
        "ticker": body.ticker,
        "message": "Ingestion dispatched",
    }
