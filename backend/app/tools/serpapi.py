"""
SerpAPI Tool for competitor ad search (AGT-02).

Searches for competitor advertising campaigns using SerpAPI and extracts
channel detection, messaging themes, and estimated search volume.
"""

import httpx
import json
import logging
import os
from typing import Dict, List, Any

logger = logging.getLogger(__name__)


async def search_competitor_ads(
    competitor_name: str,
    geography: List[str],
    year: int = 2026
) -> Dict[str, Any]:
    """
    Search for competitor advertising campaigns using SerpAPI.

    Calls SerpAPI with query "{competitor_name} advertising campaign {year}",
    extracts channels, messaging themes, and search volume metrics.

    Args:
        competitor_name: Name of competitor company
        geography: List of geographic regions to search (e.g., ["US", "UK"])
        year: Campaign year to search for (default 2026)

    Returns:
        Dict with keys:
        - channels_detected: List[str] of detected ad channels
        - messaging_samples: List[str] of extracted messaging themes (max 5)
        - estimated_search_volume: int or None
        - num_results: int count of results returned
        - raw_results: List of full SerpAPI organic results
        - error: str (if error occurred)
    """
    api_key = os.getenv("SERPAPI_API_KEY")
    if not api_key:
        logger.error("SERPAPI_API_KEY environment variable not set")
        return {
            "error": "SERPAPI_API_KEY environment variable not set",
            "channels_detected": [],
            "messaging_samples": [],
            "estimated_search_volume": None,
            "num_results": 0,
            "raw_results": []
        }

    # Build search query
    query = f"{competitor_name} advertising campaign {year}"
    geo_str = ", ".join(geography) if geography else "global"

    logger.debug(f"Searching SerpAPI for: {query} in {geo_str}")

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(
                "https://serpapi.com/search",
                params={
                    "q": query,
                    "api_key": api_key,
                    "engine": "google",
                    "num": 20
                }
            )
            response.raise_for_status()

        data = response.json()
        logger.debug(f"SerpAPI response received: {len(data.get('organic_results', []))} results")

        # Extract organic results
        organic_results = data.get("organic_results", [])
        num_results = len(organic_results)

        # Extract snippets for messaging analysis
        snippets = [
            result.get("snippet", "")
            for result in organic_results
            if result.get("snippet")
        ]

        # Extract messaging themes
        messaging_samples = _extract_messaging_themes(snippets)

        # Extract channels from all results
        all_text = " ".join(snippets)
        channels_detected = _extract_channels_from_result(all_text)

        # Get search volume if available in SerpAPI response
        estimated_search_volume = None
        if "search_information" in data:
            search_info = data["search_information"]
            if "total_results" in search_info:
                try:
                    estimated_search_volume = int(search_info["total_results"])
                except (ValueError, TypeError):
                    logger.warning("Could not parse search volume from SerpAPI")

        result = {
            "channels_detected": list(set(channels_detected)),  # Remove duplicates
            "messaging_samples": messaging_samples,
            "estimated_search_volume": estimated_search_volume,
            "num_results": num_results,
            "raw_results": organic_results
        }

        logger.info(
            f"Search complete for {competitor_name}: "
            f"{num_results} results, {len(result['channels_detected'])} channels, "
            f"{len(messaging_samples)} messaging themes"
        )

        return result

    except httpx.TimeoutException:
        logger.error(f"SerpAPI request timeout for {competitor_name}")
        return {
            "error": "SerpAPI request timeout",
            "channels_detected": [],
            "messaging_samples": [],
            "estimated_search_volume": None,
            "num_results": 0,
            "raw_results": []
        }

    except httpx.HTTPStatusError as e:
        logger.error(f"SerpAPI HTTP error {e.response.status_code}: {e.response.text}")
        return {
            "error": f"SerpAPI HTTP {e.response.status_code}",
            "channels_detected": [],
            "messaging_samples": [],
            "estimated_search_volume": None,
            "num_results": 0,
            "raw_results": []
        }

    except httpx.RequestError as e:
        logger.error(f"SerpAPI request error: {str(e)}")
        return {
            "error": f"SerpAPI request failed: {str(e)}",
            "channels_detected": [],
            "messaging_samples": [],
            "estimated_search_volume": None,
            "num_results": 0,
            "raw_results": []
        }

    except json.JSONDecodeError:
        logger.error("Failed to parse SerpAPI JSON response")
        return {
            "error": "Failed to parse SerpAPI response",
            "channels_detected": [],
            "messaging_samples": [],
            "estimated_search_volume": None,
            "num_results": 0,
            "raw_results": []
        }

    except Exception as e:
        logger.error(f"Unexpected error in search_competitor_ads: {str(e)}")
        return {
            "error": f"Unexpected error: {str(e)}",
            "channels_detected": [],
            "messaging_samples": [],
            "estimated_search_volume": None,
            "num_results": 0,
            "raw_results": []
        }


def _extract_channels_from_result(result_text: str) -> List[str]:
    """
    Extract advertising channels mentioned in result text.

    Detects common ad platform mentions:
    - google_ads (Google Ads, Google Search)
    - facebook (Facebook, Instagram)
    - linkedin (LinkedIn)
    - tiktok (TikTok)
    - youtube (YouTube)

    Args:
        result_text: Combined text from search results

    Returns:
        List of detected channels (may contain duplicates)
    """
    channels = []
    text_lower = result_text.lower()

    # Google Ads patterns
    if any(p in text_lower for p in ["google ads", "google search ads", "google advertising", "adwords"]):
        channels.append("google_ads")

    # Facebook/Instagram patterns
    if any(p in text_lower for p in ["facebook ads", "instagram ads", "meta ads", "facebook advertising"]):
        channels.append("facebook")

    # LinkedIn patterns
    if any(p in text_lower for p in ["linkedin ads", "linkedin advertising", "linkedin sponsored"]):
        channels.append("linkedin")

    # TikTok patterns
    if any(p in text_lower for p in ["tiktok ads", "tiktok advertising", "bytedance"]):
        channels.append("tiktok")

    # YouTube patterns
    if any(p in text_lower for p in ["youtube ads", "youtube advertising", "youtube video"]):
        channels.append("youtube")

    return channels


def _extract_messaging_themes(snippets: List[str]) -> List[str]:
    """
    Extract messaging themes from search result snippets.

    Identifies common advertising themes:
    - performance (speed, efficiency, productivity)
    - sustainability (eco, green, environmental)
    - innovation (new, advanced, cutting-edge)
    - lifestyle (experience, lifestyle, premium)
    - affordability (price, cost, value, budget)

    Args:
        snippets: List of search result snippet texts

    Returns:
        List of detected themes (max 5, no duplicates)
    """
    combined_text = " ".join(snippets).lower()
    themes = []

    theme_keywords = {
        "performance": ["speed", "efficiency", "productivity", "fast", "quick", "optimize", "perform", "faster"],
        "sustainability": ["eco", "green", "environmental", "sustainable", "carbon", "renewable", "climate"],
        "innovation": ["new", "advanced", "cutting-edge", "innovation", "innovative", "revolutionary", "next-gen"],
        "lifestyle": ["experience", "lifestyle", "premium", "luxury", "elegant", "style", "living"],
        "affordability": ["price", "cost", "value", "budget", "cheap", "affordable", "savings", "discount"]
    }

    for theme, keywords in theme_keywords.items():
        if any(keyword in combined_text for keyword in keywords):
            themes.append(theme)

    # Return max 5 themes
    return themes[:5]
