import pytest
from uuid import uuid4
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from backend.app.models.video import GeneratedVideo


@pytest.mark.asyncio
async def test_create_generated_video(db_session: AsyncSession):
    tenant_id = str(uuid4())
    video = GeneratedVideo(
        tenant_id=tenant_id,
        campaign_id=str(uuid4()),
        generation_id=str(uuid4()),
        asset_url="https://example.com/video/ad.mp4",
        job_id=str(uuid4()),
        model_used="runway-gen3",
        script_format="tv_15s",
        status="completed",
        duration_seconds=15.0,
    )
    db_session.add(video)
    await db_session.commit()

    result = await db_session.execute(select(GeneratedVideo).where(GeneratedVideo.tenant_id == tenant_id))
    fetched = result.scalar_one()
    assert fetched.asset_url == "https://example.com/video/ad.mp4"
    assert fetched.tenant_id == tenant_id
    assert fetched.created_at is not None


@pytest.mark.asyncio
async def test_generated_video_tenant_isolation(db_session: AsyncSession):
    t_a, t_b = str(uuid4()), str(uuid4())
    db_session.add(GeneratedVideo(
        tenant_id=t_a, campaign_id=str(uuid4()), generation_id=str(uuid4()),
        asset_url="a.mp4", job_id=str(uuid4()), model_used="m1", script_format="s1", status="done",
    ))
    db_session.add(GeneratedVideo(
        tenant_id=t_b, campaign_id=str(uuid4()), generation_id=str(uuid4()),
        asset_url="b.mp4", job_id=str(uuid4()), model_used="m1", script_format="s1", status="done",
    ))
    await db_session.commit()

    result = await db_session.execute(select(GeneratedVideo).where(GeneratedVideo.tenant_id == t_a))
    rows = result.scalars().all()
    assert len(rows) == 1
    assert rows[0].asset_url == "a.mp4"


@pytest.mark.asyncio
async def test_generated_video_fields(db_session: AsyncSession):
    video = GeneratedVideo(
        tenant_id=str(uuid4()), campaign_id=str(uuid4()), generation_id=str(uuid4()),
        asset_url="test.mp4", job_id=str(uuid4()), model_used="sora",
        script_format="digital_30s", status="processing", duration_seconds=30.0,
    )
    db_session.add(video)
    await db_session.commit()
    result = await db_session.execute(select(GeneratedVideo).where(GeneratedVideo.id == video.id))
    fetched = result.scalar_one()
    assert fetched.status == "processing"
    assert fetched.duration_seconds == 30.0
