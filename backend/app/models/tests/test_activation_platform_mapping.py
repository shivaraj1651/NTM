"""Tests for ActivationPlatformMapping model."""

import pytest
from uuid import uuid4
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.models.activation_platform_mapping import ActivationPlatformMapping


@pytest.mark.asyncio
async def test_create_activation_platform_mapping(db_session: AsyncSession):
    """Test creating and querying ActivationPlatformMapping record."""
    activation_id = str(uuid4())
    tenant_id = str(uuid4())

    mapping = ActivationPlatformMapping(
        activation_id=activation_id,
        channel_enum="google_ads",
        platform_campaign_id="camps_12345",
        platform_ad_id="ads_67890",
        status="live",
        error_message=None,
        tenant_id=tenant_id
    )

    db_session.add(mapping)
    await db_session.commit()

    result = await db_session.execute(
        select(ActivationPlatformMapping).where(
            ActivationPlatformMapping.activation_id == activation_id
        )
    )
    fetched = result.scalar_one()

    assert fetched.platform_campaign_id == "camps_12345"
    assert fetched.platform_ad_id == "ads_67890"
    assert fetched.status == "live"
    assert fetched.error_message is None


@pytest.mark.asyncio
async def test_update_platform_mapping_on_failure(db_session: AsyncSession):
    """Test updating mapping with error on failure."""
    activation_id = str(uuid4())
    tenant_id = str(uuid4())

    mapping = ActivationPlatformMapping(
        activation_id=activation_id,
        channel_enum="meta_ads",
        platform_campaign_id=None,
        platform_ad_id=None,
        status="pending",
        error_message=None,
        tenant_id=tenant_id
    )
    db_session.add(mapping)
    await db_session.commit()

    mapping.status = "failed"
    mapping.error_message = "API rate limit exceeded"
    await db_session.commit()

    result = await db_session.execute(
        select(ActivationPlatformMapping).where(
            ActivationPlatformMapping.id == mapping.id
        )
    )
    fetched = result.scalar_one()

    assert fetched.status == "failed"
    assert fetched.error_message == "API rate limit exceeded"


@pytest.mark.asyncio
async def test_activation_platform_mapping_with_all_channels(db_session: AsyncSession):
    """Test creating mappings for all supported channels."""
    tenant_id = str(uuid4())
    activation_id = str(uuid4())

    channels = ["google_ads", "meta_ads", "linkedin_ads"]

    for channel in channels:
        mapping = ActivationPlatformMapping(
            activation_id=activation_id,
            channel_enum=channel,
            platform_campaign_id=f"{channel}_camp_001",
            platform_ad_id=f"{channel}_ad_001",
            status="live",
            error_message=None,
            tenant_id=tenant_id
        )
        db_session.add(mapping)

    await db_session.commit()

    result = await db_session.execute(
        select(ActivationPlatformMapping).where(
            ActivationPlatformMapping.activation_id == activation_id
        )
    )
    fetched_all = result.scalars().all()

    assert len(fetched_all) == 3
    assert {m.channel_enum for m in fetched_all} == set(channels)


@pytest.mark.asyncio
async def test_tenant_isolation(db_session: AsyncSession):
    """Test that tenant_id properly isolates data."""
    tenant_1 = str(uuid4())
    tenant_2 = str(uuid4())
    activation_id = str(uuid4())

    mapping_1 = ActivationPlatformMapping(
        activation_id=activation_id,
        channel_enum="google_ads",
        platform_campaign_id="camps_001",
        platform_ad_id="ads_001",
        status="live",
        error_message=None,
        tenant_id=tenant_1
    )

    mapping_2 = ActivationPlatformMapping(
        activation_id=activation_id,
        channel_enum="google_ads",
        platform_campaign_id="camps_002",
        platform_ad_id="ads_002",
        status="live",
        error_message=None,
        tenant_id=tenant_2
    )

    db_session.add(mapping_1)
    db_session.add(mapping_2)
    await db_session.commit()

    result = await db_session.execute(
        select(ActivationPlatformMapping).where(
            ActivationPlatformMapping.tenant_id == tenant_1,
            ActivationPlatformMapping.activation_id == activation_id
        )
    )
    fetched = result.scalar_one()

    assert fetched.tenant_id == tenant_1
    assert fetched.platform_campaign_id == "camps_001"
