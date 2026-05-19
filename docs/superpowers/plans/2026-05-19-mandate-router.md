# Mandate Router Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add mandate CRUD + lifecycle endpoints to the existing mandate router, backed by a MandateService (SQLAlchemy/Postgres) and a Celery task for AGT-01 analysis.

**Architecture:** Thin router delegates to `MandateService` (same pattern as `CampaignService`). Mandate records live in Postgres via the existing SQLAlchemy `Mandate` model. AGT-01 summary card output is stored in MongoDB `mandate_analyses`. Celery tasks use `@shared_task(bind=True)` + `asyncio.run()` wrapper (same pattern as `competitive_intel_tasks.py`).

**Tech Stack:** FastAPI, SQLAlchemy async (asyncpg), Motor (MongoDB), Celery (shared_task), pytest, pytest-asyncio, FastAPI TestClient, unittest.mock

---

## File Map

| Action | Path |
|--------|------|
| Create | `backend/app/schemas/mandate.py` |
| Create | `backend/app/services/mandate_service.py` |
| Create | `backend/app/tasks/mandate_tasks.py` |
| Create | `backend/app/tasks/campaign_tasks.py` |
| Modify | `backend/app/routers/mandate.py` |
| Create | `backend/tests/services/__init__.py` |
| Create | `backend/tests/services/test_mandate_service.py` |
| Create | `backend/tests/tasks/__init__.py` |
| Create | `backend/tests/tasks/test_mandate_tasks.py` |
| Modify | `backend/tests/routers/test_mandate_router.py` |

---

## Task 1: Mandate Schemas

**Files:**
- Create: `backend/app/schemas/mandate.py`
- Create: `backend/tests/services/__init__.py` (empty)
- Test inline in Task 2 (schemas validated via service tests)

- [ ] **Step 1: Write the failing import test**

Create `backend/tests/services/__init__.py` (empty file), then run:

```bash
python -c "from backend.app.schemas.mandate import CreateMandateRequest, UpdateMandateRequest, MandateResponse"
```

Expected: `ModuleNotFoundError: No module named 'backend.app.schemas.mandate'`

- [ ] **Step 2: Create `backend/app/schemas/mandate.py`**

```python
"""Pydantic schemas for mandate CRUD and lifecycle endpoints."""

from datetime import date, datetime
from pydantic import BaseModel


class CreateMandateRequest(BaseModel):
    name: str
    client_id: str
    objective: str
    region: str
    total_budget: float
    currency: str
    start_date: date
    end_date: date
    description: str | None = None
    countries: list[str] = []
    competitors: list[str] = []


class UpdateMandateRequest(BaseModel):
    name: str | None = None
    client_id: str | None = None
    objective: str | None = None
    region: str | None = None
    total_budget: float | None = None
    currency: str | None = None
    start_date: date | None = None
    end_date: date | None = None
    description: str | None = None
    countries: list[str] | None = None
    competitors: list[str] | None = None


class MandateResponse(BaseModel):
    id: str
    tenant_id: str
    client_id: str
    name: str
    status: str
    objective: str
    region: str
    total_budget: float
    currency: str
    start_date: date | None
    end_date: date | None
    description: str | None
    countries: list[str]
    competitors: list[str]
    created_at: datetime | None
    updated_at: datetime | None
```

- [ ] **Step 3: Verify import succeeds**

```bash
python -c "from backend.app.schemas.mandate import CreateMandateRequest, UpdateMandateRequest, MandateResponse; print('OK')"
```

Expected: `OK`

- [ ] **Step 4: Commit**

```bash
git add backend/app/schemas/mandate.py backend/tests/services/__init__.py
git commit -m "[TASK-007] feat: add mandate Pydantic schemas"
```

---

## Task 2: MandateService

**Files:**
- Create: `backend/app/services/mandate_service.py`
- Create: `backend/tests/services/test_mandate_service.py`

- [ ] **Step 1: Write the failing tests**

Create `backend/tests/services/test_mandate_service.py`:

```python
"""Unit tests for MandateService."""

import pytest
from unittest.mock import AsyncMock, MagicMock
from fastapi import HTTPException
from datetime import date

from backend.app.schemas.mandate import CreateMandateRequest, UpdateMandateRequest


def make_mock_session(mandate=None):
    """Return a mock AsyncSession whose execute() yields the given mandate."""
    result = MagicMock()
    result.scalar_one_or_none.return_value = mandate
    session = MagicMock()
    session.execute = AsyncMock(return_value=result)
    session.add = MagicMock()
    session.commit = AsyncMock()
    session.refresh = AsyncMock()
    return session


def make_mandate(status="draft"):
    m = MagicMock()
    m.id = "m-001"
    m.tenant_id = "tenant-1"
    m.client_id = "c-001"
    m.name = "Test Mandate"
    m.status = status
    m.to_dict.return_value = {"id": "m-001", "status": status, "tenant_id": "tenant-1"}
    return m


# ── get ───────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_get_mandate_not_found_raises_404():
    from backend.app.services.mandate_service import MandateService
    session = make_mock_session(mandate=None)
    svc = MandateService(session)
    with pytest.raises(HTTPException) as exc:
        await svc.get("nonexistent", "tenant-1")
    assert exc.value.status_code == 404


@pytest.mark.asyncio
async def test_get_mandate_returns_dict():
    from backend.app.services.mandate_service import MandateService
    session = make_mock_session(mandate=make_mandate())
    svc = MandateService(session)
    result = await svc.get("m-001", "tenant-1")
    assert result["id"] == "m-001"


# ── update ────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_update_non_draft_raises_409():
    from backend.app.services.mandate_service import MandateService
    session = make_mock_session(mandate=make_mandate(status="analyzed"))
    svc = MandateService(session)
    with pytest.raises(HTTPException) as exc:
        await svc.update("m-001", UpdateMandateRequest(name="new"), "tenant-1")
    assert exc.value.status_code == 409


@pytest.mark.asyncio
async def test_update_draft_mandate_succeeds():
    from backend.app.services.mandate_service import MandateService
    mandate = make_mandate(status="draft")
    session = make_mock_session(mandate=mandate)
    svc = MandateService(session)
    result = await svc.update("m-001", UpdateMandateRequest(name="Updated"), "tenant-1")
    assert result["id"] == "m-001"
    assert session.commit.called


# ── confirm ───────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_confirm_non_analyzed_raises_400():
    from backend.app.services.mandate_service import MandateService
    session = make_mock_session(mandate=make_mandate(status="draft"))
    svc = MandateService(session)
    with pytest.raises(HTTPException) as exc:
        await svc.confirm("m-001", "tenant-1")
    assert exc.value.status_code == 400


@pytest.mark.asyncio
async def test_confirm_analyzed_mandate_sets_confirmed():
    from backend.app.services.mandate_service import MandateService
    mandate = make_mandate(status="analyzed")
    session = make_mock_session(mandate=mandate)
    svc = MandateService(session)
    result = await svc.confirm("m-001", "tenant-1")
    assert mandate.status == "confirmed"
    assert session.commit.called


# ── get_summary_card ──────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_get_summary_card_not_found_raises_404():
    from backend.app.services.mandate_service import MandateService
    session = make_mock_session(mandate=make_mandate())
    mongo_col = MagicMock()
    mongo_col.find_one = AsyncMock(return_value=None)
    mongo_db = MagicMock()
    mongo_db.__getitem__ = MagicMock(return_value=mongo_col)
    svc = MandateService(session)
    with pytest.raises(HTTPException) as exc:
        await svc.get_summary_card("m-001", "tenant-1", mongo_db)
    assert exc.value.status_code == 404


@pytest.mark.asyncio
async def test_get_summary_card_returns_doc():
    from backend.app.services.mandate_service import MandateService
    session = make_mock_session(mandate=make_mandate())
    mongo_col = MagicMock()
    mongo_col.find_one = AsyncMock(return_value={"mandate_id": "m-001", "score": 90, "_id": "x"})
    mongo_db = MagicMock()
    mongo_db.__getitem__ = MagicMock(return_value=mongo_col)
    svc = MandateService(session)
    result = await svc.get_summary_card("m-001", "tenant-1", mongo_db)
    assert result["score"] == 90
    assert "_id" not in result
```

- [ ] **Step 2: Run tests — verify they fail**

```bash
python -m pytest backend/tests/services/test_mandate_service.py -v --no-cov 2>&1 | head -30
```

Expected: `ImportError: cannot import name 'MandateService'`

- [ ] **Step 3: Create `backend/app/services/mandate_service.py`**

```python
"""MandateService — CRUD and lifecycle for mandate records (SQLAlchemy/Postgres)."""

import logging
import uuid
from datetime import datetime, timezone

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.models.mandate import Mandate
from backend.app.schemas.mandate import CreateMandateRequest, UpdateMandateRequest

logger = logging.getLogger(__name__)


class MandateService:
    def __init__(self, db: AsyncSession):
        self._db = db

    async def _get_or_404(self, mandate_id: str, tenant_id: str) -> Mandate:
        result = await self._db.execute(
            select(Mandate).where(
                Mandate.id == mandate_id,
                Mandate.tenant_id == tenant_id,
            )
        )
        mandate = result.scalar_one_or_none()
        if mandate is None:
            raise HTTPException(status_code=404, detail="Mandate not found")
        return mandate

    async def create(self, data: CreateMandateRequest, user_id: str, tenant_id: str) -> dict:
        mandate = Mandate(
            id=str(uuid.uuid4()),
            tenant_id=tenant_id,
            client_id=data.client_id,
            name=data.name,
            description=data.description,
            objective=data.objective,
            region=data.region,
            countries=data.countries,
            competitors=data.competitors,
            total_budget=data.total_budget,
            currency=data.currency,
            start_date=data.start_date,
            end_date=data.end_date,
            status="draft",
        )
        self._db.add(mandate)
        await self._db.commit()
        await self._db.refresh(mandate)
        return mandate.to_dict()

    async def get(self, mandate_id: str, tenant_id: str) -> dict:
        mandate = await self._get_or_404(mandate_id, tenant_id)
        return mandate.to_dict()

    async def update(self, mandate_id: str, data: UpdateMandateRequest, tenant_id: str) -> dict:
        mandate = await self._get_or_404(mandate_id, tenant_id)
        if mandate.status != "draft":
            raise HTTPException(
                status_code=409,
                detail=f"Cannot update mandate in status '{mandate.status}'"
            )
        for field, value in data.model_dump(exclude_none=True).items():
            setattr(mandate, field, value)
        await self._db.commit()
        await self._db.refresh(mandate)
        return mandate.to_dict()

    async def confirm(self, mandate_id: str, tenant_id: str) -> dict:
        mandate = await self._get_or_404(mandate_id, tenant_id)
        if mandate.status != "analyzed":
            raise HTTPException(
                status_code=400,
                detail=f"Cannot confirm mandate in status '{mandate.status}'"
            )
        mandate.status = "confirmed"
        await self._db.commit()
        await self._db.refresh(mandate)
        return mandate.to_dict()

    async def get_summary_card(self, mandate_id: str, tenant_id: str, mongo_db) -> dict:
        await self._get_or_404(mandate_id, tenant_id)
        doc = await mongo_db["mandate_analyses"].find_one(
            {"mandate_id": mandate_id, "tenant_id": tenant_id}
        )
        if not doc:
            raise HTTPException(status_code=404, detail="Summary card not yet available")
        doc.pop("_id", None)
        return doc
```

- [ ] **Step 4: Run tests — verify they pass**

```bash
python -m pytest backend/tests/services/test_mandate_service.py -v --no-cov
```

Expected: `8 passed`

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/mandate_service.py backend/tests/services/test_mandate_service.py
git commit -m "[TASK-007] feat: add MandateService with CRUD and lifecycle methods"
```

---

## Task 3: Celery Tasks

**Files:**
- Create: `backend/app/tasks/mandate_tasks.py`
- Create: `backend/tests/tasks/__init__.py` (empty)
- Create: `backend/tests/tasks/test_mandate_tasks.py`

- [ ] **Step 1: Write the failing tests**

Create `backend/tests/tasks/__init__.py` (empty), then create `backend/tests/tasks/test_mandate_tasks.py`:

```python
"""Unit tests for mandate Celery tasks."""

from unittest.mock import patch, MagicMock


def test_run_mandate_analysis_is_celery_task():
    from backend.app.tasks.mandate_tasks import run_mandate_analysis
    assert hasattr(run_mandate_analysis, 'delay'), "must be a Celery task"


def test_run_mandate_analysis_sets_analyzing_then_analyzed():
    """Task should update status to analyzing, run AGT-01, then set analyzed."""
    from backend.app.tasks.mandate_tasks import run_mandate_analysis

    with patch("backend.app.tasks.mandate_tasks.asyncio.run") as mock_run:
        mock_run.return_value = None
        # Should not raise
        run_mandate_analysis("m-001", "tenant-1")
        assert mock_run.called


def test_run_mandate_analysis_handles_exception_gracefully():
    """Task should not propagate uncaught exceptions (logs and returns)."""
    from backend.app.tasks.mandate_tasks import run_mandate_analysis

    with patch("backend.app.tasks.mandate_tasks.asyncio.run", side_effect=Exception("boom")):
        # Should not raise — error is logged, not re-raised
        try:
            run_mandate_analysis("m-001", "tenant-1")
        except Exception:
            assert False, "run_mandate_analysis must not propagate exceptions"
```

- [ ] **Step 2: Run tests — verify they fail**

```bash
python -m pytest backend/tests/tasks/test_mandate_tasks.py -v --no-cov 2>&1 | head -20
```

Expected: `ImportError: cannot import name 'run_mandate_analysis'`

- [ ] **Step 3: Create `backend/app/tasks/mandate_tasks.py`**

```python
"""Celery task for AGT-01 mandate analysis."""

import asyncio
import logging
import os
from datetime import datetime, timezone

from celery import shared_task
from motor.motor_asyncio import AsyncIOMotorClient
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy import select, update

from backend.app.models.mandate import Mandate
from backend.app.agents.mandate_analyst import mandate_analyst_agent

logger = logging.getLogger(__name__)

MONGO_DB_URL = os.getenv("MONGO_DB_URL", "mongodb://localhost:27017")
MONGO_DB_NAME = os.getenv("MONGO_DB_NAME", "ntm")


async def _get_sql_session() -> AsyncSession:
    db_url = os.getenv("DATABASE_URL", "sqlite+aiosqlite:///:memory:")
    engine = create_async_engine(db_url, echo=False)
    factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    return factory()


async def _run_mandate_analysis(mandate_id: str, tenant_id: str) -> None:
    async with await _get_sql_session() as session:
        result = await session.execute(
            select(Mandate).where(
                Mandate.id == mandate_id,
                Mandate.tenant_id == tenant_id,
            )
        )
        mandate = result.scalar_one_or_none()
        if not mandate:
            logger.error(f"[run_mandate_analysis] mandate not found: {mandate_id}")
            return

        mandate.status = "analyzing"
        await session.commit()

        mandate_dict = mandate.to_dict()

    try:
        analysis = await mandate_analyst_agent(mandate_dict)
    except Exception as e:
        logger.error(f"[run_mandate_analysis] AGT-01 failed for {mandate_id}: {e}")
        analysis = {"error": str(e), "completeness_score": 0}

    mongo_client = AsyncIOMotorClient(MONGO_DB_URL)
    db = mongo_client[MONGO_DB_NAME]
    doc = {
        "mandate_id": mandate_id,
        "tenant_id": tenant_id,
        "analysis": analysis,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    await db["mandate_analyses"].insert_one(doc)
    logger.info(f"[run_mandate_analysis] Stored analysis for mandate {mandate_id}")

    async with await _get_sql_session() as session:
        await session.execute(
            update(Mandate)
            .where(Mandate.id == mandate_id, Mandate.tenant_id == tenant_id)
            .values(status="analyzed")
        )
        await session.commit()


@shared_task(bind=True, max_retries=3)
def run_mandate_analysis(self, mandate_id: str, tenant_id: str) -> None:
    """Celery task: run AGT-01 mandate analysis and store output to MongoDB."""
    try:
        asyncio.run(_run_mandate_analysis(mandate_id, tenant_id))
    except Exception as e:
        logger.error(f"[run_mandate_analysis] task failed for {mandate_id}: {e}")
```

- [ ] **Step 4: Run tests — verify they pass**

```bash
python -m pytest backend/tests/tasks/test_mandate_tasks.py -v --no-cov
```

Expected: `3 passed`

- [ ] **Step 5: Commit**

```bash
git add backend/app/tasks/mandate_tasks.py backend/tests/tasks/__init__.py backend/tests/tasks/test_mandate_tasks.py
git commit -m "[TASK-007] feat: add run_mandate_analysis Celery task"
```

---

## Task 4: Campaign Tasks Stub

**Files:**
- Create: `backend/app/tasks/campaign_tasks.py`

The confirm endpoint dispatches `run_campaign_strategy`. Since `campaign_tasks.py` doesn't exist yet, create a minimal stub now.

- [ ] **Step 1: Write the failing test** (add to `test_mandate_tasks.py`)

Append to `backend/tests/tasks/test_mandate_tasks.py`:

```python
def test_run_campaign_strategy_is_celery_task():
    from backend.app.tasks.campaign_tasks import run_campaign_strategy
    assert hasattr(run_campaign_strategy, 'delay'), "must be a Celery task"
```

- [ ] **Step 2: Run test — verify it fails**

```bash
python -m pytest backend/tests/tasks/test_mandate_tasks.py::test_run_campaign_strategy_is_celery_task -v --no-cov 2>&1 | head -10
```

Expected: `ImportError: cannot import name 'run_campaign_strategy'`

- [ ] **Step 3: Create `backend/app/tasks/campaign_tasks.py`**

```python
"""Celery tasks for campaign pipeline (stubs — full implementation in campaign phase)."""

import asyncio
import logging

from celery import shared_task

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=3)
def run_campaign_strategy(self, mandate_id: str, tenant_id: str) -> None:
    """Celery task: run AGT-02 campaign strategy for a confirmed mandate."""
    logger.info(f"[run_campaign_strategy] mandate_id={mandate_id} tenant_id={tenant_id}")
```

- [ ] **Step 4: Run test — verify it passes**

```bash
python -m pytest backend/tests/tasks/test_mandate_tasks.py -v --no-cov
```

Expected: `4 passed`

- [ ] **Step 5: Commit**

```bash
git add backend/app/tasks/campaign_tasks.py backend/tests/tasks/test_mandate_tasks.py
git commit -m "[TASK-007] feat: add campaign_tasks stub with run_campaign_strategy"
```

---

## Task 5: Router Extension

**Files:**
- Modify: `backend/app/routers/mandate.py`
- Modify: `backend/tests/routers/test_mandate_router.py`

- [ ] **Step 1: Write the failing router tests**

Append the following to `backend/tests/routers/test_mandate_router.py` (keep all existing tests):

```python
# ── NEW: CRUD + lifecycle endpoint tests ──────────────────────────────────────
# These use MandateService (SQLAlchemy) not MongoDB.
# Import get_sql_db once it exists in the router.

from unittest.mock import patch, AsyncMock


def make_mock_sql_session():
    return MagicMock()


def make_svc_mock(**method_returns):
    svc = MagicMock()
    for method, retval in method_returns.items():
        if isinstance(retval, Exception):
            setattr(svc, method, AsyncMock(side_effect=retval))
        else:
            setattr(svc, method, AsyncMock(return_value=retval))
    return svc


def make_app_with_sql(mock_mongo_db=None, mock_sql_session=None):
    from backend.app.routers.mandate import router, get_db, get_sql_db
    app = FastAPI()
    app.include_router(router)
    mock_user = make_mock_user()
    app.dependency_overrides[current_user] = lambda: mock_user
    app.dependency_overrides[get_current_tenant] = lambda: "test-tenant"
    if mock_mongo_db is not None:
        app.dependency_overrides[get_db] = lambda: mock_mongo_db
    if mock_sql_session is not None:
        app.dependency_overrides[get_sql_db] = lambda: mock_sql_session
    return app


# ── POST /api/v1/mandates ─────────────────────────────────────────────────────

def test_create_mandate_returns_201():
    app = make_app_with_sql(mock_sql_session=make_mock_sql_session())
    mandate_payload = {
        "name": "Summer Campaign",
        "client_id": "c-001",
        "objective": "Brand awareness",
        "region": "EMEA",
        "total_budget": 100000.0,
        "currency": "USD",
        "start_date": "2026-06-01",
        "end_date": "2026-12-31",
    }
    svc = make_svc_mock(create={"id": "m-new", "status": "draft", "tenant_id": "test-tenant"})
    with patch("backend.app.routers.mandate.MandateService", return_value=svc), \
         patch("backend.app.routers.mandate.run_mandate_analysis") as mock_task:
        mock_task.delay = MagicMock()
        client = TestClient(app)
        response = client.post("/api/v1/mandates", json=mandate_payload)
    assert response.status_code == 201


def test_create_mandate_missing_required_field_returns_422():
    app = make_app_with_sql(mock_sql_session=make_mock_sql_session())
    with patch("backend.app.routers.mandate.MandateService"):
        client = TestClient(app)
        response = client.post("/api/v1/mandates", json={"name": "Incomplete"})
    assert response.status_code == 422


# ── GET /api/v1/mandates/{mandate_id} ────────────────────────────────────────

def test_get_mandate_returns_200():
    from fastapi import HTTPException
    app = make_app_with_sql(mock_sql_session=make_mock_sql_session())
    svc = make_svc_mock(get={"id": "m-001", "status": "draft", "tenant_id": "test-tenant"})
    with patch("backend.app.routers.mandate.MandateService", return_value=svc):
        client = TestClient(app)
        response = client.get("/api/v1/mandates/m-001")
    assert response.status_code == 200


def test_get_mandate_not_found_returns_404():
    from fastapi import HTTPException
    app = make_app_with_sql(mock_sql_session=make_mock_sql_session())
    svc = make_svc_mock(get=HTTPException(status_code=404, detail="Not found"))
    with patch("backend.app.routers.mandate.MandateService", return_value=svc):
        client = TestClient(app)
        response = client.get("/api/v1/mandates/nonexistent")
    assert response.status_code == 404


# ── PUT /api/v1/mandates/{mandate_id} ────────────────────────────────────────

def test_update_mandate_returns_200():
    app = make_app_with_sql(mock_sql_session=make_mock_sql_session())
    svc = make_svc_mock(update={"id": "m-001", "status": "draft", "name": "Updated"})
    with patch("backend.app.routers.mandate.MandateService", return_value=svc):
        client = TestClient(app)
        response = client.put("/api/v1/mandates/m-001", json={"name": "Updated"})
    assert response.status_code == 200


def test_update_mandate_non_draft_returns_409():
    from fastapi import HTTPException
    app = make_app_with_sql(mock_sql_session=make_mock_sql_session())
    svc = make_svc_mock(update=HTTPException(status_code=409, detail="Conflict"))
    with patch("backend.app.routers.mandate.MandateService", return_value=svc):
        client = TestClient(app)
        response = client.put("/api/v1/mandates/m-001", json={"name": "Late Update"})
    assert response.status_code == 409


# ── POST /api/v1/mandates/{mandate_id}/confirm ───────────────────────────────

def test_confirm_mandate_returns_200():
    app = make_app_with_sql(mock_sql_session=make_mock_sql_session())
    svc = make_svc_mock(confirm={"id": "m-001", "status": "confirmed"})
    with patch("backend.app.routers.mandate.MandateService", return_value=svc), \
         patch("backend.app.routers.mandate.run_campaign_strategy") as mock_task:
        mock_task.delay = MagicMock()
        client = TestClient(app)
        response = client.post("/api/v1/mandates/m-001/confirm")
    assert response.status_code == 200


def test_confirm_mandate_not_analyzed_returns_400():
    from fastapi import HTTPException
    app = make_app_with_sql(mock_sql_session=make_mock_sql_session())
    svc = make_svc_mock(confirm=HTTPException(status_code=400, detail="Not analyzed"))
    with patch("backend.app.routers.mandate.MandateService", return_value=svc):
        client = TestClient(app)
        response = client.post("/api/v1/mandates/m-001/confirm")
    assert response.status_code == 400


# ── GET /api/v1/mandates/{mandate_id}/summary-card ───────────────────────────

def test_get_summary_card_returns_200():
    mongo_db = make_mock_db()
    app = make_app_with_sql(mock_mongo_db=mongo_db, mock_sql_session=make_mock_sql_session())
    svc = make_svc_mock(get_summary_card={"mandate_id": "m-001", "score": 90})
    with patch("backend.app.routers.mandate.MandateService", return_value=svc):
        client = TestClient(app)
        response = client.get("/api/v1/mandates/m-001/summary-card")
    assert response.status_code == 200


def test_get_summary_card_not_available_returns_404():
    from fastapi import HTTPException
    mongo_db = make_mock_db()
    app = make_app_with_sql(mock_mongo_db=mongo_db, mock_sql_session=make_mock_sql_session())
    svc = make_svc_mock(get_summary_card=HTTPException(status_code=404, detail="Not available"))
    with patch("backend.app.routers.mandate.MandateService", return_value=svc):
        client = TestClient(app)
        response = client.get("/api/v1/mandates/m-001/summary-card")
    assert response.status_code == 404
```

- [ ] **Step 2: Run new tests — verify they fail**

```bash
python -m pytest backend/tests/routers/test_mandate_router.py -v --no-cov -k "create_mandate or get_mandate or update_mandate or confirm_mandate or summary_card" 2>&1 | head -20
```

Expected: `ImportError: cannot import name 'get_sql_db'` (or similar)

- [ ] **Step 3: Extend `backend/app/routers/mandate.py`**

Add the following imports at the top (after existing imports):

```python
from sqlalchemy.ext.asyncio import AsyncSession
from backend.app.db import get_db as _get_sql_db
from backend.app.schemas.mandate import CreateMandateRequest, UpdateMandateRequest
from backend.app.services.mandate_service import MandateService
from backend.app.tasks.mandate_tasks import run_mandate_analysis
from backend.app.tasks.campaign_tasks import run_campaign_strategy
```

Add `get_sql_db` dependency after the existing `get_db` function:

```python
async def get_sql_db():
    """SQLAlchemy AsyncSession dependency (separate from MongoDB get_db above)."""
    async for session in _get_sql_db():
        yield session
```

Add the 5 new endpoints after the existing `get_job_status` endpoint:

```python
# ---------------------------------------------------------------------------
# Mandate CRUD + lifecycle (SQLAlchemy / Postgres)
# ---------------------------------------------------------------------------

@router.post("/mandates", status_code=201)
async def create_mandate(
    body: CreateMandateRequest,
    user: User = Depends(current_user),
    tenant_id: str = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_sql_db),
) -> dict:
    svc = MandateService(db)
    result = await svc.create(body, user.id, tenant_id)
    run_mandate_analysis.delay(result["id"], tenant_id)
    return result


@router.get("/mandates/{mandate_id}", status_code=200)
async def get_mandate(
    mandate_id: str,
    user: User = Depends(current_user),
    tenant_id: str = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_sql_db),
) -> dict:
    svc = MandateService(db)
    return await svc.get(mandate_id, tenant_id)


@router.put("/mandates/{mandate_id}", status_code=200)
async def update_mandate(
    mandate_id: str,
    body: UpdateMandateRequest,
    user: User = Depends(current_user),
    tenant_id: str = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_sql_db),
) -> dict:
    svc = MandateService(db)
    return await svc.update(mandate_id, body, tenant_id)


@router.post("/mandates/{mandate_id}/confirm", status_code=200)
async def confirm_mandate(
    mandate_id: str,
    user: User = Depends(current_user),
    tenant_id: str = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_sql_db),
) -> dict:
    svc = MandateService(db)
    result = await svc.confirm(mandate_id, tenant_id)
    run_campaign_strategy.delay(mandate_id, tenant_id)
    return result


@router.get("/mandates/{mandate_id}/summary-card", status_code=200)
async def get_mandate_summary_card(
    mandate_id: str,
    user: User = Depends(current_user),
    tenant_id: str = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_sql_db),
    mongo_db: AsyncIOMotorDatabase = Depends(get_db),
) -> dict:
    svc = MandateService(db)
    return await svc.get_summary_card(mandate_id, tenant_id, mongo_db)
```

- [ ] **Step 4: Run all mandate router tests — verify they pass**

```bash
python -m pytest backend/tests/routers/test_mandate_router.py -v --no-cov
```

Expected: `15 passed` (5 existing + 10 new)

- [ ] **Step 5: Commit**

```bash
git add backend/app/routers/mandate.py backend/tests/routers/test_mandate_router.py
git commit -m "[TASK-007] feat: add mandate CRUD and lifecycle endpoints"
```

---

## Task 6: Full Suite Verification

- [ ] **Step 1: Run full backend suite**

```bash
python -m pytest backend/app backend/tests --no-cov -q 2>&1 | tail -20
```

Expected: All tests pass, zero failures.

- [ ] **Step 2: Verify new tests are collected**

```bash
python -m pytest backend/tests/services/ backend/tests/tasks/ backend/tests/routers/test_mandate_router.py --collect-only --no-cov -q
```

Expected: Shows ~27 test items (8 service + 4 task + 15 router).

- [ ] **Step 3: Run coverage on new modules**

```bash
python -m pytest backend/app/services/mandate_service.py backend/tests/services/test_mandate_service.py --cov=backend/app/services/mandate_service --cov-report=term-missing --no-header -q
```

Expected: ≥80% coverage on `mandate_service.py`.

- [ ] **Step 4: Final commit if any cleanup needed**

```bash
git add -A
git status  # verify only expected files
git commit -m "[TASK-007] test: full suite verification pass"
```

---

## Route Conflict Note

The new `GET /api/v1/mandates/{mandate_id}` may conflict with the existing `POST /api/v1/mandates/{mandate_id}/analyze-competitors` because FastAPI matches routes in registration order. Both use `{mandate_id}` as a path segment. This is safe: different HTTP methods (GET vs POST) and different paths (`/mandates/{id}` vs `/mandates/{id}/analyze-competitors`). No action required.

## Known Limitations

- `run_campaign_strategy` is a stub — full AGT-02 integration is a separate task.
- The existing CI endpoint (`analyze-competitors`) reads mandates from MongoDB; new CRUD creates in Postgres. These are separate data flows until a migration task aligns them.
- SQLAlchemy pool_size config in `_get_sql_session()` inside `mandate_tasks.py` creates a new engine per task invocation — acceptable for Celery workers, can be optimized later.
