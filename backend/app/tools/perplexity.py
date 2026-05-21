"""Perplexity AI tool — real-time web research for Competitive Intelligence Agent."""

import logging
import os
from typing import Optional

logger = logging.getLogger(__name__)

_PERPLEXITY_API_KEY = os.getenv("PERPLEXITY_API_KEY")
_PERPLEXITY_AVAILABLE = bool(_PERPLEXITY_API_KEY)
_PERPLEXITY_URL = "https://api.perplexity.ai/chat/completions"
_DEFAULT_MODEL = "llama-3.1-sonar-large-128k-online"


class PerplexityTool:
    """Wraps Perplexity API for online search-grounded research queries."""

    async def search(self, query: str, model: Optional[str] = None) -> str:
        if not _PERPLEXITY_AVAILABLE:
            logger.warning("Perplexity not configured — mock result for: %.80s", query)
            return f"[Mock Perplexity result for: {query}]"

        import httpx

        headers = {
            "Authorization": f"Bearer {_PERPLEXITY_API_KEY}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": model or _DEFAULT_MODEL,
            "messages": [
                {
                    "role": "system",
                    "content": (
                        "You are a senior marketing research analyst. Provide factual, "
                        "concise, and well-structured competitive intelligence. "
                        "Focus on verifiable recent data."
                    ),
                },
                {"role": "user", "content": query},
            ],
            "max_tokens": 1024,
            "temperature": 0.2,
        }
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(_PERPLEXITY_URL, json=payload, headers=headers)
            resp.raise_for_status()
            data = resp.json()
            return data["choices"][0]["message"]["content"]

    async def research_competitor(self, competitor_name: str, vertical: str, geography: str = "India") -> str:
        query = (
            f"Provide a competitive intelligence report on {competitor_name} in the "
            f"{vertical} industry in {geography}. Include: (1) recent marketing campaigns "
            f"in the last 12 months, (2) advertising channels used (digital, print, OOH, TV, radio), "
            f"(3) target audience and key messaging, (4) estimated ad spend, "
            f"(5) key differentiators and USPs, (6) brand sentiment. Be specific and factual."
        )
        return await self.search(query)

    async def find_competitors(self, brand_name: str, vertical: str, geography: str = "India") -> str:
        query = (
            f"List the top 8 competitors of {brand_name} in the {vertical} sector in {geography}. "
            f"For each competitor, provide: company name, market position, primary advertising channels, "
            f"and key differentiator vs {brand_name}."
        )
        return await self.search(query)

    async def find_whitespace(self, vertical: str, competitors: list[str], geography: str = "India") -> str:
        comp_list = ", ".join(competitors[:8])
        query = (
            f"In the {vertical} industry in {geography}, identify marketing channel whitespace "
            f"and messaging gaps not currently exploited by these competitors: {comp_list}. "
            f"Which audience segments, geographies, or media channels are underserved?"
        )
        return await self.search(query)
