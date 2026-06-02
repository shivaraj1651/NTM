"""Kling AI video generation tool.

Replaces Runway ML. Uses JWT (HMAC-SHA256) authentication.
Env vars required:
  KLING_AI_ACCESS_KEY  — Kling access key ID
  KLING_AI_SECRET_KEY  — Kling secret key for JWT signing
"""

import base64
import hashlib
import hmac
import json
import logging
import os
import time

import httpx

logger = logging.getLogger(__name__)

KLING_API_BASE = "https://api.klingai.com"
KLING_TEXT2VIDEO_URL  = f"{KLING_API_BASE}/v1/videos/text2video"
KLING_IMAGE2VIDEO_URL = f"{KLING_API_BASE}/v1/videos/image2video"
KLING_TASK_URL        = f"{KLING_API_BASE}/v1/videos/text2video/{{task_id}}"

KLING_DEFAULT_MODEL   = "kling-v1"
KLING_DEFAULT_MODE    = "std"   # "std" or "pro"


def is_available() -> bool:
    """Return True if Kling AI credentials are configured."""
    return bool(os.getenv("KLING_AI_ACCESS_KEY") and os.getenv("KLING_AI_SECRET_KEY"))


def _make_jwt() -> str:
    """Build a short-lived JWT (HS256) for Kling AI auth."""
    access_key = os.getenv("KLING_AI_ACCESS_KEY", "")
    secret_key = os.getenv("KLING_AI_SECRET_KEY", "")

    now = int(time.time())

    header_b64 = base64.urlsafe_b64encode(
        json.dumps({"alg": "HS256", "typ": "JWT"}).encode()
    ).rstrip(b"=").decode()

    payload_b64 = base64.urlsafe_b64encode(
        json.dumps({"iss": access_key, "exp": now + 1800, "nbf": now - 5}).encode()
    ).rstrip(b"=").decode()

    signing_input = f"{header_b64}.{payload_b64}".encode()
    signature = base64.urlsafe_b64encode(
        hmac.new(secret_key.encode(), signing_input, hashlib.sha256).digest()
    ).rstrip(b"=").decode()

    return f"{header_b64}.{payload_b64}.{signature}"


def _auth_headers() -> dict[str, str]:
    return {
        "Authorization": f"Bearer {_make_jwt()}",
        "Content-Type": "application/json",
    }


async def generate_video(
    prompt: str,
    image_url: str | None = None,
    duration: int = 5,
    model: str = KLING_DEFAULT_MODEL,
    negative_prompt: str = "",
    cfg_scale: float = 0.5,
) -> str:
    """Submit a Kling AI video generation task. Returns task_id."""
    if not is_available():
        raise RuntimeError("KLING_AI_ACCESS_KEY / KLING_AI_SECRET_KEY not set")

    if image_url:
        url = KLING_IMAGE2VIDEO_URL
        payload: dict = {
            "model_name": model,
            "image": image_url,
            "prompt": prompt,
            "negative_prompt": negative_prompt,
            "cfg_scale": cfg_scale,
            "duration": str(duration),
        }
    else:
        url = KLING_TEXT2VIDEO_URL
        payload = {
            "model_name": model,
            "prompt": prompt,
            "negative_prompt": negative_prompt,
            "cfg_scale": cfg_scale,
            "mode": KLING_DEFAULT_MODE,
            "duration": str(duration),
        }

    async with httpx.AsyncClient(timeout=60.0) as client:
        response = await client.post(url, headers=_auth_headers(), json=payload)

    if response.status_code not in (200, 201):
        raise RuntimeError(f"Kling AI returned {response.status_code}: {response.text}")

    data = response.json()
    if data.get("code", -1) != 0:
        raise RuntimeError(f"Kling AI error: {data.get('message', data)}")

    task_id = data.get("data", {}).get("task_id")
    if not task_id:
        raise RuntimeError(f"Kling AI response missing task_id: {data}")

    return task_id


async def get_video_status(task_id: str) -> dict:
    """Poll Kling AI for task status. Returns {"status": ..., "url": ...}.

    Status values: submitted | processing | succeed | failed
    Normalized to SUCCEEDED / FAILED / PENDING for compatibility with agent.
    """
    url = KLING_TASK_URL.format(task_id=task_id)

    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.get(url, headers=_auth_headers())

    if response.status_code != 200:
        raise RuntimeError(f"Kling status check returned {response.status_code}: {response.text}")

    data = response.json()
    if data.get("code", -1) != 0:
        raise RuntimeError(f"Kling AI status error: {data.get('message', data)}")

    task_data = data.get("data", {})
    raw_status = task_data.get("task_status", "submitted")

    # Normalize to the agent's expected vocabulary
    if raw_status == "succeed":
        videos = task_data.get("task_result", {}).get("videos", [])
        video_url = videos[0].get("url") if videos else None
        return {"status": "SUCCEEDED", "url": video_url}

    if raw_status == "failed":
        return {"status": "FAILED", "url": None}

    return {"status": "PENDING", "url": None}
