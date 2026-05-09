"""Shared pytest configuration and fixtures for agent tests."""

# Import all fixtures from conftest_creative_director to make them available globally
from tests.agents.conftest_creative_director import (
    brand_guidelines,
    target_audience,
    campaign_input,
    mock_claude_response,
    valid_output,
)

__all__ = [
    "brand_guidelines",
    "target_audience",
    "campaign_input",
    "mock_claude_response",
    "valid_output",
]
