"""Campaign Strategist Agent (AGT-03).

Generates 3 comprehensive campaign concepts from mandate summary + competitive intel.
Includes iterative risk filtering and strict schema validation.
"""

import json
import logging
from typing import Dict, List, Any, Optional

from pydantic import ValidationError

from backend.app.schemas.campaign_concept import CampaignConcept

logger = logging.getLogger(__name__)


class RiskFilter:
    """Assesses and filters campaigns for legal/regulatory/sensitivity risks."""

    def should_regenerate(self, risk_flags: Dict[str, Optional[str]]) -> bool:
        """
        Determine if campaign should be regenerated based on risk flags.

        Args:
            risk_flags: Dict with legal, regulatory, sensitivity keys

        Returns:
            True if any risk is detected (non-null), False otherwise
        """
        return any(risk_flags.get(key) is not None for key in ["legal", "regulatory", "sensitivity"])

    def get_regeneration_prompt(self, risk_type: str) -> str:
        """
        Get regeneration prompt for a specific risk type.

        Args:
            risk_type: One of "legal", "regulatory", "sensitivity"

        Returns:
            Regeneration prompt to append to LLM call
        """
        prompts = {
            "legal": (
                "Previous concept flagged for legal risk (unsubstantiated claims, IP issues). "
                "Revise to remove unsubstantiated claims. Ensure all benefits can be substantiated. "
                "Focus on verifiable mandate-aligned messaging while maintaining strategic relevance."
            ),
            "regulatory": (
                "Previous concept flagged for regulatory risk (geographic compliance, data privacy). "
                "Revise to ensure compliance with regulations in all target geographies. "
                "Remove any messaging that violates regional constraints while maintaining strategic relevance."
            ),
            "sensitivity": (
                "Previous concept flagged for sensitivity risk (offensive targeting, controversial positioning, tone misalignment). "
                "Revise to adopt professional, inclusive tone aligned with brand guidelines. "
                "Avoid sensitive or controversial positioning while maintaining strategic relevance."
            ),
        }
        return prompts.get(risk_type, "")


class CampaignConceptValidator:
    """Validates CampaignConcept JSON against Pydantic schema."""

    def validate_schema(self, concept_dict: dict) -> List[str]:
        """
        Validate a campaign concept dict against CampaignConcept schema.

        Args:
            concept_dict: Raw dict to validate

        Returns:
            List of validation error strings. Empty list means valid.
        """
        errors = []

        try:
            # Pydantic validation
            CampaignConcept(**concept_dict)
        except ValidationError as e:
            # Extract error messages
            for error in e.errors():
                field_path = ".".join(str(x) for x in error["loc"])
                msg = error["msg"]
                errors.append(f"Field '{field_path}': {msg}")

        return errors
