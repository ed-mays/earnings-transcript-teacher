"""Extensible LLM client wrapper for interactive chat sessions.

Currently configured to use the Perplexity API via the OpenAI SDK pattern,
but can be easily adapted to Anthropic, base OpenAI, or local models.
"""

import os
from openai import OpenAI


def get_llm_client() -> OpenAI | None:
    """Initialize the OpenAI-compatible client pointing to Perplexity."""
    api_key = os.environ.get("PERPLEXITY_API_KEY")
    if not api_key:
        return None
        
    # The Perplexity API is fully compatible with OpenAI's SDK spec
    return OpenAI(
        api_key=api_key,
        base_url="https://api.perplexity.ai"
    )


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
    client = get_llm_client()
    if not client:
        raise ValueError("PERPLEXITY_API_KEY environment variable is missing.")
        
    # Prepend the system prompt exactly once at the top of the context window
    api_messages = [{"role": "system", "content": system_prompt}] + messages
    
    response = client.chat.completions.create(
        model=model,
        messages=api_messages,
        stream=True
    )
    
    for chunk in response:
        content = chunk.choices[0].delta.content
        if content:
            yield content
