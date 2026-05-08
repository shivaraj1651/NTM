"""
Competitive Intelligence Agent (AGT-02, Phase 1 - Competitor Identification).

Identifies competitors based on mandate objectives, target audience, geography, and budget.
Phase 1 produces initial competitor list with confidence scores.
"""

import json
import logging
import uuid
from datetime import datetime
from typing import Any, Dict, List

from anthropic import AsyncAnthropic

from backend.app.schemas.competitive_intel import CompetitorIdentity, CIReportInitial

logger = logging.getLogger(__name__)


async def identify_competitors_sync(
    mandate: Dict[str, Any], client_profile: Dict[str, Any]
) -> List[CompetitorIdentity]:
    """
    Identify competitors using Claude Sonnet LLM.

    Parses mandate (objective, target_audience, geography, budget) and client_profile
    (industry, existing_competitors) to identify 5-10 most likely competitors.

    Args:
        mandate: Mandate dict with keys: objective, target_audience, geography (country_list), budget
        client_profile: Client profile dict with keys: industry, existing_competitors (optional)

    Returns:
        List of CompetitorIdentity with name and confidence (0-100)

    Raises:
        ValueError: If validation fails (count not 5-15, missing fields, invalid JSON)
    """
    client = AsyncAnthropic()

    # Parse mandate fields
    mandate_objective = mandate.get("campaign_concept", {}).get("objective", "")
    target_audience = mandate.get("campaign_concept", {}).get("target_audience", "")
    country_list = mandate.get("geography", {}).get("country_list", [])
    budget = mandate.get("budget", {}).get("total_amount", 0)

    # Parse client profile
    industry = client_profile.get("industry", "")
    existing_competitors = client_profile.get("existing_competitors", [])

    system_prompt = """You are a competitive intelligence expert. Identify the 5-10 most likely competitors.

Respond ONLY with valid JSON, no markdown. Do not wrap in code blocks.

Return exactly this structure:
{
  "competitors": [
    {"name": "company name", "confidence": <0-100>},
    ...
  ]
}"""

    user_prompt = f"""Based on the following context, identify 5-10 most likely competitors:

Industry: {industry}
Campaign Objective: {mandate_objective}
Target Audience: {target_audience}
Geographic Focus: {country_list}
Budget: ${budget}
Known Competitors: {existing_competitors if existing_competitors else "None provided"}

Return 5-15 competitors with confidence scores."""

    try:
        response = await client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=1000,
            temperature=0.3,
            system=system_prompt,
            messages=[{"role": "user", "content": user_prompt}],
        )
    except Exception as e:
        logger.error(f"LLM API call failed: {e}")
        raise ValueError(f"Failed to call LLM: {str(e)}")

    # Parse LLM response
    if not response.content or not response.content[0].text:
        logger.error("LLM returned empty response")
        raise ValueError("LLM returned empty response")

    response_text = response.content[0].text
    try:
        parsed = json.loads(response_text)
    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse LLM JSON response: {response_text}")
        raise ValueError(f"LLM response was not valid JSON: {str(e)}")

    # Validate response structure
    if "competitors" not in parsed:
        logger.error(f"Missing 'competitors' key in LLM response: {parsed}")
        raise ValueError("LLM response missing 'competitors' key")

    competitors_data = parsed["competitors"]
    if not isinstance(competitors_data, list):
        logger.error(f"'competitors' must be a list, got {type(competitors_data)}")
        raise ValueError("'competitors' must be a list")

    # Validate competitor count (5-15)
    if len(competitors_data) < 5 or len(competitors_data) > 15:
        logger.error(
            f"Competitor count out of range: {len(competitors_data)} (must be 5-15)"
        )
        raise ValueError(
            f"Competitor count must be 5-15, got {len(competitors_data)}"
        )

    # Validate each competitor has required fields
    competitors: List[CompetitorIdentity] = []
    for idx, comp in enumerate(competitors_data):
        if not isinstance(comp, dict):
            logger.error(f"Competitor {idx} is not a dict: {comp}")
            raise ValueError(f"Competitor {idx} must be a dict")

        if "name" not in comp or not comp["name"]:
            logger.error(f"Competitor {idx} missing 'name' field")
            raise ValueError(f"Competitor {idx} missing 'name' field")

        if "confidence" not in comp:
            logger.error(f"Competitor {idx} missing 'confidence' field")
            raise ValueError(f"Competitor {idx} missing 'confidence' field")

        try:
            confidence = int(comp["confidence"])
            if confidence < 0 or confidence > 100:
                raise ValueError("confidence must be 0-100")
        except (ValueError, TypeError) as e:
            logger.error(
                f"Competitor {idx} has invalid confidence '{comp['confidence']}': {e}"
            )
            raise ValueError(
                f"Competitor {idx} confidence must be integer 0-100, got '{comp['confidence']}'"
            )

        competitors.append(
            CompetitorIdentity(name=comp["name"], confidence=confidence)
        )

    logger.info(
        f"Successfully identified {len(competitors)} competitors with confidence scores"
    )
    return competitors


async def competitive_intel_agent(
    mandate: Dict[str, Any],
    client_profile: Dict[str, Any],
    mandate_id: str,
    tenant_id: str,
) -> CIReportInitial:
    """
    AGT-02 Phase 1 Competitor Identification Agent orchestration.

    Calls identify_competitors_sync() and produces initial CI report with
    pending status. Generates unique job_id for tracking.

    Args:
        mandate: Mandate dict from API
        client_profile: Client profile dict
        mandate_id: Associated mandate ID
        tenant_id: Tenant ID for multi-tenancy isolation

    Returns:
        CIReportInitial with status='pending' and competitor list

    Raises:
        ValueError: If competitor identification fails validation
    """
    logger.info(
        f"Starting Phase 1 Competitor Identification for mandate {mandate_id}"
    )

    try:
        # Identify competitors
        competitors = await identify_competitors_sync(mandate, client_profile)
        logger.info(f"Phase 1 identified {len(competitors)} competitors")

        # Generate job_id
        job_id = str(uuid.uuid4())

        # Create initial report
        report = CIReportInitial(
            job_id=job_id,
            mandate_id=mandate_id,
            competitors=competitors,
            status="pending",
            created_at=datetime.utcnow(),
        )

        logger.info(
            f"Phase 1 complete for mandate {mandate_id}, job_id {job_id}, status={report.status}"
        )
        return report

    except ValueError as e:
        logger.error(f"Phase 1 competitor identification failed: {e}")
        raise ValueError(f"Competitor identification failed: {str(e)}")
    except Exception as e:
        logger.error(f"Unexpected error in Phase 1: {e}")
        raise ValueError(f"Unexpected error in Phase 1: {str(e)}")
