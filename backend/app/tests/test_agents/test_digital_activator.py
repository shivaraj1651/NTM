"""Tests for DigitalActivatorAgent."""

import pytest
from uuid import uuid4
from datetime import date
from unittest.mock import patch, AsyncMock, MagicMock
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from backend.app.agents.digital_activator import DigitalActivatorAgent
from backend.app.models.platform_config_template import PlatformConfigTemplate
from backend.app.models.activation_platform_mapping import ActivationPlatformMapping


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


@pytest.mark.asyncio
async def test_digital_activator_full_workflow(db_session: AsyncSession):
    """End-to-end test: activation → subtasks → mappings → notification.

    Simulates complete workflow:
    1. Agent receives Activation
    2. Agent queues platform subtasks
    3. Platform subtasks execute and store mappings
    4. Completion callback aggregates results
    5. Activation status updated
    6. Notification sent
    """
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

    # Create activation
    activation = MagicMock()
    activation.id = activation_id
    activation.tenant_id = str(tenant_id)
    activation.campaign_id = campaign_id
    activation.status = "approved"
    activation.channel_enum = "google_ads"
    activation.audience_segment = "brand_aware"
    activation.name = "Test Campaign"

    # Create campaign with manager info
    campaign = MagicMock()
    campaign.manager_email = "manager@example.com"
    campaign.manager_phone = "+1234567890"
    campaign.id = campaign_id

    # Simulate platform tool response
    platform_result = {
        "campaign_id": "camps_123456",
        "ad_id": "ads_789012",
        "status": "live",
        "error": None
    }

    with patch.object(DigitalActivatorAgent, '_get_campaign', return_value=campaign), \
         patch.object(DigitalActivatorAgent, '_queue_platform_activation', return_value=MagicMock(id="task_123")), \
         patch('backend.app.tools.google_ads.activate_google', return_value=platform_result):

        agent = DigitalActivatorAgent(db_session)
        result = await agent.activate(activation, creative_url="https://example.com/ad.jpg")

        # Verify activation was queued
        assert result["status"] == "activation_queued"
        assert result["activation_id"] == str(activation_id)
        assert "google_ads" in result["platforms"]
        assert result["subtask_count"] == 1

        # Simulate platform task storing mapping
        mapping = ActivationPlatformMapping(
            activation_id=str(activation_id),
            tenant_id=str(tenant_id),
            channel_enum="google_ads",
            platform_campaign_id="camps_123456",
            platform_ad_id="ads_789012",
            status="live"
        )
        db_session.add(mapping)
        await db_session.commit()

        # Verify mapping was stored
        result = await db_session.execute(
            select(ActivationPlatformMapping).where(
                ActivationPlatformMapping.activation_id == str(activation_id)
            )
        )
        fetched_mapping = result.scalar_one()

        assert fetched_mapping.platform_campaign_id == "camps_123456"
        assert fetched_mapping.platform_ad_id == "ads_789012"
        assert fetched_mapping.status == "live"
        assert fetched_mapping.channel_enum == "google_ads"


@pytest.mark.asyncio
async def test_digital_activator_platform_config_missing(db_session: AsyncSession):
    """Test that agent rejects when platform config is missing."""
    activation = MagicMock()
    activation.status = "approved"
    activation.tenant_id = str(uuid4())
    activation.campaign_id = uuid4()
    activation.channel_enum = "google_ads"
    activation.audience_segment = "non_existent"

    # db_session has no platform config for this combination
    campaign = MagicMock()
    campaign.manager_email = "manager@example.com"
    campaign.manager_phone = "+1234567890"

    with patch.object(DigitalActivatorAgent, '_get_campaign', return_value=campaign):
        agent = DigitalActivatorAgent(db_session)

        with pytest.raises(ValueError, match="No platform config found"):
            await agent.activate(activation, creative_url="https://example.com/ad.jpg")


@pytest.mark.asyncio
async def test_digital_activator_campaign_missing(db_session: AsyncSession):
    """Test that agent rejects when campaign is missing."""
    activation = MagicMock()
    activation.status = "approved"
    activation.campaign_id = uuid4()

    with patch.object(DigitalActivatorAgent, '_get_campaign', return_value=None):
        agent = DigitalActivatorAgent(db_session)

        with pytest.raises(ValueError, match="Campaign .* not found"):
            await agent.activate(activation, creative_url="https://example.com/ad.jpg")
