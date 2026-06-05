"""Image Generator Agent (AGT-09).

Takes an ImageGenerationBrief, builds a context-rich prompt using:
  - The approved campaign concept (name, tagline, tone_board)
  - SerpAPI brand research (real taglines, product info, visual identity hints)
  - Claude Haiku for final prompt enrichment

Calls OpenAI DALL-E 3 as the primary model. No Stability AI.

Env vars:
  OPENAI_API_KEY    — required for DALL-E 3
  SERPAPI_API_KEY   — optional; enriches prompts with live brand data
"""

import base64
import logging
import os
import uuid
from datetime import UTC, datetime
from typing import Any

from anthropic import AsyncAnthropic
from pydantic import BaseModel, Field

from backend.app.external.stubs import stub_enabled
from backend.app.tools.serpapi import search_brand_info

logger = logging.getLogger(__name__)

HAIKU_MODEL  = "claude-haiku-4-5-20251001"
DALLE_MODEL  = "gpt-image-1"
MAX_RETRIES  = 2

# gpt-image-1 supported sizes per format
IMAGE_DIMENSIONS: dict[str, tuple[int, int]] = {
    "square":            (1024, 1024),
    "landscape":         (1536, 1024),
    "portrait":          (1024, 1536),
    "ooh_billboard":     (1536, 1024),
    "newspaper_insert":  (1024, 1536),
    "linkedin_post":     (1024, 1024),
}

# gpt-image-1 size strings accepted by the API
_DALLE_SIZE: dict[str, str] = {
    "square":            "1024x1024",
    "landscape":         "1536x1024",
    "portrait":          "1024x1536",
    "ooh_billboard":     "1536x1024",
    "newspaper_insert":  "1024x1536",
    "linkedin_post":     "1024x1024",
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
    # Concept context — populated from the user-approved campaign concept
    concept_name: str = ""
    concept_tagline: str = ""
    concept_tone: str = ""


class ImageGenerationOutput(BaseModel):
    campaign_id: str
    generation_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    tenant_id: str
    asset_url: str
    prompt_used: str
    model_used: str
    generation_params: dict[str, Any]
    image_format: str
    generated_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC)
    )


# ---------------------------------------------------------------------------
# Agent
# ---------------------------------------------------------------------------

class ImageGeneratorAgent:
    """Generates images via OpenAI DALL-E 3, enriched with concept + brand context."""

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

        img_bytes = await self._generate_image(prompt, brief.image_format)

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
            model_used=DALLE_MODEL,
            generation_params={
                "width": width,
                "height": height,
                "size": _DALLE_SIZE[brief.image_format],
                "quality": "hd",
            },
            image_format=brief.image_format,
        )

        if db_session is not None:
            await self._persist(output, db_session)

        return output

    # ------------------------------------------------------------------
    # Prompt construction
    # ------------------------------------------------------------------

    async def _build_prompt(self, brief: ImageGenerationBrief) -> str:
        """Build a rich, context-aware prompt using concept + SerpAPI brand data."""
        palette_csv  = ", ".join(brief.brand_palette) if brief.brand_palette else "bold brand colors"
        tone_csv     = ", ".join(brief.tone_adjectives) if brief.tone_adjectives else "premium, modern"
        brand_str    = f"for {brief.brand_name}" if brief.brand_name else ""
        audience_str = f"targeting {brief.target_audience}" if brief.target_audience else ""

        # Use concept tagline first, fall back to brief tagline
        effective_tagline = brief.concept_tagline or brief.tagline
        tagline_str = f'"{effective_tagline}"' if effective_tagline else ""
        msg_str = f'"{brief.master_message}"' if brief.master_message else ""

        # SerpAPI brand enrichment
        brand_context_str = ""
        if brief.brand_name:
            try:
                brand_info = await search_brand_info(brief.brand_name)
                real_taglines = brand_info.get("taglines", [])
                products      = brand_info.get("products", [])
                snippets      = brand_info.get("raw_snippets", [])

                parts = []
                if real_taglines and not effective_tagline:
                    # Use real brand tagline if concept didn't specify one
                    effective_tagline = real_taglines[0]
                    tagline_str = f'"{effective_tagline}"'
                    parts.append(f"brand tagline: {effective_tagline}")
                if products:
                    parts.append(f"products: {', '.join(products[:2])}")
                if snippets:
                    parts.append(snippets[0][:150])
                if parts:
                    brand_context_str = " | ".join(parts)
            except Exception as exc:
                logger.warning("SerpAPI brand search failed for image: %s", exc)

        # Concept context block
        concept_parts = []
        if brief.concept_name:
            concept_parts.append(f"Concept: '{brief.concept_name}'")
        if brief.concept_tone:
            concept_parts.append(f"Tone: {brief.concept_tone}")
        if brief.campaign_theme:
            concept_parts.append(f"Theme: {brief.campaign_theme}")
        concept_context = ". ".join(concept_parts)

        # Format-specific layout directive
        if brief.image_format == "ooh_billboard":
            hl = brief.headline_text or effective_tagline or brief.master_message
            headline_part = f'bold oversized headline text "{hl}", ' if hl else "bold oversized headline, "
            fmt_hint = (
                f"ultra-wide OOH billboard advertisement {brand_str}, "
                f"roadside hoarding seen from 50 metres, {headline_part}"
                f"massive high-contrast design, {palette_csv} color scheme, "
                f"aspirational hero image — {brief.visual_direction}, "
                f"minimal copy, maximum visual impact, photorealistic billboard quality, "
                f"city street perspective"
            )
        elif brief.image_format == "newspaper_insert":
            fmt_hint = (
                f"full-page broadsheet newspaper print advertisement {brand_str}, "
                f"portrait orientation, editorial newspaper layout, "
                f"serif headline typography space at top: {effective_tagline or brief.master_message}, "
                f"product hero image centre, CMYK-safe {palette_csv} color palette, "
                f"white margins with thin border rule, subheadline and body copy zones, "
                f"{brief.visual_direction}, premium print quality, "
                f"ink-on-paper aesthetic, broadsheet editorial design"
            )
        elif brief.image_format == "linkedin_post":
            fmt_hint = (
                f"professional LinkedIn social post image {brand_str}, "
                f"square format, corporate and aspirational, "
                f"clean white or brand-color background, "
                f"thought-leadership visual with bold typographic headline zone: {tagline_str}, "
                f"{palette_csv} accent, minimal and polished, "
                f"{brief.visual_direction}, "
                f"B2B audience, premium professional aesthetic, LinkedIn feed optimised"
            )
        elif brief.image_format == "landscape":
            fmt_hint = (
                f"wide horizontal 16:9 digital display ad {brand_str}, "
                f"digital billboard / DOOH screen, {brief.visual_direction}, "
                f"hero shot centre-right, text overlay zone left: tagline {tagline_str}, "
                f"{palette_csv} palette, clean premium layout"
            )
        elif brief.image_format == "portrait":
            fmt_hint = (
                f"vertical 9:16 mobile story ad {brand_str}, "
                f"Instagram/TikTok Story format, full-bleed {brief.visual_direction}, "
                f"lifestyle hero lower two-thirds, top third reserved for tagline {tagline_str}, "
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
            + (f"{concept_context}. " if concept_context else "")
            + (f"Brand context: {brand_context_str}. " if brand_context_str else "")
            + (f"Tagline: {tagline_str}. " if tagline_str else "")
            + (f"Core message: {msg_str}. " if msg_str else "")
            + (f"Product: {brief.product_details}. " if brief.product_details else "")
            + f"Visual direction: {brief.visual_direction}. "
            + (f"{audience_str}. " if audience_str else "")
            + f"Brand palette: {palette_csv}. Tone: {tone_csv}. "
            + f"Format: {fmt_hint}. "
            + "Style: REAL published advertising creative — NOT stock photo, NOT generic. "
            + "Bold composition, brand colors dominant, clear visual hierarchy, "
            + "commercial photography, high impact, sharp focus, professional studio lighting, "
            + "highly detailed, marketing poster aesthetic."
        )
        if brief.style_notes:
            base += f" Additional notes: {brief.style_notes}."

        if stub_enabled():
            logger.info("Image generator prompt-enrichment stubbed (NTM_STUB_EXTERNAL)")
            return base

        # Claude Haiku enriches the prompt for DALL-E 3
        try:
            response = await self.anthropic_client.messages.create(
                model=HAIKU_MODEL,
                max_tokens=400,
                system=(
                    "You are a senior advertising creative director and DALL-E 3 prompt engineer. "
                    "Transform the brief into a single precise text-to-image prompt that produces a "
                    "PROFESSIONAL PUBLISHED AD CREATIVE — never stock photography or generic imagery. "
                    f"Brand: {brief.brand_name or 'the brand'}. "
                    + (f"Concept: {brief.concept_name}. " if brief.concept_name else "")
                    + (f"Tagline: {effective_tagline!r}. " if effective_tagline else "")
                    + f"Campaign theme: {brief.campaign_theme}. "
                    "Requirements: brand colors dominant, dedicated text/headline space, "
                    "product or lifestyle hero shot, aspirational mood matching brand tone, "
                    "the tagline must be the central headline concept. "
                    "Append style tokens: highly detailed, commercial photography, "
                    "advertising creative, sharp focus, professional studio lighting, "
                    "brand identity, marketing poster aesthetic. "
                    "Return ONLY the enriched prompt string, under 250 words."
                ),
                messages=[{"role": "user", "content": base}],
            )
            return response.content[0].text.strip()
        except Exception as exc:
            logger.warning("Haiku prompt enrichment failed (%s), using base template", exc)
            return base

    # ------------------------------------------------------------------
    # DALL-E 3 generation
    # ------------------------------------------------------------------

    async def _generate_image(self, prompt: str, image_format: str) -> bytes:
        if stub_enabled():
            logger.info("Image generator _generate_image stubbed (NTM_STUB_EXTERNAL)")
            stub_png = base64.b64decode(
                "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwADhQGAWjR9awAAAABJRU5ErkJggg=="
            )
            return stub_png

        size = _DALLE_SIZE[image_format]
        client = self._get_openai_client()

        import asyncio
        last_exc: Exception | None = None
        for attempt in range(MAX_RETRIES):
            try:
                response = await client.images.generate(
                    model=DALLE_MODEL,
                    prompt=prompt,
                    size=size,
                    quality="medium",
                    n=1,
                )
                return base64.b64decode(response.data[0].b64_json)
            except Exception as exc:
                last_exc = exc
                if attempt < MAX_RETRIES - 1:
                    await asyncio.sleep(2 ** attempt)
                    logger.warning("gpt-image-1 attempt %d failed: %s", attempt + 1, exc)

        raise RuntimeError(f"gpt-image-1 failed after {MAX_RETRIES} attempts: {last_exc}")

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
