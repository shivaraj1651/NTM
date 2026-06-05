"""Audio Generator Agent (AGT-10).

Takes an AudioGenerationBrief, selects a voice based on tone board, and
generates TTS audio. Primary: ElevenLabs (when ELEVENLABS_API_KEY is set).
Fallback: OpenAI TTS (when OPENAI_API_KEY is set, no ElevenLabs key needed).
"""

import asyncio
import logging
import os
import uuid
from datetime import UTC, datetime

from pydantic import BaseModel, Field

from backend.app.tools import elevenlabs

logger = logging.getLogger(__name__)

ELEVENLABS_MODEL = "eleven_multilingual_v2"
OPENAI_TTS_MODEL = "tts-1"
MAX_RETRIES = 3

# ElevenLabs voice IDs
VOICE_MAP: dict[str, str] = {
    "warm":          "21m00Tcm4TlvDq8ikWAM",  # Rachel
    "authoritative": "ErXwobaYiN019PkySvjV",  # Antoni
    "youthful":      "AZnzlk1XvdvUeBnXmlld",  # Domi
}

# OpenAI TTS voices (fallback when ElevenLabs key absent)
OPENAI_VOICE_MAP: dict[str, str] = {
    "warm":          "nova",       # warm, natural female
    "authoritative": "onyx",       # deep, authoritative male
    "youthful":      "shimmer",    # bright, energetic
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

        generation_id = str(uuid.uuid4())

        if elevenlabs.is_available():
            voice_id = VOICE_MAP[brief.voice_style]
            model_used = ELEVENLABS_MODEL
            audio_bytes = await self._elevenlabs_with_retry(brief.script_text, voice_id)
            logger.info("Audio generated via ElevenLabs voice_id=%s", voice_id)
        else:
            voice_id = OPENAI_VOICE_MAP[brief.voice_style]
            model_used = OPENAI_TTS_MODEL
            audio_bytes = await self._openai_tts_with_retry(brief.script_text, voice_id)
            logger.info("Audio generated via OpenAI TTS voice=%s", voice_id)

        duration_seconds = len(brief.script_text) / 150.0

        asset_url = ""
        if storage_client is not None:
            key = f"{brief.campaign_id}/{generation_id}.mp3"
            asset_url = await storage_client.upload(audio_bytes, key, content_type="audio/mpeg")

        output = AudioGenerationOutput(
            campaign_id=brief.campaign_id,
            generation_id=generation_id,
            tenant_id=brief.tenant_id,
            asset_url=asset_url,
            voice_id=voice_id,
            duration_seconds=duration_seconds,
            model_used=model_used,
            script_format=brief.script_format,
        )

        if db_session is not None:
            await self._persist(output, db_session)

        return output

    async def _elevenlabs_with_retry(self, script: str, voice_id: str) -> bytes:
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

    async def _openai_tts_with_retry(self, script: str, voice: str) -> bytes:
        import openai
        client = openai.AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"), timeout=60.0)
        last_exc: Exception | None = None
        for attempt in range(MAX_RETRIES):
            try:
                response = await client.audio.speech.create(
                    model=OPENAI_TTS_MODEL,
                    voice=voice,
                    input=script[:4096],  # OpenAI TTS limit
                    response_format="mp3",
                )
                return response.content
            except Exception as exc:
                last_exc = exc
                if attempt < MAX_RETRIES - 1:
                    wait = 2 ** attempt
                    logger.warning(
                        "OpenAI TTS attempt %d/%d failed (%s), retrying in %ds",
                        attempt + 1, MAX_RETRIES, exc, wait,
                    )
                    await asyncio.sleep(wait)
        raise last_exc or RuntimeError("OpenAI TTS failed after retries")

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
