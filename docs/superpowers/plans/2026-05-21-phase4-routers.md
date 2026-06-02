# Phase 4 Routers Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Expose HTTP endpoints for AGT-12 through AGT-15 — fire-and-forget POST that triggers the existing Celery task + GET that returns the latest stored result.

**Architecture:** One router file per agent, all registered in `routers/__init__.py`. POST endpoints call `.delay()` on existing Celery tasks and return a `JobQueuedResponse`. GET endpoints query MongoDB/Postgres for the latest result and return 404 if not yet generated. Campaign `mandate_id` is resolved from `CampaignService.get()` for tasks that accept `mandate_id`.

**Tech Stack:** FastAPI, Motor (MongoDB), SQLAlchemy AsyncSession, Celery `.delay()`, Pydantic v2

---

## File Map

| Action | Path | Responsibility |
|--------|------|----------------|
| Create | `backend/app/schemas/jobs.py` | `JobQueuedResponse` shared schema |
| Create | `backend/app/routers/digital_activator.py` | POST `/campaigns/{id}/activate` |
| Create | `backend/app/routers/analytics.py` | POST `/campaigns/{id}/analytics/run` + GET `/campaigns/{id}/analytics` |
| Create | `backend/app/routers/replanning.py` | POST `/campaigns/{id}/replan` |
| Create | `backend/app/routers/report.py` | POST `/campaigns/{id}/report/generate` + GET `/campaigns/{id}/report` |
| Modify | `backend/app/routers/__init__.py` | Register all four new routers |
| Create | `backend/tests/routers/test_digital_activator_router.py` | Tests for activate endpoint |
| Create | `backend/tests/routers/test_analytics_router.py` | Tests for analytics endpoints |
| Create | `backend/tests/routers/test_replanning_router.py` | Tests for replan endpoint |
| Create | `backend/tests/routers/test_report_router.py` | Tests for report endpoints |

---

## Task 1: JobQueuedResponse Schema

**Files:**
- Create: `backend/app/schemas/jobs.py`

- [ ] **Step 1: Write the file**

```python
# backend/app/schemas/jobs.py
from typing import Literal
from pydantic import BaseModel


class JobQueuedResponse(BaseModel):
    job_id: str
    status: Literal["queued"] = "queued"
    campaign_id: str
```

- [ ] **Step 2: Verify import works**

```bash
python -c "from backend.app.schemas.jobs import JobQueuedResponse; print(JobQueuedResponse(job_id='x', campaign_id='y'))"
```

Expected output: `job_id='x' status='queued' campaign_id='y'`

- [ ] **Step 3: Commit**

```bash
git add backend/app/schemas/jobs.py
git commit -m "[TASK-phase4] feat: add JobQueuedResponse schema"
```

---

## Task 2: Digital Activator Router

**Files:**
- Create: `backend/app/routers/digital_activator.py`
- Create: `backend/tests/routers/test_digital_activator_router.py`

- [ ] **Step 1: Write the failing test**

```python
# backend/tests/routers/test_digital_activator_router.py
from unittest.mock import AsyncMock, patch, MagicMock
import pytest
from httpx import AsyncClient, ASGITransport
from backend.app.main import app


@pytest.fixture
def mock_campaign():
    return {
        "id": "camp-001",
        "mandate_id": "mand-001",
        "tenant_id": "tenant-001",
        "status": "approved",
        "concepts": [],
        "selected_concept_id": None,
        "activation_plan": [
            {"id": "act-001", "channel": "google_ads", "budget": 500},
            {"id": "act-002", "channel": "meta_ads", "budget": 300},
        ],
        "budget_proposal": None,
        "created_at": "2026-01-01T00:00:00",
        "updated_at": "2026-01-01T00:00:00",
    }


@pytest.mark.asyncio
async def test_activate_campaign_returns_job_queued(mock_campaign):
    with (
        patch("backend.app.routers.digital_activator.CampaignService") as MockSvc,
        patch("backend.app.routers.digital_activator.platform_activate_google") as mock_google,
        patch("backend.app.routers.digital_activator.platform_activate_meta") as mock_meta,
        patch("backend.app.routers.digital_activator.platform_activate_linkedin") as mock_li,
        patch("backend.app.core.auth.current_user", return_value=MagicMock(id="user-1")),
        patch("backend.app.core.dependencies.get_current_tenant", return_value="tenant-001"),
    ):
        from backend.app.schemas.campaign import CampaignResponse
        svc_instance = AsyncMock()
        svc_instance.get.return_value = CampaignResponse(**mock_campaign)
        MockSvc.return_value = svc_instance
        mock_google.delay = MagicMock()
        mock_meta.delay = MagicMock()
        mock_li.delay = MagicMock()

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.post(
                "/api/v1/campaigns/camp-001/activate",
                headers={"Authorization": "Bearer test", "X-Tenant-ID": "tenant-001"},
            )

        assert response.status_code == 202
        body = response.json()
        assert body["status"] == "queued"
        assert body["campaign_id"] == "camp-001"
        assert "job_id" in body
        mock_google.delay.assert_called_once()
        mock_meta.delay.assert_called_once()


@pytest.mark.asyncio
async def test_activate_campaign_not_found():
    with (
        patch("backend.app.routers.digital_activator.CampaignService") as MockSvc,
        patch("backend.app.core.auth.current_user", return_value=MagicMock(id="user-1")),
        patch("backend.app.core.dependencies.get_current_tenant", return_value="tenant-001"),
    ):
        from fastapi import HTTPException
        svc_instance = AsyncMock()
        svc_instance.get.side_effect = HTTPException(status_code=404, detail="Not found")
        MockSvc.return_value = svc_instance

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.post(
                "/api/v1/campaigns/bad-id/activate",
                headers={"Authorization": "Bearer test", "X-Tenant-ID": "tenant-001"},
            )

        assert response.status_code == 404
```

- [ ] **Step 2: Run test — expect failure (module not found)**

```bash
pytest backend/tests/routers/test_digital_activator_router.py -v --no-header -q
```

Expected: `ImportError` or `ModuleNotFoundError` for `digital_activator`

- [ ] **Step 3: Implement the router**

```python
# backend/app/routers/digital_activator.py
import logging
import os
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase

from backend.app.core.auth import current_user
from backend.app.core.dependencies import get_current_tenant
from backend.app.core.models import User
from backend.app.schemas.jobs import JobQueuedResponse
from backend.app.services.campaign_service import CampaignService
from backend.app.tasks.activation_tasks import (
    platform_activate_google,
    platform_activate_meta,
    platform_activate_linkedin,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1", tags=["digital-activator"])

_PLATFORM_TASK_MAP = {
    "google_ads": platform_activate_google,
    "meta_ads": platform_activate_meta,
    "linkedin_ads": platform_activate_linkedin,
}


async def get_db() -> AsyncIOMotorDatabase:
    client = AsyncIOMotorClient(os.getenv("MONGO_DB_URL", "mongodb://localhost:27017"))
    return client[os.getenv("MONGO_DB_NAME", "ntm")]


@router.post("/campaigns/{campaign_id}/activate", response_model=JobQueuedResponse, status_code=202)
async def activate_campaign(
    campaign_id: str,
    user: User = Depends(current_user),
    tenant_id: str = Depends(get_current_tenant),
    db: AsyncIOMotorDatabase = Depends(get_db),
) -> JobQueuedResponse:
    svc = CampaignService(db)
    campaign = await svc.get(campaign_id, tenant_id)

    job_id = str(uuid4())
    activation_plan = campaign.activation_plan or []

    for act in activation_plan:
        channel = act.get("channel") if isinstance(act, dict) else getattr(act, "channel", None)
        task_fn = _PLATFORM_TASK_MAP.get(channel)
        if task_fn:
            task_fn.delay(
                activation={**(act if isinstance(act, dict) else act.model_dump()), "tenant_id": tenant_id},
                platform_config={},
                creative_url="",
            )
            logger.info("Queued activation task", extra={"channel": channel, "campaign_id": campaign_id})

    return JobQueuedResponse(job_id=job_id, campaign_id=campaign_id)
```

- [ ] **Step 4: Run tests — expect pass**

```bash
pytest backend/tests/routers/test_digital_activator_router.py -v --no-header -q
```

Expected: `2 passed`

- [ ] **Step 5: Commit**

```bash
git add backend/app/routers/digital_activator.py backend/tests/routers/test_digital_activator_router.py backend/app/schemas/jobs.py
git commit -m "[TASK-phase4] feat: digital activator router POST /campaigns/{id}/activate"
```

---

## Task 3: Analytics Router

**Files:**
- Create: `backend/app/routers/analytics.py`
- Create: `backend/tests/routers/test_analytics_router.py`

- [ ] **Step 1: Write failing tests**

```python
# backend/tests/routers/test_analytics_router.py
from unittest.mock import AsyncMock, patch, MagicMock
import pytest
from httpx import AsyncClient, ASGITransport
from backend.app.main import app


@pytest.fixture
def mock_campaign_doc():
    return {
        "id": "camp-001",
        "mandate_id": "mand-001",
        "tenant_id": "tenant-001",
        "status": "live",
        "concepts": [],
        "selected_concept_id": None,
        "activation_plan": [],
        "budget_proposal": None,
        "created_at": "2026-01-01T00:00:00",
        "updated_at": "2026-01-01T00:00:00",
    }


@pytest.mark.asyncio
async def test_run_analytics_returns_job_queued(mock_campaign_doc):
    with (
        patch("backend.app.routers.analytics.CampaignService") as MockSvc,
        patch("backend.app.routers.analytics.run_daily_analytics_task") as mock_task,
        patch("backend.app.core.auth.current_user", return_value=MagicMock(id="user-1")),
        patch("backend.app.core.dependencies.get_current_tenant", return_value="tenant-001"),
    ):
        from backend.app.schemas.campaign import CampaignResponse
        svc_instance = AsyncMock()
        svc_instance.get.return_value = CampaignResponse(**mock_campaign_doc)
        MockSvc.return_value = svc_instance
        mock_task.delay = MagicMock()

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.post(
                "/api/v1/campaigns/camp-001/analytics/run",
                headers={"Authorization": "Bearer test", "X-Tenant-ID": "tenant-001"},
            )

        assert response.status_code == 202
        body = response.json()
        assert body["status"] == "queued"
        assert body["campaign_id"] == "camp-001"
        mock_task.delay.assert_called_once_with("mand-001")


@pytest.mark.asyncio
async def test_get_analytics_returns_404_when_missing(mock_campaign_doc):
    with (
        patch("backend.app.routers.analytics.CampaignService") as MockSvc,
        patch("backend.app.core.auth.current_user", return_value=MagicMock(id="user-1")),
        patch("backend.app.core.dependencies.get_current_tenant", return_value="tenant-001"),
    ):
        from backend.app.schemas.campaign import CampaignResponse
        svc_instance = AsyncMock()
        svc_instance.get.return_value = CampaignResponse(**mock_campaign_doc)
        MockSvc.return_value = svc_instance

        # Patch MongoDB find_one to return None
        with patch("backend.app.routers.analytics.AsyncIOMotorClient") as MockClient:
            mock_db = MagicMock()
            mock_db.__getitem__.return_value.__getitem__.return_value.find_one = AsyncMock(return_value=None)
            MockClient.return_value.__getitem__.return_value = mock_db

            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
                response = await client.get(
                    "/api/v1/campaigns/camp-001/analytics",
                    headers={"Authorization": "Bearer test", "X-Tenant-ID": "tenant-001"},
                )

        assert response.status_code == 404
```

- [ ] **Step 2: Run — expect failure**

```bash
pytest backend/tests/routers/test_analytics_router.py -v --no-header -q
```

Expected: `ModuleNotFoundError` for `analytics` router

- [ ] **Step 3: Implement the router**

```python
# backend/app/routers/analytics.py
import logging
import os
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase

from backend.app.core.auth import current_user
from backend.app.core.dependencies import get_current_tenant
from backend.app.core.models import User
from backend.app.schemas.jobs import JobQueuedResponse
from backend.app.services.campaign_service import CampaignService
from backend.app.tasks.analytics_tasks import run_daily_analytics_task

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1", tags=["analytics"])


async def get_db() -> AsyncIOMotorDatabase:
    client = AsyncIOMotorClient(os.getenv("MONGO_DB_URL", "mongodb://localhost:27017"))
    return client[os.getenv("MONGO_DB_NAME", "ntm")]


@router.post("/campaigns/{campaign_id}/analytics/run", response_model=JobQueuedResponse, status_code=202)
async def run_analytics(
    campaign_id: str,
    user: User = Depends(current_user),
    tenant_id: str = Depends(get_current_tenant),
    db: AsyncIOMotorDatabase = Depends(get_db),
) -> JobQueuedResponse:
    svc = CampaignService(db)
    campaign = await svc.get(campaign_id, tenant_id)
    job_id = str(uuid4())
    run_daily_analytics_task.delay(campaign.mandate_id)
    logger.info("Queued analytics task", extra={"mandate_id": campaign.mandate_id, "campaign_id": campaign_id})
    return JobQueuedResponse(job_id=job_id, campaign_id=campaign_id)


@router.get("/campaigns/{campaign_id}/analytics", status_code=200)
async def get_analytics(
    campaign_id: str,
    user: User = Depends(current_user),
    tenant_id: str = Depends(get_current_tenant),
    db: AsyncIOMotorDatabase = Depends(get_db),
) -> dict:
    svc = CampaignService(db)
    campaign = await svc.get(campaign_id, tenant_id)
    summary = await db["analytics_summaries"].find_one(
        {"mandate_id": campaign.mandate_id, "tenant_id": tenant_id},
        sort=[("date", -1)],
    )
    if not summary:
        raise HTTPException(status_code=404, detail="No analytics result found. Run analytics first.")
    summary.pop("_id", None)
    return summary
```

- [ ] **Step 4: Run tests — expect pass**

```bash
pytest backend/tests/routers/test_analytics_router.py -v --no-header -q
```

Expected: `2 passed`

- [ ] **Step 5: Commit**

```bash
git add backend/app/routers/analytics.py backend/tests/routers/test_analytics_router.py
git commit -m "[TASK-phase4] feat: analytics router POST run + GET result"
```

---

## Task 4: Replanning Router

**Files:**
- Create: `backend/app/routers/replanning.py`
- Create: `backend/tests/routers/test_replanning_router.py`

- [ ] **Step 1: Write failing test**

```python
# backend/tests/routers/test_replanning_router.py
from unittest.mock import AsyncMock, patch, MagicMock
import pytest
from httpx import AsyncClient, ASGITransport
from backend.app.main import app


@pytest.mark.asyncio
async def test_replan_returns_job_queued():
    campaign_doc = {
        "id": "camp-001", "mandate_id": "mand-001", "tenant_id": "tenant-001",
        "status": "live", "concepts": [], "selected_concept_id": None,
        "activation_plan": [], "budget_proposal": None,
        "created_at": "2026-01-01T00:00:00", "updated_at": "2026-01-01T00:00:00",
    }
    with (
        patch("backend.app.routers.replanning.CampaignService") as MockSvc,
        patch("backend.app.routers.replanning.run_weekly_replan_task") as mock_task,
        patch("backend.app.core.auth.current_user", return_value=MagicMock(id="user-1")),
        patch("backend.app.core.dependencies.get_current_tenant", return_value="tenant-001"),
    ):
        from backend.app.schemas.campaign import CampaignResponse
        svc_instance = AsyncMock()
        svc_instance.get.return_value = CampaignResponse(**campaign_doc)
        MockSvc.return_value = svc_instance
        mock_task.delay = MagicMock()

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.post(
                "/api/v1/campaigns/camp-001/replan",
                headers={"Authorization": "Bearer test", "X-Tenant-ID": "tenant-001"},
            )

        assert response.status_code == 202
        body = response.json()
        assert body["status"] == "queued"
        mock_task.delay.assert_called_once_with("mand-001")
```

- [ ] **Step 2: Run — expect failure**

```bash
pytest backend/tests/routers/test_replanning_router.py -v --no-header -q
```

Expected: `ModuleNotFoundError`

- [ ] **Step 3: Implement**

```python
# backend/app/routers/replanning.py
import logging
import os
from uuid import uuid4

from fastapi import APIRouter, Depends
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase

from backend.app.core.auth import current_user
from backend.app.core.dependencies import get_current_tenant
from backend.app.core.models import User
from backend.app.schemas.jobs import JobQueuedResponse
from backend.app.services.campaign_service import CampaignService
from backend.app.tasks.replanning_tasks import run_weekly_replan_task

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1", tags=["replanning"])


async def get_db() -> AsyncIOMotorDatabase:
    client = AsyncIOMotorClient(os.getenv("MONGO_DB_URL", "mongodb://localhost:27017"))
    return client[os.getenv("MONGO_DB_NAME", "ntm")]


@router.post("/campaigns/{campaign_id}/replan", response_model=JobQueuedResponse, status_code=202)
async def replan_campaign(
    campaign_id: str,
    user: User = Depends(current_user),
    tenant_id: str = Depends(get_current_tenant),
    db: AsyncIOMotorDatabase = Depends(get_db),
) -> JobQueuedResponse:
    svc = CampaignService(db)
    campaign = await svc.get(campaign_id, tenant_id)
    job_id = str(uuid4())
    run_weekly_replan_task.delay(campaign.mandate_id)
    logger.info("Queued replan task", extra={"mandate_id": campaign.mandate_id, "campaign_id": campaign_id})
    return JobQueuedResponse(job_id=job_id, campaign_id=campaign_id)
```

- [ ] **Step 4: Run tests — expect pass**

```bash
pytest backend/tests/routers/test_replanning_router.py -v --no-header -q
```

Expected: `1 passed`

- [ ] **Step 5: Commit**

```bash
git add backend/app/routers/replanning.py backend/tests/routers/test_replanning_router.py
git commit -m "[TASK-phase4] feat: replanning router POST /campaigns/{id}/replan"
```

---

## Task 5: Report Router

**Files:**
- Create: `backend/app/routers/report.py`
- Create: `backend/tests/routers/test_report_router.py`

- [ ] **Step 1: Write failing tests**

```python
# backend/tests/routers/test_report_router.py
from unittest.mock import AsyncMock, patch, MagicMock
import pytest
from httpx import AsyncClient, ASGITransport
from backend.app.main import app


@pytest.fixture
def campaign_doc():
    return {
        "id": "camp-001", "mandate_id": "mand-001", "tenant_id": "tenant-001",
        "status": "live", "concepts": [], "selected_concept_id": None,
        "activation_plan": [], "budget_proposal": None,
        "created_at": "2026-01-01T00:00:00", "updated_at": "2026-01-01T00:00:00",
    }


@pytest.mark.asyncio
async def test_generate_report_returns_job_queued(campaign_doc):
    with (
        patch("backend.app.routers.report.CampaignService") as MockSvc,
        patch("backend.app.routers.report.generate_daily_report_task") as mock_task,
        patch("backend.app.core.auth.current_user", return_value=MagicMock(id="user-1")),
        patch("backend.app.core.dependencies.get_current_tenant", return_value="tenant-001"),
    ):
        from backend.app.schemas.campaign import CampaignResponse
        svc_instance = AsyncMock()
        svc_instance.get.return_value = CampaignResponse(**campaign_doc)
        MockSvc.return_value = svc_instance
        mock_task.delay = MagicMock()

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.post(
                "/api/v1/campaigns/camp-001/report/generate",
                headers={"Authorization": "Bearer test", "X-Tenant-ID": "tenant-001"},
            )

        assert response.status_code == 202
        body = response.json()
        assert body["status"] == "queued"
        mock_task.delay.assert_called_once_with("mand-001", "tenant-001")


@pytest.mark.asyncio
async def test_get_report_returns_404_when_missing(campaign_doc):
    with (
        patch("backend.app.routers.report.CampaignService") as MockSvc,
        patch("backend.app.routers.report.ReportService") as MockReportSvc,
        patch("backend.app.core.auth.current_user", return_value=MagicMock(id="user-1")),
        patch("backend.app.core.dependencies.get_current_tenant", return_value="tenant-001"),
    ):
        from backend.app.schemas.campaign import CampaignResponse
        svc_instance = AsyncMock()
        svc_instance.get.return_value = CampaignResponse(**campaign_doc)
        MockSvc.return_value = svc_instance
        report_svc_instance = AsyncMock()
        report_svc_instance.get_latest.return_value = None
        MockReportSvc.return_value = report_svc_instance

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.get(
                "/api/v1/campaigns/camp-001/report",
                headers={"Authorization": "Bearer test", "X-Tenant-ID": "tenant-001"},
            )

        assert response.status_code == 404


@pytest.mark.asyncio
async def test_get_report_returns_report_when_found(campaign_doc):
    with (
        patch("backend.app.routers.report.CampaignService") as MockSvc,
        patch("backend.app.routers.report.ReportService") as MockReportSvc,
        patch("backend.app.core.auth.current_user", return_value=MagicMock(id="user-1")),
        patch("backend.app.core.dependencies.get_current_tenant", return_value="tenant-001"),
    ):
        from backend.app.schemas.campaign import CampaignResponse
        svc_instance = AsyncMock()
        svc_instance.get.return_value = CampaignResponse(**campaign_doc)
        MockSvc.return_value = svc_instance
        mock_report = MagicMock()
        mock_report.report_json = {"report_type": "daily", "mandate_id": "mand-001"}
        mock_report.id = "rep-001"
        mock_report.period_start = "2026-05-21"
        mock_report.period_end = "2026-05-21"
        report_svc_instance = AsyncMock()
        report_svc_instance.get_latest.return_value = mock_report
        MockReportSvc.return_value = report_svc_instance

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.get(
                "/api/v1/campaigns/camp-001/report",
                headers={"Authorization": "Bearer test", "X-Tenant-ID": "tenant-001"},
            )

        assert response.status_code == 200
        assert response.json()["report_type"] == "daily"
```

- [ ] **Step 2: Run — expect failure**

```bash
pytest backend/tests/routers/test_report_router.py -v --no-header -q
```

Expected: `ModuleNotFoundError`

- [ ] **Step 3: Implement**

```python
# backend/app/routers/report.py
import logging
import os
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.core.auth import current_user
from backend.app.core.dependencies import get_current_tenant
from backend.app.core.models import User
from backend.app.db import get_db as _get_sql_db
from backend.app.schemas.jobs import JobQueuedResponse
from backend.app.services.campaign_service import CampaignService
from backend.app.services.report_service import ReportService
from backend.app.tasks.report_tasks import generate_daily_report_task

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1", tags=["report"])


async def get_mongo_db() -> AsyncIOMotorDatabase:
    client = AsyncIOMotorClient(os.getenv("MONGO_DB_URL", "mongodb://localhost:27017"))
    return client[os.getenv("MONGO_DB_NAME", "ntm")]


async def get_sql_db():
    async for session in _get_sql_db():
        yield session


@router.post("/campaigns/{campaign_id}/report/generate", response_model=JobQueuedResponse, status_code=202)
async def generate_report(
    campaign_id: str,
    user: User = Depends(current_user),
    tenant_id: str = Depends(get_current_tenant),
    db: AsyncIOMotorDatabase = Depends(get_mongo_db),
) -> JobQueuedResponse:
    svc = CampaignService(db)
    campaign = await svc.get(campaign_id, tenant_id)
    job_id = str(uuid4())
    generate_daily_report_task.delay(campaign.mandate_id, tenant_id)
    logger.info("Queued report task", extra={"mandate_id": campaign.mandate_id})
    return JobQueuedResponse(job_id=job_id, campaign_id=campaign_id)


@router.get("/campaigns/{campaign_id}/report", status_code=200)
async def get_report(
    campaign_id: str,
    user: User = Depends(current_user),
    tenant_id: str = Depends(get_current_tenant),
    mongo_db: AsyncIOMotorDatabase = Depends(get_mongo_db),
    sql_db: AsyncSession = Depends(get_sql_db),
) -> dict:
    svc = CampaignService(mongo_db)
    campaign = await svc.get(campaign_id, tenant_id)
    report_svc = ReportService(sql_db)
    report = await report_svc.get_latest(campaign.mandate_id, "daily", tenant_id)
    if not report:
        raise HTTPException(status_code=404, detail="No report found. Generate one first.")
    return report.report_json
```

- [ ] **Step 4: Run tests — expect pass**

```bash
pytest backend/tests/routers/test_report_router.py -v --no-header -q
```

Expected: `3 passed`

- [ ] **Step 5: Commit**

```bash
git add backend/app/routers/report.py backend/tests/routers/test_report_router.py
git commit -m "[TASK-phase4] feat: report router POST generate + GET latest"
```

---

## Task 6: Register All Routers

**Files:**
- Modify: `backend/app/routers/__init__.py`

- [ ] **Step 1: Update `__init__.py`**

Replace the entire file contents with:

```python
# backend/app/routers/__init__.py
"""Router aggregator — mounts all domain routers onto the FastAPI app."""

from fastapi import FastAPI

from backend.app.routers.mandate import router as mandate_router
from backend.app.routers.campaign import router as campaign_router
from backend.app.routers.creative_director import router as creative_director_router
from backend.app.routers.digital_activator import router as digital_activator_router
from backend.app.routers.analytics import router as analytics_router
from backend.app.routers.replanning import router as replanning_router
from backend.app.routers.report import router as report_router


def register_routers(app: FastAPI) -> None:
    app.include_router(mandate_router)
    app.include_router(campaign_router)
    app.include_router(creative_director_router)
    app.include_router(digital_activator_router)
    app.include_router(analytics_router)
    app.include_router(replanning_router)
    app.include_router(report_router)
```

- [ ] **Step 2: Verify routes appear**

```bash
python -c "
from backend.app.main import app
phase4_routes = [r.path for r in app.routes if hasattr(r, 'path') and any(x in r.path for x in ['activate', 'analytics', 'replan', 'report'])]
for r in sorted(phase4_routes): print(r)
"
```

Expected output:
```
/api/v1/campaigns/{campaign_id}/activate
/api/v1/campaigns/{campaign_id}/analytics
/api/v1/campaigns/{campaign_id}/analytics/run
/api/v1/campaigns/{campaign_id}/replan
/api/v1/campaigns/{campaign_id}/report
/api/v1/campaigns/{campaign_id}/report/generate
```

- [ ] **Step 3: Run full test suite to confirm no regressions**

```bash
pytest --tb=short -q --no-header 2>&1 | tail -5
```

Expected: all tests pass, coverage ≥ 60%

- [ ] **Step 4: Commit**

```bash
git add backend/app/routers/__init__.py
git commit -m "[TASK-phase4] feat: register phase4 routers in app"
```
