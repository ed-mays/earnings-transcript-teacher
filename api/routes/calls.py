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
from db.repositories.competitors import CompetitorRepository
from db.repositories.news import NewsRepository
from limiter import limiter
from services.competitors import fetch_competitors
from services.recent_news import fetch_recent_news
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


class TopicInfo(BaseModel):
    label: str
    terms: list[str] = []
    summary: str = ""


class NewsItemInfo(BaseModel):
    headline: str
    url: str
    source: str
    date: str
    summary: str


class CompetitorInfo(BaseModel):
    name: str
    ticker: str
    description: str
    mentioned_in_transcript: bool


class CallDetail(BaseModel):
    ticker: str
    company_name: str | None = None
    call_date: str | None = None
    industry: str | None = None
    synthesis: SynthesisInfo | None = None
    keywords: list[str] = []
    speakers: list[SpeakerInfo] = []
    brief: CallBrief | None = None
    takeaways: list[TakeawayItem] = []
    misconceptions: list[MisconceptionItem] = []
    signal_strip: SignalStrip | None = None


class TopicsResponse(BaseModel):
    topics: list[TopicInfo] = []
    themes: list[str] = []


class EvasionResponse(BaseModel):
    evasion_analyses: list[EvasionItem] = []
    evasion_level: str | None = None


class StrategicShiftsResponse(BaseModel):
    strategic_shifts: list[StrategicShift] = []


class CompetitorsResponse(BaseModel):
    competitors: list[CompetitorInfo] = []


class NewsResponse(BaseModel):
    news_items: list[NewsItemInfo] = []


class AdjacentCallInfo(BaseModel):
    ticker: str
    fiscal_quarter: str | None = None
    company_name: str | None = None
    call_date: str | None = None


class AdjacentCalls(BaseModel):
    prev: AdjacentCallInfo | None = None
    next: AdjacentCallInfo | None = None


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

    # Signal strip — lightweight flags query, no full evasion/shift data load
    evasion_level, strategic_shift_flagged = analysis_repo.get_signal_strip_flags_for_ticker(
        ticker, conn=conn
    )
    signal_strip = SignalStrip(
        overall_sentiment=raw_synthesis[0] if raw_synthesis else None,
        executive_sentiment=raw_synthesis[1] if raw_synthesis else None,
        analyst_sentiment=raw_synthesis[2] if raw_synthesis else None,
        evasion_level=evasion_level,
        strategic_shift_flagged=strategic_shift_flagged,
    )

    response.headers["Cache-Control"] = "public, max-age=300, stale-while-revalidate=60"
    return CallDetail(
        ticker=ticker,
        company_name=company_name or None,
        call_date=str(call_date) if call_date else None,
        industry=industry or None,
        synthesis=synthesis,
        keywords=analysis_repo.get_keywords_for_ticker(ticker, conn=conn),
        speakers=speakers,
        brief=brief,
        takeaways=takeaways,
        misconceptions=misconceptions,
        signal_strip=signal_strip,
    )


@router.get("/{ticker}/topics", response_model=TopicsResponse)
def get_call_topics(ticker: str, conn: DbDep, response: Response) -> TopicsResponse:
    """Return topics and themes for a call (Understand the Narrative section)."""
    logger.info("GET /api/calls/%s/topics", ticker)
    if not _ticker_exists(ticker, conn):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No call found for ticker {ticker!r}",
        )
    analysis_repo = AnalysisRepository(_db_url())
    response.headers["Cache-Control"] = "public, max-age=300, stale-while-revalidate=60"
    return TopicsResponse(
        topics=[TopicInfo(**t) for t in analysis_repo.get_topics_for_ticker(ticker, conn=conn)],
        themes=analysis_repo.get_themes_for_ticker(ticker, conn=conn),
    )


@router.get("/{ticker}/evasion", response_model=EvasionResponse)
def get_call_evasion(ticker: str, conn: DbDep, response: Response) -> EvasionResponse:
    """Return evasion analyses for a call (Notice What Was Avoided section)."""
    logger.info("GET /api/calls/%s/evasion", ticker)
    if not _ticker_exists(ticker, conn):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No call found for ticker {ticker!r}",
        )
    analysis_repo = AnalysisRepository(_db_url())
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
    evasion_level = None
    if raw_evasion:
        avg_score = sum(r[1] for r in raw_evasion) / len(raw_evasion)
        evasion_level = "high" if avg_score > 6 else ("medium" if avg_score > 3 else "low")
    response.headers["Cache-Control"] = "public, max-age=300, stale-while-revalidate=60"
    return EvasionResponse(evasion_analyses=evasion_analyses, evasion_level=evasion_level)


@router.get("/{ticker}/strategic-shifts", response_model=StrategicShiftsResponse)
def get_call_strategic_shifts(ticker: str, conn: DbDep, response: Response) -> StrategicShiftsResponse:
    """Return strategic shifts for a call (Track What Changed section)."""
    logger.info("GET /api/calls/%s/strategic-shifts", ticker)
    if not _ticker_exists(ticker, conn):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No call found for ticker {ticker!r}",
        )
    analysis_repo = AnalysisRepository(_db_url())
    raw_shifts = analysis_repo.get_strategic_shifts_for_ticker(ticker, conn=conn) or []
    strategic_shifts = [
        StrategicShift(
            prior_position=s.get("prior_position", ""),
            current_position=s.get("current_position", ""),
            investor_significance=s.get("investor_significance", ""),
        )
        for s in raw_shifts
    ]
    response.headers["Cache-Control"] = "public, max-age=300, stale-while-revalidate=60"
    return StrategicShiftsResponse(strategic_shifts=strategic_shifts)


@router.get("/{ticker}/competitors", response_model=CompetitorsResponse)
def get_call_competitors(ticker: str, conn: DbDep, response: Response) -> CompetitorsResponse:
    """Return competitors for a call with lazy hydration on cache miss (Situate in Context)."""
    logger.info("GET /api/calls/%s/competitors", ticker)
    if not _ticker_exists(ticker, conn):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No call found for ticker {ticker!r}",
        )
    db_url = _db_url()
    call_repo = CallRepository(db_url)
    comp_repo = CompetitorRepository(db_url)
    raw_competitors = comp_repo.get(ticker)
    if not raw_competitors:
        company_name, industry = call_repo.get_company_info(ticker, conn=conn)
        transcript_text = call_repo.get_transcript_text(ticker, conn=conn)
        raw_competitors = fetch_competitors(
            ticker, company_name or "", industry or "", transcript_text
        )
        if raw_competitors:
            comp_repo.save(ticker, raw_competitors)
    competitors = [
        CompetitorInfo(
            name=c.name,
            ticker=c.ticker,
            description=c.description,
            mentioned_in_transcript=c.mentioned_in_transcript,
        )
        for c in raw_competitors
    ]
    response.headers["Cache-Control"] = "public, max-age=300, stale-while-revalidate=60"
    return CompetitorsResponse(competitors=competitors)


@router.get("/{ticker}/news", response_model=NewsResponse)
def get_call_news(ticker: str, conn: DbDep, response: Response) -> NewsResponse:
    """Return recent news items for a call with lazy hydration on cache miss (Situate in Context)."""
    logger.info("GET /api/calls/%s/news", ticker)
    if not _ticker_exists(ticker, conn):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No call found for ticker {ticker!r}",
        )
    db_url = _db_url()
    call_repo = CallRepository(db_url)
    analysis_repo = AnalysisRepository(db_url)
    news_repo = NewsRepository(db_url)
    raw_news = news_repo.get(ticker)
    if not raw_news:
        company_name, _ = call_repo.get_company_info(ticker, conn=conn)
        call_date = call_repo.get_call_date(ticker, conn=conn)
        themes = analysis_repo.get_themes_for_ticker(ticker, conn=conn)
        if call_date is not None:
            raw_news = fetch_recent_news(ticker, company_name or "", call_date, themes)
            if raw_news:
                news_repo.save(ticker, raw_news)
    news_items = [
        NewsItemInfo(
            headline=n.headline,
            url=n.url,
            source=n.source,
            date=n.date,
            summary=n.summary,
        )
        for n in raw_news
    ]
    response.headers["Cache-Control"] = "public, max-age=300, stale-while-revalidate=60"
    return NewsResponse(news_items=news_items)


@router.get("/{ticker}/adjacent", response_model=AdjacentCalls)
def get_adjacent_calls(ticker: str, conn: DbDep) -> AdjacentCalls:
    """Return the prev/next calls relative to the given ticker ordered by call date."""
    logger.info("GET /api/calls/%s/adjacent", ticker)
    if not _ticker_exists(ticker, conn):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No call found for ticker {ticker!r}",
        )
    call_repo = CallRepository(_db_url())
    raw = call_repo.get_adjacent_calls(ticker, conn=conn)
    return AdjacentCalls(
        prev=AdjacentCallInfo(**raw["prev"]) if raw["prev"] else None,
        next=AdjacentCallInfo(**raw["next"]) if raw["next"] else None,
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
    "You are a financial analyst educator. Return 2–3 numbered points, each on its own line, "
    "explaining the investor implications of the evasion pattern described. "
    "Focus on what a careful investor or analyst should infer from this behaviour — "
    "not just what happened, but why it matters."
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
    """Generator that streams investor-implications framing as SSE events."""
    import json as _json
    from services.llm import stream_investor_signals

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
    logger.debug("evasion_signals stream starting")
    try:
        has_content = False
        for chunk in stream_investor_signals(messages, _SIGNALS_SYSTEM_PROMPT):
            if not has_content:
                logger.debug("evasion_signals first token received")
            has_content = True
            yield f"data: {_json.dumps({'type': 'token', 'content': chunk})}\n\n"
        logger.debug("evasion_signals stream ended has_content=%s", has_content)
        if has_content:
            yield f"data: {_json.dumps({'type': 'done'})}\n\n"
        else:
            yield f"data: {_json.dumps({'type': 'error', 'message': 'No content received from model'})}\n\n"
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

    return StreamingResponse(
        _signals_sse_stream(body),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


# --- News context ---

_NEWS_CONTEXT_SYSTEM_PROMPT = (
    "You are a financial analyst educator. "
    "In 2–3 sentences, explain why the following news headline is relevant "
    "to an investor who is analyzing the earnings call described. "
    "Be concrete: connect the news to the specific dynamics of this call."
)


class NewsContextRequest(BaseModel):
    headline: str
    summary: str
    source: str
    date: str


def _news_context_sse_stream(ticker: str, body: NewsContextRequest, conn: psycopg.Connection | None = None):
    """Generator that streams news-context analysis as SSE events."""
    import json as _json
    from services.llm import stream_investor_signals

    call_repo = CallRepository(_db_url())
    company_name, _ = call_repo.get_company_info(ticker, conn=conn)
    call_date = call_repo.get_call_date(ticker, conn=conn)
    call_label = f"{company_name or ticker} ({ticker})"
    if call_date:
        call_label += f" earnings call on {call_date}"

    messages = [
        {
            "role": "user",
            "content": (
                f"Earnings call: {call_label}\n"
                f"News headline: {body.headline}\n"
                f"Source: {body.source} ({body.date})\n"
                f"Summary: {body.summary}"
            ),
        }
    ]
    logger.debug("news_context stream starting for %s", ticker)
    try:
        has_content = False
        for chunk in stream_investor_signals(messages, _NEWS_CONTEXT_SYSTEM_PROMPT):
            if not has_content:
                logger.debug("news_context first token received for %s", ticker)
            has_content = True
            yield f"data: {_json.dumps({'type': 'token', 'content': chunk})}\n\n"
        logger.debug("news_context stream ended has_content=%s", has_content)
        if has_content:
            yield f"data: {_json.dumps({'type': 'done'})}\n\n"
        else:
            yield f"data: {_json.dumps({'type': 'error', 'message': 'No content received from model'})}\n\n"
    except Exception:
        logger.exception("Error streaming news context for %s", ticker)
        yield f"data: {_json.dumps({'type': 'error', 'message': 'Stream error'})}\n\n"


@router.post("/{ticker}/news-context")
@limiter.limit(CHAT_RATE_LIMIT)
def news_context(
    request: Request,
    ticker: str,
    body: NewsContextRequest,
    user_id: CurrentUserDep,
) -> StreamingResponse:
    """Stream a 2–3 sentence explanation of why a news item is relevant to this call as SSE."""
    if not _ticker_exists(ticker):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No call found for ticker {ticker!r}",
        )

    return StreamingResponse(
        _news_context_sse_stream(ticker, body),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
