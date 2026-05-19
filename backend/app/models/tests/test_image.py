import pytest
from uuid import uuid4
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from backend.app.models.image import GeneratedImage


@pytest.mark.asyncio
async def test_create_generated_image(db_session: AsyncSession):
    tenant_id = str(uuid4())
    image = GeneratedImage(
        tenant_id=tenant_id,
        campaign_id=str(uuid4()),
        generation_id=str(uuid4()),
        asset_url="https://example.com/img/banner.png",
        prompt_used="A vibrant summer scene with colorful products",
        model_used="dall-e-3",
        image_format="png",
        generation_params={"width": 1200, "height": 628},
    )
    db_session.add(image)
    await db_session.commit()

    result = await db_session.execute(select(GeneratedImage).where(GeneratedImage.tenant_id == tenant_id))
    fetched = result.scalar_one()
    assert fetched.asset_url == "https://example.com/img/banner.png"
    assert fetched.tenant_id == tenant_id
    assert fetched.created_at is not None


@pytest.mark.asyncio
async def test_generated_image_tenant_isolation(db_session: AsyncSession):
    t_a, t_b = str(uuid4()), str(uuid4())
    db_session.add(GeneratedImage(
        tenant_id=t_a, campaign_id=str(uuid4()), generation_id=str(uuid4()),
        asset_url="a.png", prompt_used="prompt a", model_used="m1", image_format="png",
    ))
    db_session.add(GeneratedImage(
        tenant_id=t_b, campaign_id=str(uuid4()), generation_id=str(uuid4()),
        asset_url="b.png", prompt_used="prompt b", model_used="m1", image_format="png",
    ))
    await db_session.commit()

    result = await db_session.execute(select(GeneratedImage).where(GeneratedImage.tenant_id == t_a))
    rows = result.scalars().all()
    assert len(rows) == 1
    assert rows[0].asset_url == "a.png"


@pytest.mark.asyncio
async def test_generated_image_fields(db_session: AsyncSession):
    image = GeneratedImage(
        tenant_id=str(uuid4()), campaign_id=str(uuid4()), generation_id=str(uuid4()),
        asset_url="test.jpg", prompt_used="test prompt", model_used="stable-diffusion",
        image_format="jpg", generation_params={"steps": 50},
    )
    db_session.add(image)
    await db_session.commit()
    result = await db_session.execute(select(GeneratedImage).where(GeneratedImage.id == image.id))
    fetched = result.scalar_one()
    assert fetched.model_used == "stable-diffusion"
    assert fetched.image_format == "jpg"
