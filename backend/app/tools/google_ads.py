import logging
import os
from typing import Dict, Any, Optional

import httpx

from backend.app.external.stubs import stub_enabled, ads_test_mode

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

    test_mode = ads_test_mode()
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

        # Build campaign name — prefix [TEST] in test mode so it's visible in console
        raw_name = activation.get("name", "Campaign")
        campaign_name = f"[TEST] {raw_name}" if test_mode else raw_name

        budget_micros = int(activation.get("cost_estimated", 0) * 1_000_000)
        landing_url = creative_url if creative_url.startswith("http") else "https://example.com"

        # Use concept data from platform_config for ad copy — more relevant than generic text
        tagline        = (platform_config.get("tagline", "") or "")[:30]
        master_message = (platform_config.get("master_message", "") or "")[:30]
        description    = (platform_config.get("description", "") or activation.get("message", ""))[:90]
        concept_name   = (platform_config.get("concept_name", "") or raw_name)[:30]

        headline1 = tagline or concept_name or campaign_name[:30]
        headline2 = master_message or (raw_name + " Campaign")[:30]
        headline3 = "Learn More Today"
        desc1 = description or "Discover our latest campaign and special offers."
        desc2 = f"Contact us for more about {raw_name}."[:90]

        # PAUSED in test mode — safe, no real spend; ENABLED in production
        campaign_status  = "PAUSED" if test_mode else "ENABLED"
        adgroup_status   = "PAUSED" if test_mode else "ENABLED"
        ad_status        = "PAUSED" if test_mode else "ENABLED"

        logger.info(
            "Google Ads activation: test_mode=%s campaign=%r status=%s",
            test_mode, campaign_name, campaign_status,
        )

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
                    "status": campaign_status,
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
                    "status": adgroup_status,
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
                    "status": ad_status,
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

            result_status = "test_live" if test_mode else "live"
            logger.info(
                "Google Ads campaign %s created status=%s test_mode=%s",
                campaign_id, result_status, test_mode,
            )
            return {
                "campaign_id": campaign_id,
                "ad_id": ad_id,
                "status": result_status,
                "test_mode": test_mode,
                "error": None,
            }

    except Exception as e:
        logger.error("Google Ads activation failed: %s: %s", type(e).__name__, str(e))
        return {
            "campaign_id": None,
            "ad_id": None,
            "status": "failed",
            "test_mode": test_mode,
            "error": str(e),
        }
