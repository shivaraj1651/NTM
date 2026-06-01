import httpx
import logging
import os
from typing import Dict, Any, List, Optional
import re

from backend.app.external.stubs import stub_enabled, ads_test_mode

logger = logging.getLogger(__name__)

META_BASE = "https://graph.facebook.com/v21.0"


def _get_access_token() -> str:
    token = os.getenv("META_SYSTEM_USER_TOKEN", "")
    if not token:
        raise RuntimeError("META_SYSTEM_USER_TOKEN must be set")
    return token


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


async def create_campaign(
    ad_account_id: str,
    name: str,
    objective: str,
    budget: float,
    schedule: Dict[str, Any],
) -> str:
    """Create a Meta campaign. Returns campaign_id string.

    Args:
        ad_account_id: Ad account ID without 'act_' prefix (e.g. "123456789")
        name: Campaign name
        objective: e.g. "LINK_CLICKS", "REACH", "VIDEO_VIEWS", "BRAND_AWARENESS"
        budget: Daily budget in USD (converted to cents internally)
        schedule: Dict with "start_time" (unix timestamp). Optional "stop_time".

    Raises:
        RuntimeError: if META_SYSTEM_USER_TOKEN not set
        httpx.HTTPStatusError: on API 4xx/5xx
    """
    token = _get_access_token()
    # Map legacy objectives to v21.0 OUTCOME_* format
    _OBJ_MAP = {
        "LINK_CLICKS": "OUTCOME_TRAFFIC",
        "REACH": "OUTCOME_AWARENESS",
        "BRAND_AWARENESS": "OUTCOME_AWARENESS",
        "VIDEO_VIEWS": "OUTCOME_AWARENESS",
        "LEAD_GENERATION": "OUTCOME_LEADS",
        "CONVERSIONS": "OUTCOME_SALES",
        "APP_INSTALLS": "OUTCOME_APP_PROMOTION",
    }
    api_objective = _OBJ_MAP.get(objective.upper(), "OUTCOME_AWARENESS")
    # Ensure daily budget is at least $5 (500 cents); cost_estimated is total, divide by 30 for daily
    daily_cents = max(int((budget / 30) * 100), 500)
    payload: Dict[str, Any] = {
        "name": name,
        "objective": api_objective,
        "status": "ACTIVE",
        "daily_budget": str(daily_cents),
        "special_ad_categories": [],
        "access_token": token,
    }
    if schedule.get("start_time"):
        payload["start_time"] = schedule["start_time"]
    if schedule.get("stop_time"):
        payload["stop_time"] = schedule["stop_time"]

    async with httpx.AsyncClient(timeout=30.0) as client:
        r = await client.post(
            f"{META_BASE}/act_{ad_account_id}/campaigns",
            json=payload,
        )
        r.raise_for_status()
        return r.json()["id"]


async def create_ad_set(
    campaign_id: str,
    name: str,
    audience_spec: Dict[str, Any],
    placements: List[str],
    budget: float,
) -> str:
    """Create a Meta ad set under an existing campaign. Returns ad_set_id string.

    Args:
        campaign_id: Campaign ID returned by create_campaign
        name: Ad set name
        audience_spec: Dict with age_min, age_max, geo_locations, interests (all optional)
        placements: List of placement strings e.g. ["FACEBOOK_FEED", "INSTAGRAM_FEED"]
        budget: Daily budget in USD (converted to cents internally)

    Raises:
        RuntimeError: if META_SYSTEM_USER_TOKEN or META_AD_ACCOUNT_ID not set
        httpx.HTTPStatusError: on API 4xx/5xx
    """
    token = _get_access_token()
    account_id = os.getenv("META_AD_ACCOUNT_ID", "")
    if not account_id:
        raise RuntimeError("META_AD_ACCOUNT_ID must be set")

    targeting: Dict[str, Any] = {
        "age_min": audience_spec.get("age_min", 18),
        "age_max": audience_spec.get("age_max", 65),
        "geo_locations": audience_spec.get("geo_locations", {"countries": ["US"]}),
        "publisher_platforms": placements or ["facebook", "instagram"],
    }
    if audience_spec.get("interests"):
        targeting["interests"] = audience_spec["interests"]

    payload: Dict[str, Any] = {
        "name": name,
        "campaign_id": campaign_id,
        "status": "PAUSED",
        "daily_budget": str(int(budget * 100)),
        "billing_event": "IMPRESSIONS",
        "optimization_goal": "REACH",
        "targeting": targeting,
        "access_token": token,
    }

    async with httpx.AsyncClient(timeout=30.0) as client:
        r = await client.post(
            f"{META_BASE}/act_{account_id}/adsets",
            json=payload,
        )
        r.raise_for_status()
        return r.json()["id"]


async def create_ad(
    ad_set_id: str,
    creative_spec: Dict[str, Any],
    name: str,
) -> str:
    """Create a Meta ad under an existing ad set. Returns ad_id string.

    Args:
        ad_set_id: Ad set ID returned by create_ad_set
        creative_spec: Dict with image_hash, link, message, and optionally page_id
        name: Ad name

    Raises:
        RuntimeError: if META_SYSTEM_USER_TOKEN or META_AD_ACCOUNT_ID not set
        httpx.HTTPStatusError: on API 4xx/5xx
    """
    token = _get_access_token()
    account_id = os.getenv("META_AD_ACCOUNT_ID", "")
    if not account_id:
        raise RuntimeError("META_AD_ACCOUNT_ID must be set")
    page_id = creative_spec.get("page_id") or os.getenv("META_PAGE_ID", "")

    payload: Dict[str, Any] = {
        "name": name,
        "adset_id": ad_set_id,
        "status": "PAUSED",
        "creative": {
            "object_story_spec": {
                "page_id": page_id,
                "link_data": {
                    "image_hash": creative_spec.get("image_hash", ""),
                    "link": creative_spec.get("link", ""),
                    "message": creative_spec.get("message", ""),
                },
            }
        },
        "access_token": token,
    }

    async with httpx.AsyncClient(timeout=30.0) as client:
        r = await client.post(
            f"{META_BASE}/act_{account_id}/ads",
            json=payload,
        )
        r.raise_for_status()
        return r.json()["id"]


async def get_ad_insights(
    ad_id: str,
    date_range: Dict[str, str],
    metrics_list: List[str],
) -> Dict[str, Any]:
    """Fetch performance insights for a Meta ad.

    Args:
        ad_id: Ad ID returned by create_ad
        date_range: {"since": "YYYY-MM-DD", "until": "YYYY-MM-DD"}
        metrics_list: e.g. ["impressions", "clicks", "spend", "reach", "ctr"]

    Returns:
        {
            "ad_id": str,
            "date_range": {"since": ..., "until": ...},
            "metrics": {metric: value, ...},
            "raw": [...]
        }

    Raises:
        RuntimeError: if META_SYSTEM_USER_TOKEN not set
        httpx.HTTPStatusError: on API 4xx/5xx
    """
    token = _get_access_token()
    params = {
        "fields": ",".join(metrics_list),
        "time_range": f'{{"since":"{date_range.get("since")}","until":"{date_range.get("until")}"}}',
        "access_token": token,
    }

    async with httpx.AsyncClient(timeout=30.0) as client:
        r = await client.get(f"{META_BASE}/{ad_id}/insights", params=params)
        r.raise_for_status()
        data = r.json()

    rows = data.get("data", [])
    merged: Dict[str, Any] = {}
    for row in rows:
        merged.update(row)

    return {
        "ad_id": ad_id,
        "date_range": date_range,
        "metrics": {k: merged.get(k) for k in metrics_list},
        "raw": rows,
    }


async def pause_ad(ad_id: str) -> bool:
    """Pause a running Meta ad.

    Args:
        ad_id: Ad ID to pause

    Returns:
        True on success

    Raises:
        RuntimeError: if META_SYSTEM_USER_TOKEN not set
        httpx.HTTPStatusError: on API 4xx/5xx
    """
    token = _get_access_token()
    async with httpx.AsyncClient(timeout=30.0) as client:
        r = await client.post(
            f"{META_BASE}/{ad_id}",
            json={"status": "PAUSED", "access_token": token},
        )
        r.raise_for_status()
        return True


async def update_ad_budget(ad_set_id: str, daily_budget: float) -> bool:
    """Update the daily budget of an ad set.

    Args:
        ad_set_id: Ad set ID to update
        daily_budget: New daily budget in USD (converted to cents internally)

    Returns:
        True on success

    Raises:
        RuntimeError: if META_SYSTEM_USER_TOKEN not set
        httpx.HTTPStatusError: on API 4xx/5xx
    """
    token = _get_access_token()
    async with httpx.AsyncClient(timeout=30.0) as client:
        r = await client.post(
            f"{META_BASE}/{ad_set_id}",
            json={"daily_budget": str(int(daily_budget * 100)), "access_token": token},
        )
        r.raise_for_status()
        return True


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


async def activate_meta(
    activation: Dict[str, Any],
    platform_config: Dict[str, Any],
    creative_url: str,
    access_token: Optional[str] = None,
) -> Dict[str, Any]:
    """Activate a campaign on Meta (Facebook/Instagram).

    Orchestrates create_campaign → create_ad_set → create_ad.
    In NTM_ADS_TEST_MODE all objects are created PAUSED — safe for developer testing.

    Args:
        activation: Activation record with name, cost_estimated
        platform_config: Meta targeting + concept data: age_min, age_max,
            geo_locations, interests, tagline, master_message, page_id
        creative_url: URL used as ad link
        access_token: Ignored — token comes from META_SYSTEM_USER_TOKEN env var

    Returns:
        {campaign_id, ad_set_id, ad_id, status: "live"|"test_live"|"failed", error: str|None}
    """
    # NTM_STUB_EXTERNAL: fully fake — no real API calls
    if stub_enabled():
        logger.info("Meta Ads activate_meta stubbed (NTM_STUB_EXTERNAL)")
        return {
            "campaign_id": "stub-meta-campaign-001",
            "ad_set_id": "stub-meta-adset-001",
            "ad_id": "stub-meta-ad-001",
            "status": "live",
            "test_mode": False,
            "error": None,
        }

    test_mode = ads_test_mode()
    account_id = os.getenv("META_AD_ACCOUNT_ID", "")
    raw_name = activation.get("name", "Campaign")
    campaign_name = f"[TEST] {raw_name}" if test_mode else raw_name
    total_budget = float(activation.get("cost_estimated", 0))

    # Ad copy from concept
    tagline       = platform_config.get("tagline", "") or raw_name
    master_message = platform_config.get("master_message", "") or raw_name
    page_id       = platform_config.get("page_id", "") or os.getenv("META_PAGE_ID", "")

    # In test mode all objects PAUSED; in production campaign ACTIVE, adset/ad PAUSED
    # (adset/ad are always PAUSED in create_ad_set/create_ad — activation is manual)
    campaign_status_override = "PAUSED" if test_mode else "ACTIVE"

    logger.info(
        "Meta activation: test_mode=%s campaign=%r status=%s",
        test_mode, campaign_name, campaign_status_override,
    )

    try:
        if not account_id:
            raise RuntimeError("META_AD_ACCOUNT_ID must be set")
        if not page_id:
            raise RuntimeError("META_PAGE_ID must be set (or pass page_id in platform_config)")

        token = _get_access_token()

        # Map objective from mandate
        _OBJ_MAP = {
            "awareness": "OUTCOME_AWARENESS",
            "consideration": "OUTCOME_TRAFFIC",
            "conversion": "OUTCOME_SALES",
            "loyalty": "OUTCOME_ENGAGEMENT",
            "engagement": "OUTCOME_ENGAGEMENT",
        }
        mandate_objective = platform_config.get("objective", "awareness").lower()
        api_objective = _OBJ_MAP.get(mandate_objective, "OUTCOME_AWARENESS")

        daily_cents = max(int((total_budget / 30) * 100), 500)  # min $5/day
        payload: Dict[str, Any] = {
            "name": campaign_name,
            "objective": api_objective,
            "status": campaign_status_override,
            "daily_budget": str(daily_cents),
            "special_ad_categories": [],
            "access_token": token,
        }

        async with httpx.AsyncClient(timeout=30.0) as client:
            r = await client.post(
                f"{META_BASE}/act_{account_id}/campaigns",
                json=payload,
            )
            r.raise_for_status()
            campaign_id = r.json()["id"]

        # Audience spec from platform_config
        audience_spec = {
            "age_min": platform_config.get("age_min", 18),
            "age_max": platform_config.get("age_max", 65),
            "geo_locations": platform_config.get("geo_locations", {"countries": ["US"]}),
            "interests": platform_config.get("interests", []),
        }
        ad_set_id = await create_ad_set(
            campaign_id=campaign_id,
            name=f"{campaign_name} - AdSet",
            audience_spec=audience_spec,
            placements=["facebook", "instagram"],
            budget=max(total_budget / 30, 5.0),  # daily rate
        )

        ad_id = await create_ad(
            ad_set_id=ad_set_id,
            creative_spec={
                "link": creative_url or "https://example.com",
                "message": master_message,
                "page_id": page_id,
            },
            name=f"{campaign_name} - Ad",
        )

        result_status = "test_live" if test_mode else "live"
        logger.info(
            "Meta campaign %s created status=%s test_mode=%s",
            campaign_id, result_status, test_mode,
        )
        return {
            "campaign_id": campaign_id,
            "ad_set_id": ad_set_id,
            "ad_id": ad_id,
            "status": result_status,
            "test_mode": test_mode,
            "error": None,
        }

    except Exception as e:
        logger.error("Meta activation failed: %s: %s", type(e).__name__, str(e))
        return {
            "campaign_id": None,
            "ad_set_id": None,
            "ad_id": None,
            "status": "failed",
            "test_mode": test_mode,
            "error": str(e),
        }
