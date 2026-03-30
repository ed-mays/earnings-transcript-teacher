"""Tests that orchestrator uses logger (not print) for Q&A detection messages."""

import json
import logging
import os
import sys
from unittest.mock import MagicMock, patch

import pytest

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../.."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)


# Minimal transcript JSON that provides turns but no Q&A section markers,
# so extract_transcript_sections() returns an empty QA string.
_TRANSCRIPT_JSON = json.dumps({
    "cik": "",
    "date": "2026-01-01",
    "content": "\n".join(
        f"Speaker{i}: This is turn {i}." for i in range(20)
    ),
})


def _make_mock_schema_repo():
    """Return a SchemaRepository mock that reports a healthy schema."""
    mock = MagicMock()
    mock.check_health.return_value = (True, "")
    return mock


@pytest.fixture()
def _patch_all_io():
    """Patch every I/O boundary in orchestrator.analyze() so it runs in-process."""
    with (
        patch("services.orchestrator.SchemaRepository", return_value=_make_mock_schema_repo()),
        patch("services.orchestrator.read_text_file", return_value=_TRANSCRIPT_JSON),
        patch("services.orchestrator.extract_transcript_text", return_value=_TRANSCRIPT_JSON),
        patch("services.orchestrator.fetch_company_info", return_value=("", "")),
        patch("services.orchestrator.clean_text", return_value=""),
        patch("services.orchestrator.tokenize", return_value=[]),
        # Return empty Q&A so the LLM fallback branch is triggered
        patch("services.orchestrator.extract_transcript_sections", return_value=("prepared text", "")),
        patch("services.orchestrator.extract_spans", return_value=[]),
        patch("services.orchestrator.enrich_speakers", return_value=[]),
        patch("services.orchestrator.extract_qa_exchanges", return_value=[]),
        patch("services.orchestrator.get_embeddings", return_value=[]),
        patch("services.orchestrator.fetch_existing_embeddings", return_value={}),
        patch("services.orchestrator.TURN_PATTERN") as mock_pattern,
        patch("services.llm.AgenticExtractor") as MockExtractor,
        patch("ingestion.pipeline.IngestionPipeline"),
    ):
        # Provide 20 fake turns so candidate_turns is non-empty
        mock_match = MagicMock()
        mock_match.group.side_effect = lambda k: "Speaker" if k == "speaker" else "text"
        mock_pattern.finditer.return_value = [mock_match] * 20

        extractor_instance = MockExtractor.return_value
        extractor_instance.detect_qa_transition.return_value = {"transition_index": -1, "confidence": 0.0}

        yield


def test_qa_fallback_uses_logger_not_print(_patch_all_io, caplog):
    """When deterministic Q&A detection fails, orchestrator logs via logger.info, not print."""
    from services import orchestrator

    with caplog.at_level(logging.INFO, logger="services.orchestrator"):
        try:
            orchestrator.analyze("TEST")
        except Exception:
            pass  # downstream errors are irrelevant; we only care about the log call

    assert any(
        "Deterministic Q&A detection failed" in r.message for r in caplog.records
    ), "Expected logger.info call for Q&A fallback was not emitted"


def test_agentic_pipeline_failure_uses_logger_not_print(caplog):
    """When the agentic pipeline raises, orchestrator logs via logger.warning, not print."""
    mock_schema = _make_mock_schema_repo()

    with (
        patch("services.orchestrator.SchemaRepository", return_value=mock_schema),
        patch("services.orchestrator.read_text_file", return_value=_TRANSCRIPT_JSON),
        patch("services.orchestrator.extract_transcript_text", return_value="text"),
        patch("services.orchestrator.fetch_company_info", return_value=("", "")),
        patch("services.orchestrator.clean_text", return_value=""),
        patch("services.orchestrator.tokenize", return_value=[]),
        patch("services.orchestrator.extract_transcript_sections", return_value=("prepared", "q&a")),
        patch("services.orchestrator.extract_spans", return_value=[]),
        patch("services.orchestrator.enrich_speakers", return_value=[]),
        patch("services.orchestrator.extract_qa_exchanges", return_value=[]),
        patch("services.orchestrator.get_embeddings", return_value=[]),
        patch("services.orchestrator.fetch_existing_embeddings", return_value={}),
        patch("ingestion.pipeline.IngestionPipeline") as MockPipeline,
        caplog.at_level(logging.WARNING, logger="services.orchestrator"),
    ):
        MockPipeline.return_value.process.side_effect = RuntimeError("boom")

        from services import orchestrator
        try:
            orchestrator.analyze("TEST")
        except Exception:
            pass

    assert any(
        "Agentic pipeline failed" in r.message for r in caplog.records
    ), "Expected logger.warning call for agentic pipeline failure was not emitted"
