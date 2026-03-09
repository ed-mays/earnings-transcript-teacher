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
    
    # Mock NLP functions to avoid length/dimension errors on tiny texts
    mocker.patch("services.orchestrator.extract_keywords", return_value=[("cloud", 0.9), ("growth", 0.8)])
    
    mock_theme = MagicMock()
    mock_theme.label = 0
    mock_theme.terms = ["cloud", "azure"]
    mock_theme.weight = 1.5
    mocker.patch("services.orchestrator.extract_themes", return_value=[mock_theme])
    
    mock_takeaway = MagicMock()
    mock_takeaway.speaker = "Satya Nadella"
    mock_takeaway.text = "Cloud growth was tremendous this quarter."
    mock_takeaway.score = 2.0
    mocker.patch("services.orchestrator.extract_takeaways", return_value=[mock_takeaway])
    
    # Mock DB/Embedder
    mocker.patch("services.orchestrator.fetch_existing_embeddings", return_value={"Thank you.": [0.1, 0.1, 0.1]})
    mocker.patch("services.orchestrator.get_embeddings", return_value=[[0.2, 0.2, 0.2]] * 10) # arbitrary sufficient list
    
    # Mock IngestionPipeline to prevent API calls
    mock_pipeline_class = mocker.patch("ingestion.pipeline.IngestionPipeline")
    mock_pipeline_instance = MagicMock()
    mock_pipeline_instance.process.return_value = []
    mock_pipeline_class.return_value = mock_pipeline_instance

def test_analyze_orchestrator(mock_external_calls):
    result = analyze("MSFT")
    
    # Verify the structure of the returned CallAnalysis
    assert isinstance(result, CallAnalysis)
    assert result.call.ticker == "MSFT"
    assert result.call.token_count > 0
    
    # Check that speakers were extracted (Operator, Satya, Jane)
    assert len(result.speakers) == 3
    
    # Check that keywords, topics, and takeaways are linked
    assert len(result.keywords) == 2
    assert result.keywords[0].term == "cloud"
    
    assert len(result.topics) == 1
    assert result.topics[0].terms == ["cloud", "azure"]
    
    # The takeaway should have been linked to a span, or created as a standalone span
    assert len(result.takeaways) == 1
    assert result.takeaways[0].text == "Cloud growth was tremendous this quarter."
    assert result.takeaways[0].speaker_name == "Satya Nadella"
    
    # QA Pair extraction
    assert len(result.qa_pairs) > 0
