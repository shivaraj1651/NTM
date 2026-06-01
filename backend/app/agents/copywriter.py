"""Copywriter Agent (AGT-07).

Receives a CreativeBrief from AGT-06 and generates marketing copy for 7 asset
types (2 A/B variants each) via 7 concurrent Claude API calls.
"""

import asyncio
import json
import logging
import uuid
from backend.app.agents.json_parsing import extract_json
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Optional

from anthropic import AsyncAnthropic
from pydantic import BaseModel, Field
from backend.app.external.stubs import stub_enabled

logger = logging.getLogger(__name__)

MODEL = "claude-sonnet-4-6"
TEMPERATURE = 0.8
MAX_RETRIES = 3


# ---------------------------------------------------------------------------
# Asset configuration
# ---------------------------------------------------------------------------

@dataclass
class AssetConfig:
    constraints: str
    content_fields: list[str]
    prompt_hint: str


ASSET_CONFIGS: dict[str, AssetConfig] = {
    "social_caption": AssetConfig(
        constraints="Maximum 280 characters. Include relevant hashtags.",
        content_fields=["text"],
        prompt_hint="Write a social media caption optimised for engagement and shareability.",
    ),
    "headline": AssetConfig(
        constraints="Maximum 10 words. Punchy, attention-grabbing hook.",
        content_fields=["text"],
        prompt_hint="Write a short, punchy headline that stops the scroll.",
    ),
    "body_copy": AssetConfig(
        constraints="50 to 150 words. Lead with the core benefit, not features.",
        content_fields=["text"],
        prompt_hint="Write benefit-led body copy that builds desire and drives action.",
    ),
    "print_ad": AssetConfig(
        constraints=(
            "Headline ≤10 words. Subhead ≤15 words. Body ≤50 words. CTA ≤5 words."
        ),
        content_fields=["headline", "subhead", "body", "cta"],
        prompt_hint="Write a complete print advertisement with all four components.",
    ),
    "email": AssetConfig(
        constraints="Subject line ≤60 characters. Body 100–200 words.",
        content_fields=["subject", "body"],
        prompt_hint="Write a compelling email subject line and body.",
    ),
    "ooh_billboard": AssetConfig(
        constraints=(
            "Headline MAXIMUM 7 WORDS — this is a hard limit. "
            "Include a brief visual hook note (one sentence)."
        ),
        content_fields=["headline", "visual_note"],
        prompt_hint=(
            "Write ultra-concise outdoor billboard copy. "
            "The headline MUST be 7 words or fewer — no exceptions."
        ),
    ),
    "influencer_brief": AssetConfig(
        constraints=(
            "Key message: 1 sentence. "
            "Talking points: exactly 3 bullet strings. "
            "Dos: exactly 3 items. "
            "Don'ts: exactly 3 items."
        ),
        content_fields=["key_message", "talking_points", "dos", "donts"],
        prompt_hint="Write a structured influencer brief with clear do/don't guidance.",
    ),
}


# ---------------------------------------------------------------------------
# Data models
# ---------------------------------------------------------------------------

class CreativeBrief(BaseModel):
    """Input to AGT-07, assembled by the caller from AGT-06 output."""

    campaign_id: str
    tenant_id: str
    core_concept: str
    tone_adjectives: list[str]
    visual_direction: str
    brand_voice: str
    campaign_theme: str
    primary_cta: str
    target_audience: str
    product_details: str
    messaging_rules: list[str]
    tagline: str = ""
    master_message: str = ""


class CopyVariant(BaseModel):
    variant_id: str
    content: dict[str, Any]
    word_count: int
    rationale: str


class AssetCopy(BaseModel):
    asset_type: str
    variants: list[CopyVariant]


class CopyOutput(BaseModel):
    campaign_id: str
    generation_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    tenant_id: str
    generated_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )
    assets: list[AssetCopy]
    model_used: str = MODEL
    errors: list[str] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Agent
# ---------------------------------------------------------------------------

class CopywriterAgent:
    """Generates A/B copy variants for 7 asset types via concurrent LLM calls."""

    def __init__(self, api_key: Optional[str] = None):
        self.client = AsyncAnthropic(api_key=api_key)
        self.model = MODEL

    async def generate(
        self, brief: CreativeBrief, db_session=None
    ) -> CopyOutput:
        """Generate copy for all asset types and optionally persist to DB."""
        generation_id = str(uuid.uuid4())
        system_prompt = self._build_system_prompt(brief)

        results = await asyncio.gather(
            *[
                self._generate_asset(asset_type, brief, system_prompt)
                for asset_type in ASSET_CONFIGS
            ],
            return_exceptions=True,
        )

        assets: list[AssetCopy] = []
        errors: list[str] = []
        for asset_type, result in zip(ASSET_CONFIGS.keys(), results):
            if isinstance(result, Exception):
                logger.error("Failed to generate %s: %s", asset_type, result)
                errors.append(f"{asset_type}: {result}")
                assets.append(AssetCopy(asset_type=asset_type, variants=[]))
            else:
                assets.append(result)

        output = CopyOutput(
            campaign_id=brief.campaign_id,
            generation_id=generation_id,
            tenant_id=brief.tenant_id,
            assets=assets,
            errors=errors,
        )

        if db_session is not None:
            await self._persist(output, db_session)

        return output

    def _build_system_prompt(self, brief: CreativeBrief) -> str:
        rules = "\n".join(f"- {r}" for r in brief.messaging_rules) or "- Stay on-brand and benefit-led."
        adjectives = ", ".join(brief.tone_adjectives) or "professional, engaging"
        tagline_line = f"\nTagline (THE anchor — every asset must feel like it belongs to this line): {brief.tagline}" if brief.tagline else ""
        master_line  = f"\nMaster Message (core copy idea): {brief.master_message}" if brief.master_message else ""
        return f"""You are a world-class advertising copywriter.

## Brand Voice
{brief.brand_voice or "Professional, clear, and benefit-led."}

## Selected Campaign Concept
Name: {brief.core_concept}
Theme: {brief.campaign_theme}{tagline_line}{master_line}

## Tone Board
Adjectives: {adjectives}
Visual Direction: {brief.visual_direction}

## Campaign Details
Product/Service: {brief.product_details}
Target Audience: {brief.target_audience}
Primary CTA: {brief.primary_cta}

## Messaging Rules (MUST follow ALL)
{rules}

CRITICAL: All copy variants must be grounded in the selected concept — the tagline and master message above are the strategic north star. Every asset must feel like it belongs to the same campaign."""

    async def _generate_asset(
        self,
        asset_type: str,
        brief: CreativeBrief,
        system_prompt: str,
    ) -> AssetCopy:
        config = ASSET_CONFIGS[asset_type]
        fields_example = ", ".join(f'"{f}": "..."' for f in config.content_fields)

        user_message = f"""Generate 2 A/B copy variants for this asset type.

## Asset Type: {asset_type.upper().replace("_", " ")}
{config.prompt_hint}

## Constraints
{config.constraints}

## Campaign Details
Primary CTA: {brief.primary_cta}

## Required Output Format
Return ONLY valid JSON (no markdown, no code blocks):
{{
  "variants": [
    {{
      "variant_id": "A",
      "content": {{{fields_example}}},
      "rationale": "Why Variant A works"
    }},
    {{
      "variant_id": "B",
      "content": {{{fields_example}}},
      "rationale": "Why Variant B is different"
    }}
  ]
}}"""

        raw = await self._call_with_retry(system_prompt, user_message)

        variants: list[CopyVariant] = []
        for v in raw.get("variants", []):
            content = v.get("content", {})
            all_text = " ".join(
                " ".join(val) if isinstance(val, list) else str(val)
                for val in content.values()
            )
            variants.append(
                CopyVariant(
                    variant_id=v.get("variant_id", ""),
                    content=content,
                    word_count=len(all_text.split()),
                    rationale=v.get("rationale", ""),
                )
            )

        return AssetCopy(asset_type=asset_type, variants=variants)

    async def _call_with_retry(self, system_prompt: str, user_message: str) -> dict:
        # NTM_STUB_EXTERNAL: stubbed external call
        if stub_enabled():
            logger.info("Copywriter LLM stubbed (NTM_STUB_EXTERNAL)")
            return {"variants": [{"copy": "Stub copy variant A.", "rationale": "stub"}, {"copy": "Stub copy variant B.", "rationale": "stub"}]}
        last_exc: Optional[Exception] = None
        for attempt in range(MAX_RETRIES):
            try:
                response = await self.client.messages.create(
                    model=self.model,
                    max_tokens=2048,
                    temperature=TEMPERATURE,
                    system=system_prompt,
                    messages=[{"role": "user", "content": user_message}],
                )
                return extract_json(response.content[0].text)
            except Exception as exc:
                last_exc = exc
                if attempt < MAX_RETRIES - 1:
                    wait = 2 ** attempt
                    logger.warning(
                        "Attempt %d/%d failed (%s), retrying in %ds",
                        attempt + 1,
                        MAX_RETRIES,
                        exc,
                        wait,
                    )
                    await asyncio.sleep(wait)
        raise last_exc or Exception("API call failed after retries")

    async def _persist(self, output: CopyOutput, session) -> None:
        from backend.app.models.copy import GeneratedCopy

        for asset in output.assets:
            for variant in asset.variants:
                row = GeneratedCopy(
                    campaign_id=output.campaign_id,
                    tenant_id=output.tenant_id,
                    generation_id=output.generation_id,
                    asset_type=asset.asset_type,
                    variant_id=variant.variant_id,
                    content=variant.content,
                    word_count=variant.word_count,
                    model_used=output.model_used,
                )
                session.add(row)
        await session.commit()
