import pytest
import json
import textwrap
from unittest.mock import MagicMock
from services.orchestrator import analyze
from core.models import CallAnalysis

@pytest.fixture
def mock_external_calls(mocker):
    # Mock file reading
    raw_text = textwrap.dedent("""\
    Operator:
    Welcome to the MSFT Q1 call. We will begin with Satya.
    Satya Nadella:
    Thank you. Cloud growth was tremendous this quarter. We saw 50% growth. This is great.
    Operator:
    We will now open the floor for questions.
    John Doe:
    Why did cloud margins drop?
    Satya Nadella:
    They actually increased due to efficiency.
    """)
    mocker.patch("services.orchestrator.read_text_file", return_value=json.dumps({"transcript": raw_text}))

    # Mock schema health check to pass without a real DB connection
    mock_schema_repo = MagicMock()
    mock_schema_repo.check_health.return_value = (True, "ok")
    mocker.patch("services.orchestrator.SchemaRepository", return_value=mock_schema_repo)

    # Mock DB/Embedder
    mocker.patch("services.orchestrator.fetch_existing_embeddings", return_value={"Thank you.": [0.1, 0.1, 0.1]})
    mocker.patch("services.orchestrator.get_embeddings", return_value=[[0.2, 0.2, 0.2]] * 10)

    # Mock IngestionPipeline — return 4-tuple including NLP synthesis output
    from core.models import CallSynthesisRecord, TokenUsageSummary
    mock_synthesis = CallSynthesisRecord(
        overall_sentiment="positive",
        executive_tone="confident",
        key_themes=["cloud"],
        strategic_shifts=[],
        analyst_sentiment="cautious",
    )
    nlp_synthesis = {
        "keywords": [
            {"term": "cloud", "significance": "core growth driver"},
            {"term": "azure", "significance": "flagship product"},
        ],
        "themes": [
            {"name": "Cloud Expansion", "terms": ["cloud", "azure", "growth"]},
        ],
        "top_takeaways": [
            {"speaker": "Satya Nadella", "takeaway": "Cloud growth was tremendous.", "why_it_matters": "Signals accelerating adoption."},
        ],
    }
    mock_pipeline_class = mocker.patch("ingestion.pipeline.IngestionPipeline")
    mock_pipeline_instance = MagicMock()
    mock_pipeline_instance.process.return_value = ([], mock_synthesis, TokenUsageSummary(), nlp_synthesis, None)
    mock_pipeline_class.return_value = mock_pipeline_instance


def test_analyze_orchestrator(mock_external_calls):
    result = analyze("MSFT")

    # Verify the structure of the returned CallAnalysis
    assert isinstance(result, CallAnalysis)
    assert result.call.ticker == "MSFT"
    assert result.call.token_count > 0

    # Check that speakers were extracted (Operator, Satya, John Doe)
    assert len(result.speakers) == 3

    # Keywords come from NLP synthesis
    assert len(result.keywords) == 2
    assert result.keywords[0].term == "cloud"

    # Topics come from NLP synthesis
    assert len(result.topics) == 1
    assert result.topics[0].terms == ["cloud", "azure", "growth"]
    assert result.topics[0].name == "Cloud Expansion"

    # Takeaways list is empty (scikit-learn TextRank removed; NLP takeaways go to console)
    assert result.takeaways == []

    # QA Pair extraction
    assert len(result.qa_pairs) > 0
