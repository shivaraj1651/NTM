import httpx
import logging
from typing import Dict, Any, List, Optional
import re

logger = logging.getLogger(__name__)


def _parse_spend_range(spend_str: str) -> Optional[float]:
    """
    Parse spend range string and convert to monthly estimate.
    Example: "1,000 - 2,000" -> 1500 * 4 = 6000 (monthly)
    """
    if not spend_str or not isinstance(spend_str, str):
        return None

    try:
        # Remove common currency symbols and whitespace
        cleaned = spend_str.replace("$", "").replace("USD", "").replace(",", "").strip()

        # Try to extract range (e.g., "1000 - 2000")
        match = re.search(r"([\d.]+)\s*-\s*([\d.]+)", cleaned)
        if match:
            low = float(match.group(1))
            high = float(match.group(2))
            weekly_avg = (low + high) / 2
            monthly_estimate = weekly_avg * 4
            return round(monthly_estimate, 2)

        # Try single number
        match = re.search(r"([\d.]+)", cleaned)
        if match:
            weekly_value = float(match.group(1))
            monthly_estimate = weekly_value * 4
            return round(monthly_estimate, 2)
    except (ValueError, AttributeError):
        pass

    return None


def _extract_placements(ad_data: Dict[str, Any]) -> List[str]:
    """Extract ad placements from Meta Ad Library response."""
    placements = []

    # Check various possible fields for placement info
    if isinstance(ad_data, dict):
        # Direct placement field
        if "platform_and_placement" in ad_data:
            placement = ad_data["platform_and_placement"]
            if isinstance(placement, str) and placement.lower() not in ["unknown", "none"]:
                placements.append(placement.lower())

        # Fallback to common Meta placements if any spend detected
        if ad_data.get("estimated_monthly_spend") or ad_data.get("spend"):
            default_placements = ["feed", "stories", "reels"]
            placements.extend([p for p in default_placements if p not in placements])

    return list(set(placements)) if placements else ["feed", "stories"]


def _extract_primary_audiences(ad_data: Dict[str, Any]) -> List[str]:
    """Extract primary audience demographics from ad data."""
    audiences = []

    # Check for age targeting
    if "age_range" in ad_data:
        age_range = ad_data["age_range"]
        if isinstance(age_range, str):
            audiences.append(age_range)

    # Check for demographic info
    if "demographic_info" in ad_data:
        demo = ad_data["demographic_info"]
        if isinstance(demo, dict):
            if demo.get("age"):
                audiences.append(str(demo["age"]))
            if demo.get("gender"):
                audiences.append(demo["gender"])

    # Default age brackets if none found
    if not audiences:
        audiences = ["18-24", "25-34", "35-44", "45-54", "55+"]

    return audiences[:5]  # Return top 5


async def lookup_meta_ads(
    advertiser_name: str,
    date_range_days: int = 90
) -> Dict[str, Any]:
    """
    Query Meta Ad Library for competitor ads.

    Args:
        advertiser_name: Name of the advertiser/company to search
        date_range_days: How many days back to search (default 90)

    Returns:
        Dict with:
        - ads_found: Count of ads
        - placements: List of ad placements (feed, stories, reels, etc.)
        - estimated_monthly_spend: Monthly spend estimate or None
        - impressions_estimate: Monthly impressions estimate or None
        - primary_audiences: List of top 5 audience demographics
        - error: Error message or None
    """

    # Meta Ad Library endpoint (public, no auth required)
    endpoint = "https://graph.facebook.com/v21.0/ads_archive"

    params = {
        "search_terms": advertiser_name,
        "ad_type": "all",  # Get all ad types
        "fields": "ad_snapshot_url,ad_creation_time,ad_delivery_start_time,ad_delivery_stop_time,funding_entity,ad_creative_bodies,ad_creative_link_captions,ad_creative_link_descriptions,ad_creative_link_titles,ad_creative_link_urls,currency,spend,impression_range,platform_and_placement,demographic_distribution,estimated_monthly_spend",
        "limit": 100,
    }

    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(
                endpoint,
                params=params,
                timeout=10.0
            )
            response.raise_for_status()
        except httpx.HTTPError as e:
            logger.error(f"Meta Ad Library API request failed for '{advertiser_name}': {e}")
            return {
                "ads_found": 0,
                "placements": [],
                "estimated_monthly_spend": None,
                "impressions_estimate": None,
                "primary_audiences": [],
                "error": f"API request failed: {str(e)}"
            }
        except Exception as e:
            logger.error(f"Unexpected error querying Meta Ad Library: {e}")
            return {
                "ads_found": 0,
                "placements": [],
                "estimated_monthly_spend": None,
                "impressions_estimate": None,
                "primary_audiences": [],
                "error": f"Unexpected error: {str(e)}"
            }

    try:
        data = response.json()
        ads = data.get("data", [])

        if not ads:
            logger.info(f"No ads found for '{advertiser_name}'")
            return {
                "ads_found": 0,
                "placements": [],
                "estimated_monthly_spend": None,
                "impressions_estimate": None,
                "primary_audiences": [],
                "error": None
            }

        # Aggregate data across all ads
        all_placements = set()
        all_audiences = set()
        total_monthly_spend = 0.0
        total_impressions = 0
        spend_count = 0
        impressions_count = 0

        for ad in ads:
            # Placements
            placements = _extract_placements(ad)
            all_placements.update(placements)

            # Audiences
            audiences = _extract_primary_audiences(ad)
            all_audiences.update(audiences)

            # Spend processing
            spend_str = ad.get("spend") or ad.get("estimated_monthly_spend")
            if spend_str:
                parsed_spend = _parse_spend_range(str(spend_str))
                if parsed_spend:
                    total_monthly_spend += parsed_spend
                    spend_count += 1

            # Impressions processing
            impression_range = ad.get("impression_range")
            if impression_range and isinstance(impression_range, dict):
                min_imp = impression_range.get("lower_bound", 0)
                max_imp = impression_range.get("upper_bound", 0)
                if min_imp and max_imp:
                    avg_imp = (min_imp + max_imp) / 2
                    total_impressions += avg_imp
                    impressions_count += 1

        # Calculate averages
        estimated_spend = (total_monthly_spend / spend_count) if spend_count > 0 else None
        estimated_impressions = int(total_impressions / impressions_count) if impressions_count > 0 else None

        # Convert weekly to monthly if needed
        if estimated_spend:
            estimated_spend = round(estimated_spend * 4, 2)
        if estimated_impressions:
            estimated_impressions = int(estimated_impressions * 4)

        result = {
            "ads_found": len(ads),
            "placements": sorted(list(all_placements)) or ["feed", "stories"],
            "estimated_monthly_spend": estimated_spend,
            "impressions_estimate": estimated_impressions,
            "primary_audiences": sorted(list(all_audiences))[:5] or ["18-24", "25-34", "35-44"],
            "error": None
        }

        logger.info(f"Retrieved {len(ads)} ads for '{advertiser_name}'")
        return result

    except ValueError as e:
        logger.error(f"Failed to parse Meta Ad Library response: {e}")
        return {
            "ads_found": 0,
            "placements": [],
            "estimated_monthly_spend": None,
            "impressions_estimate": None,
            "primary_audiences": [],
            "error": f"Response parsing failed: {str(e)}"
        }
