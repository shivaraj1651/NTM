"""Tests for AuditTrail model."""

import pytest
import pytest_asyncio
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

from backend.app.models.audit_trail import AuditTrail, Base


@pytest_asyncio.fixture
async def audit_db():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False, future=True)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    factory = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with factory() as session:
        yield session
    await engine.dispose()


@pytest.mark.asyncio
async def test_audit_trail_insert(audit_db):
    row = AuditTrail(
        tenant_id="t1",
        entity_type="mandate",
        entity_id="m1",
        action="create",
        actor_id="u1",
    )
    audit_db.add(row)
    await audit_db.flush()
    result = await audit_db.execute(select(AuditTrail).where(AuditTrail.entity_id == "m1"))
    saved = result.scalar_one()
    assert saved.tenant_id == "t1"
    assert saved.action == "create"
    assert saved.status == "success"
    assert saved.created_at is not None


@pytest.mark.asyncio
async def test_audit_trail_to_dict(audit_db):
    row = AuditTrail(
        tenant_id="t1",
        entity_type="campaign",
        entity_id="c1",
        action="update",
        actor_id="u2",
        actor_role="tenant_admin",
        payload_before={"name": "old"},
        payload_after={"name": "new"},
    )
    audit_db.add(row)
    await audit_db.flush()
    d = row.to_dict()
    assert d["entity_type"] == "campaign"
    assert d["payload_before"] == {"name": "old"}
    assert d["payload_after"] == {"name": "new"}
    assert "created_at" in d


@pytest.mark.asyncio
async def test_audit_trail_indexes_exist(audit_db):
    result = await audit_db.execute(
        text("SELECT name FROM sqlite_master WHERE type='index' AND tbl_name='audit_trail'")
    )
    index_names = {r[0] for r in result.fetchall()}
    assert "ix_audit_trail_tenant" in index_names
    assert "ix_audit_trail_actor" in index_names
