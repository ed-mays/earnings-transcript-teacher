"""Feynman chat routes — SSE streaming endpoint."""

import json
import os
import uuid
from pathlib import Path

import psycopg
from fastapi import APIRouter, HTTPException, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from dependencies import CurrentUserDep

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
    with psycopg.connect(_db_url()) as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT 1 FROM calls WHERE ticker = %s LIMIT 1", (ticker,))
            return cur.fetchone() is not None


def _load_session(session_id: str, user_id: str) -> dict | None:
    """Load session notes by ID; return None if not found.

    Raises HTTPException 403 if the session belongs to a different user.
    """
    with psycopg.connect(_db_url()) as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT notes, user_id FROM learning_sessions WHERE id = %s LIMIT 1",
                (session_id,),
            )
            row = cur.fetchone()

    if not row:
        return None

    notes_json, owner_id = row
    if str(owner_id) != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Session belongs to a different user",
        )
    return json.loads(notes_json) if notes_json else {}


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
    with psycopg.connect(_db_url()) as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT id FROM calls WHERE ticker = %s LIMIT 1", (ticker,))
            row = cur.fetchone()
            if not row:
                return
            call_id = str(row[0])

            notes = json.dumps({"topic": topic, "stage": stage, "messages": messages})
            completed_sql = "now()" if completed else "NULL"
            cur.execute(
                f"""
                INSERT INTO learning_sessions (id, user_id, call_id, notes, completed_at)
                VALUES (%s, %s::uuid, %s::uuid, %s, {completed_sql})
                ON CONFLICT (id) DO UPDATE SET
                    notes = EXCLUDED.notes,
                    completed_at = COALESCE(
                        learning_sessions.completed_at,
                        EXCLUDED.completed_at
                    )
                """,
                (session_id, user_id, call_id, notes),
            )
        conn.commit()


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
    try:
        for chunk in stream_chat(messages, system_prompt):
            if isinstance(chunk, str):
                accumulated.append(chunk)
                yield f"data: {json.dumps({'type': 'token', 'content': chunk})}\n\n"
            # usage dict is silently skipped — not surfaced to the client

        assistant_turn = {"role": "assistant", "content": "".join(accumulated)}
        updated_messages = messages + [assistant_turn]
        _upsert_session(ticker, session_id, user_id, topic, stage, updated_messages, completed=False)
        yield f"data: {json.dumps({'type': 'done', 'session_id': session_id})}\n\n"

    except Exception as exc:
        yield f"data: {json.dumps({'type': 'error', 'message': str(exc)})}\n\n"


# --- Request model ---

class ChatRequest(BaseModel):
    message: str
    session_id: str | None = None
    stage: int = 1  # only applied when creating a new session; 1–5


# --- Endpoint ---

@router.post("/{ticker}/chat")
def chat(
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
    else:
        session_id = str(uuid.uuid4())
        topic = body.message
        stage = max(1, min(body.stage, 5))
        history = []

    system_prompt = _load_prompt(stage)
    messages = history + [{"role": "user", "content": body.message}]

    return StreamingResponse(
        _sse_stream(messages, system_prompt, session_id, ticker, user_id, topic, stage),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
