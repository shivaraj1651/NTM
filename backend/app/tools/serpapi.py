import httpx
import json
import logging
import os
from typing import Dict, List, Any

logger = logging.getLogger(__name__)
SERPAPI_API_KEY = os.getenv("SERPAPI_API_KEY")

def _extract_channels_from_result(result_text: str) -> List[str]:
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

def _extract_messaging_themes(snippets: List[str]) -> List[str]:
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
    geography: List[str],
    year: int = 2026
) -> Dict[str, Any]:
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
