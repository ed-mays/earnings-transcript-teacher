import pytest
import json
from unittest.mock import MagicMock
from services.llm import stream_chat, AgenticExtractor

def test_stream_chat_success(mocker, monkeypatch):
    monkeypatch.setenv("PERPLEXITY_API_KEY", "fake_key")
    
    # Mock requests.post
    mock_post = mocker.patch("requests.post")
    mock_response = MagicMock()
    mock_post.return_value.__enter__.return_value = mock_response
    
    # Mock iter_lines to return SSE format lines
    mock_response.iter_lines.return_value = [
        b'data: {"choices": [{"delta": {"content": "Hello"}}]}',
        b'data: {"choices": [{"delta": {"content": " World"}}]}',
        b'data: {"usage": {"prompt_tokens": 10, "completion_tokens": 20}}',
        b'data: [DONE]'
    ]
    
    chunks = list(stream_chat([{"role": "user", "content": "hi"}], "system prompt"))
    
    assert "Hello" in chunks
    assert " World" in chunks
    
    # Usage stats should be yielded as a dict
    usage_chunk = next((c for c in chunks if isinstance(c, dict) and "usage" in c), None)
    assert usage_chunk is not None
    assert usage_chunk["usage"]["prompt_tokens"] == 10

def test_stream_chat_missing_key(monkeypatch):
    monkeypatch.delenv("PERPLEXITY_API_KEY", raising=False)
    with pytest.raises(ValueError, match="PERPLEXITY_API_KEY environment variable is missing"):
        list(stream_chat([], "prompt"))

def test_agentic_extractor_tier1(mocker, monkeypatch):
    monkeypatch.setenv("PERPLEXITY_API_KEY", "fake_key")
    
    # Mock Perplexity client
    mock_perplexity = mocker.patch("services.llm.Perplexity")
    mock_instance = MagicMock()
    mock_perplexity.return_value = mock_instance
    
    # Mock the response
    mock_response = MagicMock()
    mock_response.output_text = '```json\n{"tier1_score": 8, "requires_deep_analysis": true}\n```'
    mock_instance.responses.create.return_value = mock_response
    
    extractor = AgenticExtractor()
    result = extractor.extract_tier1("Some transcript text", "prepared_remarks")
    
    assert result["tier1_score"] == 8
    assert result["requires_deep_analysis"] is True

def test_agentic_extractor_tier2_failure(mocker, monkeypatch):
    monkeypatch.setenv("PERPLEXITY_API_KEY", "fake_key")
    
    mock_perplexity = mocker.patch("services.llm.Perplexity")
    mock_instance = MagicMock()
    mock_perplexity.return_value = mock_instance
    
    # Simulate an API error
    mock_instance.responses.create.side_effect = Exception("API Timeout")
    
    extractor = AgenticExtractor()
    result = extractor.extract_tier2("Some text", "qa")
    
    # Should safely handle the error and return default empty structure
    assert result["takeaways"] == []
    assert result["evasion_analysis"] is None
