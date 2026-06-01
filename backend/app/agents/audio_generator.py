"""Audio Generator Agent (AGT-10).

Takes an AudioGenerationBrief from AGT-08, selects an ElevenLabs voice based
on tone board, calls ElevenLabs TTS, uploads MP3 via injected storage client,
and returns the asset URL + metadata.
"""

import asyncio
import logging
import uuid
from datetime import UTC, datetime

from pydantic import BaseModel, Field

from backend.app.tools import elevenlabs

logger = logging.getLogger(__name__)

ELEVENLABS_MODEL = "eleven_multilingual_v2"
MAX_RETRIES = 3

VOICE_MAP: dict[str, str] = {
    "warm":          "21m00Tcm4TlvDq8ikWAM",  # Rachel
    "authoritative": "ErXwobaYiN019PkySvjV",  # Antoni
    "youthful":      "AZnzlk1XvdvUeBnXmlld",  # Domi
}


# ---------------------------------------------------------------------------
# Data models
# ---------------------------------------------------------------------------

class AudioGenerationBrief(BaseModel):
    campaign_id: str
    tenant_id: str
    script_text: str
    voice_style: str          # "warm" | "authoritative" | "youthful"
    script_format: str        # "radio" | "tvc_vo" | "social_video"
    campaign_theme: str = ""


class AudioGenerationOutput(BaseModel):
    campaign_id: str
    generation_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    tenant_id: str
    asset_url: str
    voice_id: str
    duration_seconds: float
    model_used: str
    script_format: str
    generated_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC)
    )


# ---------------------------------------------------------------------------
# Agent
# ---------------------------------------------------------------------------

class AudioGeneratorAgent:
    """Generates voiceover audio via ElevenLabs TTS."""

    async def generate(
        self,
        brief: AudioGenerationBrief,
        storage_client=None,
        db_session=None,
    ) -> AudioGenerationOutput:
        if brief.voice_style not in VOICE_MAP:
            raise ValueError(f"Unknown voice_style: {brief.voice_style!r}")

        voice_id = VOICE_MAP[brief.voice_style]
        generation_id = str(uuid.uuid4())

        audio_bytes = await self._generate_with_retry(brief.script_text, voice_id)
        duration_seconds = len(brief.script_text) / 150.0

        asset_url = ""
        if storage_client is not None:
            key = f"{brief.campaign_id}/{generation_id}.mp3"
            asset_url = await storage_client.upload(audio_bytes, key)

        output = AudioGenerationOutput(
            campaign_id=brief.campaign_id,
            generation_id=generation_id,
            tenant_id=brief.tenant_id,
            asset_url=asset_url,
            voice_id=voice_id,
            duration_seconds=duration_seconds,
            model_used=ELEVENLABS_MODEL,
            script_format=brief.script_format,
        )

        if db_session is not None:
            await self._persist(output, db_session)

        return output

    async def _generate_with_retry(self, script: str, voice_id: str) -> bytes:
        last_exc: Exception | None = None
        for attempt in range(MAX_RETRIES):
            try:
                return await elevenlabs.generate_vo(script, voice_id, ELEVENLABS_MODEL)
            except Exception as exc:
                last_exc = exc
                if attempt < MAX_RETRIES - 1:
                    wait = 2 ** attempt
                    logger.warning(
                        "ElevenLabs attempt %d/%d failed (%s), retrying in %ds",
                        attempt + 1, MAX_RETRIES, exc, wait,
                    )
                    await asyncio.sleep(wait)
        raise last_exc or RuntimeError("ElevenLabs failed after retries")

    async def _persist(self, output: AudioGenerationOutput, session) -> None:
        from backend.app.models.audio import GeneratedAudio

        row = GeneratedAudio(
            campaign_id=output.campaign_id,
            tenant_id=output.tenant_id,
            generation_id=output.generation_id,
            asset_url=output.asset_url,
            voice_id=output.voice_id,
            model_used=output.model_used,
            script_format=output.script_format,
            duration_seconds=output.duration_seconds,
        )
        session.add(row)
        await session.commit()
