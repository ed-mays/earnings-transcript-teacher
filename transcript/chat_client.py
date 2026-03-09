"""Extensible LLM client wrapper for interactive chat sessions.

Currently configured to use the Perplexity API via the OpenAI SDK pattern,
but can be easily adapted to Anthropic, base OpenAI, or local models.
"""

import os
import json
import logging
import requests

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
        
    # Prepend the system prompt exactly once at the top of the context window
    api_messages = [{"role": "system", "content": system_prompt}] + messages
    
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "Accept": "text/event-stream"
    }
    
    payload = {
        "model": model,
        "messages": api_messages,
        "stream": True,
        "stream_options": {"include_usage": True} # Ask standards-compliant APIs to send final usage
    }
    
    try:
        with requests.post(
            "https://api.perplexity.ai/chat/completions",
            headers=headers,
            json=payload,
            stream=True
        ) as response:
            response.raise_for_status()
            
            for line in response.iter_lines():
                if line:
                    line_str = line.decode('utf-8')
                    if line_str.startswith("data: "):
                        data_str = line_str[6:]
                        if data_str == "[DONE]":
                            break
                        try:
                            # Parse JSON and extract delta content
                            data_json = json.loads(data_str)
                            
                            # Optional: Send usage stats back up
                            if "usage" in data_json and data_json["usage"]:
                                yield {"model": data_json.get("model", model), "usage": data_json["usage"]}
                                
                            if "choices" in data_json and len(data_json["choices"]) > 0:
                                delta = data_json["choices"][0].get("delta", {})
                                content = delta.get("content", "")
                                if content:
                                    yield content
                        except json.JSONDecodeError:
                            continue
    except Exception as e:
        yield f"\n[Error connecting to Perplexity API: {e}]"
