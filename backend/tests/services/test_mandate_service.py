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
async def test_get_summary_card_returns_flat_mandate_when_analysis_absent():
    """The card is the flat mandate, available immediately after create — no 404
    while the async analysis is still pending."""
    from backend.app.services.mandate_service import MandateService
    session = make_mock_session(mandate=make_mandate())
    mongo_col = MagicMock()
    mongo_col.find_one = AsyncMock(return_value=None)
    mongo_db = MagicMock()
    mongo_db.__getitem__ = MagicMock(return_value=mongo_col)
    svc = MandateService(session)
    result = await svc.get_summary_card("m-001", "tenant-1", mongo_db)
    assert result["id"] == "m-001"
    assert result["status"] == "draft"
    assert "analysis" not in result


@pytest.mark.asyncio
async def test_get_summary_card_merges_analysis_when_present():
    from backend.app.services.mandate_service import MandateService
    session = make_mock_session(mandate=make_mandate())
    mongo_col = MagicMock()
    mongo_col.find_one = AsyncMock(return_value={
        "mandate_id": "m-001", "tenant_id": "tenant-1",
        "analysis": {"completeness_score": 90}, "created_at": "2026-05-31T00:00:00+00:00", "_id": "x",
    })
    mongo_db = MagicMock()
    mongo_db.__getitem__ = MagicMock(return_value=mongo_col)
    svc = MandateService(session)
    result = await svc.get_summary_card("m-001", "tenant-1", mongo_db)
    assert result["id"] == "m-001"  # flat mandate fields present
    assert result["analysis"]["completeness_score"] == 90
    assert "_id" not in result


@pytest.mark.asyncio
async def test_get_summary_card_mandate_missing_raises_404():
    from backend.app.services.mandate_service import MandateService
    session = make_mock_session(mandate=None)
    mongo_db = MagicMock()
    svc = MandateService(session)
    with pytest.raises(HTTPException) as exc:
        await svc.get_summary_card("nope", "tenant-1", mongo_db)
    assert exc.value.status_code == 404


# ── create ────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_create_mandate_sets_draft_status():
    from backend.app.services.mandate_service import MandateService
    session = make_mock_session()
    # refresh needs to work on the real Mandate object; just make it a no-op
    session.refresh = AsyncMock()

    svc = MandateService(session)
    data = CreateMandateRequest(
        name="Test",
        client_id="c-001",
        objective="Brand awareness",
        region="EMEA",
        total_budget=50000.0,
        currency="USD",
        start_date=date(2026, 6, 1),
        end_date=date(2026, 12, 31),
    )
    # We can't call to_dict on a real Mandate without a DB, but we can verify
    # that add and commit were called — meaning an ORM object was persisted
    await svc.create(data, "user-1", "tenant-1")
    assert session.add.called
    assert session.commit.called


# ── list ──────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_list_returns_tenant_mandates():
    from unittest.mock import AsyncMock, MagicMock
    from backend.app.services.mandate_service import MandateService
    m = make_mandate()
    result = MagicMock()
    result.scalars.return_value.all.return_value = [m]
    session = MagicMock()
    session.execute = AsyncMock(return_value=result)
    svc = MandateService(session)
    rows = await svc.list("tenant-1")
    assert rows == [m.to_dict.return_value]
