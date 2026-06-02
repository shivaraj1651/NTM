import logging
import os
from typing import Any

import httpx

logger = logging.getLogger(__name__)
SERPAPI_API_KEY = os.getenv("SERPAPI_API_KEY") or os.getenv("SERPAPI_KEY")

_SERPAPI_BASE = "https://serpapi.com/search"


async def _serpapi_get(params: dict) -> dict:
    """Shared SerpAPI GET helper. Returns raw response dict or empty dict on error."""
    if not SERPAPI_API_KEY:
        logger.warning("SERPAPI_API_KEY not set — skipping search")
        return {}
    params["api_key"] = SERPAPI_API_KEY
    async with httpx.AsyncClient() as client:
        try:
            resp = await client.get(_SERPAPI_BASE, params=params, timeout=10.0)
            resp.raise_for_status()
            return resp.json()
        except httpx.HTTPError as exc:
            logger.warning("SerpAPI request failed: %s", exc)
            return {}


async def search_brand_info(brand_name: str) -> dict[str, Any]:
    """Search for company-specific taglines, products, and ad context.

    Returns a dict with:
      taglines      – list[str] candidate taglines/slogans found
      products      – list[str] product names / offerings
      logo_hint     – str  description of visual identity
      recent_campaigns – list[str] recent campaign themes
      raw_snippets  – list[str] first-page organic snippets for prompt enrichment
    """
    # Query 1: brand tagline / slogan
    slogan_data = await _serpapi_get({
        "q": f"{brand_name} tagline slogan official",
        "num": 5,
    })
    # Query 2: products and ads
    product_data = await _serpapi_get({
        "q": f"{brand_name} products advertising campaign",
        "num": 5,
    })

    def _snippets(data: dict) -> list[str]:
        return [r.get("snippet", "") for r in data.get("organic_results", []) if r.get("snippet")]

    slogan_snippets = _snippets(slogan_data)
    product_snippets = _snippets(product_data)
    all_snippets = slogan_snippets + product_snippets

    # Heuristic extraction of short slogan-like phrases (≤ 8 words, sentence-final)
    import re
    taglines: list[str] = []
    for snippet in slogan_snippets:
        matches = re.findall(r'"([^"]{5,60})"', snippet)
        taglines.extend(m for m in matches if len(m.split()) <= 10)
    taglines = list(dict.fromkeys(taglines))[:5]  # deduplicate, cap at 5

    # Product names: first-sentence nouns from product snippets (simple heuristic)
    products: list[str] = []
    for snippet in product_snippets[:3]:
        first_sent = snippet.split(".")[0]
        products.append(first_sent[:120])

    return {
        "taglines": taglines,
        "products": products[:5],
        "logo_hint": f"{brand_name} brand visual identity",
        "recent_campaigns": _extract_messaging_themes(all_snippets),
        "raw_snippets": all_snippets[:8],
    }

def _extract_channels_from_result(result_text: str) -> list[str]:
    """Parse text for advertising channels (google_ads, facebook, linkedin, tiktok, youtube)."""
    channels = []
    channel_patterns = {
        "google_ads": ["google ads", "search ads", "google adwords"],
        "facebook": ["facebook ads", "meta ads", "instagram ads"],
        "linkedin": ["linkedin ads", "linkedin campaign"],
        "tiktok": ["tiktok ads", "tiktok promotional"],
        "youtube": ["youtube ads", "youtube advertising"],
    }
    result_lower = result_text.lower()
    for channel, patterns in channel_patterns.items():
        if any(p in result_lower for p in patterns):
            channels.append(channel)
    return channels

def _extract_messaging_themes(snippets: list[str]) -> list[str]:
    """Extract messaging themes from snippets."""
    themes = []
    keywords = {
        "performance": ["performance", "fast", "speed", "efficiency"],
        "sustainability": ["sustainable", "eco-friendly", "green"],
        "innovation": ["innovation", "cutting-edge", "technology"],
        "lifestyle": ["lifestyle", "aspiration", "inspire"],
        "affordability": ["affordable", "budget", "savings"],
    }
    all_text = " ".join(snippets).lower()
    for theme, patterns in keywords.items():
        if any(p in all_text for p in patterns) and theme not in themes:
            themes.append(theme)
    return themes[:5]

async def search_competitor_ads(
    competitor_name: str,
    year: int = 2026
) -> dict[str, Any]:
    """Search SerpAPI for competitor ad campaigns."""
    if not SERPAPI_API_KEY:
        logger.error("SERPAPI_API_KEY not set")
        return {
            "channels_detected": [],
            "messaging_samples": [],
            "estimated_search_volume": 0,
            "num_results": 0,
            "error": "API key not configured"
        }

    query = f"{competitor_name} advertising campaign {year}"

    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(
                "https://serpapi.com/search",
                params={
                    "q": query,
                    "api_key": SERPAPI_API_KEY,
                    "num": 10,
                },
                timeout=10.0
            )
            response.raise_for_status()
        except httpx.HTTPError as e:
            logger.error(f"SerpAPI request failed: {e}")
            return {
                "channels_detected": [],
                "messaging_samples": [],
                "estimated_search_volume": 0,
                "num_results": 0,
                "error": str(e)
            }

    data = response.json()
    organic_results = data.get("organic_results", [])

    all_text = " ".join([r.get("snippet", "") for r in organic_results])
    channels = _extract_channels_from_result(all_text)
    snippets = [r.get("snippet", "") for r in organic_results]
    messaging = _extract_messaging_themes(snippets)

    return {
        "channels_detected": list(set(channels)),
        "messaging_samples": messaging,
        "estimated_search_volume": data.get("search_information", {}).get("total_results", 0),
        "num_results": len(organic_results),
        "raw_results": organic_results
    }
