"""Unit tests for CampaignService — campaign lifecycle business logic."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi import HTTPException

from backend.app.services.campaign_service import CampaignService


def make_db(campaigns=None, mandates=None, ci_reports=None):
    """Build a mock MongoDB with configurable collection returns."""
    db = MagicMock()
    campaign_col = MagicMock()
    mandate_col = MagicMock()
    ci_col = MagicMock()

    campaign_col.find_one = AsyncMock(return_value=campaigns)
    campaign_col.insert_one = AsyncMock()
    campaign_col.find_one_and_update = AsyncMock(return_value=campaigns)

    mandate_col.find_one = AsyncMock(return_value=mandates)
    ci_col.find_one = AsyncMock(return_value=ci_reports)

    def _col(name: str):
        if name == "campaigns":
            return campaign_col
        if name == "mandates":
            return mandate_col
        if name == "ci_reports":
            return ci_col
        return MagicMock()

    db.__getitem__ = MagicMock(side_effect=_col)
    return db, campaign_col, mandate_col, ci_col


CAMPAIGN_DOC = {
    "_id": "camp-001",
    "tenant_id": "tenant-001",
    "mandate_id": "mand-001",
    "status": "concepts_ready",
    "concepts": [{"id": "concept-001", "theme": "Bold Launch"}],
    "selected_concept_id": None,
    "activation_plan": None,
    "budget_proposal": None,
}

MANDATE_DOC = {
    "_id": "mand-001",
    "tenant_id": "tenant-001",
    "title": "Brand Launch Q3",
    "objective": "brand_launch",
}

CI_REPORT_DOC = {
    "_id": "ci-001",
    "mandate_id": "mand-001",
    "tenant_id": "tenant-001",
    "status": "complete",
}


# ── get ────────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_get_campaign_returns_doc():
    db, campaign_col, _, __ = make_db(campaigns=CAMPAIGN_DOC)
    svc = CampaignService(db)

    result = await svc.get("camp-001", "tenant-001")

    campaign_col.find_one.assert_called_once_with({"_id": "camp-001", "tenant_id": "tenant-001"})
    assert result["_id"] == "camp-001"
    assert result["mandate_id"] == "mand-001"


@pytest.mark.asyncio
async def test_get_campaign_not_found_raises_404():
    db, _, __, ___ = make_db(campaigns=None)
    svc = CampaignService(db)

    with pytest.raises(HTTPException) as exc_info:
        await svc.get("nonexistent", "tenant-001")

    assert exc_info.value.status_code == 404


@pytest.mark.asyncio
async def test_get_campaign_wrong_tenant_raises_404():
    db, campaign_col, _, __ = make_db(campaigns=None)
    svc = CampaignService(db)

    with pytest.raises(HTTPException) as exc_info:
        await svc.get("camp-001", "wrong-tenant")

    assert exc_info.value.status_code == 404
    campaign_col.find_one.assert_called_once_with({"_id": "camp-001", "tenant_id": "wrong-tenant"})


# ── create ─────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_create_campaign_inserts_doc():
    db, campaign_col, _, __ = make_db(campaigns=CAMPAIGN_DOC, mandates=MANDATE_DOC, ci_reports=CI_REPORT_DOC)
    svc = CampaignService(db)

    mock_strategy_result = {
        "campaigns": [{"id": "concept-001", "theme": "Test Theme", "name_options": ["Name A"]}]
    }
    with patch("backend.app.services.campaign_service.campaign_strategist_agent",
               new=AsyncMock(return_value=mock_strategy_result)):
        result = await svc.create("mand-001", "tenant-001")

    campaign_col.insert_one.assert_called_once()
    assert result["mandate_id"] == "mand-001"
    assert result["tenant_id"] == "tenant-001"
    assert result["status"] == "concepts_ready"


@pytest.mark.asyncio
async def test_create_campaign_missing_mandate_raises_404():
    db, _, mandate_col, __ = make_db(campaigns=None, mandates=None, ci_reports=None)
    svc = CampaignService(db)

    with pytest.raises(HTTPException) as exc_info:
        await svc.create("missing-mand", "tenant-001")

    assert exc_info.value.status_code == 404
    assert "Mandate" in exc_info.value.detail


# ── update ─────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_update_campaign_returns_updated_doc():
    updated_doc = {**CAMPAIGN_DOC, "status": "confirmed"}
    db, campaign_col, _, __ = make_db(campaigns=updated_doc)
    campaign_col.find_one_and_update = AsyncMock(return_value=updated_doc)
    svc = CampaignService(db)

    result = await svc.update("camp-001", "tenant-001", {"status": "confirmed"})

    assert result["status"] == "confirmed"


# ── list ───────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_list_returns_tenant_campaigns():
    db, campaign_col, _m, _c = make_db()
    cursor = MagicMock()
    cursor.to_list = AsyncMock(return_value=[CAMPAIGN_DOC])
    campaign_col.find = MagicMock(return_value=cursor)
    svc = CampaignService(db)
    rows = await svc.list("tenant-001")
    assert rows == [CAMPAIGN_DOC]
    campaign_col.find.assert_called_once_with({"tenant_id": "tenant-001"})
