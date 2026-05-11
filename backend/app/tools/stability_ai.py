"""Stability AI SDXL tool for image generation."""

import base64
import logging
import os

import httpx

logger = logging.getLogger(__name__)

STABILITY_API_URL = (
    "https://api.stability.ai/v1/generation/"
    "stable-diffusion-xl-1024-v1-0/text-to-image"
)


async def generate_image(
    prompt: str,
    width: int = 1024,
    height: int = 1024,
    steps: int = 30,
    cfg_scale: float = 7.0,
) -> bytes:
    """Call Stability AI SDXL and return raw PNG bytes."""
    api_key = os.getenv("STABILITY_AI_API_KEY")
    if not api_key:
        raise RuntimeError("STABILITY_AI_API_KEY not set")

    payload = {
        "text_prompts": [{"text": prompt, "weight": 1}],
        "width": width,
        "height": height,
        "steps": steps,
        "cfg_scale": cfg_scale,
    }

    async with httpx.AsyncClient(timeout=60.0) as client:
        response = await client.post(
            STABILITY_API_URL,
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
                "Accept": "application/json",
            },
            json=payload,
        )

    if response.status_code != 200:
        raise RuntimeError(
            f"Stability AI returned {response.status_code}: {response.text}"
        )

    data = response.json()
    artifacts = data.get("artifacts", [])
    if not artifacts:
        raise RuntimeError("Stability AI returned no artifacts")

    return base64.b64decode(artifacts[0]["base64"])
