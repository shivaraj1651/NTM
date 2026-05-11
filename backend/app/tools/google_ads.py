import logging
from typing import Dict, Any, Optional
import httpx

logger = logging.getLogger(__name__)

GOOGLE_ADS_API_ENDPOINT = "https://googleads.googleapis.com/v17/customers/{customer_id}/campaigns"


async def activate_google(
    activation: Dict[str, Any],
    platform_config: Dict[str, Any],
    creative_url: str,
    customer_id: Optional[str] = None
) -> Dict[str, Any]:
    """
    Activate a campaign on Google Ads.

    Args:
        activation: Activation record with budget and targeting
        platform_config: Google Ads-specific targeting from PlatformConfigTemplate
        creative_url: URL to creative asset
        customer_id: Google Ads customer ID

    Returns:
        Dict with:
        - campaign_id: Google campaign ID or None
        - ad_id: Google ad ID or None
        - status: 'live' or 'failed'
        - error: Error message or None
    """
    if not customer_id:
        customer_id = "1234567890"  # Placeholder

    try:
        # Build campaign payload with budget and targeting
        payload = {
            "campaign": {
                "name": activation.get("name", "Campaign"),
                "status": "ENABLED",
                "budget_allocation_strategy": "OPTIMIZE_FOR_REACH",
                "bidding_strategy": {
                    "type_": "MAXIMIZE_CONVERSIONS",
                    "maximize_conversions": {
                        "target_cpa_micros": int(activation.get("cost_estimated", 0) * 1_000_000)
                    }
                }
            },
            "targeting": {
                "age_range": platform_config.get("age_range"),
                "interests": platform_config.get("interests", []),
                "geographic": platform_config.get("geographic")
            },
            "creatives": [
                {
                    "url": creative_url,
                    "type": "VIDEO"
                }
            ]
        }

        async with httpx.AsyncClient(timeout=30.0) as client:
            # Create campaign
            response = await client.post(
                f"{GOOGLE_ADS_API_ENDPOINT}",
                json=payload,
                headers={
                    "Authorization": f"Bearer <token>",
                    "Content-Type": "application/json"
                }
            )
            response.raise_for_status()

            data = response.json()
            campaign_id = data.get("id")

            # Create ad under campaign
            ad_payload = {"creative_url": creative_url}
            ad_response = await client.post(
                f"{GOOGLE_ADS_API_ENDPOINT}/{campaign_id}/ads",
                json=ad_payload,
                headers={"Authorization": f"Bearer <token>"}
            )
            ad_response.raise_for_status()
            ad_data = ad_response.json()
            ad_id = ad_data.get("id")

            logger.info(f"Google Ads campaign {campaign_id} activated successfully")

            return {
                "campaign_id": campaign_id,
                "ad_id": ad_id,
                "status": "live",
                "error": None
            }

    except Exception as e:
        logger.error(f"Google Ads activation failed: {e}")
        return {
            "campaign_id": None,
            "ad_id": None,
            "status": "failed",
            "error": str(e)
        }
