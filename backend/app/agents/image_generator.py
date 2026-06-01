"""Image Generator Agent (AGT-09).

Takes an ImageGenerationBrief, builds an optimised T2I prompt via hybrid
Claude Haiku enrichment, calls Stability AI SDXL (with DALL-E 3 fallback),
uploads the result via an injected storage client, and returns the asset URL.
"""

import asyncio
import base64
import logging
import os
import uuid
from datetime import UTC, datetime
from typing import Any, Literal

from anthropic import AsyncAnthropic
from pydantic import BaseModel, Field

from backend.app.external.stubs import stub_enabled
from backend.app.tools import stability_ai

logger = logging.getLogger(__name__)

HAIKU_MODEL = "claude-haiku-4-5-20251001"
STABILITY_MODEL = "stability-sdxl"
DALLE_MODEL = "dall-e-3"
MAX_RETRIES = 2

IMAGE_DIMENSIONS: dict[str, tuple[int, int]] = {
    "square":        (1024, 1024),
    "landscape":     (1344, 768),
    "portrait":      (768, 1344),
    "ooh_billboard": (1344, 768),
}


# ---------------------------------------------------------------------------
# Data models
# ---------------------------------------------------------------------------

class ImageGenerationBrief(BaseModel):
    campaign_id: str
    tenant_id: str
    image_format: str
    visual_direction: str
    brand_palette: list[str] = Field(default_factory=list)
    tone_adjectives: list[str] = Field(default_factory=list)
    campaign_theme: str
    style_notes: str = ""
    brand_name: str = ""
    product_details: str = ""
    target_audience: str = ""
    headline_text: str = ""
    tagline: str = ""
    master_message: str = ""


class ImageGenerationOutput(BaseModel):
    campaign_id: str
    generation_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    tenant_id: str
    asset_url: str
    prompt_used: str
    model_used: Literal["stability-sdxl", "dall-e-3"]
    generation_params: dict[str, Any]
    image_format: str
    generated_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC)
    )


# ---------------------------------------------------------------------------
# Agent
# ---------------------------------------------------------------------------

class ImageGeneratorAgent:
    """Generates images via Stability AI SDXL with DALL-E 3 fallback."""

    def __init__(self, api_key: str | None = None, openai_client=None):
        self.anthropic_client = AsyncAnthropic(api_key=api_key)
        self._openai_client = openai_client

    async def generate(
        self,
        brief: ImageGenerationBrief,
        storage_client=None,
        db_session=None,
    ) -> ImageGenerationOutput:
        if brief.image_format not in IMAGE_DIMENSIONS:
            raise ValueError(f"Unknown image_format: {brief.image_format!r}")

        width, height = IMAGE_DIMENSIONS[brief.image_format]
        prompt = await self._build_prompt(brief)
        generation_id = str(uuid.uuid4())

        img_bytes, model_used = await self._generate_image(prompt, width, height)

        asset_url = ""
        if storage_client is not None:
            key = f"{brief.campaign_id}/{generation_id}.png"
            asset_url = await storage_client.upload(img_bytes, key)

        output = ImageGenerationOutput(
            campaign_id=brief.campaign_id,
            generation_id=generation_id,
            tenant_id=brief.tenant_id,
            asset_url=asset_url,
            prompt_used=prompt,
            model_used=model_used,
            generation_params={"width": width, "height": height, "steps": 30, "cfg_scale": 7.0},
            image_format=brief.image_format,
        )

        if db_session is not None:
            await self._persist(output, db_session)

        return output

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    async def _build_prompt(self, brief: ImageGenerationBrief) -> str:
        palette_csv  = ", ".join(brief.brand_palette) if brief.brand_palette else "bold brand colors"
        tone_csv     = ", ".join(brief.tone_adjectives) if brief.tone_adjectives else "premium, modern"
        brand_str    = f"for {brief.brand_name}" if brief.brand_name else ""
        product_str  = f"featuring {brief.product_details}" if brief.product_details else ""
        audience_str = f"targeting {brief.target_audience}" if brief.target_audience else ""
        tagline_str  = f'"{brief.tagline}"' if brief.tagline else ""
        msg_str      = f'"{brief.master_message}"' if brief.master_message else ""

        if brief.image_format == "ooh_billboard":
            # Concept tagline IS the billboard headline — display it large
            hl = brief.headline_text or brief.tagline or brief.master_message
            headline_part = f'with bold oversized headline text "{hl}", ' if hl else "with bold oversized headline text area, "
            fmt_hint = (
                f"ultra-wide outdoor OOH billboard advertisement {brand_str}, "
                f"roadside hoarding poster seen from 50 meters, {headline_part}"
                f"massive high-contrast design, {palette_csv} color scheme, "
                f"aspirational hero image — {brief.visual_direction}, "
                f"minimal copy, maximum visual impact, photorealistic billboard printing quality, "
                f"architectural scale, city street perspective"
            )
        elif brief.image_format == "landscape":
            fmt_hint = (
                f"wide horizontal digital display ad {brand_str}, 16:9 landscape format, "
                f"digital billboard / DOOH screen, {brief.visual_direction}, "
                f"product or lifestyle hero shot center-right, "
                f"text overlay zone on left: tagline {tagline_str}, "
                f"{palette_csv} dominant palette, clean premium layout"
            )
        elif brief.image_format == "portrait":
            fmt_hint = (
                f"vertical 9:16 mobile story advertisement {brand_str}, "
                f"Instagram/TikTok story format, full-bleed {brief.visual_direction}, "
                f"lifestyle hero shot lower two-thirds, top third reserved for tagline {tagline_str}, "
                f"{palette_csv}, bold typography space"
            )
        else:  # square
            fmt_hint = (
                f"square 1:1 social media ad {brand_str}, Instagram/Facebook feed post, "
                f"{brief.visual_direction}, product or lifestyle centred, "
                f"tagline {tagline_str} text overlay, {palette_csv}, "
                f"clean brand composition, high-contrast"
            )

        base = (
            f"Professional advertising creative {brand_str}. "
            f"Campaign: {brief.campaign_theme}. "
            + (f"Tagline: {tagline_str}. " if tagline_str else "")
            + (f"Core message: {msg_str}. " if msg_str else "")
            + (f"{product_str}. " if product_str else "")
            + f"Visual direction: {brief.visual_direction}. "
            + (f"{audience_str}. " if audience_str else "")
            + f"Brand palette: {palette_csv}. Tone: {tone_csv}. "
            + f"Format: {fmt_hint}. "
            + "Style: REAL published advertising creative — NOT stock photo, NOT generic. "
            + "Bold composition, brand colors dominant, clear visual hierarchy, "
            + "commercial photography, high impact, sharp focus, professional studio lighting, "
            + "highly detailed, 8K UHD, marketing poster aesthetic."
        )
        if brief.style_notes:
            base += f" Competitor context: {brief.style_notes}."

        # NTM_STUB_EXTERNAL: stubbed external call
        if stub_enabled():
            logger.info("Image generator prompt-enrichment LLM stubbed (NTM_STUB_EXTERNAL)")
            return base

        try:
            response = await self.anthropic_client.messages.create(
                model=HAIKU_MODEL,
                max_tokens=400,
                system=(
                    "You are a senior advertising creative director and Stability AI prompt engineer. "
                    "Transform the brief into a single precise text-to-image prompt that produces a "
                    "PROFESSIONAL PUBLISHED AD CREATIVE — never stock photography or generic imagery. "
                    f"Brand: {brief.brand_name or 'the brand'}. "
                    f"Tagline: {brief.tagline!r}. "
                    f"Campaign: {brief.campaign_theme}. "
                    "Requirements: brand colors dominant, dedicated text/headline space, "
                    "product or lifestyle hero shot, aspirational mood matching brand tone, "
                    "the tagline must be embedded as the central headline concept. "
                    "Append style tokens: highly detailed, 8K UHD, commercial photography, "
                    "advertising creative, sharp focus, professional studio lighting, "
                    "brand identity, marketing poster aesthetic. "
                    "Return ONLY the enriched prompt string, under 220 words."
                ),
                messages=[{"role": "user", "content": base}],
            )
            return response.content[0].text.strip()
        except Exception as exc:
            logger.warning("Haiku prompt enrichment failed (%s), using base template", exc)
            return base

    async def _generate_image(
        self, prompt: str, width: int, height: int
    ) -> tuple[bytes, str]:
        # NTM_STUB_EXTERNAL: stubbed external call — return 1x1 white PNG, no real API call
        if stub_enabled():
            logger.info("Image generator _generate_image stubbed (NTM_STUB_EXTERNAL)")
            import base64 as _b64
            # Minimal 1x1 white PNG (67 bytes)
            stub_png = _b64.b64decode(
                "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwADhQGAWjR9awAAAABJRU5ErkJggg=="
            )
            return stub_png, "stub"

        # Primary: Stability AI
        for attempt in range(MAX_RETRIES):
            try:
                img_bytes = await stability_ai.generate_image(prompt, width=width, height=height)
                return img_bytes, STABILITY_MODEL
            except Exception as exc:
                if attempt < MAX_RETRIES - 1:
                    await asyncio.sleep(2 ** attempt)
                    logger.warning("Stability attempt %d failed: %s", attempt + 1, exc)
                else:
                    logger.warning("Stability exhausted retries, falling back to DALL-E 3")

        # Fallback: DALL-E 3
        for attempt in range(MAX_RETRIES):
            try:
                img_bytes = await self._dalle_generate(prompt, width, height)
                return img_bytes, DALLE_MODEL
            except Exception as exc:
                if attempt < MAX_RETRIES - 1:
                    await asyncio.sleep(2 ** attempt)
                    logger.warning("DALL-E attempt %d failed: %s", attempt + 1, exc)

        raise RuntimeError("All image generation providers failed")

    async def _dalle_generate(self, prompt: str, width: int, height: int) -> bytes:
        client = self._get_openai_client()
        response = await client.images.generate(
            model=DALLE_MODEL,
            prompt=prompt,
            size=f"{width}x{height}",
            response_format="b64_json",
        )
        return base64.b64decode(response.data[0].b64_json)

    def _get_openai_client(self):
        if self._openai_client is not None:
            return self._openai_client
        import openai
        return openai.AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))

    async def _persist(self, output: ImageGenerationOutput, session) -> None:
        from backend.app.models.image import GeneratedImage

        row = GeneratedImage(
            campaign_id=output.campaign_id,
            tenant_id=output.tenant_id,
            generation_id=output.generation_id,
            asset_url=output.asset_url,
            prompt_used=output.prompt_used,
            model_used=output.model_used,
            generation_params=output.generation_params,
            image_format=output.image_format,
        )
        session.add(row)
        await session.commit()
