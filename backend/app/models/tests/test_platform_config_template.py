"""Tests for PlatformConfigTemplate model."""

from uuid import uuid4

import pytest
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.models.platform_config_template import PlatformConfigTemplate


@pytest.mark.asyncio
async def test_create_platform_config_template(db_session: AsyncSession):
    """Test creating platform config template."""
    config = PlatformConfigTemplate(
        channel_enum="google_ads",
        audience_segment="brand_aware",
        platform_targeting_json={
            "age_min": 18,
            "age_max": 65,
            "interests": ["technology", "business"],
            "device": "mobile"
        },
        budget_multiplier=1.0,
        tenant_id=str(uuid4())
    )

    db_session.add(config)
    await db_session.commit()

    result = await db_session.execute(
        select(PlatformConfigTemplate).where(
            PlatformConfigTemplate.channel_enum == "google_ads"
        )
    )
    fetched = result.scalar_one()

    assert fetched.audience_segment == "brand_aware"
    assert fetched.platform_targeting_json["age_min"] == 18
    assert fetched.budget_multiplier == 1.0


@pytest.mark.asyncio
async def test_platform_config_unique_constraint(db_session: AsyncSession):
    """Test unique constraint on tenant/channel/audience."""
    tenant_id = str(uuid4())
    config1 = PlatformConfigTemplate(
        channel_enum="meta_ads",
        audience_segment="consideration",
        platform_targeting_json={"age_min": 25},
        budget_multiplier=1.1,
        tenant_id=tenant_id
    )
    db_session.add(config1)
    await db_session.commit()

    # Try to add duplicate - should fail
    config2 = PlatformConfigTemplate(
        channel_enum="meta_ads",
        audience_segment="consideration",
        platform_targeting_json={"age_min": 30},
        budget_multiplier=1.2,
        tenant_id=tenant_id
    )
    db_session.add(config2)

    with pytest.raises(IntegrityError):
        await db_session.commit()


@pytest.mark.asyncio
async def test_platform_config_multiple_channels(db_session: AsyncSession):
    """Test creating configs for all supported channels."""
    tenant_id = str(uuid4())
    segment = "consideration"

    channels = ["google_ads", "meta_ads", "linkedin_ads"]

    for channel in channels:
        config = PlatformConfigTemplate(
            channel_enum=channel,
            audience_segment=segment,
            platform_targeting_json={
                "age_min": 25,
                "interests": ["technology"],
            },
            budget_multiplier=1.0,
            tenant_id=tenant_id
        )
        db_session.add(config)

    await db_session.commit()

    result = await db_session.execute(
        select(PlatformConfigTemplate).where(
            PlatformConfigTemplate.tenant_id == tenant_id,
            PlatformConfigTemplate.audience_segment == segment
        )
    )
    fetched_all = result.scalars().all()

    assert len(fetched_all) == 3
    assert {c.channel_enum for c in fetched_all} == set(channels)


@pytest.mark.asyncio
async def test_tenant_isolation(db_session: AsyncSession):
    """Test that tenant_id properly isolates data."""
    tenant_1 = str(uuid4())
    tenant_2 = str(uuid4())

    config_1 = PlatformConfigTemplate(
        channel_enum="google_ads",
        audience_segment="brand_aware",
        platform_targeting_json={"age_min": 18, "age_max": 65},
        budget_multiplier=1.0,
        tenant_id=tenant_1
    )

    config_2 = PlatformConfigTemplate(
        channel_enum="google_ads",
        audience_segment="brand_aware",
        platform_targeting_json={"age_min": 25, "age_max": 55},
        budget_multiplier=1.2,
        tenant_id=tenant_2
    )

    db_session.add(config_1)
    db_session.add(config_2)
    await db_session.commit()

    result = await db_session.execute(
        select(PlatformConfigTemplate).where(
            PlatformConfigTemplate.tenant_id == tenant_1,
            PlatformConfigTemplate.audience_segment == "brand_aware"
        )
    )
    fetched = result.scalar_one()

    assert fetched.tenant_id == tenant_1
    assert fetched.platform_targeting_json["age_min"] == 18


@pytest.mark.asyncio
async def test_platform_config_budget_multiplier(db_session: AsyncSession):
    """Test budget multiplier field."""
    config = PlatformConfigTemplate(
        channel_enum="linkedin_ads",
        audience_segment="decision",
        platform_targeting_json={
            "job_titles": ["Director", "VP", "C-level"],
            "industries": ["technology", "finance"]
        },
        budget_multiplier=1.5,
        tenant_id=str(uuid4())
    )

    db_session.add(config)
    await db_session.commit()

    result = await db_session.execute(
        select(PlatformConfigTemplate).where(
            PlatformConfigTemplate.channel_enum == "linkedin_ads"
        )
    )
    fetched = result.scalar_one()

    assert fetched.budget_multiplier == 1.5


@pytest.mark.asyncio
async def test_platform_config_to_dict(db_session: AsyncSession):
    """Test to_dict conversion."""
    tenant_id = str(uuid4())
    config = PlatformConfigTemplate(
        channel_enum="meta_ads",
        audience_segment="consideration",
        platform_targeting_json={"age_min": 25, "interests": ["tech"]},
        budget_multiplier=1.1,
        tenant_id=tenant_id
    )

    db_session.add(config)
    await db_session.commit()

    result = await db_session.execute(
        select(PlatformConfigTemplate).where(
            PlatformConfigTemplate.id == config.id
        )
    )
    fetched = result.scalar_one()
    config_dict = fetched.to_dict()

    assert config_dict["tenant_id"] == tenant_id
    assert config_dict["channel_enum"] == "meta_ads"
    assert config_dict["audience_segment"] == "consideration"
    assert config_dict["platform_targeting_json"]["age_min"] == 25
    assert config_dict["budget_multiplier"] == 1.1
    assert "created_at" in config_dict
    assert "updated_at" in config_dict
