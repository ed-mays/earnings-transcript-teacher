import os
import json
import logging
import requests
from typing import Dict, Any

from perplexity import Perplexity
from ingestion.prompts import TIER_1_SYSTEM_PROMPT, TIER_2_SYSTEM_PROMPT

logger = logging.getLogger(__name__)

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


class AgenticExtractor:
    def __init__(self):
        # The prompt says: "Assuming I will be using the Perplexity Agent API, I will have access to both Anthropic and OpenAI models."
        self.api_key = get_api_key()
        if not self.api_key:
            logger.warning("PERPLEXITY_API_KEY environment variable is not set. LLM extraction will fail.")
            self.api_key = "dummy-key"
            
        self.client = Perplexity(api_key=self.api_key)
        
        # Define the dynamic routing models described in the plan
        self.tier1_model = "openai/gpt-5-mini"         # Cheap, fast router
        self.tier2_model = "anthropic/claude-sonnet-4-5"  # Expensive, deep analysis

    def extract_tier1(self, text: str, chunk_type: str) -> Dict[str, Any]:
        """
        Run Tier 1 extraction for glossary, core concepts, and complexity score.
        """
        user_prompt = f"### Chunk Type: {chunk_type}\n### Transcript Text:\n{text}\n\nExtract the requested JSON metadata."
        
        try:
            response = self.client.responses.create(
                model=self.tier1_model,
                instructions=TIER_1_SYSTEM_PROMPT,
                input=user_prompt
            )
            
            content = response.output_text
            # Basic cleanup in case the model wraps JSON in markdown blocks
            content = content.strip()
            if content.startswith("```json"):
                content = content[7:-3].strip()
            elif content.startswith("```"):
                content = content[3:-3].strip()
                
            result = json.loads(content)
            if hasattr(response, 'usage') and response.usage:
                result["_usage_stats"] = {
                    "model": response.model,
                    "prompt_tokens": response.usage.input_tokens,
                    "completion_tokens": response.usage.output_tokens
                }
            return result
            
        except Exception as e:
            logger.error(f"Tier 1 Extraction failed: {e}")
            return {
                "extracted_terms": [],
                "core_concepts": [],
                "tier1_score": 0,
                "requires_deep_analysis": False
            }

    def extract_tier2(self, text: str, chunk_type: str) -> Dict[str, Any]:
        """
        Run Tier 2 extraction for takeaways, evasion analysis, and misconceptions.
        """
        user_prompt = f"### Chunk Type: {chunk_type}\n### Transcript Text:\n{text}\n\nExtract the requested pedagogical JSON metadata."
        
        try:
            response = self.client.responses.create(
                model=self.tier2_model,
                instructions=TIER_2_SYSTEM_PROMPT,
                input=user_prompt
            )
            
            content = response.output_text
            content = content.strip()
            if content.startswith("```json"):
                content = content[7:-3].strip()
            elif content.startswith("```"):
                content = content[3:-3].strip()
                
            result = json.loads(content)
            if hasattr(response, 'usage') and response.usage:
                result["_usage_stats"] = {
                    "model": response.model,
                    "prompt_tokens": response.usage.input_tokens,
                    "completion_tokens": response.usage.output_tokens
                }
            return result
            
        except Exception as e:
            logger.error(f"Tier 2 Extraction failed: {e}")
            return {
                "takeaways": [],
                "evasion_analysis": None,
                "misconceptions": []
            }
