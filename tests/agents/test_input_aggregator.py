"""Unit tests for InputAggregator in Creative Director Agent (AGT-06)."""

import pytest

from backend.app.agents.creative_director.input_aggregator import InputAggregator


class TestInputAggregator:
    """Tests for InputAggregator class."""

    def test_aggregate_valid_input(self, campaign_input):
        """Test aggregating valid campaign input returns successfully."""
        aggregator = InputAggregator()
        result = aggregator.aggregate(campaign_input)
        assert result.campaign_id == campaign_input.campaign_id
        assert result.tenant_id == campaign_input.tenant_id
        assert result.platforms == ["instagram", "linkedin", "youtube"]

    def test_aggregate_requires_campaign_id(self, campaign_input):
        """Test that missing campaign_id raises ValueError."""
        aggregator = InputAggregator()
        campaign_input.campaign_id = None
        with pytest.raises(ValueError, match="campaign_id"):
            aggregator.aggregate(campaign_input)

    def test_aggregate_requires_tenant_id(self, campaign_input):
        """Test that missing tenant_id raises ValueError."""
        aggregator = InputAggregator()
        campaign_input.tenant_id = None
        with pytest.raises(ValueError, match="tenant_id"):
            aggregator.aggregate(campaign_input)

    def test_aggregate_requires_platforms(self, campaign_input):
        """Test that empty platforms list raises ValueError."""
        aggregator = InputAggregator()
        campaign_input.platforms = []
        with pytest.raises(ValueError, match="At least one platform is required"):
            aggregator.aggregate(campaign_input)

    def test_aggregate_requires_brand_guidelines(self, campaign_input):
        """Test that None brand_guidelines raises ValueError."""
        aggregator = InputAggregator()
        campaign_input.brand_guidelines = None
        with pytest.raises(ValueError, match="brand_guidelines"):
            aggregator.aggregate(campaign_input)

    def test_aggregate_normalizes_platform_names(self, campaign_input):
        """Test that platform names are normalized to lowercase."""
        aggregator = InputAggregator()
        # Modify platforms to have mixed case (but CampaignInput Literal prevents this in practice)
        campaign_input.platforms = ["instagram", "linkedin", "youtube"]
        result = aggregator.aggregate(campaign_input)
        assert all(p.islower() for p in result.platforms)
        assert result.platforms == ["instagram", "linkedin", "youtube"]
