import numpy as np
import pytest

from db.repositories.analysis import AnalysisRepository
from core.models import CallAnalysis, CallRecord, CallSynthesisRecord


def test_get_topics_for_ticker(mock_psycopg_connect):
    m_connect, m_cursor = mock_psycopg_connect

    m_cursor.fetchall.return_value = [
        ("Cloud & Azure Growth", ["cloud", "azure", "growth"], "Management highlighted accelerating Azure adoption as the primary growth driver."),
        ("AI & Copilot Momentum", ["ai", "copilot", "chat"], "Copilot integrations are driving seat expansion across enterprise accounts."),
    ]

    repo = AnalysisRepository("fake_connection_string")
    topics = repo.get_topics_for_ticker("MSFT")

    assert len(topics) == 2
    assert topics[0]["label"] == "Cloud & Azure Growth"
    assert topics[0]["terms"] == ["cloud", "azure", "growth"]
    assert "Azure" in topics[0]["summary"]


def test_get_synthesis_for_ticker(mock_psycopg_connect):
    m_connect, m_cursor = mock_psycopg_connect

    m_cursor.fetchone.return_value = ("Positive", "Confident", "Bullish")

    repo = AnalysisRepository("fake_connection_string")
    synthesis = repo.get_synthesis_for_ticker("MSFT")

    assert synthesis == ("Positive", "Confident", "Bullish")
    m_cursor.execute.assert_called_once()
    assert "call_synthesis" in m_cursor.execute.call_args[0][0]


def test_get_synthesis_not_found(mock_psycopg_connect):
    m_connect, m_cursor = mock_psycopg_connect
    m_cursor.fetchone.return_value = None

    repo = AnalysisRepository("fake_connection_string")
    synthesis = repo.get_synthesis_for_ticker("UNKNOWN")

    assert synthesis is None


def test_fetch_existing_embeddings(mock_psycopg_connect, mocker):
    mocker.patch('db.repositories.embeddings.register_vector')

    m_connect, m_cursor = mock_psycopg_connect

    emb1 = np.array([0.1, 0.2, 0.3])
    emb2 = np.array([0.4, 0.5, 0.6])

    m_cursor.fetchall.return_value = [
        ("Some text span", emb1),
        ("Another span", emb2),
    ]

    from db.repositories.embeddings import EmbeddingRepository
    repo = EmbeddingRepository("fake_connection_string")
    cache = repo.fetch_existing_embeddings("MSFT", "Q1 2024 MSFT")

    assert "Some text span" in cache
    assert cache["Another span"] == [0.4, 0.5, 0.6]


def test_save_analysis_calls_helpers(mock_psycopg_connect, mocker):
    mocker.patch('db.repositories.analysis.register_vector')

    m_connect, m_cursor = mock_psycopg_connect

    call = CallRecord(
        ticker="MSFT",
        transcript_json="{}",
        transcript_text="transcript",
        token_count=100,
        prepared_len=80,
        qa_len=20,
    )
    synthesis = CallSynthesisRecord(
        overall_sentiment="Positive",
        executive_tone="Confident",
        key_themes=["cloud"],
        strategic_shifts=[],
        analyst_sentiment="Bullish",
    )
    analysis = CallAnalysis(
        call=call,
        speakers=[],
        spans=[],
        keywords=[],
        topics=[],
        takeaways=[],
        qa_pairs=[],
        synthesis=synthesis,
    )

    repo = AnalysisRepository("fake_connection_string")

    for method in (
        '_save_call', '_save_speakers', '_save_spans', '_save_topics',
        '_save_keywords', '_save_qa_pairs', '_save_agentic_chunks',
        '_save_call_synthesis',
    ):
        mocker.patch.object(repo, method)

    repo.save_analysis(analysis)

    repo._save_call.assert_called_once()
    repo._save_speakers.assert_called_once()
    repo._save_spans.assert_called_once()
    repo._save_topics.assert_called_once()
    repo._save_keywords.assert_called_once()
    repo._save_qa_pairs.assert_called_once()
    repo._save_agentic_chunks.assert_called_once()
    repo._save_call_synthesis.assert_called_once()
    m_connect.commit.assert_called_once()
