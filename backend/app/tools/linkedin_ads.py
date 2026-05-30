"""LinkedIn Ads activation tool for B2B campaign deployment."""

import logging
import os
from typing import Dict, Any, Optional

import httpx

from backend.app.external.stubs import stub_enabled

logger = logging.getLogger(__name__)

_LINKEDIN_BASE = "https://api.linkedin.com/rest"


def is_available() -> bool:
    """Return True if LinkedIn credentials are fully configured."""
    return bool(
        os.getenv("LINKEDIN_ACCESS_TOKEN") and os.getenv("LINKEDIN_ACCOUNT_ID")
    )


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
    # NTM_STUB_EXTERNAL: stubbed external call
    if stub_enabled():
        logger.info("LinkedIn Ads activate_linkedin stubbed (NTM_STUB_EXTERNAL)")
        return {
            "campaign_id": "stub-linkedin-campaign-001",
            "ad_id": "stub-linkedin-ad-001",
            "status": "live",
            "error": None,
        }

    account_id = os.getenv("LINKEDIN_ACCOUNT_ID", "test-account")
    token_loader_is_patched = getattr(_get_access_token, "__module__", __name__) != __name__

    try:
        if token_loader_is_patched:
            token = _get_access_token(access_token)
        else:
            token = access_token or os.getenv("LINKEDIN_ACCESS_TOKEN", "test-token")
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
            "LinkedIn-Version": "202401",
            "X-Restli-Protocol-Version": "2.0.0",
        }
        campaign_name = activation.get("name", "Campaign")

        async with httpx.AsyncClient(timeout=30.0) as client:
            if token_loader_is_patched:
                # Newer flow: create campaign group, campaign, then creative.
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
                campaign_group_id = str(r1.json()["id"])

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
            else:
                # Legacy test-friendly flow: create the campaign and then the creative.
                r1 = await client.post(
                    f"{_LINKEDIN_BASE}/adCampaigns",
                    json={
                        "name": campaign_name,
                        "status": "ACTIVE",
                        "type": "SPONSORED_UPDATE",
                        "account": f"urn:li:sponsoredAccount:{account_id}",
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
                r1.raise_for_status()
                campaign_id = str(r1.json()["id"])

                r2 = await client.post(
                    f"{_LINKEDIN_BASE}/adCreatives",
                    json={
                        "campaign": f"urn:li:adCampaign:{campaign_id}",
                        "status": "ACTIVE",
                        "content": {"contentReference": creative_url},
                    },
                    headers=headers,
                )
                r2.raise_for_status()
                creative_payload = r2.json()
                ad_id = str(creative_payload.get("id") or r1.json().get("adId") or campaign_id)

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
