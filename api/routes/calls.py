"""Earnings calls routes — library and transcript data."""

import logging
import os

logger = logging.getLogger(__name__)

import psycopg
from fastapi import APIRouter, HTTPException, Query, Request, status
from pydantic import BaseModel

from db.analytics import track
from db.repositories import AnalysisRepository, CallRepository
from limiter import limiter
from settings import SEARCH_QUERY_MAX_LENGTH, SEARCH_RATE_LIMIT

router = APIRouter(prefix="/api/calls", tags=["calls"])


def _db_url() -> str:
    """Return the database connection URL from environment."""
    return os.environ["DATABASE_URL"]


def _ticker_exists(ticker: str) -> bool:
    """Return True if a call record exists for the given ticker."""
    with psycopg.connect(_db_url()) as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT 1 FROM calls WHERE ticker = %s LIMIT 1", (ticker,))
            return cur.fetchone() is not None


# --- Response models ---

class CallSummary(BaseModel):
    ticker: str
    company_name: str | None = None
    call_date: str | None = None
    industry: str | None = None


class SpeakerInfo(BaseModel):
    name: str
    role: str
    title: str | None = None
    firm: str | None = None


class EvasionItem(BaseModel):
    analyst_concern: str
    defensiveness_score: int
    evasion_explanation: str


class StrategicShift(BaseModel):
    prior_position: str
    current_position: str
    investor_significance: str


class SynthesisInfo(BaseModel):
    overall_sentiment: str | None = None
    executive_tone: str | None = None
    analyst_sentiment: str | None = None


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
                "SELECT ticker, company_name, call_date, industry FROM calls ORDER BY created_at DESC"
            )
            rows = cur.fetchall()
    return [
        CallSummary(
            ticker=r[0],
            company_name=r[1],
            call_date=str(r[2]) if r[2] else None,
            industry=r[3],
        )
        for r in rows
    ]


@router.get("/{ticker}", response_model=CallDetail)
def get_call(ticker: str) -> CallDetail:
    """Return full metadata for a single analyzed call."""
    logger.info("GET /api/calls/%s", ticker)
    if not _ticker_exists(ticker):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No call found for ticker {ticker!r}",
        )

    db_url = _db_url()
    call_repo = CallRepository(db_url)
    analysis_repo = AnalysisRepository(db_url)

    company_name, industry = call_repo.get_company_info(ticker)
    call_date = call_repo.get_call_date(ticker)

    raw_synthesis = analysis_repo.get_synthesis_for_ticker(ticker)
    synthesis = (
        SynthesisInfo(
            overall_sentiment=raw_synthesis[0],
            executive_tone=raw_synthesis[1],
            analyst_sentiment=raw_synthesis[2],
        )
        if raw_synthesis
        else None
    )

    raw_shifts = analysis_repo.get_strategic_shifts_for_ticker(ticker) or []
    strategic_shifts = [
        StrategicShift(
            prior_position=s.get("prior_position", ""),
            current_position=s.get("current_position", ""),
            investor_significance=s.get("investor_significance", ""),
        )
        for s in raw_shifts
    ]

    raw_evasion = analysis_repo.get_evasion_for_ticker(ticker)
    evasion_analyses = [
        EvasionItem(
            analyst_concern=r[0],
            defensiveness_score=r[1],
            evasion_explanation=r[2],
        )
        for r in raw_evasion
    ]

    raw_speakers = analysis_repo.get_speakers_for_ticker(ticker)
    speakers = [SpeakerInfo(name=r[0], role=r[1], title=r[2], firm=r[3]) for r in raw_speakers]

    return CallDetail(
        ticker=ticker,
        company_name=company_name or None,
        call_date=str(call_date) if call_date else None,
        industry=industry or None,
        synthesis=synthesis,
        keywords=analysis_repo.get_keywords_for_ticker(ticker),
        themes=analysis_repo.get_themes_for_ticker(ticker),
        topics=analysis_repo.get_topics_for_ticker(ticker),
        evasion_analyses=evasion_analyses,
        strategic_shifts=strategic_shifts,
        speakers=speakers,
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
    embed_result = client.embed([q], model="voyage-finance-2")
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
