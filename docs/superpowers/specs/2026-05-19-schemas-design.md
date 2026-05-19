# Campaign Schemas Design

**Date:** 2026-05-19
**Scope:** Router-driven — campaign schemas only

## Problem

`routers/campaign.py` defines 4 Pydantic schemas inline (CampaignCreateRequest, CampaignUpdateRequest, CampaignConfirmRequest, CampaignResponse). None of the 7 campaign endpoints declare `response_model`, so FastAPI emits untyped `dict` responses and the OpenAPI doc is missing response shapes.

## Goal

- Extract inline schemas to `schemas/campaign.py`
- Add typed `CampaignResponse` with status enum and MongoDB `_id` remapping
- Wire `response_model=CampaignResponse` on all 7 campaign endpoints
- Export new schemas from `schemas/__init__.py`
- Add schema unit tests

## `schemas/campaign.py`

### CampaignStatusEnum

```python
class CampaignStatusEnum(str, Enum):
    pending = "pending"
    concepts_ready = "concepts_ready"
    confirmed = "confirmed"
    planned = "planned"
    budget_proposed = "budget_proposed"
    approved = "approved"
```

### Request schemas (moved from router, unchanged)

```python
class CampaignCreateRequest(BaseModel):
    mandate_id: str

class CampaignUpdateRequest(BaseModel):
    mandate_id: str | None = None
    selected_concept_id: str | None = None

class CampaignConfirmRequest(BaseModel):
    selected_concept_id: str
```

### CampaignResponse

```python
class CampaignResponse(BaseModel):
    id: str
    tenant_id: str
    mandate_id: str
    status: CampaignStatusEnum
    concepts: list[dict] = []
    selected_concept_id: str | None = None
    activation_plan: list[dict] | None = None
    budget_proposal: dict | None = None
    created_at: str | None = None
    updated_at: str | None = None

    @model_validator(mode='before')
    @classmethod
    def _remap_mongo_id(cls, data):
        if isinstance(data, dict) and "_id" in data and "id" not in data:
            data = dict(data)
            data["id"] = data.pop("_id")
        return data
```

`concepts`, `activation_plan`, `budget_proposal` stay as `dict`/`list[dict]` — these are validated at the agent layer and stored as flexible JSON in MongoDB. Over-typing them would couple campaign response to agent output schemas.

## Router changes (`routers/campaign.py`)

- Remove 4 inline class definitions
- Import from `backend.app.schemas.campaign`
- Add `response_model=CampaignResponse` to all 7 endpoints:
  - `POST /campaigns`
  - `GET /campaigns/{id}`
  - `PUT /campaigns/{id}`
  - `POST /campaigns/{id}/confirm`
  - `GET /campaigns/{id}/activation-plan`
  - `POST /campaigns/{id}/approve-budget`
  - `POST /campaigns/{id}/confirm-budget`

## `schemas/__init__.py`

Add block importing: `CampaignStatusEnum`, `CampaignCreateRequest`, `CampaignUpdateRequest`, `CampaignConfirmRequest`, `CampaignResponse`

## Tests (`backend/app/schemas/tests/test_campaign.py`)

| Test | What it checks |
|------|----------------|
| `test_response_from_mongo_doc` | `_id` remapped to `id` |
| `test_response_from_id_key` | `id` key accepted directly |
| `test_status_enum_valid` | all 6 status values accepted |
| `test_status_enum_invalid` | unknown status raises ValidationError |
| `test_create_request_requires_mandate_id` | missing field raises error |
| `test_update_request_all_none` | all-None passes validation |
| `test_confirm_request_requires_concept_id` | missing field raises error |

## File changes summary

| File | Action |
|------|--------|
| `backend/app/schemas/campaign.py` | Create |
| `backend/app/schemas/__init__.py` | Update (add exports) |
| `backend/app/routers/campaign.py` | Update (remove inline, import, add response_model) |
| `backend/app/schemas/tests/__init__.py` | Create (if not exists) |
| `backend/app/schemas/tests/test_campaign.py` | Create |
