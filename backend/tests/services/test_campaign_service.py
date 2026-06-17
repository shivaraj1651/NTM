"""Unit tests for CampaignService — campaign lifecycle business logic."""


from unittest.mock import AsyncMock, MagicMock, patch

import pytest
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

    with patch("backend.app.tasks.campaign_tasks.run_concept_generation") as mock_task:
        mock_task.delay = MagicMock()
        result = await svc.create("mand-001", "tenant-001")

    campaign_col.insert_one.assert_called_once()
    assert result["mandate_id"] == "mand-001"
    assert result["tenant_id"] == "tenant-001"
    assert result["status"] == "pending"


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


# ── TASK 1: create → background task ──────────────────────────────────────────

@pytest.mark.asyncio
async def test_create_campaign_status_pending_no_agent():
    """create() returns status=pending, concepts=[], dispatches run_concept_generation without calling agent."""
    db, campaign_col, _, __ = make_db(campaigns=CAMPAIGN_DOC, mandates=MANDATE_DOC, ci_reports=CI_REPORT_DOC)
    svc = CampaignService(db)

    mock_delay = MagicMock()

    with patch("backend.app.tasks.campaign_tasks.run_concept_generation") as mock_task:
        mock_task.delay = mock_delay
        result = await svc.create("mand-001", "tenant-001")

    campaign_col.insert_one.assert_called_once()
    assert result["status"] == "pending"
    assert result["concepts"] == []
    mock_task.delay.assert_called_once()
    call_args = mock_task.delay.call_args[0]
    assert call_args[1] == "tenant-001"


@pytest.mark.asyncio
async def test_create_campaign_missing_mandate_still_404():
    """create() still raises 404 when mandate not found (guard preserved)."""
    db, _, mandate_col, __ = make_db(campaigns=None, mandates=None, ci_reports=None)
    svc = CampaignService(db)

    with pytest.raises(HTTPException) as exc_info:
        with patch.object(svc, "_load_mandate_from_postgres", new=AsyncMock(return_value=None)):
            await svc.create("missing-mand", "tenant-001")

    assert exc_info.value.status_code == 404


# ── TASK 2: confirm → dispatches run_media_planning ───────────────────────────

@pytest.mark.asyncio
async def test_confirm_dispatches_media_planning():
    """confirm() sets status=confirmed and dispatches run_media_planning."""
    confirmed_doc = {**CAMPAIGN_DOC, "status": "confirmed", "selected_concept_id": "concept-001"}
    db, campaign_col, _, __ = make_db(campaigns=CAMPAIGN_DOC)
    campaign_col.find_one_and_update = AsyncMock(return_value=confirmed_doc)
    svc = CampaignService(db)

    mock_delay = MagicMock()

    with patch("backend.app.tasks.campaign_tasks.run_media_planning") as mock_task:
        mock_task.delay = mock_delay
        result = await svc.confirm("camp-001", "concept-001", "tenant-001")

    assert result["status"] == "confirmed"
    mock_task.delay.assert_called_once_with("camp-001", "tenant-001")


@pytest.mark.asyncio
async def test_confirm_wrong_status_raises_409():
    """confirm() raises 409 if status is not concepts_ready."""
    pending_doc = {**CAMPAIGN_DOC, "status": "pending"}
    db, _, __, ___ = make_db(campaigns=pending_doc)
    svc = CampaignService(db)

    with pytest.raises(HTTPException) as exc_info:
        await svc.confirm("camp-001", "concept-001", "tenant-001")

    assert exc_info.value.status_code == 409


# ── TASK 3: propose_budget → background task ──────────────────────────────────

@pytest.mark.asyncio
async def test_propose_budget_status_budget_pending_dispatches_task():
    """propose_budget() sets status=budget_pending and dispatches run_budget_optimization."""
    planned_doc = {**CAMPAIGN_DOC, "status": "planned", "activation_plan": []}
    budget_pending_doc = {**planned_doc, "status": "budget_pending"}
    db, campaign_col, mandate_col, __ = make_db(campaigns=planned_doc)
    campaign_col.find_one_and_update = AsyncMock(return_value=budget_pending_doc)
    svc = CampaignService(db)

    mock_delay = MagicMock()

    with patch("backend.app.tasks.campaign_tasks.run_budget_optimization") as mock_task:
        mock_task.delay = mock_delay
        result = await svc.propose_budget("camp-001", "tenant-001")

    assert result["status"] == "budget_pending"
    mock_task.delay.assert_called_once_with("camp-001", "tenant-001")


@pytest.mark.asyncio
async def test_propose_budget_wrong_status_raises_409():
    """propose_budget() raises 409 if status is not planned."""
    db, _, __, ___ = make_db(campaigns=CAMPAIGN_DOC)  # status=concepts_ready
    svc = CampaignService(db)

    with pytest.raises(HTTPException) as exc_info:
        await svc.propose_budget("camp-001", "tenant-001")

    assert exc_info.value.status_code == 409


# ── generate_creatives → background task ─────────────────────────────────────

@pytest.mark.asyncio
async def test_generate_creatives_dispatches_task_sets_creative_generating(monkeypatch):
    """generate_creatives() sets status=creative_generating and dispatches run_creative_generation."""
    approved_doc = {
        "_id": "c1",
        "tenant_id": "t1",
        "status": "approved",
        "concepts": [{"id": "k1"}],
        "selected_concept_id": "k1",
    }
    creative_generating_doc = {**approved_doc, "status": "creative_generating"}
    db, campaign_col, _, __ = make_db(campaigns=approved_doc)
    campaign_col.find_one_and_update = AsyncMock(return_value=creative_generating_doc)
    svc = CampaignService(db)

    called = {}

    import backend.app.tasks.campaign_tasks as ct
    original = getattr(ct, "run_creative_generation", None)

    class FakeTask:
        @staticmethod
        def delay(cid, tid, concept=None):
            called["cid"] = cid

    ct.run_creative_generation = FakeTask()
    try:
        doc = await svc.generate_creatives("c1", "t1")
        assert doc["status"] == "creative_generating", f"expected creative_generating, got {doc['status']}"
        assert called.get("cid") == "c1", f"task not dispatched, called={called}"
    finally:
        if original is not None:
            ct.run_creative_generation = original


@pytest.mark.asyncio
async def test_generate_creatives_wrong_status_raises_409():
    """generate_creatives() raises 409 if status is not approved."""
    db, _, __, ___ = make_db(campaigns=CAMPAIGN_DOC)  # status=concepts_ready
    svc = CampaignService(db)

    with pytest.raises(HTTPException) as exc_info:
        await svc.generate_creatives("camp-001", "tenant-001")

    assert exc_info.value.status_code == 409
