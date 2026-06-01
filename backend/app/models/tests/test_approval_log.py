from uuid import uuid4

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.models.approval_log import ApprovalLog


@pytest.mark.asyncio
async def test_create_approval_log(db_session: AsyncSession):
    tenant_id = str(uuid4())
    log = ApprovalLog(
        tenant_id=tenant_id,
        entity_type="campaign",
        entity_id=str(uuid4()),
        action="submitted",
        actor_id=str(uuid4()),
        status_before="planned",
        status_after="pending_review",
    )
    db_session.add(log)
    await db_session.commit()

    result = await db_session.execute(
        select(ApprovalLog).where(ApprovalLog.tenant_id == tenant_id)
    )
    fetched = result.scalar_one()

    assert fetched.entity_type == "campaign"
    assert fetched.action == "submitted"
    assert fetched.status_before == "planned"
    assert fetched.status_after == "pending_review"
    assert fetched.notes is None
    assert fetched.created_at is not None


@pytest.mark.asyncio
async def test_approval_log_with_notes(db_session: AsyncSession):
    tenant_id = str(uuid4())
    log = ApprovalLog(
        tenant_id=tenant_id,
        entity_type="budget",
        entity_id=str(uuid4()),
        action="rejected",
        actor_id=str(uuid4()),
        notes="Budget exceeds Q3 cap by 15%.",
        status_before="pending_review",
        status_after="rejected",
    )
    db_session.add(log)
    await db_session.commit()

    result = await db_session.execute(
        select(ApprovalLog).where(ApprovalLog.tenant_id == tenant_id)
    )
    fetched = result.scalar_one()
    assert fetched.notes == "Budget exceeds Q3 cap by 15%."


@pytest.mark.asyncio
async def test_approval_log_nullable_status_fields(db_session: AsyncSession):
    tenant_id = str(uuid4())
    log = ApprovalLog(
        tenant_id=tenant_id,
        entity_type="mandate",
        entity_id=str(uuid4()),
        action="approved",
        actor_id=str(uuid4()),
    )
    db_session.add(log)
    await db_session.commit()

    result = await db_session.execute(
        select(ApprovalLog).where(ApprovalLog.tenant_id == tenant_id)
    )
    fetched = result.scalar_one()
    assert fetched.status_before is None
    assert fetched.status_after is None


@pytest.mark.asyncio
async def test_approval_log_to_dict(db_session: AsyncSession):
    tenant_id = str(uuid4())
    actor_id = str(uuid4())
    entity_id = str(uuid4())
    log = ApprovalLog(
        tenant_id=tenant_id,
        entity_type="campaign",
        entity_id=entity_id,
        action="approved",
        actor_id=actor_id,
        status_before="pending_review",
        status_after="approved",
    )
    db_session.add(log)
    await db_session.commit()

    result = await db_session.execute(
        select(ApprovalLog).where(ApprovalLog.id == log.id)
    )
    fetched = result.scalar_one()
    d = fetched.to_dict()

    assert d["tenant_id"] == tenant_id
    assert d["entity_type"] == "campaign"
    assert d["entity_id"] == entity_id
    assert d["action"] == "approved"
    assert d["actor_id"] == actor_id
    assert d["status_before"] == "pending_review"
    assert d["status_after"] == "approved"
    assert "created_at" in d
    assert "updated_at" not in d


@pytest.mark.asyncio
async def test_approval_log_tenant_isolation(db_session: AsyncSession):
    tenant_a = str(uuid4())
    tenant_b = str(uuid4())
    db_session.add(ApprovalLog(
        tenant_id=tenant_a, entity_type="campaign", entity_id=str(uuid4()),
        action="submitted", actor_id=str(uuid4()),
    ))
    db_session.add(ApprovalLog(
        tenant_id=tenant_b, entity_type="budget", entity_id=str(uuid4()),
        action="approved", actor_id=str(uuid4()),
    ))
    await db_session.commit()

    result = await db_session.execute(
        select(ApprovalLog).where(ApprovalLog.tenant_id == tenant_a)
    )
    logs = result.scalars().all()
    assert len(logs) == 1
    assert logs[0].entity_type == "campaign"
