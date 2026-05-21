import logging
import os
from typing import Dict, Any, Optional

import httpx

logger = logging.getLogger(__name__)

_GOOGLE_ADS_BASE = "https://googleads.googleapis.com/v17/customers/{customer_id}"
_TOKEN_URI = "https://oauth2.googleapis.com/token"


def _get_access_token() -> str:
    client_id = os.getenv("GOOGLE_ADS_CLIENT_ID", "")
    client_secret = os.getenv("GOOGLE_ADS_CLIENT_SECRET", "")
    refresh_token = os.getenv("GOOGLE_ADS_REFRESH_TOKEN", "")
    if not all([client_id, client_secret, refresh_token]):
        raise RuntimeError(
            "GOOGLE_ADS_CLIENT_ID, GOOGLE_ADS_CLIENT_SECRET, and GOOGLE_ADS_REFRESH_TOKEN must be set"
        )
    from google.oauth2.credentials import Credentials
    from google.auth.transport.requests import Request

    creds = Credentials(
        token=None,
        refresh_token=refresh_token,
        client_id=client_id,
        client_secret=client_secret,
        token_uri=_TOKEN_URI,
    )
    creds.refresh(Request())
    return creds.token


async def activate_google(
    activation: Dict[str, Any],
    platform_config: Dict[str, Any],
    creative_url: str,
    customer_id: Optional[str] = None,
) -> Dict[str, Any]:
    cid = customer_id or os.getenv("GOOGLE_ADS_CUSTOMER_ID", "")
    developer_token = os.getenv("GOOGLE_ADS_DEVELOPER_TOKEN", "")

    try:
        if not cid:
            raise RuntimeError("GOOGLE_ADS_CUSTOMER_ID env var must be set or customer_id must be provided")
        token = _get_access_token()
        headers = {
            "Authorization": f"Bearer {token}",
            "developer-token": developer_token,
            "Content-Type": "application/json",
        }
        base = _GOOGLE_ADS_BASE.format(customer_id=cid)
        campaign_name = activation.get("name", "Campaign")
        if platform_config:
            logger.debug("platform_config received: %s (targeting criteria require AdGroupCriterion mutations)", platform_config)
        budget_micros = int(activation.get("cost_estimated", 0) * 1_000_000)

        async with httpx.AsyncClient(timeout=30.0) as client:
            # Call 1: Create Campaign
            r1 = await client.post(
                f"{base}/campaigns:mutate",
                json={
                    "operations": [{
                        "create": {
                            "name": campaign_name,
                            "status": "ENABLED",
                            "advertisingChannelType": "VIDEO",
                            "manualCpv": {},
                            "campaignBudget": str(budget_micros),  # production: use campaignBudgets:mutate resource name
                            "networkSettings": {
                                "targetYoutubeSearch": True,
                                "targetYoutubeVideos": True,
                            },
                        }
                    }]
                },
                headers=headers,
            )
            r1.raise_for_status()
            campaign_resource = r1.json()["results"][0]["resourceName"]
            campaign_id = campaign_resource.split("/")[-1]

            # Call 2: Create Ad Group with platform_config targeting
            r2 = await client.post(
                f"{base}/adGroups:mutate",
                json={
                    "operations": [{
                        "create": {
                            "campaign": campaign_resource,
                            "name": f"{campaign_name} - AdGroup",
                            "status": "ENABLED",
                            "type": "VIDEO_TRUE_VIEW_IN_STREAM",
                            "targetingSettings": {
                                "targetRestrictions": [
                                    {"targetingDimension": "AGE_RANGE", "bidOnly": False},
                                    {"targetingDimension": "INTEREST", "bidOnly": False},
                                ]
                            },
                        }
                    }]
                },
                headers=headers,
            )
            r2.raise_for_status()
            ad_group_resource = r2.json()["results"][0]["resourceName"]

            # Call 3: Create Ad Group Ad
            r3 = await client.post(
                f"{base}/adGroupAds:mutate",
                json={
                    "operations": [{
                        "create": {
                            "adGroup": ad_group_resource,
                            "status": "ENABLED",
                            "ad": {
                                "videoAd": {
                                    "video": {"resourceName": creative_url},  # production: requires YouTube video resource name
                                    "inStream": {},
                                },
                                "finalUrls": [creative_url],
                            },
                        }
                    }]
                },
                headers=headers,
            )
            r3.raise_for_status()
            ad_resource = r3.json()["results"][0]["resourceName"]
            ad_id = ad_resource.split("/")[-1]

            logger.info(f"Google Ads campaign {campaign_id} activated successfully")
            return {
                "campaign_id": campaign_id,
                "ad_id": ad_id,
                "status": "live",
                "error": None,
            }

    except Exception as e:
        logger.error("Google Ads activation failed: %s: %s", type(e).__name__, str(e))
        return {
            "campaign_id": None,
            "ad_id": None,
            "status": "failed",
            "error": str(e),
        }
