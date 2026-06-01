"""Tests for PlatformConfigService."""

from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.models.platform_config_template import PlatformConfigTemplate
from backend.app.services.platform_config import PlatformConfigService


@pytest.mark.asyncio
async def test_get_platform_config_success(db_session: AsyncSession):
    """Test retrieving platform config for a channel and audience."""
    tenant_id = str(uuid4())

    # Create a template
    template = PlatformConfigTemplate(
        tenant_id=tenant_id,
        channel_enum="google_ads",
        audience_segment="brand_aware",
        platform_targeting_json={
            "age_min": 18,
            "age_max": 55,
            "interests": ["tech", "startup"]
        },
        budget_multiplier=1.2
    )
    db_session.add(template)
    await db_session.commit()

    # Retrieve via service
    service = PlatformConfigService(db_session)
    config = await service.get_platform_config(
        tenant_id=tenant_id,
        channel_enum="google_ads",
        audience_segment="brand_aware"
    )

    assert config is not None
    assert config.platform_targeting_json["age_min"] == 18
    assert config.budget_multiplier == 1.2


@pytest.mark.asyncio
async def test_get_platform_config_not_found(db_session: AsyncSession):
    """Test retrieving non-existent config returns None."""
    service = PlatformConfigService(db_session)

    config = await service.get_platform_config(
        tenant_id=str(uuid4()),
        channel_enum="linkedin_ads",
        audience_segment="non_existent"
    )

    assert config is None


@pytest.mark.asyncio
async def test_calculate_platform_budget(db_session: AsyncSession):
    """Test budget calculation with multiplier."""
    service = PlatformConfigService(db_session)

    budget = await service.calculate_platform_budget(
        activation_cost=5000.0,
        budget_multiplier=1.2
    )

    assert budget == 6000.0


@pytest.mark.asyncio
async def test_get_platform_config_tenant_isolation(db_session: AsyncSession):
    """Test that configs are isolated by tenant."""
    tenant1 = str(uuid4())
    tenant2 = str(uuid4())

    # Create config for tenant1
    config1 = PlatformConfigTemplate(
        tenant_id=tenant1,
        channel_enum="meta_ads",
        audience_segment="consideration",
        platform_targeting_json={"age_min": 25},
        budget_multiplier=1.0
    )
    db_session.add(config1)

    # Create different config for tenant2
    config2 = PlatformConfigTemplate(
        tenant_id=tenant2,
        channel_enum="meta_ads",
        audience_segment="consideration",
        platform_targeting_json={"age_min": 30},
        budget_multiplier=1.1
    )
    db_session.add(config2)
    await db_session.commit()

    # Service should return correct config per tenant
    service = PlatformConfigService(db_session)

    result1 = await service.get_platform_config(tenant1, "meta_ads", "consideration")
    assert result1.platform_targeting_json["age_min"] == 25

    result2 = await service.get_platform_config(tenant2, "meta_ads", "consideration")
    assert result2.platform_targeting_json["age_min"] == 30
