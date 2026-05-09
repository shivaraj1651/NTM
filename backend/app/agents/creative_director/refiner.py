"""Refinement loop for Creative Director Agent (AGT-06).

Auto-refines creatives based on validation violations with max_attempts limit.
Escalates to partial status if max_attempts exceeded.
"""

import logging
from typing import Dict, Any
import asyncio

logger = logging.getLogger(__name__)


class Refiner:
    """Refines creatives iteratively based on validation violations."""

    def __init__(self, max_attempts: int = 2):
        """Initialize Refiner with max refinement attempts.

        Args:
            max_attempts: Maximum number of refinement iterations (default: 2)
        """
        self.max_attempts = max_attempts
        # These will be initialized externally
        self.generator = None
        self.validator = None

    async def refine(
        self,
        creative: Dict[str, Any],
        validation_result: Dict[str, Any],
        platform: str,
        brand_rules: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Refine creative iteratively based on validation violations.

        Args:
            creative: The creative content to refine (dict with content, etc.)
            validation_result: Result from validation with violations list
            platform: Target platform
            brand_rules: Brand guidelines dict

        Returns:
            Dict with:
                - status: "passed", "failed", or "partial" (escalated after max_attempts)
                - content: The refined creative content
                - attempts: Number of refinement attempts made
                - violations: List of remaining violations
                - escalated: Boolean indicating if escalated to partial status
        """
        if self.generator is None or self.validator is None:
            raise RuntimeError("Refiner not properly initialized: generator and validator required")

        current_creative = creative.copy()
        current_validation = validation_result.copy()
        attempt_count = 0
        escalated = False

        # Iterate refinement up to max_attempts
        while attempt_count < self.max_attempts and current_validation.get("status") == "failed":
            attempt_count += 1
            violations = current_validation.get("violations", [])

            if not violations:
                # No violations means it should have passed
                break

            logger.info(
                f"Refining creative on platform {platform} - attempt {attempt_count}/{self.max_attempts}"
            )

            # Call generator to refine based on violations
            try:
                # Build refinement prompt context
                refinement_context = {
                    "current_creative": current_creative,
                    "violations": violations,
                    "platform": platform,
                    "brand_rules": brand_rules
                }

                # Generate refined version (assuming generator has a refine method)
                if hasattr(self.generator, "refine_creative"):
                    refined_content = await self.generator.refine_creative(refinement_context)
                else:
                    # Fallback: use standard generation with violations context
                    refined_content = await self.generator.generate_platform_creatives(
                        platform=platform,
                        core_concept={},
                        campaign_data={
                            "campaign_input": brand_rules,
                            "violations": violations
                        },
                        creative_type=creative.get("type", "copy")
                    )

                # Extract first refined creative if list returned
                if isinstance(refined_content, list) and len(refined_content) > 0:
                    current_creative = refined_content[0]
                else:
                    current_creative = refined_content

                # Validate the refined creative
                if hasattr(current_creative, "copy"):
                    # Pydantic model
                    from backend.app.agents.creative_director.models import Copy

                    if isinstance(current_creative, Copy):
                        current_validation = {
                            "status": current_creative.validation.status,
                            "violations": current_creative.validation.violations,
                            "warnings": current_creative.validation.warnings
                        }
                    else:
                        # Re-validate
                        current_validation = self._validate_refined_creative(
                            current_creative, platform, brand_rules
                        )
                else:
                    # Re-validate dict form
                    current_validation = self._validate_refined_creative(
                        current_creative, platform, brand_rules
                    )

            except Exception as e:
                logger.error(f"Error during refinement attempt {attempt_count}: {e}")
                # Don't break - try next attempt
                continue

        # Check if we exhausted attempts while still failing
        if attempt_count >= self.max_attempts and current_validation.get("status") == "failed":
            escalated = True
            final_status = "partial"
        else:
            final_status = current_validation.get("status", "failed")

        return {
            "status": final_status,
            "content": current_creative,
            "attempts": attempt_count,
            "violations": current_validation.get("violations", []),
            "escalated": escalated
        }

    def _validate_refined_creative(
        self,
        creative: Dict[str, Any],
        platform: str,
        brand_rules: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Validate a refined creative.

        Args:
            creative: Creative content dict
            platform: Target platform
            brand_rules: Brand guidelines

        Returns:
            Validation result dict
        """
        if self.validator is None:
            return {
                "status": "passed",
                "violations": [],
                "warnings": []
            }

        try:
            # Attempt to validate based on creative type
            creative_type = creative.get("type", "copy")

            if creative_type == "copy" or "content" in creative:
                # Validate as copy
                from backend.app.agents.creative_director.models import Copy

                copy_obj = Copy(
                    content=creative.get("content", ""),
                    character_count=len(creative.get("content", "")),
                    tone=creative.get("tone", ""),
                )
                validation = self.validator.validate_copy(copy_obj, platform, brand_rules)
                return {
                    "status": validation.status,
                    "violations": validation.violations,
                    "warnings": validation.warnings
                }
            else:
                # Default pass for unknown types
                return {
                    "status": "passed",
                    "violations": [],
                    "warnings": []
                }
        except Exception as e:
            logger.error(f"Error validating refined creative: {e}")
            return {
                "status": "failed",
                "violations": [{"message": str(e), "severity": "error"}],
                "warnings": []
            }
