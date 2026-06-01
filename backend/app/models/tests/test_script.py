from uuid import uuid4

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.models.script import GeneratedScript


@pytest.mark.asyncio
async def test_create_generated_script(db_session: AsyncSession):
    tenant_id = str(uuid4())
    gen_id = str(uuid4())
    script = GeneratedScript(
        tenant_id=tenant_id,
        campaign_id=str(uuid4()),
        generation_id=gen_id,
        script_format="tv_30s",
        variant_label="A",
        content={"scenes": [{"id": 1, "action": "Open on sunny beach"}]},
        model_used="claude-sonnet-4",
    )
    db_session.add(script)
    await db_session.commit()

    result = await db_session.execute(select(GeneratedScript).where(GeneratedScript.tenant_id == tenant_id))
    fetched = result.scalar_one()
    assert fetched.script_format == "tv_30s"
    assert fetched.tenant_id == tenant_id
    assert fetched.created_at is not None


@pytest.mark.asyncio
async def test_generated_script_tenant_isolation(db_session: AsyncSession):
    t_a, t_b = str(uuid4()), str(uuid4())
    db_session.add(GeneratedScript(
        tenant_id=t_a, campaign_id=str(uuid4()), generation_id=str(uuid4()),
        script_format="radio_15s", variant_label="A", content={}, model_used="m1",
    ))
    db_session.add(GeneratedScript(
        tenant_id=t_b, campaign_id=str(uuid4()), generation_id=str(uuid4()),
        script_format="radio_15s", variant_label="A", content={}, model_used="m1",
    ))
    await db_session.commit()

    result = await db_session.execute(select(GeneratedScript).where(GeneratedScript.tenant_id == t_a))
    assert len(result.scalars().all()) == 1


@pytest.mark.asyncio
async def test_generated_script_fields(db_session: AsyncSession):
    script = GeneratedScript(
        tenant_id=str(uuid4()), campaign_id=str(uuid4()), generation_id=str(uuid4()),
        script_format="digital_15s", variant_label="B", content={"text": "test"},
        model_used="claude-sonnet-4", production_brief="Shoot on location",
    )
    db_session.add(script)
    await db_session.commit()
    result = await db_session.execute(select(GeneratedScript).where(GeneratedScript.id == script.id))
    fetched = result.scalar_one()
    assert fetched.variant_label == "B"
    assert fetched.production_brief == "Shoot on location"
