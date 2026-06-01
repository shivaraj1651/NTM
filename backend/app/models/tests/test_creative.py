from uuid import uuid4

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.models.creative import GeneratedCreative


@pytest.mark.asyncio
async def test_create_generated_creative(db_session: AsyncSession):
    tenant_id = str(uuid4())
    gen_id = str(uuid4())
    creative = GeneratedCreative(
        tenant_id=tenant_id,
        campaign_id=str(uuid4()),
        generation_id=gen_id,
        platform="instagram",
        creative_type="story",
        content={"copy": "Summer sale!", "cta": "Shop Now"},
        validation_status="passed",
    )
    db_session.add(creative)
    await db_session.commit()

    result = await db_session.execute(select(GeneratedCreative).where(GeneratedCreative.tenant_id == tenant_id))
    fetched = result.scalar_one()
    assert fetched.platform == "instagram"
    assert fetched.tenant_id == tenant_id
    assert fetched.created_at is not None


@pytest.mark.asyncio
async def test_generated_creative_tenant_isolation(db_session: AsyncSession):
    t_a, t_b = str(uuid4()), str(uuid4())
    db_session.add(GeneratedCreative(
        tenant_id=t_a, campaign_id=str(uuid4()), generation_id=str(uuid4()),
        platform="instagram", creative_type="feed", content={}, validation_status="passed",
    ))
    db_session.add(GeneratedCreative(
        tenant_id=t_b, campaign_id=str(uuid4()), generation_id=str(uuid4()),
        platform="instagram", creative_type="feed", content={}, validation_status="passed",
    ))
    await db_session.commit()

    result = await db_session.execute(select(GeneratedCreative).where(GeneratedCreative.tenant_id == t_a))
    assert len(result.scalars().all()) == 1


@pytest.mark.asyncio
async def test_generated_creative_to_dict(db_session: AsyncSession):
    tenant_id = str(uuid4())
    creative = GeneratedCreative(
        tenant_id=tenant_id, campaign_id=str(uuid4()), generation_id=str(uuid4()),
        platform="linkedin", creative_type="banner", content={}, validation_status="passed",
    )
    db_session.add(creative)
    await db_session.commit()
    result = await db_session.execute(select(GeneratedCreative).where(GeneratedCreative.id == creative.id))
    d = result.scalar_one().to_dict()
    assert d["tenant_id"] == tenant_id
    assert "created_at" in d
