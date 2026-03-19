"""Schema-aligned data models for the analysis pipeline.

These dataclasses mirror the Postgres schema in db/schema.sql and serve
as the structured output contract of the pipeline.  Downstream consumers
(display, persistence, LLM prompts) all operate on a ``CallAnalysis``
instance rather than raw print statements.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from uuid import UUID, uuid4

from parsing.sections import SpeakerProfile

# Local import to avoid circular dependency loop for now or we can use Any, 
# but usually it's better to just structure these carefully.
# For simplicity, we can do:
from typing import Any


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
    
    # NEW Agentic Ingestion Outputs
    chunks: list[Any] = field(default_factory=list) # List of TranscriptChunk
    synthesis: CallSynthesisRecord | None = None
