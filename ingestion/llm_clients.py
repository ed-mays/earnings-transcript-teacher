import os
import json
import logging
from typing import Dict, Any

from perplexity import Perplexity
from ingestion.prompts import TIER_1_SYSTEM_PROMPT, TIER_2_SYSTEM_PROMPT

logger = logging.getLogger(__name__)

class AgenticExtractor:
    def __init__(self):
        # The prompt says: "Assuming I will be using the Perplexity Agent API, I will have access to both Anthropic and OpenAI models."
        self.api_key = os.environ.get("PERPLEXITY_API_KEY")
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
                
            return json.loads(content)
            
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
                
            return json.loads(content)
            
        except Exception as e:
            logger.error(f"Tier 2 Extraction failed: {e}")
            return {
                "takeaways": [],
                "evasion_analysis": None,
                "misconceptions": []
            }
