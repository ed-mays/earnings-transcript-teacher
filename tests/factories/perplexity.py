"""Factory for realistic Perplexity streaming LLM responses — no live API call.

services.llm.stream_chat yields:
  - str chunks (the assistant's text, citation markers already stripped)
  - one final dict  {"model": <str>, "usage": {"prompt_tokens": N, "completion_tokens": M}}

These factories return iterators with that shape so tests can patch stream_chat
without knowing about the underlying SSE protocol.
"""

from collections.abc import Iterator
from typing import Any


def stream_chunks(
    text: str = "Revenue grew strongly in Q4.",
    model: str = "sonar-pro",
    prompt_tokens: int = 42,
) -> list[Any]:
    """Return a list of values that stream_chat would yield for the given text.

    The list contains one str per word (space-separated, preserving trailing
    spaces for all but the last word) followed by a usage metadata dict.

    Args:
        text: The assistant response text to split into word-level chunks.
        model: Model name to embed in the trailing usage dict.
        prompt_tokens: Simulated prompt token count for the usage dict.
    """
    words = text.split()
    chunks: list[Any] = [
        word + (" " if i < len(words) - 1 else "")
        for i, word in enumerate(words)
    ]
    completion_tokens = len(words)
    chunks.append(
        {
            "model": model,
            "usage": {
                "prompt_tokens": prompt_tokens,
                "completion_tokens": completion_tokens,
            },
        }
    )
    return chunks


def stream_response(
    text: str = "Revenue grew strongly in Q4.",
    model: str = "sonar-pro",
    prompt_tokens: int = 42,
) -> Iterator[Any]:
    """Return an iterator that mimics stream_chat output for the given text.

    Suitable for use as the return value when patching services.llm.stream_chat::

        with patch("services.llm.stream_chat", return_value=stream_response("Hello world")):
            ...

    Args:
        text: The assistant response text to stream word by word.
        model: Model name to embed in the trailing usage dict.
        prompt_tokens: Simulated prompt token count.
    """
    return iter(stream_chunks(text, model=model, prompt_tokens=prompt_tokens))


def investor_signals_response(
    text: str = "Investors should monitor margin compression closely.",
) -> Iterator[str]:
    """Return an iterator of string chunks mimicking stream_investor_signals output.

    stream_investor_signals yields plain str tokens (no trailing usage dict).

    Args:
        text: The response text to split into word-level string chunks.
    """
    words = text.split()
    return iter(
        word + (" " if i < len(words) - 1 else "")
        for i, word in enumerate(words)
    )
