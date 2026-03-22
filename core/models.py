"""Schema-aligned data models for the analysis pipeline.

These dataclasses mirror the Postgres schema in db/schema.sql and serve
as the structured output contract of the pipeline.  Downstream consumers
(display, persistence, LLM prompts) all operate on a ``CallAnalysis``
instance rather than raw print statements.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
from uuid import UUID, uuid4

# ---------------------------------------------------------------------------
# Token usage tracking
# ---------------------------------------------------------------------------

# Pricing in USD per 1 million tokens (input, output)
_MODEL_PRICING: dict[str, tuple[float, float]] = {
    "claude-haiku-4-5-20251001": (0.80, 4.00),
    "claude-haiku-4-5":          (0.80, 4.00),
    "claude-sonnet-4-5":         (3.00, 15.00),
    "claude-sonnet-4-6":         (3.00, 15.00),
    "claude-opus-4-5":           (15.00, 75.00),
    "claude-opus-4-6":           (15.00, 75.00),
}

_MODEL_DISPLAY_NAMES: dict[str, str] = {
    "claude-haiku-4-5-20251001": "Claude Haiku 4.5",
    "claude-haiku-4-5":          "Claude Haiku 4.5",
    "claude-sonnet-4-5":         "Claude Sonnet 4.5",
    "claude-sonnet-4-6":         "Claude Sonnet 4.6",
    "claude-opus-4-5":           "Claude Opus 4.5",
    "claude-opus-4-6":           "Claude Opus 4.6",
}


@dataclass
class ModelTokenUsage:
    """Accumulated token usage and estimated cost for one model."""

    model_id: str
    display_name: str
    input_tokens: int = 0
    output_tokens: int = 0

    @property
    def estimated_cost(self) -> float:
        """Estimated cost in USD based on known pricing."""
        input_rate, output_rate = _MODEL_PRICING.get(self.model_id, (0.0, 0.0))
        return (self.input_tokens * input_rate + self.output_tokens * output_rate) / 1_000_000


@dataclass
class TokenUsageSummary:
    """Aggregated token usage across all LLM calls during ingestion."""

    by_model: dict[str, ModelTokenUsage] = field(default_factory=dict)

    def add(self, model_id: str, input_tokens: int, output_tokens: int) -> None:
        """Record usage for a model, creating the entry if needed."""
        if model_id not in self.by_model:
            display_name = _MODEL_DISPLAY_NAMES.get(model_id, model_id)
            self.by_model[model_id] = ModelTokenUsage(
                model_id=model_id, display_name=display_name
            )
        self.by_model[model_id].input_tokens += input_tokens
        self.by_model[model_id].output_tokens += output_tokens

    @property
    def total_input_tokens(self) -> int:
        return sum(m.input_tokens for m in self.by_model.values())

    @property
    def total_output_tokens(self) -> int:
        return sum(m.output_tokens for m in self.by_model.values())

    @property
    def total_cost(self) -> float:
        return sum(m.estimated_cost for m in self.by_model.values())

from parsing.sections import SpeakerProfile
from pydantic import BaseModel, Field as PydanticField


# ---------------------------------------------------------------------------
# Core records
# ---------------------------------------------------------------------------

@dataclass
class CallRecord:
    """Mirrors the ``calls`` table."""

    ticker: str
    transcript_json: str
    transcript_text: str
    token_count: int
    prepared_len: int
    qa_len: int
    id: UUID = field(default_factory=uuid4)
    company_name: str = ""
    industry: str = ""
    call_date: str | None = None   # ISO date string from the transcript JSON
    cached_embeddings_count: int = 0
    api_embeddings_count: int = 0


@dataclass
class SpanRecord:
    """Mirrors the ``spans`` table."""

    call_id: UUID
    speaker_name: str
    section: str            # 'prepared' | 'qa'
    span_type: str          # 'turn'
    sequence_order: int
    text: str
    textrank_score: float | None = None
    embedding: list[float] | None = None
    id: UUID = field(default_factory=uuid4)

    @property
    def char_count(self) -> int:
        return len(self.text)


# ---------------------------------------------------------------------------
# Analysis records
# ---------------------------------------------------------------------------

@dataclass
class KeywordRecord:
    """Mirrors the ``span_keywords`` table."""

    term: str
    score: float

    @property
    def ngram_size(self) -> int:
        return len(self.term.split())


@dataclass
class TopicRecord:
    """Mirrors the ``call_topics`` table."""

    label: int
    terms: list[str]
    weight: float
    rank_order: int


# ---------------------------------------------------------------------------
# Q&A record
# ---------------------------------------------------------------------------

@dataclass
class QAPairRecord:
    """Mirrors the ``qa_pairs`` table.

    Each record represents one exchange.  ``question_span_ids`` and
    ``answer_span_ids`` reference :attr:`SpanRecord.id` values.
    """

    exchange_order: int
    question_span_ids: list[UUID]
    answer_span_ids: list[UUID]


# ---------------------------------------------------------------------------
# News item
# ---------------------------------------------------------------------------

@dataclass
class NewsItem:
    """A single news article fetched around the earnings call date."""

    headline: str
    url: str
    source: str
    date: str       # ISO date string, e.g. "2025-01-15"
    summary: str


# ---------------------------------------------------------------------------
# Synthesis record
# ---------------------------------------------------------------------------

@dataclass
class CallSynthesisRecord:
    """Mirrors the ``call_synthesis`` table."""
    overall_sentiment: str
    executive_tone: str
    key_themes: list[str]
    strategic_shifts: str
    analyst_sentiment: str
    call_id: UUID = field(default_factory=uuid4)
    id: UUID = field(default_factory=uuid4)


# ---------------------------------------------------------------------------
# Agentic ingestion chunk
# ---------------------------------------------------------------------------

class TranscriptChunk(BaseModel):
    """A standardized chunk of the transcript ready for LLM ingestion."""

    chunk_id: str
    chunk_type: str  # 'prepared' or 'qa'
    text: str
    speakers: List[str]
    sequence_order: int

    # Tier 1 outputs (populated by cheap model)
    tier1_score: Optional[int] = None
    extracted_terms: List[Dict[str, str]] = PydanticField(default_factory=list)
    core_concepts: List[str] = PydanticField(default_factory=list)
    requires_deep_analysis: bool = False

    # Tier 2 outputs (populated by reasoning model)
    takeaways: List[Dict[str, str]] = PydanticField(default_factory=list)
    evasion_analysis: Optional[Dict[str, Any]] = None
    misconceptions: List[Dict[str, str]] = PydanticField(default_factory=list)


# ---------------------------------------------------------------------------
# Top-level result
# ---------------------------------------------------------------------------

@dataclass
class CallAnalysis:
    """Complete structured output of the analysis pipeline for one call."""

    call: CallRecord
    speakers: list[SpeakerProfile]
    spans: list[SpanRecord]
    keywords: list[KeywordRecord]
    topics: list[TopicRecord]
    takeaways: list[SpanRecord]     # subset of spans with textrank_score set
    qa_pairs: list[QAPairRecord]
    
    chunks: list[TranscriptChunk] = field(default_factory=list)
    synthesis: CallSynthesisRecord | None = None
    token_usage: TokenUsageSummary | None = None
