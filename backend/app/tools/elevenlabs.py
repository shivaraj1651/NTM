"""ElevenLabs text-to-speech tool."""

import logging
import os

import httpx

logger = logging.getLogger(__name__)

ELEVENLABS_API_URL = "https://api.elevenlabs.io/v1/text-to-speech/{voice_id}"

# Minimal valid MP3 (silent frame) used as placeholder when API key is absent.
# ID3v2 header + one silent MPEG1 Layer3 frame at 128kbps 44.1kHz mono.
_SILENT_MP3_PLACEHOLDER = (
    b"ID3\x03\x00\x00\x00\x00\x00\x00"   # ID3v2 header (10 bytes, empty tags)
    + b"\xff\xfb\x90\x00"                   # MPEG1 Layer3 frame header
    + b"\x00" * 413                          # silent frame data
)


def is_available() -> bool:
    """Return True if a real ElevenLabs API key is configured."""
    return bool(os.getenv("ELEVENLABS_API_KEY"))


async def generate_vo(
    script: str,
    voice_id: str,
    model: str = "eleven_multilingual_v2",
) -> bytes:
    """Call ElevenLabs TTS and return raw MP3 bytes.

    Returns a silent placeholder MP3 when ELEVENLABS_API_KEY is not set so the
    rest of the pipeline can proceed without a live key.
    """
    api_key = os.getenv("ELEVENLABS_API_KEY")
    if not api_key:
        logger.warning("ELEVENLABS_API_KEY not configured — returning silent placeholder audio")
        return _SILENT_MP3_PLACEHOLDER

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
