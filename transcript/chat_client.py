"""Extensible LLM client wrapper for interactive chat sessions.

Currently configured to use the Perplexity API via the OpenAI SDK pattern,
but can be easily adapted to Anthropic, base OpenAI, or local models.
"""

import os
import json
import logging
from perplexity import Perplexity

def get_api_key() -> str | None:
    """Retrieve the Perplexity API key."""
    return os.environ.get("PERPLEXITY_API_KEY")


def stream_chat(
    messages: list[dict], 
    system_prompt: str, 
    model: str = "sonar-pro"
):
    """Send a chat history to the LLM and yield streaming string chunks.
    
    Args:
        messages: Previous conversation turns [{"role": "user"/"assistant", "content": "..."}]
        system_prompt: The persona definition and rules.
        model: The Perplexity model to route to.
        
    Yields:
        String chunks of the assistant's response as they stream in.
    """
    api_key = get_api_key()
    if not api_key:
        raise ValueError("PERPLEXITY_API_KEY environment variable is missing.")
        
    client = Perplexity(api_key=api_key)
    
    try:
        response_stream = client.responses.create(
            model=model,
            instructions=system_prompt,
            input=messages,
            stream=True
        )
        
        for chunk in response_stream:
            # ResponseStreamChunk is a pydantic union.
            chunk_dict = chunk.model_dump()
            if chunk_dict.get("type") == "response.output_text.delta":
                delta_text = chunk_dict.get("delta", "")
                if delta_text:
                    yield delta_text
    except Exception as e:
        yield f"\n[Error connecting to Perplexity API: {e}]"
