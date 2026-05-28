"""Runway ML video generation tool."""

import os

import httpx


def is_available() -> bool:
    """Return True if Runway ML API key is configured."""
    return bool(os.getenv("RUNWAY_API_KEY"))

RUNWAY_IMAGE_TO_VIDEO_URL = "https://api.dev.runwayml.com/v1/image_to_video"
RUNWAY_TEXT_TO_VIDEO_URL  = "https://api.dev.runwayml.com/v1/text_to_video"
RUNWAY_TASK_URL           = "https://api.dev.runwayml.com/v1/tasks/{job_id}"


async def generate_video(
    prompt: str,
    image_url: str | None,
    duration: int = 5,
) -> str:
    """Submit a Runway ML video generation job. Returns job_id."""
    api_key = os.getenv("RUNWAY_API_KEY")
    if not api_key:
        raise RuntimeError("RUNWAY_API_KEY not set")

    url = RUNWAY_IMAGE_TO_VIDEO_URL if image_url else RUNWAY_TEXT_TO_VIDEO_URL
    payload: dict = {
        "model": "gen3a_turbo",
        "promptText": prompt,
        "duration": duration,
    }
    if image_url:
        payload["promptImage"] = image_url

    async with httpx.AsyncClient(timeout=60.0) as client:
        response = await client.post(
            url,
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            json=payload,
        )

    if response.status_code != 200:
        raise RuntimeError(
            f"Runway returned {response.status_code}: {response.text}"
        )

    data = response.json()
    if "id" not in data:
        raise RuntimeError(f"Runway response missing 'id' field: {data}")
    return data["id"]


async def get_video_status(job_id: str) -> dict:
    """Poll Runway ML for job status. Returns {"status": ..., "url": ...}."""
    api_key = os.getenv("RUNWAY_API_KEY")
    if not api_key:
        raise RuntimeError("RUNWAY_API_KEY not set")

    url = RUNWAY_TASK_URL.format(job_id=job_id)

    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.get(
            url,
            headers={"Authorization": f"Bearer {api_key}"},
        )

    if response.status_code != 200:
        raise RuntimeError(
            f"Runway status check returned {response.status_code}: {response.text}"
        )

    data = response.json()
    output = data.get("output") or []
    return {
        "status": data.get("status", "PENDING"),
        "url": output[0] if output else None,
    }
