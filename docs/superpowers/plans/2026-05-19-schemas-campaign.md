# Campaign Schemas Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Extract inline campaign schemas from the router into `schemas/campaign.py`, add a typed `CampaignResponse` with status enum and MongoDB `_id` remapping, and wire `response_model=CampaignResponse` on all 7 campaign endpoints.

**Architecture:** New `schemas/campaign.py` holds all 5 Pydantic models. A `model_validator(mode='before')` on `CampaignResponse` remaps MongoDB's `_id` key to `id` transparently. The router drops its inline definitions and imports from the schemas module. FastAPI handles dict-to-model coercion via `response_model`.

**Tech Stack:** Python 3.12, Pydantic v2, FastAPI

---

## File Map

| File | Action |
|------|--------|
| `backend/app/schemas/campaign.py` | **Create** — 5 Pydantic models |
| `backend/app/schemas/tests/__init__.py` | **Create** — empty package marker |
| `backend/app/schemas/tests/test_campaign.py` | **Create** — 7 unit tests |
| `backend/app/schemas/__init__.py` | **Modify** — add campaign exports |
| `backend/app/routers/campaign.py` | **Modify** — remove inline schemas, import from schemas, add response_model |

---

### Task 1: Write failing tests for campaign schemas

**Files:**
- Create: `backend/app/schemas/tests/__init__.py`
- Create: `backend/app/schemas/tests/test_campaign.py`

- [ ] **Step 1: Create the tests package**

Create `backend/app/schemas/tests/__init__.py` — empty file.

- [ ] **Step 2: Write the failing tests**

Create `backend/app/schemas/tests/test_campaign.py`:

```python
import pytest
from pydantic import ValidationError

from backend.app.schemas.campaign import (
    CampaignStatusEnum,
    CampaignCreateRequest,
    CampaignUpdateRequest,
    CampaignConfirmRequest,
    CampaignResponse,
)


def _base_doc(**overrides):
    doc = {
        "id": "abc123",
        "tenant_id": "t1",
        "mandate_id": "m1",
        "status": "pending",
        "concepts": [],
    }
    doc.update(overrides)
    return doc


def test_response_from_mongo_doc():
    doc = {
        "_id": "abc123",
        "tenant_id": "t1",
        "mandate_id": "m1",
        "status": "pending",
        "concepts": [],
    }
    resp = CampaignResponse.model_validate(doc)
    assert resp.id == "abc123"


def test_response_from_id_key():
    resp = CampaignResponse.model_validate(_base_doc(status="concepts_ready"))
    assert resp.id == "abc123"


def test_status_enum_valid():
    for status in ["pending", "concepts_ready", "confirmed", "planned", "budget_proposed", "approved"]:
        resp = CampaignResponse.model_validate(_base_doc(status=status))
        assert resp.status == CampaignStatusEnum(status)


def test_status_enum_invalid():
    with pytest.raises(ValidationError):
        CampaignResponse.model_validate(_base_doc(status="INVALID"))


def test_create_request_requires_mandate_id():
    with pytest.raises(ValidationError):
        CampaignCreateRequest()


def test_update_request_all_none():
    req = CampaignUpdateRequest()
    assert req.mandate_id is None
    assert req.selected_concept_id is None


def test_confirm_request_requires_concept_id():
    with pytest.raises(ValidationError):
        CampaignConfirmRequest()
```

- [ ] **Step 3: Run tests — expect ImportError (module does not exist yet)**

```bash
cd D:/staging/ntm
python -m pytest backend/app/schemas/tests/test_campaign.py -v 2>&1 | head -20
```

Expected: `ModuleNotFoundError: No module named 'backend.app.schemas.campaign'`

---

### Task 2: Create `schemas/campaign.py`

**Files:**
- Create: `backend/app/schemas/campaign.py`

- [ ] **Step 1: Create the schema file**

Create `backend/app/schemas/campaign.py`:

```python
"""Pydantic schemas for campaign CRUD and lifecycle endpoints."""

from enum import Enum
from typing import Any

from pydantic import BaseModel, model_validator


class CampaignStatusEnum(str, Enum):
    pending = "pending"
    concepts_ready = "concepts_ready"
    confirmed = "confirmed"
    planned = "planned"
    budget_proposed = "budget_proposed"
    approved = "approved"


class CampaignCreateRequest(BaseModel):
    mandate_id: str


class CampaignUpdateRequest(BaseModel):
    mandate_id: str | None = None
    selected_concept_id: str | None = None


class CampaignConfirmRequest(BaseModel):
    selected_concept_id: str


class CampaignResponse(BaseModel):
    id: str
    tenant_id: str
    mandate_id: str
    status: CampaignStatusEnum
    concepts: list[dict[str, Any]] = []
    selected_concept_id: str | None = None
    activation_plan: list[dict[str, Any]] | None = None
    budget_proposal: dict[str, Any] | None = None
    created_at: str | None = None
    updated_at: str | None = None

    @model_validator(mode="before")
    @classmethod
    def _remap_mongo_id(cls, data: Any) -> Any:
        if isinstance(data, dict) and "_id" in data and "id" not in data:
            data = dict(data)
            data["id"] = data.pop("_id")
        return data
```

- [ ] **Step 2: Run tests — expect all 7 to pass**

```bash
cd D:/staging/ntm
python -m pytest backend/app/schemas/tests/test_campaign.py -v
```

Expected output:
```
test_campaign.py::test_response_from_mongo_doc PASSED
test_campaign.py::test_response_from_id_key PASSED
test_campaign.py::test_status_enum_valid PASSED
test_campaign.py::test_status_enum_invalid PASSED
test_campaign.py::test_create_request_requires_mandate_id PASSED
test_campaign.py::test_update_request_all_none PASSED
test_campaign.py::test_confirm_request_requires_concept_id PASSED
7 passed
```

- [ ] **Step 3: Commit**

```bash
git add backend/app/schemas/campaign.py backend/app/schemas/tests/__init__.py backend/app/schemas/tests/test_campaign.py
git commit -m "[TASK-schemas] feat: add campaign schemas with status enum and mongo id remapping"
```

---

### Task 3: Export campaign schemas from `schemas/__init__.py`

**Files:**
- Modify: `backend/app/schemas/__init__.py`

- [ ] **Step 1: Add campaign imports and exports**

In `backend/app/schemas/__init__.py`, add after the existing imports (after line 32, before `__all__`):

```python
from backend.app.schemas.campaign import (
    CampaignStatusEnum,
    CampaignCreateRequest,
    CampaignUpdateRequest,
    CampaignConfirmRequest,
    CampaignResponse,
)
```

And extend `__all__` with:

```python
    "CampaignStatusEnum",
    "CampaignCreateRequest",
    "CampaignUpdateRequest",
    "CampaignConfirmRequest",
    "CampaignResponse",
```

The full updated file:

```python
"""Schemas module for NTM application."""

from backend.app.schemas.campaign import (
    CampaignStatusEnum,
    CampaignCreateRequest,
    CampaignUpdateRequest,
    CampaignConfirmRequest,
    CampaignResponse,
)
from backend.app.schemas.campaign_concept import (
    CampaignConcept,
    AudienceSegmentation,
    ChannelRecommendation,
    MessageArchitecture,
    CampaignPhasing,
    ToneBoard,
    RiskFlags,
)
from backend.app.schemas.media_plan import (
    Activation,
    BudgetSummary,
    PhaseBreakdown,
    ChannelSpend,
    ContingencyBreakdown,
    MediaPlanResponse,
    ChannelEnum,
    PhaseEnum,
    AudienceSegmentEnum,
)
from backend.app.schemas.budget_optimizer import (
    OptimizedActivation,
    ROIAnalysis,
    BudgetOptimizerResponse,
    OptimizationReport,
    PhaseROISummary,
    ChannelROISummary,
    BudgetShift,
    OptimizationActionEnum,
)

__all__ = [
    "CampaignStatusEnum",
    "CampaignCreateRequest",
    "CampaignUpdateRequest",
    "CampaignConfirmRequest",
    "CampaignResponse",
    "CampaignConcept",
    "AudienceSegmentation",
    "ChannelRecommendation",
    "MessageArchitecture",
    "CampaignPhasing",
    "ToneBoard",
    "RiskFlags",
    "Activation",
    "BudgetSummary",
    "PhaseBreakdown",
    "ChannelSpend",
    "ContingencyBreakdown",
    "MediaPlanResponse",
    "ChannelEnum",
    "PhaseEnum",
    "AudienceSegmentEnum",
    "OptimizedActivation",
    "ROIAnalysis",
    "BudgetOptimizerResponse",
    "OptimizationReport",
    "PhaseROISummary",
    "ChannelROISummary",
    "BudgetShift",
    "OptimizationActionEnum",
]
```

- [ ] **Step 2: Verify import works**

```bash
cd D:/staging/ntm
python -c "from backend.app.schemas import CampaignResponse, CampaignStatusEnum; print('OK')"
```

Expected: `OK`

- [ ] **Step 3: Commit**

```bash
git add backend/app/schemas/__init__.py
git commit -m "[TASK-schemas] feat: export campaign schemas from schemas __init__"
```

---

### Task 4: Update `routers/campaign.py`

**Files:**
- Modify: `backend/app/routers/campaign.py`

- [ ] **Step 1: Replace the router file**

Replace the full content of `backend/app/routers/campaign.py` with:

```python
"""FastAPI router for Campaign endpoints (TASK-012)."""

import logging
import os

from fastapi import APIRouter, Depends, HTTPException
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase

from backend.app.core.auth import current_user
from backend.app.core.dependencies import get_current_tenant
from backend.app.core.models import User
from backend.app.schemas.campaign import (
    CampaignCreateRequest,
    CampaignUpdateRequest,
    CampaignConfirmRequest,
    CampaignResponse,
)
from backend.app.services.campaign_service import CampaignService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1", tags=["campaigns"])


# ---------------------------------------------------------------------------
# Dependency
# ---------------------------------------------------------------------------

async def get_db() -> AsyncIOMotorDatabase:
    mongo_url = os.getenv("MONGO_DB_URL", "mongodb://localhost:27017")
    mongo_db_name = os.getenv("MONGO_DB_NAME", "ntm")
    client = AsyncIOMotorClient(mongo_url)
    return client[mongo_db_name]


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.post("/campaigns", response_model=CampaignResponse, status_code=201)
async def create_campaign(
    body: CampaignCreateRequest,
    user: User = Depends(current_user),
    tenant_id: str = Depends(get_current_tenant),
    db: AsyncIOMotorDatabase = Depends(get_db),
) -> CampaignResponse:
    svc = CampaignService(db)
    return await svc.create(body.mandate_id, tenant_id)


@router.get("/campaigns/{campaign_id}", response_model=CampaignResponse, status_code=200)
async def get_campaign(
    campaign_id: str,
    user: User = Depends(current_user),
    tenant_id: str = Depends(get_current_tenant),
    db: AsyncIOMotorDatabase = Depends(get_db),
) -> CampaignResponse:
    svc = CampaignService(db)
    return await svc.get(campaign_id, tenant_id)


@router.put("/campaigns/{campaign_id}", response_model=CampaignResponse, status_code=200)
async def update_campaign(
    campaign_id: str,
    body: CampaignUpdateRequest,
    user: User = Depends(current_user),
    tenant_id: str = Depends(get_current_tenant),
    db: AsyncIOMotorDatabase = Depends(get_db),
) -> CampaignResponse:
    svc = CampaignService(db)
    return await svc.update(campaign_id, tenant_id, body.model_dump(exclude_none=True))


@router.post("/campaigns/{campaign_id}/confirm", response_model=CampaignResponse, status_code=200)
async def confirm_campaign(
    campaign_id: str,
    body: CampaignConfirmRequest,
    user: User = Depends(current_user),
    tenant_id: str = Depends(get_current_tenant),
    db: AsyncIOMotorDatabase = Depends(get_db),
) -> CampaignResponse:
    svc = CampaignService(db)
    return await svc.confirm(campaign_id, body.selected_concept_id, tenant_id)


@router.get("/campaigns/{campaign_id}/activation-plan", response_model=CampaignResponse, status_code=200)
async def get_activation_plan(
    campaign_id: str,
    user: User = Depends(current_user),
    tenant_id: str = Depends(get_current_tenant),
    db: AsyncIOMotorDatabase = Depends(get_db),
) -> CampaignResponse:
    svc = CampaignService(db)
    return await svc.get_activation_plan(campaign_id, tenant_id)


@router.post("/campaigns/{campaign_id}/approve-budget", response_model=CampaignResponse, status_code=200)
async def propose_budget(
    campaign_id: str,
    user: User = Depends(current_user),
    tenant_id: str = Depends(get_current_tenant),
    db: AsyncIOMotorDatabase = Depends(get_db),
) -> CampaignResponse:
    svc = CampaignService(db)
    return await svc.propose_budget(campaign_id, tenant_id)


@router.post("/campaigns/{campaign_id}/confirm-budget", response_model=CampaignResponse, status_code=200)
async def confirm_budget(
    campaign_id: str,
    user: User = Depends(current_user),
    tenant_id: str = Depends(get_current_tenant),
    db: AsyncIOMotorDatabase = Depends(get_db),
) -> CampaignResponse:
    svc = CampaignService(db)
    return await svc.confirm_budget(campaign_id, tenant_id)
```

- [ ] **Step 2: Verify router imports cleanly**

```bash
cd D:/staging/ntm
python -c "from backend.app.routers.campaign import router; print('OK')"
```

Expected: `OK`

- [ ] **Step 3: Run full schema + router test suite**

```bash
cd D:/staging/ntm
python -m pytest backend/app/schemas/tests/test_campaign.py backend/app/routers/tests/ -v 2>&1 | tail -20
```

Expected: all previously passing router tests still pass, plus 7 new schema tests pass.

- [ ] **Step 4: Commit**

```bash
git add backend/app/routers/campaign.py
git commit -m "[TASK-schemas] refactor: extract inline schemas from campaign router, add response_model"
```

---

### Task 5: Final verification

- [ ] **Step 1: Run the full backend test suite**

```bash
cd D:/staging/ntm
python -m pytest backend/ -v --tb=short 2>&1 | tail -30
```

Expected: no regressions. New count includes 7 additional schema tests.

- [ ] **Step 2: Verify OpenAPI schema renders CampaignResponse**

```bash
cd D:/staging/ntm
python -c "
from backend.app.routers.campaign import router
for route in router.routes:
    if hasattr(route, 'response_model'):
        print(route.path, '->', route.response_model)
"
```

Expected: all 7 routes show `-> <class 'backend.app.schemas.campaign.CampaignResponse'>`.
