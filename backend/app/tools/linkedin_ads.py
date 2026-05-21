"""LinkedIn Ads activation tool for B2B campaign deployment."""

import logging
import os
from typing import Dict, Any, Optional

import httpx

logger = logging.getLogger(__name__)

_LINKEDIN_BASE = "https://api.linkedin.com/rest"


def _get_access_token(token: Optional[str] = None) -> str:
    t = token or os.getenv("LINKEDIN_ACCESS_TOKEN", "")
    if not t:
        raise RuntimeError(
            "LINKEDIN_ACCESS_TOKEN must be set or access_token must be provided"
        )
    return t


async def activate_linkedin(
    activation: Dict[str, Any],
    platform_config: Dict[str, Any],
    creative_url: str,
    access_token: Optional[str] = None,
) -> Dict[str, Any]:
    account_id = os.getenv("LINKEDIN_ACCOUNT_ID", "")

    try:
        token = _get_access_token(access_token)
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
            "LinkedIn-Version": "202401",
            "X-Restli-Protocol-Version": "2.0.0",
        }
        campaign_name = activation.get("name", "Campaign")

        async with httpx.AsyncClient(timeout=30.0) as client:
            # Call 1: Create Campaign Group
            r1 = await client.post(
                f"{_LINKEDIN_BASE}/adCampaignGroups",
                json={
                    "name": f"{campaign_name} - Group",
                    "status": "ACTIVE",
                    "account": f"urn:li:sponsoredAccount:{account_id}",
                },
                headers=headers,
            )
            r1.raise_for_status()
            campaign_group_id = r1.json()["id"]

            # Call 2: Create Campaign with B2B targeting from platform_config
            r2 = await client.post(
                f"{_LINKEDIN_BASE}/adCampaigns",
                json={
                    "name": campaign_name,
                    "status": "ACTIVE",
                    "type": "SPONSORED_UPDATE",
                    "campaignGroup": f"urn:li:adCampaignGroup:{campaign_group_id}",
                    "costType": "CPM",
                    "dailyBudget": {
                        "amount": str(activation.get("cost_estimated", 0)),
                        "currencyCode": "USD",
                    },
                    "targetingCriteria": {
                        "include": {
                            "and": [
                                {"seniorities": platform_config.get("seniority", [])},
                                {"jobFunctions": platform_config.get("job_title", [])},
                                {"industries": platform_config.get("industries", [])},
                                {"locations": platform_config.get("locations", ["US"])},
                            ]
                        }
                    },
                },
                headers=headers,
            )
            r2.raise_for_status()
            campaign_id = str(r2.json()["id"])

            # Call 3: Create Creative
            r3 = await client.post(
                f"{_LINKEDIN_BASE}/adCreatives",
                json={
                    "campaign": f"urn:li:adCampaign:{campaign_id}",
                    "status": "ACTIVE",
                    "content": {"contentReference": creative_url},
                },
                headers=headers,
            )
            r3.raise_for_status()
            ad_id = str(r3.json()["id"])

            logger.info("LinkedIn campaign %s activated successfully", campaign_id)
            return {
                "campaign_id": campaign_id,
                "ad_id": ad_id,
                "status": "live",
                "error": None,
            }

    except Exception as e:
        logger.error("LinkedIn activation failed: %s: %s", type(e).__name__, str(e))
        return {
            "campaign_id": None,
            "ad_id": None,
            "status": "failed",
            "error": str(e),
        }
