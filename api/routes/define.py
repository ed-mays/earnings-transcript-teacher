"""Term definition route — streams a short LLM definition for unknown glossary terms."""

import json
import logging
import os

from fastapi import APIRouter, HTTPException, Request, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from db.repositories import CallRepository
from dependencies import CurrentUserDep
from limiter import limiter
from settings import CHAT_RATE_LIMIT

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/calls", tags=["define"])

_SYSTEM_PROMPT = (
    "You are a concise financial educator. Define the given term in 1-2 sentences "
    "as it would be used on an earnings call. Be practical and direct. No preamble."
)


def _db_url() -> str:
    """Return the database connection URL from environment."""
    return os.environ["DATABASE_URL"]


def _ticker_exists(ticker: str) -> bool:
    """Return True if a call record exists for the given ticker."""
    return CallRepository(_db_url()).get_company_info(ticker) is not None


def _sse_stream(term: str):
    """Generator that streams an Anthropic definition as SSE-formatted lines."""
    from services.llm import stream_investor_signals

    try:
        for chunk in stream_investor_signals(
            messages=[{"role": "user", "content": f"Define: {term}"}],
            system_prompt=_SYSTEM_PROMPT,
        ):
            yield f"data: {json.dumps({'type': 'token', 'content': chunk})}\n\n"
        yield f"data: {json.dumps({'type': 'done'})}\n\n"
    except Exception:
        logger.exception("SSE stream error for define term=%r", term)
        yield f"data: {json.dumps({'type': 'error', 'message': 'Stream error'})}\n\n"


class DefineRequest(BaseModel):
    term: str = Field(min_length=1, max_length=200)


@router.post("/{ticker}/define")
@limiter.limit(CHAT_RATE_LIMIT)
def define_term(
    request: Request,
    ticker: str,
    body: DefineRequest,
    user_id: CurrentUserDep,
) -> StreamingResponse:
    """Stream a short LLM definition of a term in the context of an earnings call.

    Emits: data: {type: token, content: ...}  per chunk,
           data: {type: done}                  on completion,
           data: {type: error, message: ...}   on failure.
    """
    if not _ticker_exists(ticker):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No call found for ticker {ticker!r}",
        )

    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Define is unavailable — ANTHROPIC_API_KEY is not configured",
        )

    return StreamingResponse(
        _sse_stream(body.term),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
