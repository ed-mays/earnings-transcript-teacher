"""Feynman chat routes — SSE streaming endpoint."""

import json
import logging
import os
import time
import uuid
from pathlib import Path

from fastapi import APIRouter, HTTPException, Request, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from db.analytics import track
from db.repositories import CallRepository, LearningRepository
from dependencies import CurrentUserDep
from limiter import limiter
from settings import CHAT_MESSAGE_MAX_LENGTH, CHAT_RATE_LIMIT, SESSION_HISTORY_MAX_TURNS

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/calls", tags=["chat"])

_PROMPTS_DIR = Path(__file__).parent.parent.parent / "prompts" / "feynman"

_STAGE_PROMPTS: dict[int, str] = {
    1: "01_initial_explanation.md",
    2: "02_gap_analysis.md",
    3: "03_guided_refinement.md",
    4: "04_understanding_test.md",
    5: "05_teaching_note.md",
}


def _db_url() -> str:
    """Return the database connection URL from environment."""
    return os.environ["DATABASE_URL"]


def _load_prompt(stage: int) -> str:
    """Read and return the Feynman system prompt file for the given stage."""
    filename = _STAGE_PROMPTS.get(stage, "01_initial_explanation.md")
    return (_PROMPTS_DIR / filename).read_text(encoding="utf-8")


def _ticker_exists(ticker: str) -> bool:
    """Return True if a call record exists for the given ticker."""
    return CallRepository(_db_url()).get_company_info(ticker) is not None


def _load_session(session_id: str, user_id: str) -> dict | None:
    """Load session notes by ID; return None if not found.

    Raises HTTPException 403 if the session belongs to a different user.
    """
    try:
        return LearningRepository(_db_url()).get_session_by_id(session_id, user_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Session belongs to a different user",
        )


def _upsert_session(
    ticker: str,
    session_id: str,
    user_id: str,
    topic: str,
    stage: int,
    messages: list[dict],
    completed: bool,
) -> None:
    """Insert or update a learning session row with the given message history."""
    LearningRepository(_db_url()).save_session(
        ticker=ticker,
        session_id=session_id,
        topic=topic,
        stage=stage,
        messages=messages,
        completed=completed,
        user_id=user_id,
    )


def _sse_stream(
    messages: list[dict],
    system_prompt: str,
    session_id: str,
    ticker: str,
    user_id: str,
    topic: str,
    stage: int,
):
    """Generator that calls stream_chat and emits SSE-formatted lines."""
    from services.llm import stream_chat

    accumulated: list[str] = []
    usage: dict | None = None
    start = time.monotonic()
    try:
        for chunk in stream_chat(messages, system_prompt):
            if isinstance(chunk, str):
                accumulated.append(chunk)
                yield f"data: {json.dumps({'type': 'token', 'content': chunk})}\n\n"
            elif isinstance(chunk, dict) and "usage" in chunk:
                usage = chunk

        assistant_turn = {"role": "assistant", "content": "".join(accumulated)}
        updated_messages = messages + [assistant_turn]
        _upsert_session(ticker, session_id, user_id, topic, stage, updated_messages, completed=False)
        track(
            "chat_turn",
            session_id=session_id,
            properties={
                "turn_number": len(messages),
                "message_length": len(messages[-1]["content"]),
                "latency_ms": int((time.monotonic() - start) * 1000),
            },
        )
        if usage:
            track(
                "api_call_completed",
                session_id=session_id,
                properties={
                    "service": "perplexity",
                    "operation": "feynman",
                    "input_tokens": usage["usage"].get("prompt_tokens", 0),
                    "output_tokens": usage["usage"].get("completion_tokens", 0),
                },
            )
        # Fire stage_completed after the first response in a new session (len == 1 means
        # only the opening user message was in the list — no prior assistant turns).
        if len(messages) == 1:
            track(
                "feynman_stage_completed",
                session_id=session_id,
                properties={"stage": stage, "ticker": ticker},
            )
        yield f"data: {json.dumps({'type': 'done', 'session_id': session_id})}\n\n"

    except Exception:
        logger.exception("SSE stream error for session %s", session_id)
        yield f"data: {json.dumps({'type': 'error', 'message': 'Stream error'})}\n\n"


# --- Request model ---

class ChatRequest(BaseModel):
    message: str = Field(max_length=CHAT_MESSAGE_MAX_LENGTH)
    session_id: str | None = None
    stage: int = 1  # only applied when creating a new session; 1–5


# --- Endpoint ---

@router.post("/{ticker}/chat")
@limiter.limit(CHAT_RATE_LIMIT)
def chat(
    request: Request,
    ticker: str,
    body: ChatRequest,
    user_id: CurrentUserDep,
) -> StreamingResponse:
    """Stream a Feynman chat response as Server-Sent Events.

    Creates a new session when session_id is null; resumes an existing one otherwise.
    Emits: data: {type: token, content: ...}  per chunk,
           data: {type: done, session_id: ...} on completion,
           data: {type: error, message: ...}  on failure.
    """
    if not _ticker_exists(ticker):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No call found for ticker {ticker!r}",
        )

    api_key = os.environ.get("PERPLEXITY_API_KEY")
    if not api_key:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Chat is unavailable — PERPLEXITY_API_KEY is not configured",
        )

    # Resolve session: load existing or start fresh
    if body.session_id:
        notes = _load_session(body.session_id, user_id)
        if notes is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Session {body.session_id!r} not found",
            )
        session_id = body.session_id
        topic: str = notes.get("topic", body.message)
        stage: int = notes.get("stage", 1)
        history: list[dict] = notes.get("messages", [])
        user_turns = sum(1 for m in history if m["role"] == "user")
        if user_turns >= SESSION_HISTORY_MAX_TURNS:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Session has reached the {SESSION_HISTORY_MAX_TURNS}-turn limit. Start a new session.",
            )
    else:
        session_id = str(uuid.uuid4())
        topic = body.message
        stage = max(1, min(body.stage, 5))
        history = []
        track("session_start", session_id=session_id, properties={"ticker": ticker, "stage": stage})

    system_prompt = _load_prompt(stage)
    messages = history + [{"role": "user", "content": body.message}]

    return StreamingResponse(
        _sse_stream(messages, system_prompt, session_id, ticker, user_id, topic, stage),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
