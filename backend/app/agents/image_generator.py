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
from datetime import datetime, timezone
from typing import Any, Literal, Optional

from anthropic import AsyncAnthropic
from pydantic import BaseModel, Field

from backend.app.tools import stability_ai

logger = logging.getLogger(__name__)

HAIKU_MODEL = "claude-haiku-4-5-20251001"
STABILITY_MODEL = "stability-sdxl"
DALLE_MODEL = "dall-e-3"
MAX_RETRIES = 2

IMAGE_DIMENSIONS: dict[str, tuple[int, int]] = {
    "square":    (1024, 1024),
    "landscape": (1344, 768),
    "portrait":  (768, 1344),
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
        default_factory=lambda: datetime.now(timezone.utc)
    )


# ---------------------------------------------------------------------------
# Agent
# ---------------------------------------------------------------------------

class ImageGeneratorAgent:
    """Generates images via Stability AI SDXL with DALL-E 3 fallback."""

    def __init__(self, api_key: Optional[str] = None, openai_client=None):
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
        palette_csv = ", ".join(brief.brand_palette) if brief.brand_palette else ""
        tone_csv = ", ".join(brief.tone_adjectives) if brief.tone_adjectives else ""

        base = f"{brief.visual_direction}."
        if palette_csv:
            base += f" Brand palette: {palette_csv}."
        if tone_csv:
            base += f" Tone: {tone_csv}."
        if brief.style_notes:
            base += f" {brief.style_notes}"

        try:
            response = await self.anthropic_client.messages.create(
                model=HAIKU_MODEL,
                max_tokens=300,
                system=(
                    "You are a text-to-image prompt engineer. Take the base description "
                    "and add precise photographic/artistic style tokens: lighting type, "
                    "camera angle, texture quality, render style. "
                    "Return ONLY the enriched prompt string, no explanation, under 200 words."
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
