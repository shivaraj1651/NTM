from uuid import uuid4

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.models.audio import GeneratedAudio


@pytest.mark.asyncio
async def test_create_generated_audio(db_session: AsyncSession):
    tenant_id = str(uuid4())
    audio = GeneratedAudio(
        tenant_id=tenant_id,
        campaign_id=str(uuid4()),
        generation_id=str(uuid4()),
        asset_url="https://example.com/audio/spot.mp3",
        voice_id="en-US-voice-1",
        model_used="elevenlabs-v2",
        script_format="radio_30s",
    )
    db_session.add(audio)
    await db_session.commit()

    result = await db_session.execute(select(GeneratedAudio).where(GeneratedAudio.tenant_id == tenant_id))
    fetched = result.scalar_one()
    assert fetched.asset_url == "https://example.com/audio/spot.mp3"
    assert fetched.tenant_id == tenant_id
    assert fetched.created_at is not None


@pytest.mark.asyncio
async def test_generated_audio_tenant_isolation(db_session: AsyncSession):
    t_a, t_b = str(uuid4()), str(uuid4())
    db_session.add(GeneratedAudio(tenant_id=t_a, campaign_id=str(uuid4()), generation_id=str(uuid4()),
                                   asset_url="a.mp3", voice_id="v1", model_used="m1", script_format="s1"))
    db_session.add(GeneratedAudio(tenant_id=t_b, campaign_id=str(uuid4()), generation_id=str(uuid4()),
                                   asset_url="b.mp3", voice_id="v1", model_used="m1", script_format="s1"))
    await db_session.commit()

    result = await db_session.execute(select(GeneratedAudio).where(GeneratedAudio.tenant_id == t_a))
    rows = result.scalars().all()
    assert len(rows) == 1
    assert rows[0].asset_url == "a.mp3"


@pytest.mark.asyncio
async def test_generated_audio_fields(db_session: AsyncSession):
    audio = GeneratedAudio(
        tenant_id=str(uuid4()), campaign_id=str(uuid4()), generation_id=str(uuid4()),
        asset_url="test.mp3", voice_id="voice-99", model_used="model-x", script_format="tv_15s",
        duration_seconds=15.0,
    )
    db_session.add(audio)
    await db_session.commit()
    result = await db_session.execute(select(GeneratedAudio).where(GeneratedAudio.id == audio.id))
    fetched = result.scalar_one()
    assert fetched.voice_id == "voice-99"
    assert fetched.duration_seconds == 15.0
