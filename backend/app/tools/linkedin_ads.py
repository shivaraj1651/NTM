"""LinkedIn Ads activation tool for B2B campaign deployment."""

import logging
from typing import Dict, Any, Optional
import httpx

logger = logging.getLogger(__name__)

LINKEDIN_ADS_API_ENDPOINT = "https://api.linkedin.com/v2/sponsoredCampaigns"


async def activate_linkedin(
    activation: Dict[str, Any],
    platform_config: Dict[str, Any],
    creative_url: str,
    access_token: Optional[str] = None
) -> Dict[str, Any]:
    """
    Activate a campaign on LinkedIn.

    Args:
        activation: Activation record with budget and targeting
        platform_config: LinkedIn-specific B2B targeting from PlatformConfigTemplate
                         Keys: seniority, job_title, industries, locations
        creative_url: URL to creative asset
        access_token: LinkedIn API access token

    Returns:
        Dict with:
        - campaign_id: LinkedIn campaign ID (urn:li:sponsoredCampaign:...) or None
        - ad_id: LinkedIn ad ID (urn:li:sponsoredCreative:...) or None
        - status: 'live' or 'failed'
        - error: Error message or None
    """
    if not access_token:
        access_token = "<linkedin-token>"  # Placeholder

    try:
        # Create campaign payload with budget
        campaign_payload = {
            "name": activation.get("name", "Campaign"),
            "status": "ACTIVE",
            "costType": "CPM",
            "unitCost": {"currencyCode": "USD", "amount": 5},
            "dailyBudget": {
                "currencyCode": "USD",
                "amount": int(activation.get("cost_estimated", 0))
            }
        }

        async with httpx.AsyncClient(timeout=30.0) as client:
            # Create sponsored campaign
            campaign_response = await client.post(
                LINKEDIN_ADS_API_ENDPOINT,
                headers={
                    "Authorization": f"Bearer {access_token}",
                    "Content-Type": "application/json",
                    "LinkedIn-Version": "202401"
                },
                json=campaign_payload
            )
            campaign_response.raise_for_status()
            campaign_data = campaign_response.json()
            campaign_id = campaign_data.get("id")

            # Create ad creative with B2B targeting
            creative_payload = {
                "campaignId": campaign_id,
                "status": "ACTIVE",
                "creativeContent": {
                    "contentReference": creative_url,
                    "contentTitle": activation.get("name", "Campaign"),
                    "contentDescription": "Check out our latest campaign"
                },
                "targetingCriteria": {
                    "seniorities": platform_config.get("seniority", []),
                    "jobTitles": platform_config.get("job_title", []),
                    "industries": platform_config.get("industries", []),
                    "locations": [
                        {"country": loc}
                        for loc in platform_config.get("locations", ["US"])
                    ]
                }
            }

            creative_response = await client.post(
                "https://api.linkedin.com/v2/sponsoredCreatives",
                headers={
                    "Authorization": f"Bearer {access_token}",
                    "Content-Type": "application/json",
                    "LinkedIn-Version": "202401"
                },
                json=creative_payload
            )
            creative_response.raise_for_status()
            creative_data = creative_response.json()
            ad_id = creative_data.get("id")

            logger.info(f"LinkedIn campaign {campaign_id} activated successfully")

            return {
                "campaign_id": campaign_id,
                "ad_id": ad_id,
                "status": "live",
                "error": None
            }

    except Exception as e:
        logger.error(f"LinkedIn activation failed: {e}")
        return {
            "campaign_id": None,
            "ad_id": None,
            "status": "failed",
            "error": str(e)
        }
