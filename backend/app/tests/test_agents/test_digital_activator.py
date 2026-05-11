"""Tests for DigitalActivatorAgent."""

import pytest
from uuid import uuid4
from datetime import date
from unittest.mock import patch, AsyncMock, MagicMock
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.agents.digital_activator import DigitalActivatorAgent
from backend.app.models.platform_config_template import PlatformConfigTemplate


@pytest.mark.asyncio
async def test_digital_activator_agent_happy_path(db_session: AsyncSession):
    """Test agent activates campaign across platforms."""
    activation_id = uuid4()
    tenant_id = uuid4()
    campaign_id = uuid4()

    # Create platform config first
    config = PlatformConfigTemplate(
        tenant_id=str(tenant_id),
        channel_enum="google_ads",
        audience_segment="brand_aware",
        platform_targeting_json={"age_min": 18, "age_max": 65},
        budget_multiplier=1.0
    )
    db_session.add(config)
    await db_session.commit()

    # Mock Activation object
    activation = MagicMock()
    activation.id = activation_id
    activation.tenant_id = str(tenant_id)
    activation.campaign_id = campaign_id
    activation.status = "approved"
    activation.channel_enum = "google_ads"
    activation.audience_segment = "brand_aware"

    # Mock Campaign lookup
    campaign = MagicMock()
    campaign.manager_email = "manager@example.com"
    campaign.manager_phone = "+1234567890"

    with patch.object(DigitalActivatorAgent, '_get_campaign', return_value=campaign) as mock_get_campaign, \
         patch.object(DigitalActivatorAgent, '_queue_platform_activation') as mock_queue:

        agent = DigitalActivatorAgent(db_session)
        result = await agent.activate(activation, creative_url="https://example.com/ad.jpg")

        # Verify result structure
        assert result["status"] == "activation_queued"
        assert result["activation_id"] == str(activation_id)
        assert len(result["platforms"]) > 0

        # Verify campaign lookup was called
        mock_get_campaign.assert_called_once()

        # Verify platform activation was queued
        mock_queue.assert_called()


@pytest.mark.asyncio
async def test_digital_activator_rejects_unapproved_activation():
    """Test agent rejects activation not in approved status."""
    activation = MagicMock()
    activation.status = "draft"  # Not approved

    agent = DigitalActivatorAgent(None)

    with pytest.raises(ValueError, match="Activation must be in 'approved' status"):
        await agent.activate(activation, creative_url="https://example.com/ad.jpg")


@pytest.mark.asyncio
async def test_digital_activator_maps_channels_to_platforms():
    """Test channel to platform mapping."""
    agent = DigitalActivatorAgent(None)

    # google_ads → ["google_ads"]
    result = agent._map_channel_to_platforms("google_ads")
    assert result == ["google_ads"]

    # meta_ads → ["meta_ads"]
    result = agent._map_channel_to_platforms("meta_ads")
    assert result == ["meta_ads"]

    # linkedin_ads → ["linkedin_ads"]
    result = agent._map_channel_to_platforms("linkedin_ads")
    assert result == ["linkedin_ads"]


@pytest.mark.asyncio
async def test_digital_activator_rejects_missing_campaign():
    """Test agent rejects activation when campaign not found."""
    activation = MagicMock()
    activation.status = "approved"
    activation.campaign_id = uuid4()

    with patch.object(DigitalActivatorAgent, '_get_campaign', return_value=None):
        agent = DigitalActivatorAgent(None)

        with pytest.raises(ValueError, match="Campaign .* not found"):
            await agent.activate(activation, creative_url="https://example.com/ad.jpg")


@pytest.mark.asyncio
async def test_digital_activator_rejects_missing_platform_config(db_session: AsyncSession):
    """Test agent rejects activation when platform config not found."""
    activation_id = uuid4()
    tenant_id = uuid4()
    campaign_id = uuid4()

    # Mock Activation object with no matching platform config
    activation = MagicMock()
    activation.id = activation_id
    activation.tenant_id = str(tenant_id)
    activation.campaign_id = campaign_id
    activation.status = "approved"
    activation.channel_enum = "google_ads"
    activation.audience_segment = "brand_aware"

    # Mock Campaign lookup
    campaign = MagicMock()
    campaign.manager_email = "manager@example.com"
    campaign.manager_phone = "+1234567890"

    with patch.object(DigitalActivatorAgent, '_get_campaign', return_value=campaign):
        agent = DigitalActivatorAgent(db_session)

        with pytest.raises(ValueError, match="No platform config found"):
            await agent.activate(activation, creative_url="https://example.com/ad.jpg")


@pytest.mark.asyncio
async def test_digital_activator_returns_correct_platforms(db_session: AsyncSession):
    """Test agent returns queued platforms in response."""
    activation_id = uuid4()
    tenant_id = uuid4()
    campaign_id = uuid4()

    # Create platform config
    config = PlatformConfigTemplate(
        tenant_id=str(tenant_id),
        channel_enum="google_ads",
        audience_segment="brand_aware",
        platform_targeting_json={"age_min": 18, "age_max": 65},
        budget_multiplier=1.0
    )
    db_session.add(config)
    await db_session.commit()

    # Mock Activation object
    activation = MagicMock()
    activation.id = activation_id
    activation.tenant_id = str(tenant_id)
    activation.campaign_id = campaign_id
    activation.status = "approved"
    activation.channel_enum = "google_ads"
    activation.audience_segment = "brand_aware"

    # Mock Campaign lookup
    campaign = MagicMock()
    campaign.manager_email = "manager@example.com"
    campaign.manager_phone = "+1234567890"

    with patch.object(DigitalActivatorAgent, '_get_campaign', return_value=campaign), \
         patch.object(DigitalActivatorAgent, '_queue_platform_activation') as mock_queue:

        agent = DigitalActivatorAgent(db_session)
        result = await agent.activate(activation, creative_url="https://example.com/ad.jpg")

        # Verify platforms list
        assert result["platforms"] == ["google_ads"]
        assert result["subtask_count"] == 1
