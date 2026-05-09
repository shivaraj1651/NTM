"""Input aggregator for Creative Director Agent (AGT-06).

Consolidates and validates inputs from upstream agents before passing to the generator.
"""

from typing import Dict, Optional
from backend.app.agents.creative_director.models import CampaignInput


class InputAggregator:
    """Validates and normalizes campaign input for creative generation."""

    VALID_PLATFORMS = {
        "instagram",
        "linkedin",
        "youtube",
        "meta_ads",
        "tiktok",
        "twitter",
    }

    def aggregate(self, campaign_input: CampaignInput) -> CampaignInput:
        """Validate and normalize campaign input.

        Args:
            campaign_input: Campaign input with all context needed for creative generation

        Returns:
            Normalized campaign input

        Raises:
            ValueError: If required fields are missing or invalid
        """
        # Validate required fields
        if not campaign_input.campaign_id:
            raise ValueError("campaign_id is required")

        if not campaign_input.tenant_id:
            raise ValueError("tenant_id is required")

        if not campaign_input.platforms:
            raise ValueError("At least one platform is required")

        if campaign_input.brand_guidelines is None:
            raise ValueError("brand_guidelines are required")

        # Normalize platform names to lowercase
        normalized_platforms = [p.lower() for p in campaign_input.platforms]

        # Validate platform names
        invalid_platforms = set(normalized_platforms) - self.VALID_PLATFORMS
        if invalid_platforms:
            raise ValueError(
                f"Invalid platform names: {invalid_platforms}. Valid platforms are: {self.VALID_PLATFORMS}"
            )

        # Update platforms with normalized names
        campaign_input.platforms = normalized_platforms

        return campaign_input

    def validate_upstream_inputs(self, inputs: Dict) -> Dict:
        """Validate that all required upstream inputs are present.

        Args:
            inputs: Dictionary of upstream inputs

        Returns:
            Validated inputs dictionary

        Raises:
            ValueError: If required inputs are missing
        """
        required_keys = {"campaign_input"}

        missing_keys = required_keys - set(inputs.keys())
        if missing_keys:
            raise ValueError(
                f"Missing required upstream inputs: {missing_keys}"
            )

        return inputs
