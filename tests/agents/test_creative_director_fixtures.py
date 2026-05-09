"""Verification tests for Creative Director Agent fixtures."""

import pytest
from tests.agents.conftest_creative_director import (
    brand_guidelines,
    target_audience,
    campaign_input,
    mock_claude_response,
    valid_output,
)


def test_fixtures_load_successfully(brand_guidelines, target_audience, campaign_input, valid_output):
    """Test that all fixtures load and are properly formed."""
    assert brand_guidelines is not None
    assert target_audience is not None
    assert campaign_input is not None
    assert valid_output is not None


def test_brand_guidelines_fixture(brand_guidelines):
    """Test brand_guidelines fixture is complete."""
    assert brand_guidelines.tone == "professional yet approachable"
    assert len(brand_guidelines.colors) == 3
    assert len(brand_guidelines.messaging_rules) == 3
    assert len(brand_guidelines.mandatory_ctas) == 3
    assert brand_guidelines.visual_style is not None
    assert brand_guidelines.tagline is not None


def test_target_audience_fixture(target_audience):
    """Test target_audience fixture is complete."""
    assert target_audience.demographics is not None
    assert target_audience.psychographics is not None
    assert target_audience.segments is not None
    assert len(target_audience.segments) == 2
    assert target_audience.language == "en"


def test_campaign_input_fixture(campaign_input, brand_guidelines, target_audience):
    """Test campaign_input fixture is complete."""
    assert campaign_input.campaign_id is not None
    assert campaign_input.tenant_id is not None
    assert len(campaign_input.objectives) == 3
    assert campaign_input.target_audience == target_audience
    assert campaign_input.brand_guidelines == brand_guidelines
    assert len(campaign_input.platforms) == 3
    assert "instagram" in campaign_input.platforms
    assert "linkedin" in campaign_input.platforms
    assert "youtube" in campaign_input.platforms
    assert campaign_input.budget_allocation is not None
    assert campaign_input.competitor_insights is not None


def test_mock_claude_response_fixture(mock_claude_response):
    """Test mock_claude_response fixture is complete."""
    assert "core_concept" in mock_claude_response
    assert "platforms" in mock_claude_response
    assert mock_claude_response["core_concept"]["message"] is not None
    assert "instagram" in mock_claude_response["platforms"]
    assert "linkedin" in mock_claude_response["platforms"]


def test_valid_output_fixture(valid_output, campaign_input):
    """Test valid_output fixture is complete."""
    assert valid_output.campaign_id == campaign_input.campaign_id
    assert valid_output.tenant_id == campaign_input.tenant_id
    assert valid_output.generation_id is not None
    assert valid_output.generated_at is not None
    assert len(valid_output.platforms) == 3
    assert "instagram" in valid_output.platforms
    assert "linkedin" in valid_output.platforms
    assert "youtube" in valid_output.platforms

    # Check instagram creatives
    instagram = valid_output.platforms["instagram"]
    assert len(instagram.copy) > 0
    assert len(instagram.image_prompts) > 0

    # Check linkedin creatives
    linkedin = valid_output.platforms["linkedin"]
    assert len(linkedin.copy) > 0

    # Check youtube creatives (most complete)
    youtube = valid_output.platforms["youtube"]
    assert len(youtube.copy) > 0
    assert len(youtube.video_concepts) > 0
    assert len(youtube.voiceover_scripts) > 0

    # Check metadata
    assert valid_output.metadata.validation_status == "passed"
    assert valid_output.metadata.core_concept is not None
