"""ElevenLabs text-to-speech tool."""

import logging
import os

import httpx

logger = logging.getLogger(__name__)

ELEVENLABS_API_URL = "https://api.elevenlabs.io/v1/text-to-speech/{voice_id}"


async def generate_vo(
    script: str,
    voice_id: str,
    model: str = "eleven_multilingual_v2",
) -> bytes:
    """Call ElevenLabs TTS and return raw MP3 bytes."""
    api_key = os.getenv("ELEVENLABS_API_KEY")
    if not api_key:
        raise RuntimeError("ELEVENLABS_API_KEY not set")

    url = ELEVENLABS_API_URL.format(voice_id=voice_id)
    payload = {
        "text": script,
        "model_id": model,
        "voice_settings": {"stability": 0.5, "similarity_boost": 0.75},
    }

    async with httpx.AsyncClient(timeout=60.0) as client:
        response = await client.post(
            url,
            headers={
                "xi-api-key": api_key,
                "Content-Type": "application/json",
                "Accept": "audio/mpeg",
            },
            json=payload,
        )

    if response.status_code != 200:
        raise RuntimeError(
            f"ElevenLabs returned {response.status_code}: {response.text}"
        )

    return response.content
