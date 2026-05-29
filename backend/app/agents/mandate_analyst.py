"""
Mandate Analyst Agent (AGT-01).

Validates mandates for completeness and contradictions, produces structured summary cards.
"""

import json
import logging
from datetime import datetime, timezone
from typing import Dict, List, Any

from anthropic import AsyncAnthropic
from backend.app.external.stubs import stub_enabled

logger = logging.getLogger(__name__)


class MandateValidator:
    """
    Validates mandate dict for required fields and basic type checks.

    Required fields (17 total):
    - Top-level: approval_date, mandated_by, version, status (4)
    - campaign_concept: id, name, objective, description, target_audience, timeline (6)
    - budget: total_amount, currency, allocation_strategy, contingency_reserve (4)
    - geography: regions, markets, country_list (3)
    """

    REQUIRED_FIELDS = {
        "top_level": ["approval_date", "mandated_by", "version", "status"],
        "campaign_concept": ["id", "name", "objective", "description", "target_audience", "timeline"],
        "budget": ["total_amount", "currency", "allocation_strategy", "contingency_reserve"],
        "geography": ["regions", "markets", "country_list"]
    }

    def __init__(self):
        """Initialize validator."""
        self.total_required = sum(len(v) for v in self.REQUIRED_FIELDS.values())

    def validate(self, mandate: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate mandate for required fields.

        Args:
            mandate: Raw mandate dict

        Returns:
            Dict with is_complete, missing_fields, field_count, field_total
        """
        missing_fields: List[str] = []
        field_count = 0

        # Check top-level fields
        for field in self.REQUIRED_FIELDS["top_level"]:
            if field in mandate and mandate[field] is not None:
                field_count += 1
            else:
                missing_fields.append(field)

        # Check nested sections
        for section, fields in self.REQUIRED_FIELDS.items():
            if section == "top_level":
                continue

            if section not in mandate or mandate[section] is None:
                # Entire section missing
                for field in fields:
                    missing_fields.append(f"{section}.{field}")
            else:
                section_data = mandate[section]
                if not isinstance(section_data, dict):
                    # Non-dict section treated as missing
                    for field in fields:
                        missing_fields.append(f"{section}.{field}")
                else:
                    for field in fields:
                        if field in section_data and section_data[field] is not None:
                            field_count += 1
                        else:
                            missing_fields.append(f"{section}.{field}")

        return {
            "is_complete": len(missing_fields) == 0,
            "missing_fields": missing_fields,
            "field_count": field_count,
            "field_total": self.total_required
        }


async def analyze_mandate_with_llm(mandate: Dict[str, Any], validation_result: Dict[str, Any]) -> Dict[str, Any]:
    """
    Call Claude Sonnet to detect contradictions and produce summary card.

    Args:
        mandate: Full mandate dict
        validation_result: Output from MandateValidator

    Returns:
        Dict with contradictions, mandate_summary, completeness_score
    """
    client = AsyncAnthropic()

    system_prompt = """You are a mandate validation expert. Analyze the provided mandate for:
1. Contradictions between sections (budget vs timeline, geography vs audience)
2. Risk flags (unrealistic timelines, insufficient budget, scope creep)
3. Completeness and strategic intent clarity

Respond ONLY with valid JSON, no markdown. Do not wrap in code blocks.

Structure your response exactly as:
{
  "contradictions": ["list", "of", "contradiction", "strings"],
  "mandate_summary": {
    "objective": "clear statement of mandate objective",
    "budget_total": "budget amount and currency",
    "timeline": "timeline description",
    "key_risks": ["list", "of", "risk", "flags"],
    "readiness": "Ready to proceed" or "Needs clarification"
  },
  "completeness_score": <integer 0-100>
}"""

    user_prompt = f"""Analyze this mandate for contradictions and quality.

Missing fields: {validation_result['missing_fields']}

Mandate data:
{json.dumps(mandate, indent=2)}"""

    # NTM_STUB_EXTERNAL: stubbed external call
    if stub_enabled():
        logger.info("Mandate analyst LLM stubbed (NTM_STUB_EXTERNAL)")
        return {
            "contradictions": [],
            "mandate_summary": {
                "objective": mandate.get("objective", "stub"),
                "budget_total": str(mandate.get("budget", {}).get("total_amount", 0)),
                "timeline": "stub timeline",
                "key_risks": [],
                "readiness": "Ready to proceed",
            },
            "completeness_score": 90,
        }

    response = await client.messages.create(
        model="claude-sonnet-4-5",
        max_tokens=2000,
        system=system_prompt,
        messages=[{"role": "user", "content": user_prompt}]
    )

    # Parse LLM response
    if not response.content or not response.content[0].text:
        return {
            "contradictions": [],
            "mandate_summary": {
                "objective": "API response empty or malformed",
                "budget_total": "N/A",
                "timeline": "N/A",
                "key_risks": ["Response parsing failed"],
                "readiness": "Needs clarification"
            },
            "completeness_score": 0,
            "error": "API returned empty response"
        }

    response_text = response.content[0].text
    try:
        result = json.loads(response_text)
    except json.JSONDecodeError:
        # Fallback if LLM response isn't valid JSON
        return {
            "contradictions": [],
            "mandate_summary": {
                "objective": "Unable to parse LLM response",
                "budget_total": "N/A",
                "timeline": "N/A",
                "key_risks": ["LLM parsing failed"],
                "readiness": "Needs clarification"
            },
            "completeness_score": 0,
            "error": "LLM response was not valid JSON"
        }

    return result


async def mandate_analyst_agent(mandate: Dict[str, Any]) -> Dict[str, Any]:
    """
    AGT-01 Mandate Analyst Agent entry point.

    Orchestrates two-phase validation:
    1. Python validator: checks required fields
    2. LLM validator: detects contradictions and synthesizes summary

    Args:
        mandate: Raw mandate dict from API

    Returns:
        Pure JSON output with validation results and summary card
    """
    # Phase 1: Python validation
    validator = MandateValidator()
    validation_result = validator.validate(mandate)

    # Phase 2: LLM analysis
    llm_result = await analyze_mandate_with_llm(mandate, validation_result)

    # Merge results
    final_output = {
        "completeness_score": llm_result["completeness_score"],
        "missing_fields": validation_result["missing_fields"],
        "contradictions": llm_result.get("contradictions", []),
        "mandate_summary": llm_result.get("mandate_summary", {}),
        "validated_at": datetime.now(timezone.utc).isoformat()
    }

    return final_output
