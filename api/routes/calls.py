"""Earnings calls routes — library and transcript data."""

import logging
import os
import time
from contextlib import nullcontext

logger = logging.getLogger(__name__)

import psycopg
from fastapi import APIRouter, HTTPException, Query, Request, Response, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from dependencies import CurrentUserDep, DbDep
from db.analytics import track
from db.repositories import AnalysisRepository, CallRepository
from limiter import limiter
from settings import CHAT_RATE_LIMIT, SEARCH_QUERY_MAX_LENGTH, SEARCH_RATE_LIMIT

router = APIRouter(prefix="/api/calls", tags=["calls"])


def _db_url() -> str:
    """Return the database connection URL from environment."""
    return os.environ["DATABASE_URL"]


def _ticker_exists(ticker: str, conn: psycopg.Connection | None = None) -> bool:
    """Return True if a call record exists for the given ticker."""
    ctx = nullcontext(conn) if conn is not None else psycopg.connect(_db_url())
    with ctx as c:
        with c.cursor() as cur:
            cur.execute("SELECT 1 FROM calls WHERE ticker = %s LIMIT 1", (ticker,))
            return cur.fetchone() is not None


# --- Response models ---

class CallSummary(BaseModel):
    ticker: str
    company_name: str | None = None
    call_date: str | None = None
    industry: str | None = None
    evasion_level: str | None = None
    overall_sentiment: str | None = None
    top_strategic_shift: str | None = None


class SpeakerInfo(BaseModel):
    name: str
    role: str
    title: str | None = None
    firm: str | None = None


class EvasionItem(BaseModel):
    analyst_concern: str
    defensiveness_score: int
    evasion_explanation: str
    question_topic: str | None = None
    analyst_name: str | None = None


class StrategicShift(BaseModel):
    prior_position: str
    current_position: str
    investor_significance: str


class SynthesisInfo(BaseModel):
    overall_sentiment: str | None = None
    executive_tone: str | None = None
    analyst_sentiment: str | None = None


class TakeawayItem(BaseModel):
    takeaway: str
    why_it_matters: str


class MisconceptionItem(BaseModel):
    fact: str
    misinterpretation: str
    correction: str


class CallBrief(BaseModel):
    context_line: str
    bigger_picture: list[str] = []
    interpretation_questions: list[str] = []


class SignalStrip(BaseModel):
    overall_sentiment: str | None = None
    executive_sentiment: str | None = None
    analyst_sentiment: str | None = None
    evasion_level: str | None = None
    strategic_shift_flagged: bool = False


class CallDetail(BaseModel):
    ticker: str
    company_name: str | None = None
    call_date: str | None = None
    industry: str | None = None
    synthesis: SynthesisInfo | None = None
    keywords: list[str] = []
    themes: list[str] = []
    topics: list[list[str]] = []
    evasion_analyses: list[EvasionItem] = []
    strategic_shifts: list[StrategicShift] = []
    speakers: list[SpeakerInfo] = []
    brief: CallBrief | None = None
    takeaways: list[TakeawayItem] = []
    misconceptions: list[MisconceptionItem] = []
    signal_strip: SignalStrip | None = None


class SpanItem(BaseModel):
    speaker: str
    section: str
    text: str
    sequence_order: int


class SpansResponse(BaseModel):
    total: int
    page: int
    page_size: int
    spans: list[SpanItem]


class SearchResult(BaseModel):
    speaker: str
    section: str
    text: str
    similarity: float


class SearchResponse(BaseModel):
    query: str
    results: list[SearchResult]


# --- Endpoints ---

@router.get("", response_model=list[CallSummary])
def list_calls() -> list[CallSummary]:
    """Return summary metadata for all analyzed calls."""
    logger.info("GET /api/calls")
    with psycopg.connect(_db_url()) as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT
                    c.ticker,
                    c.company_name,
                    c.call_date::text,
                    c.industry,
                    cs.overall_sentiment,
                    CASE
                        WHEN COUNT(ea.id) = 0 THEN NULL
                        WHEN AVG(ea.defensiveness_score) <= 3 THEN 'low'
                        WHEN AVG(ea.defensiveness_score) <= 6 THEN 'medium'
                        ELSE 'high'
                    END AS evasion_level,
                    CASE
                        WHEN cs.strategic_shifts IS NOT NULL
                             AND array_length(cs.strategic_shifts, 1) > 0
                        THEN cs.strategic_shifts[1]->>'current_position'
                        ELSE NULL
                    END AS top_strategic_shift
                FROM calls c
                LEFT JOIN call_synthesis cs ON cs.call_id = c.id
                LEFT JOIN evasion_analysis ea ON ea.call_id = c.id
                GROUP BY c.ticker, c.company_name, c.call_date, c.industry, c.created_at,
                         cs.overall_sentiment, cs.strategic_shifts
                ORDER BY c.created_at DESC
                """
            )
            rows = cur.fetchall()
    return [
        CallSummary(
            ticker=r[0],
            company_name=r[1],
            call_date=r[2],
            industry=r[3],
            overall_sentiment=r[4],
            evasion_level=r[5],
            top_strategic_shift=r[6],
        )
        for r in rows
    ]


@router.get("/{ticker}", response_model=CallDetail)
def get_call(ticker: str, conn: DbDep, response: Response) -> CallDetail:
    """Return full metadata for a single analyzed call."""
    logger.info("GET /api/calls/%s", ticker)
    if not _ticker_exists(ticker, conn):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No call found for ticker {ticker!r}",
        )

    db_url = _db_url()
    call_repo = CallRepository(db_url)
    analysis_repo = AnalysisRepository(db_url)

    company_name, industry = call_repo.get_company_info(ticker, conn=conn)
    call_date = call_repo.get_call_date(ticker, conn=conn)

    raw_synthesis = analysis_repo.get_synthesis_for_ticker(ticker, conn=conn)
    synthesis = (
        SynthesisInfo(
            overall_sentiment=raw_synthesis[0],
            executive_tone=raw_synthesis[1],
            analyst_sentiment=raw_synthesis[2],
        )
        if raw_synthesis
        else None
    )

    raw_shifts = analysis_repo.get_strategic_shifts_for_ticker(ticker, conn=conn) or []
    strategic_shifts = [
        StrategicShift(
            prior_position=s.get("prior_position", ""),
            current_position=s.get("current_position", ""),
            investor_significance=s.get("investor_significance", ""),
        )
        for s in raw_shifts
    ]

    raw_evasion = analysis_repo.get_evasion_for_ticker(ticker, conn=conn)
    evasion_analyses = [
        EvasionItem(
            analyst_concern=r[0],
            defensiveness_score=r[1],
            evasion_explanation=r[2],
            question_topic=r[3],
            analyst_name=r[4],
        )
        for r in raw_evasion
    ]

    raw_speakers = analysis_repo.get_speakers_for_ticker(ticker, conn=conn)
    speakers = [SpeakerInfo(name=r[0], role=r[1], title=r[2], firm=r[3]) for r in raw_speakers]

    # Brief
    raw_brief = analysis_repo.get_call_brief_for_ticker(ticker)
    brief = CallBrief(**raw_brief) if raw_brief else None

    # Takeaways (top 3 for the brief)
    raw_takeaways = analysis_repo.get_takeaways_for_ticker(ticker, limit=3)
    takeaways = [TakeawayItem(takeaway=r[0], why_it_matters=r[1]) for r in raw_takeaways]

    # Misconceptions (top 3 for the brief)
    raw_misconceptions = analysis_repo.get_misconceptions_for_ticker(ticker)
    misconceptions = [
        MisconceptionItem(fact=r[0], misinterpretation=r[1], correction=r[2])
        for r in raw_misconceptions[:3]
    ]

    # Signal strip
    evasion_level = None
    if raw_evasion:
        avg_score = sum(r[1] for r in raw_evasion) / len(raw_evasion)
        evasion_level = "high" if avg_score > 6 else ("medium" if avg_score > 3 else "low")
    signal_strip = SignalStrip(
        overall_sentiment=raw_synthesis[0] if raw_synthesis else None,
        executive_sentiment=raw_synthesis[1] if raw_synthesis else None,
        analyst_sentiment=raw_synthesis[2] if raw_synthesis else None,
        evasion_level=evasion_level,
        strategic_shift_flagged=len(raw_shifts) > 0,
    )

    response.headers["Cache-Control"] = "public, max-age=300, stale-while-revalidate=60"
    return CallDetail(
        ticker=ticker,
        company_name=company_name or None,
        call_date=str(call_date) if call_date else None,
        industry=industry or None,
        synthesis=synthesis,
        keywords=analysis_repo.get_keywords_for_ticker(ticker, conn=conn),
        themes=analysis_repo.get_themes_for_ticker(ticker, conn=conn),
        topics=analysis_repo.get_topics_for_ticker(ticker, conn=conn),
        evasion_analyses=evasion_analyses,
        strategic_shifts=strategic_shifts,
        speakers=speakers,
        brief=brief,
        takeaways=takeaways,
        misconceptions=misconceptions,
        signal_strip=signal_strip,
    )


@router.get("/{ticker}/spans", response_model=SpansResponse)
def get_spans(
    ticker: str,
    section: str = Query(default="all", pattern="^(prepared|qa|all)$"),
    speaker: str | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=200),
) -> SpansResponse:
    """Return paginated speaker turns for a transcript, with optional filtering."""
    logger.info("GET /api/calls/%s/spans section=%s", ticker, section)
    if not _ticker_exists(ticker):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No call found for ticker {ticker!r}",
        )

    conditions = ["c.ticker = %s", "s.span_type = 'turn'", "s.sequence_order >= 0"]
    params: list = [ticker]

    if section != "all":
        conditions.append("s.section = %s")
        params.append(section)
    if speaker:
        conditions.append("LOWER(COALESCE(sp.name, '')) LIKE LOWER(%s)")
        params.append(f"%{speaker}%")

    where = (
        "FROM spans s "
        "JOIN calls c ON s.call_id = c.id "
        "LEFT JOIN speakers sp ON s.speaker_id = sp.id "
        "WHERE " + " AND ".join(conditions)
    )

    with psycopg.connect(_db_url()) as conn:
        with conn.cursor() as cur:
            cur.execute(f"SELECT COUNT(*) {where}", params)
            total: int = cur.fetchone()[0]

            cur.execute(
                f"SELECT COALESCE(sp.name, 'Unknown'), s.section, s.text, s.sequence_order "
                f"{where} ORDER BY s.sequence_order ASC LIMIT %s OFFSET %s",
                params + [page_size, (page - 1) * page_size],
            )
            rows = cur.fetchall()

    spans = [SpanItem(speaker=r[0], section=r[1], text=r[2], sequence_order=r[3]) for r in rows]
    return SpansResponse(total=total, page=page, page_size=page_size, spans=spans)


@router.get("/{ticker}/search", response_model=SearchResponse)
@limiter.limit(SEARCH_RATE_LIMIT)
def search_transcript(
    request: Request,
    ticker: str,
    q: str = Query(min_length=1, max_length=SEARCH_QUERY_MAX_LENGTH),
    top_k: int = Query(default=5, ge=1, le=20),
) -> SearchResponse:
    """Semantic search within a transcript using pgvector similarity."""
    logger.info("GET /api/calls/%s/search q=%r", ticker, q)
    if not _ticker_exists(ticker):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No call found for ticker {ticker!r}",
        )

    api_key = os.environ.get("VOYAGE_API_KEY")
    if not api_key:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Semantic search is unavailable — VOYAGE_API_KEY is not configured",
        )

    import voyageai
    from pgvector.psycopg import register_vector

    client = voyageai.Client(api_key=api_key)
    _t0 = time.monotonic()
    embed_result = client.embed([q], model="voyage-finance-2")
    logger.debug("voyage embed completed in %.0fms", (time.monotonic() - _t0) * 1000)
    query_vector = embed_result.embeddings[0]
    track(
        "api_call_completed",
        properties={
            "service": "voyage",
            "operation": "search",
            "input_tokens": embed_result.total_tokens,
            "output_tokens": 0,
        },
    )

    with psycopg.connect(_db_url()) as conn:
        register_vector(conn)
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT COALESCE(sp.name, 'Unknown'), s.section, s.text,
                       1 - (s.embedding <=> %s::vector) AS similarity
                FROM spans s
                JOIN calls c ON s.call_id = c.id
                LEFT JOIN speakers sp ON s.speaker_id = sp.id
                WHERE c.ticker = %s AND s.embedding IS NOT NULL
                ORDER BY s.embedding <=> %s::vector
                LIMIT %s
                """,
                (query_vector, ticker, query_vector, top_k),
            )
            rows = cur.fetchall()

    return SearchResponse(
        query=q,
        results=[
            SearchResult(speaker=r[0], section=r[1], text=r[2], similarity=float(r[3]))
            for r in rows
        ],
    )


# --- Evasion signals ---

_SIGNALS_SYSTEM_PROMPT = (
    "You are a financial analyst educator. In 2–3 sentences, explain the investor "
    "implications of the evasion pattern described. Focus on what a careful investor "
    "or analyst should infer from this behaviour — not just what happened, but why it matters."
)


def _defensiveness_label(score: int) -> str:
    """Map a 1–10 defensiveness score to a human-readable label."""
    if score >= 8:
        return "high"
    if score >= 5:
        return "medium"
    return "low"


class EvasionSignalsRequest(BaseModel):
    analyst_concern: str
    defensiveness_score: int
    evasion_explanation: str


def _signals_sse_stream(body: EvasionSignalsRequest):
    """Generator that calls stream_chat and emits SSE-formatted lines for evasion signals."""
    import json as _json
    from services.llm import stream_chat

    level = _defensiveness_label(body.defensiveness_score)
    messages = [
        {
            "role": "user",
            "content": (
                f"Evasion concern: {body.analyst_concern}\n"
                f"Defensiveness level: {level}\n"
                f"What the executive avoided: {body.evasion_explanation}"
            ),
        }
    ]
    try:
        for chunk in stream_chat(messages, _SIGNALS_SYSTEM_PROMPT):
            if isinstance(chunk, str):
                yield f"data: {_json.dumps({'type': 'token', 'content': chunk})}\n\n"
        yield f"data: {_json.dumps({'type': 'done'})}\n\n"
    except Exception:
        logger.exception("Error streaming evasion signals")
        yield f"data: {_json.dumps({'type': 'error', 'message': 'Stream error'})}\n\n"


@router.post("/{ticker}/evasion-signals")
@limiter.limit(CHAT_RATE_LIMIT)
def evasion_signals(
    request: Request,
    ticker: str,
    body: EvasionSignalsRequest,
    user_id: CurrentUserDep,
) -> StreamingResponse:
    """Stream a 2–3 sentence investor-implications framing for an evasion item as SSE."""
    if not _ticker_exists(ticker):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No call found for ticker {ticker!r}",
        )

    api_key = os.environ.get("PERPLEXITY_API_KEY")
    if not api_key:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Signals unavailable — PERPLEXITY_API_KEY is not configured",
        )

    return StreamingResponse(
        _signals_sse_stream(body),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
