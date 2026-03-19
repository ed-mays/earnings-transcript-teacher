import os
import json
import logging
import requests
import threading
import time
from typing import Dict, Any
from tenacity import retry, wait_exponential_jitter, stop_after_attempt, retry_if_exception

import anthropic
from ingestion.prompts import TIER_1_SYSTEM_PROMPT, TIER_2_SYSTEM_PROMPT, TIER_3_SYNTHESIS_PROMPT, QA_DETECTION_SYSTEM_PROMPT

logger = logging.getLogger(__name__)


def _should_retry_error(exception: Exception) -> bool:
    """Return True only for transient API errors that are worth retrying."""
    if isinstance(exception, anthropic.APIStatusError):
        return exception.status_code in [429, 500, 502, 503, 504]
    return False


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
        logger.error("Error connecting to Perplexity API: %s", e)
        raise


class RateLimiter:
    """A simple token-bucket-like rate limiter for the Anthropic API. Thread-safe."""
    def __init__(self, requests_per_minute: int = 50, requests_per_second: int = 1):
        self.rpm = requests_per_minute
        self.rps = requests_per_second
        self.minute_allowance = requests_per_minute
        self.second_allowance = requests_per_second
        self.last_check = time.time()
        self._lock = threading.Lock()

    def wait(self):
        """Blocks until a request is allowed according to both RPM and RPS limits."""
        with self._lock:
            current = time.time()
            time_passed = current - self.last_check
            self.last_check = current

            self.minute_allowance += time_passed * (self.rpm / 60.0)
            if self.minute_allowance > self.rpm:
                self.minute_allowance = self.rpm

            self.second_allowance += time_passed * self.rps
            if self.second_allowance > self.rps:
                self.second_allowance = self.rps

            while self.minute_allowance < 1.0 or self.second_allowance < 1.0:
                self._lock.release()
                time.sleep(0.1)
                self._lock.acquire()
                current = time.time()
                time_passed = current - self.last_check
                self.last_check = current
                self.minute_allowance += time_passed * (self.rpm / 60.0)
                self.second_allowance += time_passed * self.rps

            self.minute_allowance -= 1.0
            self.second_allowance -= 1.0

class AgenticExtractor:
    def __init__(self, rpm_limit: int = 50, rps_limit: int = 5):
        self.client = anthropic.Anthropic()
        # self.tier1_model = "claude-haiku-4-5-20251001"
        self.tier1_model = "claude-sonnet-4-5"
        self.tier2_model = "claude-sonnet-4-5"
        self.tier3_model = "claude-haiku-4-5-20251001"
        self.rate_limiter = RateLimiter(requests_per_minute=rpm_limit, requests_per_second=rps_limit)

    def _parse_response(self, message) -> Dict[str, Any]:
        """Parse an Anthropic message response into a result dict with usage stats."""
        content = message.content[0].text.strip()
        if content.startswith("```json"):
            content = content[7:-3].strip()
        elif content.startswith("```"):
            content = content[3:-3].strip()
        try:
            result = json.loads(content)
        except json.JSONDecodeError as e:
            logger.error("Failed to parse LLM JSON response: %s. Content: %.200s", e, content)
            raise ValueError(f"LLM returned malformed JSON: {e}") from e
        result["_usage_stats"] = {
            "model": message.model,
            "prompt_tokens": message.usage.input_tokens,
            "completion_tokens": message.usage.output_tokens
        }
        return result

    @retry(
        wait=wait_exponential_jitter(initial=2, max=60),
        stop=stop_after_attempt(5),
        retry=retry_if_exception(_should_retry_error),
        reraise=True
    )
    def extract_tier1(self, text: str, chunk_type: str, company_context: str = "") -> Dict[str, Any]:
        """Run Tier 1 extraction for glossary, core concepts, and complexity score."""
        company_header = f"### Company: {company_context}\n" if company_context else ""
        user_prompt = f"{company_header}### Chunk Type: {chunk_type}\n### Transcript Text:\n{text}\n\nExtract the requested JSON metadata."
        self.rate_limiter.wait()
        message = self.client.messages.create(
            model=self.tier1_model,
            max_tokens=4096,
            system=TIER_1_SYSTEM_PROMPT,
            messages=[{"role": "user", "content": user_prompt}]
        )
        return self._parse_response(message)

    @retry(
        wait=wait_exponential_jitter(initial=2, max=60),
        stop=stop_after_attempt(5),
        retry=retry_if_exception(_should_retry_error),
        reraise=True
    )
    def extract_tier2(self, text: str, chunk_type: str) -> Dict[str, Any]:
        """Run Tier 2 extraction for takeaways, evasion analysis, and misconceptions."""
        user_prompt = f"### Chunk Type: {chunk_type}\n### Transcript Text:\n{text}\n\nExtract the requested pedagogical JSON metadata."
        self.rate_limiter.wait()
        message = self.client.messages.create(
            model=self.tier2_model,
            max_tokens=4096,
            system=TIER_2_SYSTEM_PROMPT,
            messages=[{"role": "user", "content": user_prompt}]
        )
        return self._parse_response(message)

    @retry(
        wait=wait_exponential_jitter(initial=2, max=60),
        stop=stop_after_attempt(5),
        retry=retry_if_exception(_should_retry_error),
        reraise=True
    )
    def extract_synthesis(self, aggregated_text: str) -> Dict[str, Any]:
        """Run Tier 3 extraction: overall strategic synthesis across all chunks."""
        user_prompt = f"### Aggregated Output from All Chunks:\n{aggregated_text}\n\nProduce the final pedagogical strategic synthesis."
        self.rate_limiter.wait()
        message = self.client.messages.create(
            model=self.tier3_model,
            max_tokens=1024,
            system=TIER_3_SYNTHESIS_PROMPT,
            messages=[{"role": "user", "content": user_prompt}]
        )
        return self._parse_response(message)
    @retry(
        wait=wait_exponential_jitter(initial=2, max=60),
        stop=stop_after_attempt(5),
        retry=retry_if_exception(_should_retry_error),
        reraise=True
    )
    def detect_qa_transition(self, turns: list[dict[str, str]]) -> dict[str, Any]:
        """Use LLM to identify the exact turn where Q&A begins.
        
        Args:
            turns: List of {"speaker": "...", "text": "..."} turns.
                  Should be a subset of the transcript (e.g. the middle 60%).
        """
        user_prompt = f"### Transcript Turns:\n{json.dumps(turns, indent=2)}\n\nIdentify the transition index."
        self.rate_limiter.wait()
        message = self.client.messages.create(
            model=self.tier3_model, # Use cheaper model (Haiku) for this
            max_tokens=512,
            system=QA_DETECTION_SYSTEM_PROMPT,
            messages=[{"role": "user", "content": user_prompt}]
        )
        return self._parse_response(message)
