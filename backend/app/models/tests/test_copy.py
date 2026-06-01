from uuid import uuid4

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.models.copy import GeneratedCopy


@pytest.mark.asyncio
async def test_create_generated_copy(db_session: AsyncSession):
    tenant_id = str(uuid4())
    gen_id = str(uuid4())
    copy = GeneratedCopy(
        tenant_id=tenant_id,
        campaign_id=str(uuid4()),
        generation_id=gen_id,
        asset_type="headline",
        variant_id="v1",
        content={"text": "Bold. Fresh. You."},
        model_used="claude-sonnet-4",
    )
    db_session.add(copy)
    await db_session.commit()

    result = await db_session.execute(select(GeneratedCopy).where(GeneratedCopy.tenant_id == tenant_id))
    fetched = result.scalar_one()
    assert fetched.asset_type == "headline"
    assert fetched.tenant_id == tenant_id
    assert fetched.created_at is not None


@pytest.mark.asyncio
async def test_generated_copy_tenant_isolation(db_session: AsyncSession):
    t_a, t_b = str(uuid4()), str(uuid4())
    db_session.add(GeneratedCopy(
        tenant_id=t_a, campaign_id=str(uuid4()), generation_id=str(uuid4()),
        asset_type="body", variant_id="v1", content={"text": "copy A"}, model_used="m1",
    ))
    db_session.add(GeneratedCopy(
        tenant_id=t_b, campaign_id=str(uuid4()), generation_id=str(uuid4()),
        asset_type="body", variant_id="v1", content={"text": "copy B"}, model_used="m1",
    ))
    await db_session.commit()

    result = await db_session.execute(select(GeneratedCopy).where(GeneratedCopy.tenant_id == t_a))
    rows = result.scalars().all()
    assert len(rows) == 1


@pytest.mark.asyncio
async def test_generated_copy_to_dict(db_session: AsyncSession):
    tenant_id = str(uuid4())
    copy = GeneratedCopy(
        tenant_id=tenant_id, campaign_id=str(uuid4()), generation_id=str(uuid4()),
        asset_type="cta", variant_id="v1", content={"text": "test"}, model_used="m1",
    )
    db_session.add(copy)
    await db_session.commit()
    result = await db_session.execute(select(GeneratedCopy).where(GeneratedCopy.id == copy.id))
    d = result.scalar_one().to_dict()
    assert d["tenant_id"] == tenant_id
    assert "created_at" in d
