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
