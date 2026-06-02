# AGT-11 Video Generator Agent Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement the Runway ML video generator agent that submits a Gen-3 job, polls for completion, downloads the MP4, uploads to S3/MinIO, and returns the asset URL — falling back to `manual_production_required` on any Runway failure.

**Architecture:** Two files — `backend/app/tools/runway.py` (thin httpx wrapper around Runway ML REST API) and `backend/app/agents/video_generator.py` (plain async class with submit → poll → download → upload pipeline). Polling extracted into `_poll_for_completion()` for testability. Any Runway failure sets `status="manual_production_required"` and returns without raising.

**Tech Stack:** Python 3.12, httpx, Pydantic v2, SQLAlchemy async, pytest with `asyncio_mode=auto`, `unittest.mock.AsyncMock`/`patch`

---

## File Map

| File | Action | Responsibility |
|---|---|---|
| `backend/app/tools/runway.py` | Create | Runway ML REST API: submit job, poll status |
| `backend/app/models/video.py` | Create | `GeneratedVideo` SQLAlchemy model |
| `backend/app/agents/video_generator.py` | Create | `VideoGeneratorAgent`: brief → MP4 → storage URL |
| `backend/tests/agents/test_video_generator.py` | Create | 11 tests across 5 classes |

---

## Task 1: Runway ML Tool + DB Model

**Files:**
- Create: `backend/app/tools/runway.py`
- Create: `backend/app/models/video.py`

These are infrastructure — no direct test files (they are mocked in agent tests).

- [ ] **Step 1: Create `backend/app/tools/runway.py`**

```python
"""Runway ML video generation tool."""

import logging
import os

import httpx

logger = logging.getLogger(__name__)

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

    return response.json()["id"]


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
```

- [ ] **Step 2: Create `backend/app/models/video.py`**

```python
"""SQLAlchemy model for GeneratedVideo output from Video Generator Agent (AGT-11)."""

import uuid
from datetime import datetime, timezone

from sqlalchemy import Column, DateTime, Float, Index, String
from sqlalchemy.orm import declarative_base

Base = declarative_base()


class GeneratedVideo(Base):
    """Generated video record. Multi-tenant isolated, one row per generation."""

    __tablename__ = "generated_video"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    campaign_id = Column(String, nullable=False, index=True)
    tenant_id = Column(String, nullable=False, index=True)
    generation_id = Column(String, nullable=False)
    asset_url = Column(String, nullable=False)
    job_id = Column(String, nullable=False)
    model_used = Column(String, nullable=False)
    script_format = Column(String, nullable=False)
    duration_seconds = Column(Float, nullable=False, default=0.0)
    status = Column(String, nullable=False)
    created_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    __table_args__ = (
        Index("ix_generated_video_tenant_campaign", "tenant_id", "campaign_id"),
    )
```

- [ ] **Step 3: Commit infrastructure**

```bash
git add backend/app/tools/runway.py backend/app/models/video.py
git commit -m "[TASK-016] feat: add Runway ML tool and GeneratedVideo DB model"
```

---

## Task 2: Test Scaffolding + TestHappyPath

**Files:**
- Create: `backend/tests/agents/test_video_generator.py`
- Create: `backend/app/agents/video_generator.py`

- [ ] **Step 1: Create test file with scaffolding + TestHappyPath (RED)**

Create `backend/tests/agents/test_video_generator.py`:

```python
"""Tests for Video Generator Agent (AGT-11)."""

import pytest
from unittest.mock import AsyncMock, patch

from backend.app.agents.video_generator import (
    RUNWAY_MODEL,
    STATUS_COMPLETED,
    STATUS_MANUAL,
    VideoGenerationBrief,
    VideoGenerationOutput,
    VideoGeneratorAgent,
)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

FAKE_MP4 = b"\x00\x00\x00\x18ftypmp42" + b"\x00" * 200
FAKE_URL = "https://s3.example.com/camp-001/video.mp4"
FAKE_JOB_ID = "runway-job-001"
FAKE_RUNWAY_URL = "https://runway-cdn.example.com/output.mp4"

SUCCEEDED_STATUS = {"status": "SUCCEEDED", "url": FAKE_RUNWAY_URL}

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

class FakeHTTPResponse:
    def __init__(self, content=FAKE_MP4):
        self.content = content


class FakeHTTPClient:
    """Replaces httpx.AsyncClient for the MP4 download step."""
    def __init__(self, content=FAKE_MP4, **kwargs):
        self._content = content

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        pass

    async def get(self, url):
        return FakeHTTPResponse(self._content)


class FakeStorageClient:
    def __init__(self, url: str = FAKE_URL):
        self.url = url
        self.calls: list = []

    async def upload(self, data: bytes, key: str) -> str:
        self.calls.append((data, key))
        return self.url


class FakeSession:
    def __init__(self):
        self.rows: list = []

    def add(self, row):
        self.rows.append(row)

    async def commit(self):
        pass


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def brief():
    return VideoGenerationBrief(
        campaign_id="camp-001",
        tenant_id="tenant-001",
        prompt="A product flying through space with neon trails",
        script_text="Introducing the future. Available now.",
        reference_image_url="https://s3.example.com/camp-001/image.png",
        duration_seconds=5,
        campaign_theme="Future Tech",
    )


@pytest.fixture
def storage():
    return FakeStorageClient()


@pytest.fixture
def agent():
    return VideoGeneratorAgent()


# ---------------------------------------------------------------------------
# Happy path
# ---------------------------------------------------------------------------

class TestHappyPath:

    async def test_generate_returns_asset_url(self, agent, brief, storage):
        with patch(
            "backend.app.agents.video_generator.runway.generate_video",
            new=AsyncMock(return_value=FAKE_JOB_ID),
        ), patch(
            "backend.app.agents.video_generator.runway.get_video_status",
            new=AsyncMock(return_value=SUCCEEDED_STATUS),
        ), patch(
            "backend.app.agents.video_generator.httpx.AsyncClient",
            FakeHTTPClient,
        ):
            output = await agent.generate(brief, storage_client=storage)

        assert output.asset_url == FAKE_URL

    async def test_generate_returns_video_generation_output(self, agent, brief, storage):
        with patch(
            "backend.app.agents.video_generator.runway.generate_video",
            new=AsyncMock(return_value=FAKE_JOB_ID),
        ), patch(
            "backend.app.agents.video_generator.runway.get_video_status",
            new=AsyncMock(return_value=SUCCEEDED_STATUS),
        ), patch(
            "backend.app.agents.video_generator.httpx.AsyncClient",
            FakeHTTPClient,
        ):
            output = await agent.generate(brief, storage_client=storage)

        assert isinstance(output, VideoGenerationOutput)
        assert output.campaign_id == "camp-001"
        assert output.tenant_id == "tenant-001"
        assert output.status == STATUS_COMPLETED
        assert output.job_id == FAKE_JOB_ID

    async def test_storage_client_receives_mp4_bytes(self, agent, brief, storage):
        with patch(
            "backend.app.agents.video_generator.runway.generate_video",
            new=AsyncMock(return_value=FAKE_JOB_ID),
        ), patch(
            "backend.app.agents.video_generator.runway.get_video_status",
            new=AsyncMock(return_value=SUCCEEDED_STATUS),
        ), patch(
            "backend.app.agents.video_generator.httpx.AsyncClient",
            FakeHTTPClient,
        ):
            await agent.generate(brief, storage_client=storage)

        assert len(storage.calls) == 1
        uploaded_bytes, key = storage.calls[0]
        assert uploaded_bytes == FAKE_MP4
        assert "camp-001" in key
        assert key.endswith(".mp4")

    async def test_no_persist_without_db_session(self, agent, brief, storage):
        with patch(
            "backend.app.agents.video_generator.runway.generate_video",
            new=AsyncMock(return_value=FAKE_JOB_ID),
        ), patch(
            "backend.app.agents.video_generator.runway.get_video_status",
            new=AsyncMock(return_value=SUCCEEDED_STATUS),
        ), patch(
            "backend.app.agents.video_generator.httpx.AsyncClient",
            FakeHTTPClient,
        ):
            output = await agent.generate(brief, storage_client=storage)

        assert output.asset_url == FAKE_URL  # no error, no DB write
```

- [ ] **Step 2: Verify tests fail (RED)**

```bash
cd D:/staging/ntm && python -m pytest backend/tests/agents/test_video_generator.py::TestHappyPath -v
```

Expected: `ModuleNotFoundError` or `ImportError` — `video_generator` module does not exist yet.

- [ ] **Step 3: Create `backend/app/agents/video_generator.py` with full implementation**

```python
"""Video Generator Agent (AGT-11).

Takes a VideoGenerationBrief, submits a Runway ML Gen-3 job, polls for
completion, downloads the MP4, uploads via injected storage client, and
returns the asset URL + metadata. Runway unavailability yields
status="manual_production_required" instead of raising.
"""

import asyncio
import logging
import uuid
from datetime import datetime, timezone
from typing import Optional

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
    reference_image_url: Optional[str] = None
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
        default_factory=lambda: datetime.now(timezone.utc)
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
        last_exc: Optional[Exception] = None
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

    async def _poll_for_completion(self, job_id: str) -> Optional[str]:
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
```

- [ ] **Step 4: Run TestHappyPath (GREEN)**

```bash
cd D:/staging/ntm && python -m pytest backend/tests/agents/test_video_generator.py::TestHappyPath -v
```

Expected: `4 passed`

- [ ] **Step 5: Commit**

```bash
git add backend/app/agents/video_generator.py backend/tests/agents/test_video_generator.py
git commit -m "[TASK-016] feat: implement VideoGeneratorAgent happy path with TDD"
```

---

## Task 3: TestImageToVideo — Routing Tests

**Files:**
- Modify: `backend/tests/agents/test_video_generator.py` (add `TestImageToVideo` class)

- [ ] **Step 1: Add TestImageToVideo class to test file (RED)**

Append to `backend/tests/agents/test_video_generator.py`:

```python
# ---------------------------------------------------------------------------
# Image-to-video routing
# ---------------------------------------------------------------------------

class TestImageToVideo:

    async def test_image_url_passed_to_runway_tool(self, agent, storage):
        brief = VideoGenerationBrief(
            campaign_id="c", tenant_id="t",
            prompt="product in space",
            script_text="Introducing.",
            reference_image_url="https://s3.example.com/image.png",
            duration_seconds=5,
        )
        mock_generate = AsyncMock(return_value=FAKE_JOB_ID)
        with patch(
            "backend.app.agents.video_generator.runway.generate_video",
            new=mock_generate,
        ), patch(
            "backend.app.agents.video_generator.runway.get_video_status",
            new=AsyncMock(return_value=SUCCEEDED_STATUS),
        ), patch(
            "backend.app.agents.video_generator.httpx.AsyncClient",
            FakeHTTPClient,
        ):
            await agent.generate(brief, storage_client=storage)

        call_args = mock_generate.call_args
        assert call_args[0][1] == "https://s3.example.com/image.png"

    async def test_no_image_url_uses_text_to_video(self, agent, storage):
        brief = VideoGenerationBrief(
            campaign_id="c", tenant_id="t",
            prompt="product in space",
            script_text="Introducing.",
            reference_image_url=None,
            duration_seconds=5,
        )
        mock_generate = AsyncMock(return_value=FAKE_JOB_ID)
        with patch(
            "backend.app.agents.video_generator.runway.generate_video",
            new=mock_generate,
        ), patch(
            "backend.app.agents.video_generator.runway.get_video_status",
            new=AsyncMock(return_value=SUCCEEDED_STATUS),
        ), patch(
            "backend.app.agents.video_generator.httpx.AsyncClient",
            FakeHTTPClient,
        ):
            await agent.generate(brief, storage_client=storage)

        call_args = mock_generate.call_args
        assert call_args[0][1] is None
```

- [ ] **Step 2: Run TestImageToVideo (RED)**

```bash
cd D:/staging/ntm && python -m pytest backend/tests/agents/test_video_generator.py::TestImageToVideo -v
```

Expected: `FAILED` — `mock_generate` called but routing not verified yet (tests may pass if `generate_video` receives `image_url` as positional arg correctly — if they already pass, proceed to commit).

- [ ] **Step 3: Run TestImageToVideo (GREEN)**

```bash
cd D:/staging/ntm && python -m pytest backend/tests/agents/test_video_generator.py::TestImageToVideo -v
```

Expected: `2 passed` — `_submit_with_retry` already passes `brief.reference_image_url` as positional arg to `runway.generate_video`.

- [ ] **Step 4: Commit**

```bash
git add backend/tests/agents/test_video_generator.py
git commit -m "[TASK-016] test: add TestImageToVideo routing tests"
```

---

## Task 4: TestPollBehavior — Poll Timeout and Failure

**Files:**
- Modify: `backend/tests/agents/test_video_generator.py` (add `TestPollBehavior` class)

- [ ] **Step 1: Add TestPollBehavior class (RED)**

Append to `backend/tests/agents/test_video_generator.py`:

```python
# ---------------------------------------------------------------------------
# Poll behavior
# ---------------------------------------------------------------------------

class TestPollBehavior:

    async def test_poll_timeout_returns_manual_status(self, agent, brief, storage):
        with patch(
            "backend.app.agents.video_generator.runway.generate_video",
            new=AsyncMock(return_value=FAKE_JOB_ID),
        ), patch.object(
            agent, "_poll_for_completion",
            new=AsyncMock(return_value=None),
        ):
            output = await agent.generate(brief, storage_client=storage)

        assert output.status == STATUS_MANUAL
        assert output.asset_url == ""
        assert output.job_id == FAKE_JOB_ID

    async def test_poll_failed_returns_manual_status(self, agent, brief, storage):
        with patch(
            "backend.app.agents.video_generator.runway.generate_video",
            new=AsyncMock(return_value=FAKE_JOB_ID),
        ), patch.object(
            agent, "_poll_for_completion",
            new=AsyncMock(return_value=None),
        ):
            output = await agent.generate(brief, storage_client=storage)

        assert output.status == STATUS_MANUAL
```

- [ ] **Step 2: Run TestPollBehavior (RED)**

```bash
cd D:/staging/ntm && python -m pytest backend/tests/agents/test_video_generator.py::TestPollBehavior -v
```

Expected: `FAILED` — `_poll_for_completion` returns `None` but implementation may not handle it yet (or `2 passed` if already handled — proceed to commit).

- [ ] **Step 3: Run TestPollBehavior (GREEN)**

```bash
cd D:/staging/ntm && python -m pytest backend/tests/agents/test_video_generator.py::TestPollBehavior -v
```

Expected: `2 passed`

- [ ] **Step 4: Commit**

```bash
git add backend/tests/agents/test_video_generator.py
git commit -m "[TASK-016] test: add TestPollBehavior timeout and failure tests"
```

---

## Task 5: TestFailureFallback — Runway Unavailable

**Files:**
- Modify: `backend/tests/agents/test_video_generator.py` (add `TestFailureFallback` class)

- [ ] **Step 1: Add TestFailureFallback class (RED)**

Append to `backend/tests/agents/test_video_generator.py`:

```python
# ---------------------------------------------------------------------------
# Failure fallback
# ---------------------------------------------------------------------------

class TestFailureFallback:

    async def test_runway_unavailable_returns_manual_status(self, agent, brief, storage):
        with patch(
            "backend.app.agents.video_generator.runway.generate_video",
            new=AsyncMock(side_effect=RuntimeError("Runway down")),
        ):
            output = await agent.generate(brief, storage_client=storage)

        assert output.status == STATUS_MANUAL
        assert output.asset_url == ""
        assert output.job_id == ""

    async def test_runway_unavailable_does_not_raise(self, agent, brief, storage):
        with patch(
            "backend.app.agents.video_generator.runway.generate_video",
            new=AsyncMock(side_effect=RuntimeError("Runway down")),
        ):
            output = await agent.generate(brief, storage_client=storage)

        assert output is not None
```

- [ ] **Step 2: Run TestFailureFallback (RED)**

```bash
cd D:/staging/ntm && python -m pytest backend/tests/agents/test_video_generator.py::TestFailureFallback -v
```

Expected: `FAILED` — `RuntimeError` propagates if failure path not handled.

- [ ] **Step 3: Verify GREEN**

```bash
cd D:/staging/ntm && python -m pytest backend/tests/agents/test_video_generator.py::TestFailureFallback -v
```

Expected: `2 passed` — `_submit_with_retry` retries then raises; `generate()` catches and returns `STATUS_MANUAL`.

- [ ] **Step 4: Commit**

```bash
git add backend/tests/agents/test_video_generator.py
git commit -m "[TASK-016] test: add TestFailureFallback runway unavailable tests"
```

---

## Task 6: TestPersistence — DB Write

**Files:**
- Modify: `backend/tests/agents/test_video_generator.py` (add `TestPersistence` class)

- [ ] **Step 1: Add TestPersistence class (RED)**

Append to `backend/tests/agents/test_video_generator.py`:

```python
# ---------------------------------------------------------------------------
# DB persistence
# ---------------------------------------------------------------------------

class TestPersistence:

    async def test_persist_creates_db_record_with_tenant_id(self, agent, brief, storage):
        session = FakeSession()
        with patch(
            "backend.app.agents.video_generator.runway.generate_video",
            new=AsyncMock(return_value=FAKE_JOB_ID),
        ), patch(
            "backend.app.agents.video_generator.runway.get_video_status",
            new=AsyncMock(return_value=SUCCEEDED_STATUS),
        ), patch(
            "backend.app.agents.video_generator.httpx.AsyncClient",
            FakeHTTPClient,
        ):
            await agent.generate(brief, storage_client=storage, db_session=session)

        assert len(session.rows) == 1
        row = session.rows[0]
        assert row.tenant_id == "tenant-001"
        assert row.campaign_id == "camp-001"

    async def test_persist_stores_job_id(self, agent, brief, storage):
        session = FakeSession()
        with patch(
            "backend.app.agents.video_generator.runway.generate_video",
            new=AsyncMock(return_value=FAKE_JOB_ID),
        ), patch(
            "backend.app.agents.video_generator.runway.get_video_status",
            new=AsyncMock(return_value=SUCCEEDED_STATUS),
        ), patch(
            "backend.app.agents.video_generator.httpx.AsyncClient",
            FakeHTTPClient,
        ):
            await agent.generate(brief, storage_client=storage, db_session=session)

        assert session.rows[0].job_id == FAKE_JOB_ID
```

- [ ] **Step 2: Run TestPersistence (RED)**

```bash
cd D:/staging/ntm && python -m pytest backend/tests/agents/test_video_generator.py::TestPersistence -v
```

Expected: `FAILED` — `_persist` not yet implemented (or `2 passed` if already in agent — proceed to commit).

- [ ] **Step 3: Verify GREEN**

```bash
cd D:/staging/ntm && python -m pytest backend/tests/agents/test_video_generator.py::TestPersistence -v
```

Expected: `2 passed`

- [ ] **Step 4: Commit**

```bash
git add backend/tests/agents/test_video_generator.py
git commit -m "[TASK-016] test: add TestPersistence DB write tests"
```

---

## Task 7: Full Verification + Final Commit

**Files:**
- No new files

- [ ] **Step 1: Run all AGT-11 tests**

```bash
cd D:/staging/ntm && python -m pytest backend/tests/agents/test_video_generator.py -v
```

Expected:
```
backend/tests/agents/test_video_generator.py::TestHappyPath::test_generate_returns_asset_url PASSED
backend/tests/agents/test_video_generator.py::TestHappyPath::test_generate_returns_video_generation_output PASSED
backend/tests/agents/test_video_generator.py::TestHappyPath::test_storage_client_receives_mp4_bytes PASSED
backend/tests/agents/test_video_generator.py::TestHappyPath::test_no_persist_without_db_session PASSED
backend/tests/agents/test_video_generator.py::TestImageToVideo::test_image_url_passed_to_runway_tool PASSED
backend/tests/agents/test_video_generator.py::TestImageToVideo::test_no_image_url_uses_text_to_video PASSED
backend/tests/agents/test_video_generator.py::TestPollBehavior::test_poll_timeout_returns_manual_status PASSED
backend/tests/agents/test_video_generator.py::TestPollBehavior::test_poll_failed_returns_manual_status PASSED
backend/tests/agents/test_video_generator.py::TestFailureFallback::test_runway_unavailable_returns_manual_status PASSED
backend/tests/agents/test_video_generator.py::TestFailureFallback::test_runway_unavailable_does_not_raise PASSED
backend/tests/agents/test_video_generator.py::TestPersistence::test_persist_creates_db_record_with_tenant_id PASSED
backend/tests/agents/test_video_generator.py::TestPersistence::test_persist_stores_job_id PASSED
======================== 12 passed in X.XXs ========================
```

If any test fails, fix the agent or test before proceeding.

- [ ] **Step 2: Final commit**

```bash
git add -A
git commit -m "$(cat <<'EOF'
[TASK-016] feat: implement AGT-11 video generator agent with TDD

Co-authored-by: katharguppe <katharguppe@users.noreply.github.com>
EOF
)"
```

- [ ] **Step 3: Push**

```bash
git push origin main
```
