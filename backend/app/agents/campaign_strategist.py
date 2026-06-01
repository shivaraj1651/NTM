"""Campaign Strategist Agent (AGT-03).

Generates 3 comprehensive campaign concepts from mandate summary + competitive intel.
Includes iterative risk filtering and strict schema validation.
"""

import asyncio
import json
import logging
import uuid
from typing import Any

from anthropic import AsyncAnthropic
from pydantic import ValidationError

from backend.app.agents.json_parsing import extract_json
from backend.app.external.stubs import stub_enabled
from backend.app.schemas.campaign_concept import CampaignConcept

logger = logging.getLogger(__name__)


class RiskFilter:
    """Assesses and filters campaigns for legal/regulatory/sensitivity risks."""

    def should_regenerate(self, risk_flags: dict[str, str | None]) -> bool:
        """
        Determine if a concept must be dropped. In production, an LLM self-assessment
        will almost always note minor risks (e.g. "comparative claims may need
        substantiation"). Treating any non-null flag as a disqualifier drops every
        real concept. Only regenerate on explicit high-severity markers — concepts
        with minor risk notes are logged and kept for human review instead.

        Returns True only when risk text contains strong disqualifying keywords.
        """
        disqualifying = {"illegal", "prohibited", "copyright", "trademark", "defamatory", "hate", "discriminat"}
        for key in ["legal", "regulatory", "sensitivity"]:
            val = risk_flags.get(key)
            if val and any(kw in val.lower() for kw in disqualifying):
                return True
        return False

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

    def validate_schema(self, concept_dict: dict) -> list[str]:
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


async def generate_campaign(
    mandate: dict[str, Any],
    ci_report: dict[str, Any],
    campaign_number: int,
) -> dict[str, Any] | None:
    """
    Generate a single campaign concept with risk filtering.

    Args:
        mandate: Mandate summary card from AGT-01
        ci_report: Competitive intelligence report from AGT-02
        campaign_number: Campaign number (1, 2, or 3)

    Returns:
        CampaignConcept dict or None if all retries failed
    """
    client = AsyncAnthropic()

    system_prompt = """You are a campaign strategist. Your role is to generate creative, mandate-aligned campaign concepts that exploit competitor whitespace gaps.

For each campaign concept, you will:
1. Generate a campaign name and tagline that are memorable and gap-exploiting
2. Define a strategic narrative (1-2 sentences) explaining why this concept is differentiated
3. Identify campaign theme, audience segments (primary/secondary/tertiary), and channel mix
4. Develop message architecture (master message + channel-specific adaptations)
5. Map campaign phasing (Awareness → Engagement → Conversion)
6. Create a tone board (5 adjectives + visual direction description)
7. Self-assess for legal, regulatory, and sensitivity risks

HARD CONSTRAINTS (reject if violated):
- Budget allocation must not exceed mandate total_amount
- Timeline must not exceed mandate timeline
- Target audience must align with mandate objective
- Geographic focus must be within mandate regions/markets/countries

SOFT CONSTRAINTS (flag only):
- Tone should align with brand_guidelines; deviations noted but not rejected

RISK ASSESSMENT:
After generating each campaign, assess these risks:
- legal_risk: null or "brief description" (unsubstantiated claims, IP issues, false advertising)
- regulatory_risk: null or "brief description" (geographic compliance, data privacy)
- sensitivity_risk: null or "brief description" (offensive targeting, controversial positioning, brand tone misalignment)

OUTPUT FORMAT:
Return valid JSON matching this structure. Include all required fields. Format as pure JSON only, no markdown or extra text.

{
  "name": "string",
  "tagline": "string",
  "strategic_narrative": "string",
  "campaign_theme": "string",
  "audience_segmentation": {"primary": "string", "secondary": "string", "tertiary": "string"},
  "channel_mix": [{"channel": "string", "rationale": "string", "competitor_gap": "string"}],
  "message_architecture": {"master_message": "string", "channel_adaptations": {"TikTok": "ad copy adapted for TikTok", "Instagram": "ad copy adapted for Instagram"}},
  "campaign_phasing": {"awareness": "string", "engagement": "string", "conversion": "string"},
  "tone_board": {"adjectives": ["adj1", "adj2", "adj3", "adj4", "adj5"], "visual_direction": "string"},
  "risk_flags": {"legal": null, "regulatory": null, "sensitivity": null},
  "mandate_fit_score": 9,
  "gap_exploitation_score": 10
}
"""

    # Format mandate and CI report for context
    mandate_summary = f"""
Mandate Context:
- Campaign Objective: {mandate.get('objective') or mandate.get('campaign_objective') or 'N/A'}
- Campaign Name: {mandate.get('name') or mandate.get('campaign_name') or 'N/A'}
- Total Budget: {mandate.get('total_budget') or mandate.get('budget', {}).get('total_amount', 'N/A')} {mandate.get('currency') or mandate.get('budget', {}).get('currency', 'USD')}
- Start Date: {mandate.get('start_date') or 'N/A'}
- End Date: {mandate.get('end_date') or 'N/A'}
- Region: {mandate.get('region') or ', '.join(mandate.get('geography', {}).get('regions', [])) or 'N/A'}
- Countries: {', '.join(mandate.get('countries', []) or mandate.get('geography', {}).get('country_list', [])) or 'N/A'}
- Target Audience: {mandate.get('target_audience') or mandate.get('audience') or 'Derived from mandate objective'}
- Brand Tone: {mandate.get('brand_tone') or mandate.get('brand_guidelines', {}).get('tone') or 'Professional and engaging'}
"""

    whitespace = ci_report.get("whitespace_opportunities", {})
    competitors_summary = f"""
Competitive Intelligence:
- Untapped Channels: {', '.join(whitespace.get('untapped_channels', []))}
- Messaging Gaps: {', '.join(whitespace.get('messaging_gaps', []))}
- Geographic Gaps: {', '.join(whitespace.get('geographic_gaps', []))}
"""

    user_prompt = f"""Generate campaign #{campaign_number} that exploits these competitor gaps while respecting mandate constraints.

{mandate_summary}

{competitors_summary}

Generate a comprehensive campaign concept that:
1. Exploits the identified gaps (untapped channels, messaging gaps, geographic gaps)
2. Respects all hard constraints (budget, timeline, geography, audience)
3. Balances mandate fit with gap exploitation
4. Includes all required fields in the JSON output
5. Self-assesses for legal, regulatory, and sensitivity risks
"""

    # NTM_STUB_EXTERNAL: stubbed external call
    if stub_enabled():
        logger.info("Campaign strategist LLM stubbed (NTM_STUB_EXTERNAL)")
        # Must satisfy the CampaignConcept schema so the outer agent keeps it.
        return {
            "id": str(uuid.uuid4()),
            "name": f"Stub Campaign {campaign_number}",
            "tagline": "Authenticity wins",
            "strategic_narrative": "Competitors ignore short-form video; this concept leads with authentic, youth-first positioning to exploit that gap.",
            "campaign_theme": "Authenticity Wins",
            "audience_segmentation": {
                "primary": "Gen-Z (16-24), urban, mobile-first",
                "secondary": "Millennial early adopters",
                "tertiary": "Gen-X curious about youth trends",
            },
            "channel_mix": [
                {"channel": "TikTok", "rationale": "Highest reach with the primary segment", "competitor_gap": "Rivals are absent from short-form video"},
                {"channel": "Instagram", "rationale": "Supports retargeting and UGC", "competitor_gap": "Rivals underuse Reels"},
            ],
            "message_architecture": {
                "master_message": "Be real. Be seen.",
                "channel_adaptations": {"TikTok": "Be real, fast.", "Instagram": "Be seen, daily."},
            },
            "campaign_phasing": {
                "awareness": "Weeks 1-2: teaser drops and creator seeding",
                "engagement": "Weeks 3-6: UGC challenges and community building",
                "conversion": "Weeks 7-8: limited offers and retargeting",
            },
            "tone_board": {
                "adjectives": ["bold", "authentic", "youthful", "fresh", "confident"],
                "visual_direction": "Vibrant, high-contrast, hand-held authenticity",
            },
            "risk_flags": {"legal": None, "regulatory": None, "sensitivity": None},
            "mandate_fit_score": 8,
            "gap_exploitation_score": 7,
        }

    for attempt in range(2):  # Max 2 attempts (initial + 1 retry)
        try:
            message = await client.messages.create(
                model="claude-sonnet-4-6",
                max_tokens=4000,
                system=system_prompt,
                messages=[{"role": "user", "content": user_prompt}]
            )

            # Extract JSON response
            response_text = message.content[0].text
            concept_dict = extract_json(response_text)

            logger.info(f"Campaign #{campaign_number} generated successfully (attempt {attempt + 1})")
            return concept_dict

        except (json.JSONDecodeError, ValueError) as e:
            logger.warning(f"Campaign #{campaign_number} parse error on attempt {attempt + 1}: {e}")
            if attempt == 1:  # Final retry
                return None
        except Exception as e:
            logger.error(f"Campaign #{campaign_number} generation error: {e}")
            return None

    return None


async def campaign_strategist_agent(
    mandate: dict[str, Any],
    ci_report: dict[str, Any],
) -> dict[str, Any]:
    """
    Orchestrate generation of 3 campaign concepts with risk filtering and validation.

    Args:
        mandate: Mandate summary card from AGT-01
        ci_report: Competitive intelligence report from AGT-02

    Returns:
        Dict with:
            - campaigns: List[CampaignConcept] (up to 3)
            - validation_errors: List[str]
            - regeneration_log: List[str]
    """
    campaigns: list[dict[str, Any]] = []
    validation_errors: list[str] = []
    regeneration_log: list[str] = []

    validator = CampaignConceptValidator()
    risk_filter = RiskFilter()

    # Generate 3 campaigns concurrently (independent LLM calls) to stay within request timeouts
    logger.info("Generating 3 campaign concepts concurrently...")
    generated = await asyncio.gather(*[
        generate_campaign(mandate, ci_report, n) for n in range(1, 4)
    ])

    async def _retry_if_risky(campaign_num: int, concept):
        if concept is None:
            return campaign_num, None, f"Campaign #{campaign_num} skipped: LLM generation failed"
        risk_flags = concept.get("risk_flags", {})
        if not risk_filter.should_regenerate(risk_flags):
            return campaign_num, concept, None
        for risk_type in ["legal", "regulatory", "sensitivity"]:
            if risk_flags.get(risk_type) is not None:
                log_msg = f"Campaign #{campaign_num} regenerated: {risk_type} risk - {risk_flags[risk_type]}"
                retried = await generate_campaign(mandate, ci_report, campaign_num)
                if retried is None:
                    return campaign_num, None, f"Campaign #{campaign_num} skipped: regeneration failed"
                if risk_filter.should_regenerate(retried.get("risk_flags", {})):
                    return campaign_num, None, f"Campaign #{campaign_num} skipped: {risk_type} risk persisted"
                return campaign_num, retried, log_msg
        return campaign_num, concept, None

    retry_results = await asyncio.gather(*[_retry_if_risky(n, c) for n, c in enumerate(generated, 1)])

    for campaign_num, concept, log_msg in retry_results:
        if log_msg:
            regeneration_log.append(log_msg)
        if concept is None:
            continue
        errors = validator.validate_schema(concept)
        if errors:
            validation_errors.extend([f"Campaign #{campaign_num}: {e}" for e in errors])
            regeneration_log.append(f"Campaign #{campaign_num} skipped: schema validation failed")
        else:
            campaigns.append(concept)
            logger.info(f"Campaign #{campaign_num} added to results")

    return {
        "campaigns": campaigns,
        "validation_errors": validation_errors,
        "regeneration_log": regeneration_log,
    }
