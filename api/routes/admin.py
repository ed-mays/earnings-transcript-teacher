"""Admin routes — protected ingestion dispatch."""

import logging
import re
from datetime import UTC, datetime

import modal
from fastapi import APIRouter, Depends
from pydantic import BaseModel, field_validator

from dependencies import AdminDep

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


@router.post("/ingest", status_code=202)
async def trigger_ingestion(body: IngestRequest, _: AdminDep) -> dict:
    """Dispatch ticker to the Modal ingestion pipeline and return 202 immediately."""
    fn = modal.Function.lookup("earnings-ingestion", "ingest_ticker")
    fn.spawn(body.ticker)
    logger.info("Ingestion dispatched: ticker=%s at=%s", body.ticker, datetime.now(UTC).isoformat())
    return {
        "status": "accepted",
        "ticker": body.ticker,
        "message": "Ingestion dispatched",
    }
