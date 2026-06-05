"""Video Generator Agent (AGT-11).

Takes a VideoGenerationBrief, submits a Kling AI video generation task, polls
for completion, downloads the MP4, uploads via injected storage client, and
returns the asset URL + metadata.

Before generating, enriches the prompt with:
  - The approved campaign concept (name, tagline, tone_board, channels)
  - SerpAPI brand research (company taglines, products, recent campaigns)

Kling unavailability yields status="manual_production_required" instead of raising.

Env vars:
  KLING_AI_ACCESS_KEY, KLING_AI_SECRET_KEY  — required for video generation
  SERPAPI_API_KEY                            — optional; enriches prompts with brand data
"""

import asyncio
import logging
import uuid
from datetime import UTC, datetime

import httpx
from pydantic import BaseModel, Field

from backend.app.external.stubs import stub_enabled
from backend.app.tools import kling_ai
from backend.app.tools.serpapi import search_brand_info

logger = logging.getLogger(__name__)

KLING_MODEL           = "kling-v1"
MAX_RETRIES           = 2
MAX_POLL_ATTEMPTS     = 36   # 36 × 10s = 6 minutes — Kling takes up to 5 min
POLL_INTERVAL_SECONDS = 10
STATUS_COMPLETED      = "completed"
STATUS_MANUAL         = "manual_production_required"


# ---------------------------------------------------------------------------
# Data models
# ---------------------------------------------------------------------------

class VideoGenerationBrief(BaseModel):
    campaign_id: str
    tenant_id: str
    prompt: str
    script_text: str
    reference_image_url: str | None = None
    duration_seconds: int = 5
    script_format: str = "social_video"
    # Concept context — populated from the user-approved campaign concept
    campaign_theme: str = ""
    concept_name: str = ""
    concept_tagline: str = ""
    concept_tone: str = ""
    # Brand context
    brand_name: str = ""
    target_audience: str = ""


class VideoGenerationOutput(BaseModel):
    campaign_id: str
    generation_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    tenant_id: str
    asset_url: str
    job_id: str
    model_used: str
    duration_seconds: int
    status: str
    script_format: str
    generated_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC)
    )


# ---------------------------------------------------------------------------
# Agent
# ---------------------------------------------------------------------------

class VideoGeneratorAgent:
    """Generates video via Kling AI, enriched with concept context and brand research."""

    async def generate(
        self,
        brief: VideoGenerationBrief,
        storage_client=None,
        db_session=None,
    ) -> VideoGenerationOutput:
        generation_id = str(uuid.uuid4())

        if stub_enabled():
            logger.info("VideoGeneratorAgent stubbed (NTM_STUB_EXTERNAL)")
            output = VideoGenerationOutput(
                campaign_id=brief.campaign_id,
                generation_id=generation_id,
                tenant_id=brief.tenant_id,
                asset_url="",
                job_id="stub",
                model_used=KLING_MODEL,
                duration_seconds=brief.duration_seconds,
                status=STATUS_MANUAL,
                script_format=brief.script_format,
            )
            if db_session is not None:
                await self._persist(output, db_session)
            return output

        # Enrich prompt with brand research + concept context
        enriched_prompt = await self._build_prompt(brief)

        # Submit Kling job with retry
        job_id = ""
        task_type = "text2video"
        try:
            job_id, task_type = await self._submit_with_retry(brief, enriched_prompt)
        except Exception as exc:
            logger.warning("Kling AI submit failed after retries: %s", exc)
            output = VideoGenerationOutput(
                campaign_id=brief.campaign_id,
                generation_id=generation_id,
                tenant_id=brief.tenant_id,
                asset_url="",
                job_id="",
                model_used=KLING_MODEL,
                duration_seconds=brief.duration_seconds,
                status=STATUS_MANUAL,
                script_format=brief.script_format,
            )
            if db_session is not None:
                await self._persist(output, db_session)
            return output

        # Poll for completion URL using the correct endpoint for the task type
        completion_url = await self._poll_for_completion(job_id, task_type)
        if completion_url is None:
            logger.warning("Kling AI poll timed out or failed for task %s", job_id)
            output = VideoGenerationOutput(
                campaign_id=brief.campaign_id,
                generation_id=generation_id,
                tenant_id=brief.tenant_id,
                asset_url="",
                job_id=job_id,
                model_used=KLING_MODEL,
                duration_seconds=brief.duration_seconds,
                status=STATUS_MANUAL,
                script_format=brief.script_format,
            )
            if db_session is not None:
                await self._persist(output, db_session)
            return output

        # Download MP4 bytes from Kling CDN
        async with httpx.AsyncClient(timeout=120.0) as client:
            resp = await client.get(completion_url)
        video_bytes = resp.content

        # Upload to storage
        asset_url = ""
        if storage_client is not None:
            key = f"{brief.campaign_id}/{generation_id}.mp4"
            asset_url = await storage_client.upload(video_bytes, key)

        output = VideoGenerationOutput(
            campaign_id=brief.campaign_id,
            generation_id=generation_id,
            tenant_id=brief.tenant_id,
            asset_url=asset_url,
            job_id=job_id,
            model_used=KLING_MODEL,
            duration_seconds=brief.duration_seconds,
            status=STATUS_COMPLETED,
            script_format=brief.script_format,
        )

        if db_session is not None:
            await self._persist(output, db_session)

        return output

    # ------------------------------------------------------------------
    # Prompt enrichment
    # ------------------------------------------------------------------

    async def _build_prompt(self, brief: VideoGenerationBrief) -> str:
        """Build a context-rich video prompt from concept + brand research."""
        # Fetch brand info from SerpAPI if brand name is available
        brand_context = ""
        if brief.brand_name:
            try:
                brand_info = await search_brand_info(brief.brand_name)
                taglines = brand_info.get("taglines", [])
                products = brand_info.get("products", [])
                snippets = brand_info.get("raw_snippets", [])

                if taglines:
                    brand_context += f"Brand slogans/taglines: {'; '.join(taglines[:3])}. "
                if products:
                    brand_context += f"Products/offerings: {'; '.join(products[:2])}. "
                if snippets:
                    brand_context += f"Brand context: {snippets[0][:200]}. "
            except Exception as exc:
                logger.warning("SerpAPI brand search failed: %s", exc)

        # Build concept context
        concept_parts = []
        if brief.concept_name:
            concept_parts.append(f"Campaign concept: '{brief.concept_name}'")
        if brief.concept_tagline:
            concept_parts.append(f"Tagline: \"{brief.concept_tagline}\"")
        if brief.campaign_theme:
            concept_parts.append(f"Theme: {brief.campaign_theme}")
        if brief.concept_tone:
            concept_parts.append(f"Tone: {brief.concept_tone}")
        if brief.target_audience:
            concept_parts.append(f"Audience: {brief.target_audience}")
        concept_context = ". ".join(concept_parts)

        # Base script text
        script_excerpt = brief.script_text[:400] if brief.script_text else brief.prompt

        prompt = (
            f"Cinematic advertising video for {brief.brand_name or 'the brand'}. "
            + (f"{brand_context}" if brand_context else "")
            + (f"{concept_context}. " if concept_context else "")
            + f"Script: {script_excerpt}. "
            + f"Format: {brief.script_format.replace('_', ' ')}. "
            + "Style: professional advertising creative, broadcast quality, "
            + "brand colors prominent, aspirational visuals, "
            + "cinematic lighting, sharp focus, 4K resolution. "
            + "NOT generic stock footage — brand-specific storytelling."
        )

        return prompt

    # ------------------------------------------------------------------
    # Kling API calls
    # ------------------------------------------------------------------

    async def _submit_with_retry(self, brief: VideoGenerationBrief, prompt: str) -> tuple[str, str]:
        """Returns (task_id, task_type)."""
        last_exc: Exception | None = None
        for attempt in range(MAX_RETRIES):
            try:
                return await kling_ai.generate_video(
                    prompt=prompt,
                    image_url=brief.reference_image_url,
                    duration=brief.duration_seconds,
                    model=KLING_MODEL,
                )
            except Exception as exc:
                last_exc = exc
                if attempt < MAX_RETRIES - 1:
                    wait = 2 ** attempt
                    logger.warning(
                        "Kling AI submit attempt %d/%d failed (%s), retrying in %ds",
                        attempt + 1, MAX_RETRIES, exc, wait,
                    )
                    await asyncio.sleep(wait)
        raise last_exc or RuntimeError("Kling AI submit failed after retries")

    async def _poll_for_completion(self, task_id: str, task_type: str = "text2video") -> str | None:
        """Poll until SUCCEEDED (returns URL) or FAILED/timeout (returns None)."""
        for _ in range(MAX_POLL_ATTEMPTS):
            try:
                result = await kling_ai.get_video_status(task_id, task_type)
            except Exception as exc:
                logger.warning("Kling AI status check error: %s", exc)
                await asyncio.sleep(POLL_INTERVAL_SECONDS)
                continue
            status = result.get("status", "PENDING")
            if status == "SUCCEEDED":
                return result.get("url")
            if status == "FAILED":
                return None
            await asyncio.sleep(POLL_INTERVAL_SECONDS)
        return None

    async def _persist(self, output: VideoGenerationOutput, session) -> None:
        from backend.app.models.video import GeneratedVideo

        row = GeneratedVideo(
            campaign_id=output.campaign_id,
            tenant_id=output.tenant_id,
            generation_id=output.generation_id,
            asset_url=output.asset_url,
            job_id=output.job_id,
            model_used=output.model_used,
            script_format=output.script_format,
            duration_seconds=float(output.duration_seconds),
            status=output.status,
        )
        session.add(row)
        await session.commit()
