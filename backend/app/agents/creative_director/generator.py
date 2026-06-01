"""Creative Brief Generator with Claude API integration.

Generates platform-specific creatives using Claude API with retry logic.
Implements async methods for:
1. Core concept generation (unified across platforms)
2. Platform-specific creative variations
3. Refinement of creatives based on violations
"""

import asyncio
import json
import logging

from anthropic import AsyncAnthropic

from backend.app.agents.json_parsing import extract_json
from backend.app.external.stubs import stub_enabled

logger = logging.getLogger(__name__)


class CreativeGenerator:
    """Generates creatives using Claude API with exponential backoff retry logic."""

    def __init__(self, api_key: str | None = None, model: str = "claude-opus-4-7"):
        """Initialize CreativeGenerator with AsyncAnthropic client.

        Args:
            api_key: Optional API key. If None, uses ANTHROPIC_API_KEY env var.
            model: Claude model to use. Default: claude-opus-4-7
        """
        self.client = AsyncAnthropic(api_key=api_key)
        self.model = model
        self.max_retries = 3
        self.backoff_base = 2  # Exponential: 2^n seconds

    async def generate_core_concept(self, campaign_data: dict) -> dict:
        """Generate unified core concept for a campaign.

        Args:
            campaign_data: Campaign data dict with campaign_input

        Returns:
            Dict with keys: message, visual_direction, audio_direction, tone
        """
        from backend.app.agents.creative_director.models import CampaignInput
        from backend.app.agents.creative_director.prompts import CreativePrompts

        campaign_input = campaign_data.get("campaign_input")

        # Convert dict to CampaignInput if needed
        if isinstance(campaign_input, dict):
            campaign_input = CampaignInput(**campaign_input)

        prompt = CreativePrompts.core_concept_prompt(campaign_input)

        response = await self._call_claude_with_retry(prompt)
        return response

    async def generate_platform_creatives(
        self,
        platform: str,
        core_concept: dict,
        campaign_data: dict,
        creative_type: str
    ) -> list[dict]:
        """Generate platform-specific creative variations.

        Args:
            platform: Target platform (instagram, linkedin, youtube, meta_ads, tiktok, twitter)
            core_concept: Dict with message, visual_direction, audio_direction, tone
            campaign_data: Campaign data dict with campaign_input
            creative_type: Type of creative (copy, image_prompt, video_concept, voiceover_script)

        Returns:
            List of creative variation dicts
        """
        from backend.app.agents.creative_director.models import CampaignInput
        from backend.app.agents.creative_director.prompts import CreativePrompts

        campaign_input = campaign_data.get("campaign_input")

        # Convert dict to CampaignInput if needed
        if isinstance(campaign_input, dict):
            campaign_input = CampaignInput(**campaign_input)

        prompt = CreativePrompts.platform_specific_prompt(
            core_concept, platform, campaign_input, creative_type
        )

        response = await self._call_claude_with_retry(prompt)

        # Ensure response is a list
        if isinstance(response, dict) and "variations" in response:
            return response["variations"]
        elif isinstance(response, list):
            return response
        else:
            return [response]

    async def refine_creative(self, original_content: str, violations: list[dict]) -> str:
        """Refine creative based on validation violations.

        Args:
            original_content: Original creative content
            violations: List of violation dicts with rule, severity, message, suggestion

        Returns:
            Refined creative string
        """
        from backend.app.agents.creative_director.prompts import CreativePrompts

        prompt = CreativePrompts.refinement_prompt(original_content, violations)
        response = await self._call_claude_with_retry(prompt)

        # Response should be a string for refinement
        if isinstance(response, dict):
            return response.get("refined_content", str(response))
        return str(response)

    async def _call_claude_with_retry(
        self, prompt: str, max_retries: int | None = None
    ) -> dict:
        """Call Claude API with exponential backoff retry logic.

        Args:
            prompt: Prompt to send to Claude
            max_retries: Max retry attempts. Default: self.max_retries

        Returns:
            Parsed response dict

        Raises:
            Exception: After max_retries failed attempts
        """
        if max_retries is None:
            max_retries = self.max_retries

        last_exception = None

        for attempt in range(max_retries):
            try:
                response = await self._make_api_call(prompt)
                return response
            except Exception as e:
                last_exception = e
                if attempt < max_retries - 1:
                    wait_seconds = self.backoff_base ** attempt
                    logger.warning(
                        f"Attempt {attempt + 1} failed, retrying in {wait_seconds}s: {e}"
                    )
                    await asyncio.sleep(wait_seconds)
                else:
                    logger.error(f"All {max_retries} attempts failed")

        raise last_exception or Exception("API call failed after retries")

    async def _make_api_call(self, prompt: str) -> dict:
        """Make actual Claude API call and parse JSON response.

        Args:
            prompt: Prompt to send to Claude

        Returns:
            Parsed JSON response dict

        Raises:
            Exception: If API call fails or response is not valid JSON
        """
        # NTM_STUB_EXTERNAL: stubbed external call
        if stub_enabled():
            logger.info("Creative director LLM stubbed (NTM_STUB_EXTERNAL)")
            return {"concept": "Stub creative concept", "platform_variants": {}, "rationale": "stub"}

        message = await self.client.messages.create(
            model=self.model,
            max_tokens=2048,
            messages=[
                {
                    "role": "user",
                    "content": prompt
                }
            ]
        )

        # Extract text from response
        response_text = message.content[0].text

        # Parse JSON from response
        try:
            parsed = extract_json(response_text)
            return parsed
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON from Claude response: {response_text}")
            raise Exception(f"Invalid JSON in response: {e}")
