import pytest
import json
from unittest.mock import MagicMock
from services.llm import stream_chat, AgenticExtractor, _CITATION_PATTERN
from tenacity import RetryError

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

def test_stream_chat_strips_numeric_citations(mocker, monkeypatch):
    monkeypatch.setenv("PERPLEXITY_API_KEY", "fake_key")

    mock_post = mocker.patch("requests.post")
    mock_response = MagicMock()
    mock_post.return_value.__enter__.return_value = mock_response

    mock_response.iter_lines.return_value = [
        b'data: {"choices": [{"delta": {"content": "Good point.[1] Another idea.[2]"}}]}',
        b'data: [DONE]'
    ]

    chunks = list(stream_chat([{"role": "user", "content": "hi"}], "sys"))
    full = "".join(c for c in chunks if isinstance(c, str))
    assert "[1]" not in full
    assert "[2]" not in full
    assert "Good point." in full
    assert "Another idea." in full


def test_stream_chat_strips_transcript_context_citations(mocker, monkeypatch):
    monkeypatch.setenv("PERPLEXITY_API_KEY", "fake_key")

    mock_post = mocker.patch("requests.post")
    mock_response = MagicMock()
    mock_post.return_value.__enter__.return_value = mock_response

    mock_response.iter_lines.return_value = [
        b'data: {"choices": [{"delta": {"content": "Tesla said this.[transcript_context]"}}]}',
        b'data: [DONE]'
    ]

    chunks = list(stream_chat([{"role": "user", "content": "hi"}], "sys"))
    full = "".join(c for c in chunks if isinstance(c, str))
    assert "[transcript_context]" not in full
    assert "Tesla said this." in full


def test_stream_chat_strips_citation_split_across_chunks(mocker, monkeypatch):
    """Citation split across two SSE chunks must still be removed."""
    monkeypatch.setenv("PERPLEXITY_API_KEY", "fake_key")

    mock_post = mocker.patch("requests.post")
    mock_response = MagicMock()
    mock_post.return_value.__enter__.return_value = mock_response

    mock_response.iter_lines.return_value = [
        b'data: {"choices": [{"delta": {"content": "Hello [tra"}}]}',
        b'data: {"choices": [{"delta": {"content": "nscript_context] world"}}]}',
        b'data: [DONE]'
    ]

    chunks = list(stream_chat([{"role": "user", "content": "hi"}], "sys"))
    full = "".join(c for c in chunks if isinstance(c, str))
    assert "[transcript_context]" not in full
    assert "Hello" in full
    assert "world" in full


def test_stream_chat_missing_key(monkeypatch):
    monkeypatch.delenv("PERPLEXITY_API_KEY", raising=False)
    with pytest.raises(ValueError, match="PERPLEXITY_API_KEY environment variable is missing"):
        list(stream_chat([], "prompt"))

def test_agentic_extractor_tier1(mocker, monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "fake_key")

    mock_anthropic = mocker.patch("services.llm.anthropic.Anthropic")
    mock_instance = MagicMock()
    mock_anthropic.return_value = mock_instance

    mock_message = MagicMock()
    mock_message.content = [MagicMock(text='{"tier1_score": 8, "requires_deep_analysis": true}')]
    mock_message.model = "claude-haiku-4-5-20251001"
    mock_message.usage.input_tokens = 100
    mock_message.usage.output_tokens = 50
    mock_instance.messages.create.return_value = mock_message

    extractor = AgenticExtractor()
    result = extractor.extract_tier1("Some transcript text", "prepared_remarks")

    assert result["tier1_score"] == 8
    assert result["requires_deep_analysis"] is True


def test_agentic_extractor_tier1_includes_company_context(mocker, monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "fake_key")

    mock_anthropic = mocker.patch("services.llm.anthropic.Anthropic")
    mock_instance = MagicMock()
    mock_anthropic.return_value = mock_instance

    mock_message = MagicMock()
    mock_message.content = [MagicMock(text='{"tier1_score": 5, "requires_deep_analysis": false}')]
    mock_message.model = "claude-haiku-4-5-20251001"
    mock_message.usage.input_tokens = 100
    mock_message.usage.output_tokens = 50
    mock_instance.messages.create.return_value = mock_message

    extractor = AgenticExtractor()
    extractor.extract_tier1("Some transcript text", "prepared_remarks", company_context="Tesla, Inc. (TSLA) — Motor Vehicles")

    call_kwargs = mock_instance.messages.create.call_args
    user_message = call_kwargs[1]["messages"][0]["content"]
    assert "### Company: Tesla, Inc. (TSLA) — Motor Vehicles" in user_message


def test_agentic_extractor_tier1_no_company_context_header(mocker, monkeypatch):
    """When company_context is empty, no ### Company header should appear."""
    monkeypatch.setenv("ANTHROPIC_API_KEY", "fake_key")

    mock_anthropic = mocker.patch("services.llm.anthropic.Anthropic")
    mock_instance = MagicMock()
    mock_anthropic.return_value = mock_instance

    mock_message = MagicMock()
    mock_message.content = [MagicMock(text='{"tier1_score": 3, "requires_deep_analysis": false}')]
    mock_message.model = "claude-haiku-4-5-20251001"
    mock_message.usage.input_tokens = 50
    mock_message.usage.output_tokens = 20
    mock_instance.messages.create.return_value = mock_message

    extractor = AgenticExtractor()
    extractor.extract_tier1("Some transcript text", "prepared_remarks")

    call_kwargs = mock_instance.messages.create.call_args
    user_message = call_kwargs[1]["messages"][0]["content"]
    assert "### Company:" not in user_message


def test_agentic_extractor_tier2_failure(mocker, monkeypatch):
    import anthropic as anthropic_lib
    monkeypatch.setenv("ANTHROPIC_API_KEY", "fake_key")

    mock_anthropic = mocker.patch("services.llm.anthropic.Anthropic")
    mock_instance = MagicMock()
    mock_anthropic.return_value = mock_instance

    # Simulate an APIStatusError (non-retryable by our retry decorator since it only retries APIStatusError)
    mock_response = MagicMock()
    mock_response.status_code = 500
    mock_instance.messages.create.side_effect = anthropic_lib.APIStatusError(
        "Server Error", response=mock_response, body={}
    )

    extractor = AgenticExtractor()

    with pytest.raises((anthropic_lib.APIStatusError, RetryError)):
        extractor.extract_tier2("Some text", "qa")
