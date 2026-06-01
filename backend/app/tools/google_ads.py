import logging
import os
from typing import Dict, Any, Optional

import httpx

from backend.app.external.stubs import stub_enabled

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
    # NTM_STUB_EXTERNAL: stubbed external call
    if stub_enabled():
        logger.info("Google Ads activate_google stubbed (NTM_STUB_EXTERNAL)")
        return {
            "campaign_id": "stub-google-campaign-001",
            "ad_id": "stub-google-ad-001",
            "status": "live",
            "error": None,
        }

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

        landing_url = creative_url if creative_url.startswith("http") else "https://example.com"
        headline1 = campaign_name[:30]
        headline2 = (activation.get("channel", "Digital") + " Campaign")[:30]
        headline3 = "Learn More Today"
        desc1 = activation.get("message", "Discover our latest campaign and special offers.")[:90]
        desc2 = "Contact us today to learn more about our products and services."[:90]

        async with httpx.AsyncClient(timeout=30.0) as client:
            # Call 0: Create Campaign Budget resource
            r0 = await client.post(
                f"{base}/campaignBudgets:mutate",
                json={"operations": [{"create": {
                    "name": f"Budget - {campaign_name}",
                    "amountMicros": str(max(budget_micros, 1_000_000)),
                    "deliveryMethod": "STANDARD",
                }}]},
                headers=headers,
            )
            r0.raise_for_status()
            budget_resource = r0.json()["results"][0]["resourceName"]

            # Call 1: Create Search Campaign
            r1 = await client.post(
                f"{base}/campaigns:mutate",
                json={"operations": [{"create": {
                    "name": campaign_name,
                    "status": "ENABLED",
                    "advertisingChannelType": "SEARCH",
                    "campaignBudget": budget_resource,
                    "manualCpc": {},
                    "networkSettings": {
                        "targetGoogleSearch": True,
                        "targetSearchNetwork": True,
                        "targetContentNetwork": False,
                    },
                }}]},
                headers=headers,
            )
            r1.raise_for_status()
            campaign_resource = r1.json()["results"][0]["resourceName"]
            campaign_id = campaign_resource.split("/")[-1]

            # Call 2: Create Ad Group
            r2 = await client.post(
                f"{base}/adGroups:mutate",
                json={"operations": [{"create": {
                    "campaign": campaign_resource,
                    "name": f"{campaign_name} - AdGroup",
                    "status": "ENABLED",
                    "type": "SEARCH_STANDARD",
                    "cpcBidMicros": "2000000",
                }}]},
                headers=headers,
            )
            r2.raise_for_status()
            ad_group_resource = r2.json()["results"][0]["resourceName"]

            # Call 3: Create Responsive Search Ad
            r3 = await client.post(
                f"{base}/adGroupAds:mutate",
                json={"operations": [{"create": {
                    "adGroup": ad_group_resource,
                    "status": "ENABLED",
                    "ad": {
                        "responsiveSearchAd": {
                            "headlines": [
                                {"text": headline1},
                                {"text": headline2},
                                {"text": headline3},
                            ],
                            "descriptions": [
                                {"text": desc1},
                                {"text": desc2},
                            ],
                        },
                        "finalUrls": [landing_url],
                    },
                }}]},
                headers=headers,
            )
            r3.raise_for_status()
            ad_resource = r3.json()["results"][0]["resourceName"]
            ad_id = ad_resource.split("/")[-1]

            logger.info("Google Ads campaign %s activated successfully", campaign_id)
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
