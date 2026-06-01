"""Video Generator Agent (AGT-11).

Takes a VideoGenerationBrief, submits a Runway ML Gen-3 job, polls for
completion, downloads the MP4, uploads via injected storage client, and
returns the asset URL + metadata. Runway unavailability yields
status="manual_production_required" instead of raising.
"""

import asyncio
import logging
import uuid
from datetime import UTC, datetime

import httpx
from pydantic import BaseModel, Field

from backend.app.tools import runway

logger = logging.getLogger(__name__)

RUNWAY_MODEL          = "gen3a_turbo"
MAX_RETRIES           = 2
MAX_POLL_ATTEMPTS     = 10
POLL_INTERVAL_SECONDS = 6
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
    campaign_theme: str = ""


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
    """Generates video via Runway ML Gen-3."""

    async def generate(
        self,
        brief: VideoGenerationBrief,
        storage_client=None,
        db_session=None,
    ) -> VideoGenerationOutput:
        generation_id = str(uuid.uuid4())

        # Submit job with retry
        job_id = ""
        try:
            job_id = await self._submit_with_retry(brief)
        except Exception as exc:
            logger.warning("Runway submit failed after retries: %s", exc)
            output = VideoGenerationOutput(
                campaign_id=brief.campaign_id,
                generation_id=generation_id,
                tenant_id=brief.tenant_id,
                asset_url="",
                job_id="",
                model_used=RUNWAY_MODEL,
                duration_seconds=brief.duration_seconds,
                status=STATUS_MANUAL,
                script_format=brief.script_format,
            )
            if db_session is not None:
                await self._persist(output, db_session)
            return output

        # Poll for completion URL
        completion_url = await self._poll_for_completion(job_id)
        if completion_url is None:
            logger.warning("Runway poll timed out or failed for job %s", job_id)
            output = VideoGenerationOutput(
                campaign_id=brief.campaign_id,
                generation_id=generation_id,
                tenant_id=brief.tenant_id,
                asset_url="",
                job_id=job_id,
                model_used=RUNWAY_MODEL,
                duration_seconds=brief.duration_seconds,
                status=STATUS_MANUAL,
                script_format=brief.script_format,
            )
            if db_session is not None:
                await self._persist(output, db_session)
            return output

        # Download MP4 bytes from Runway CDN
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
            model_used=RUNWAY_MODEL,
            duration_seconds=brief.duration_seconds,
            status=STATUS_COMPLETED,
            script_format=brief.script_format,
        )

        if db_session is not None:
            await self._persist(output, db_session)

        return output

    async def _submit_with_retry(self, brief: VideoGenerationBrief) -> str:
        last_exc: Exception | None = None
        for attempt in range(MAX_RETRIES):
            try:
                return await runway.generate_video(
                    brief.prompt,
                    brief.reference_image_url,
                    brief.duration_seconds,
                )
            except Exception as exc:
                last_exc = exc
                if attempt < MAX_RETRIES - 1:
                    wait = 2 ** attempt
                    logger.warning(
                        "Runway submit attempt %d/%d failed (%s), retrying in %ds",
                        attempt + 1, MAX_RETRIES, exc, wait,
                    )
                    await asyncio.sleep(wait)
        raise last_exc or RuntimeError("Runway submit failed after retries")

    async def _poll_for_completion(self, job_id: str) -> str | None:
        """Poll until SUCCEEDED (returns URL) or FAILED/timeout (returns None)."""
        for _ in range(MAX_POLL_ATTEMPTS):
            result = await runway.get_video_status(job_id)
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
