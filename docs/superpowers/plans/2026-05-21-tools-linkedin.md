# Tools LinkedIn Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Harden `linkedin_ads.py` with env-var token auth and a 3-call LinkedIn Marketing API flow (campaign group → campaign → creative), and add 6 tests.

**Architecture:** `_get_access_token()` helper reads `LINKEDIN_ACCESS_TOKEN` from env (or accepts explicit arg for backward compat). `activate_linkedin()` becomes a 3-call flow using LinkedIn's native object hierarchy at the `/rest` base URL. Tests follow TDD: write failing tests first, then rewrite implementation to pass them.

**Tech Stack:** Python 3.12, httpx, pytest, unittest.mock

---

## File Map

| File | Action | Responsibility |
|------|--------|---------------|
| `backend/app/tools/linkedin_ads.py` | Rewrite | Token helper + 3-call activate flow |
| `backend/app/tools/tests/test_linkedin_ads.py` | Create | 6 tests — TDD red then green |

---

## Task 1: Write test_linkedin_ads.py (TDD red phase)

Write all 6 tests expecting the new `_get_access_token` helper and 3-call flow. Run first — they must fail because the current implementation has neither.

**Files:**
- Create: `backend/app/tools/tests/test_linkedin_ads.py`

- [ ] **Step 1: Create test_linkedin_ads.py**

```python
import os
import pytest
from uuid import uuid4
from unittest.mock import patch, AsyncMock

from backend.app.tools.linkedin_ads import activate_linkedin


def _group_response():
    m = AsyncMock()
    m.json = lambda: {"id": 111}
    m.raise_for_status = lambda: None
    return m


def _campaign_response():
    m = AsyncMock()
    m.json = lambda: {"id": 222}
    m.raise_for_status = lambda: None
    return m


def _creative_response():
    m = AsyncMock()
    m.json = lambda: {"id": 333}
    m.raise_for_status = lambda: None
    return m


@pytest.mark.asyncio
async def test_activate_linkedin_success():
    activation = {
        "id": str(uuid4()),
        "name": "Test Campaign",
        "cost_estimated": 3000.0,
    }
    platform_config = {
        "seniority": ["SENIOR"],
        "job_title": ["Software Engineer"],
        "industries": ["Technology"],
        "locations": ["US"],
    }
    creative_url = "https://example.com/creative.mp4"

    with patch("backend.app.tools.linkedin_ads._get_access_token", return_value="test-tok"), \
         patch.dict(os.environ, {"LINKEDIN_ACCOUNT_ID": "999"}), \
         patch("backend.app.tools.linkedin_ads.httpx.AsyncClient") as mock_cls:

        mock_client = AsyncMock()
        mock_client.post = AsyncMock(side_effect=[
            _group_response(), _campaign_response(), _creative_response()
        ])
        mock_cls.return_value.__aenter__.return_value = mock_client

        result = await activate_linkedin(
            activation=activation,
            platform_config=platform_config,
            creative_url=creative_url,
        )

    assert result["campaign_id"] == "222"
    assert result["ad_id"] == "333"
    assert result["status"] == "live"
    assert result["error"] is None


@pytest.mark.asyncio
async def test_activate_linkedin_api_failure():
    activation = {"id": str(uuid4()), "name": "Test"}

    with patch("backend.app.tools.linkedin_ads._get_access_token", return_value="test-tok"), \
         patch.dict(os.environ, {"LINKEDIN_ACCOUNT_ID": "999"}), \
         patch("backend.app.tools.linkedin_ads.httpx.AsyncClient") as mock_cls:

        mock_client = AsyncMock()
        mock_client.post.side_effect = Exception("API Error")
        mock_cls.return_value.__aenter__.return_value = mock_client

        result = await activate_linkedin(
            activation=activation, platform_config={}, creative_url="https://example.com/c.mp4"
        )

    assert result["status"] == "failed"
    assert result["campaign_id"] is None
    assert result["ad_id"] is None
    assert "API Error" in result["error"]


@pytest.mark.asyncio
async def test_activate_linkedin_returns_required_fields():
    activation = {"id": str(uuid4()), "name": "Test"}

    with patch("backend.app.tools.linkedin_ads._get_access_token", return_value="test-tok"), \
         patch.dict(os.environ, {"LINKEDIN_ACCOUNT_ID": "999"}), \
         patch("backend.app.tools.linkedin_ads.httpx.AsyncClient") as mock_cls:

        mock_client = AsyncMock()
        mock_client.post = AsyncMock(side_effect=[
            _group_response(), _campaign_response(), _creative_response()
        ])
        mock_cls.return_value.__aenter__.return_value = mock_client

        result = await activate_linkedin(
            activation=activation, platform_config={}, creative_url="https://example.com/c.mp4"
        )

    for field in ("campaign_id", "ad_id", "status", "error"):
        assert field in result


@pytest.mark.asyncio
async def test_activate_linkedin_missing_token_returns_failed():
    activation = {"id": str(uuid4()), "name": "Test"}

    with patch("backend.app.tools.linkedin_ads._get_access_token",
               side_effect=RuntimeError("LINKEDIN_ACCESS_TOKEN must be set or access_token must be provided")):

        result = await activate_linkedin(
            activation=activation, platform_config={}, creative_url="https://example.com/c.mp4"
        )

    assert result["status"] == "failed"
    assert result["campaign_id"] is None
    assert result["ad_id"] is None
    assert result["error"] is not None


@pytest.mark.asyncio
async def test_activate_linkedin_sends_auth_header():
    activation = {"id": str(uuid4()), "name": "Test Campaign", "cost_estimated": 1000.0}

    with patch("backend.app.tools.linkedin_ads._get_access_token", return_value="my-token"), \
         patch.dict(os.environ, {"LINKEDIN_ACCOUNT_ID": "999"}), \
         patch("backend.app.tools.linkedin_ads.httpx.AsyncClient") as mock_cls:

        mock_client = AsyncMock()
        mock_client.post = AsyncMock(side_effect=[
            _group_response(), _campaign_response(), _creative_response()
        ])
        mock_cls.return_value.__aenter__.return_value = mock_client

        await activate_linkedin(
            activation=activation, platform_config={}, creative_url="https://example.com/c.mp4"
        )

        assert mock_client.post.call_count == 3
        for call in mock_client.post.call_args_list:
            assert call[1]["headers"]["Authorization"] == "Bearer my-token"


@pytest.mark.asyncio
async def test_activate_linkedin_token_param_overrides_env():
    activation = {"id": str(uuid4()), "name": "Test"}

    with patch.dict(os.environ, {"LINKEDIN_ACCESS_TOKEN": "env-token", "LINKEDIN_ACCOUNT_ID": "999"}), \
         patch("backend.app.tools.linkedin_ads.httpx.AsyncClient") as mock_cls:

        mock_client = AsyncMock()
        mock_client.post = AsyncMock(side_effect=[
            _group_response(), _campaign_response(), _creative_response()
        ])
        mock_cls.return_value.__aenter__.return_value = mock_client

        await activate_linkedin(
            activation=activation,
            platform_config={},
            creative_url="https://example.com/c.mp4",
            access_token="explicit-token",
        )

        first_kwargs = mock_client.post.call_args_list[0][1]
        assert first_kwargs["headers"]["Authorization"] == "Bearer explicit-token"
```

- [ ] **Step 2: Run tests — expect failure (red phase)**

```
cd D:\staging\ntm
python -m pytest backend/app/tools/tests/test_linkedin_ads.py -v
```

Expected: tests that patch `_get_access_token` fail with `AttributeError: <module> does not have attribute '_get_access_token'`. That's correct — implementation not yet updated.

- [ ] **Step 3: Commit the test file**

```
git add backend/app/tools/tests/test_linkedin_ads.py
git commit -m "test: add test_linkedin_ads.py — 6 tests for 3-call flow (red phase)"
```

---

## Task 2: Rewrite linkedin_ads.py (green phase)

Replace the entire file. The new implementation adds `_get_access_token()` and restructures `activate_linkedin()` to use LinkedIn's `/rest` API with 3 calls.

**Files:**
- Modify: `backend/app/tools/linkedin_ads.py`

- [ ] **Step 4: Rewrite linkedin_ads.py**

```python
"""LinkedIn Ads activation tool for B2B campaign deployment."""

import logging
import os
from typing import Dict, Any, Optional

import httpx

logger = logging.getLogger(__name__)

_LINKEDIN_BASE = "https://api.linkedin.com/rest"


def _get_access_token(token: Optional[str] = None) -> str:
    t = token or os.getenv("LINKEDIN_ACCESS_TOKEN", "")
    if not t:
        raise RuntimeError(
            "LINKEDIN_ACCESS_TOKEN must be set or access_token must be provided"
        )
    return t


async def activate_linkedin(
    activation: Dict[str, Any],
    platform_config: Dict[str, Any],
    creative_url: str,
    access_token: Optional[str] = None,
) -> Dict[str, Any]:
    account_id = os.getenv("LINKEDIN_ACCOUNT_ID", "")

    try:
        token = _get_access_token(access_token)
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
            "LinkedIn-Version": "202401",
            "X-Restli-Protocol-Version": "2.0.0",
        }
        campaign_name = activation.get("name", "Campaign")

        async with httpx.AsyncClient(timeout=30.0) as client:
            # Call 1: Create Campaign Group
            r1 = await client.post(
                f"{_LINKEDIN_BASE}/adCampaignGroups",
                json={
                    "name": f"{campaign_name} - Group",
                    "status": "ACTIVE",
                    "account": f"urn:li:sponsoredAccount:{account_id}",
                },
                headers=headers,
            )
            r1.raise_for_status()
            campaign_group_id = r1.json()["id"]

            # Call 2: Create Campaign with B2B targeting from platform_config
            r2 = await client.post(
                f"{_LINKEDIN_BASE}/adCampaigns",
                json={
                    "name": campaign_name,
                    "status": "ACTIVE",
                    "type": "SPONSORED_UPDATE",
                    "campaignGroup": f"urn:li:adCampaignGroup:{campaign_group_id}",
                    "costType": "CPM",
                    "dailyBudget": {
                        "amount": str(activation.get("cost_estimated", 0)),
                        "currencyCode": "USD",
                    },
                    "targetingCriteria": {
                        "include": {
                            "and": [
                                {"seniorities": platform_config.get("seniority", [])},
                                {"jobFunctions": platform_config.get("job_title", [])},
                                {"industries": platform_config.get("industries", [])},
                                {"locations": platform_config.get("locations", ["US"])},
                            ]
                        }
                    },
                },
                headers=headers,
            )
            r2.raise_for_status()
            campaign_id = str(r2.json()["id"])

            # Call 3: Create Creative
            r3 = await client.post(
                f"{_LINKEDIN_BASE}/adCreatives",
                json={
                    "campaign": f"urn:li:adCampaign:{campaign_id}",
                    "status": "ACTIVE",
                    "content": {"contentReference": creative_url},
                },
                headers=headers,
            )
            r3.raise_for_status()
            ad_id = str(r3.json()["id"])

            logger.info("LinkedIn campaign %s activated successfully", campaign_id)
            return {
                "campaign_id": campaign_id,
                "ad_id": ad_id,
                "status": "live",
                "error": None,
            }

    except Exception as e:
        logger.error("LinkedIn activation failed: %s: %s", type(e).__name__, str(e))
        return {
            "campaign_id": None,
            "ad_id": None,
            "status": "failed",
            "error": str(e),
        }
```

- [ ] **Step 5: Run LinkedIn tests — expect all 6 to pass**

```
cd D:\staging\ntm
python -m pytest backend/app/tools/tests/test_linkedin_ads.py -v
```

Expected output:
```
test_activate_linkedin_success PASSED
test_activate_linkedin_api_failure PASSED
test_activate_linkedin_returns_required_fields PASSED
test_activate_linkedin_missing_token_returns_failed PASSED
test_activate_linkedin_sends_auth_header PASSED
test_activate_linkedin_token_param_overrides_env PASSED
6 passed
```

- [ ] **Step 6: Run full tools test suite — confirm no regressions**

```
python -m pytest backend/app/tools/tests/ -v
```

Expected: 6 linkedin + 6 google_ads + 3 meta_ads + 9 google_analytics = 24 passed.

- [ ] **Step 7: Commit**

```
git add backend/app/tools/linkedin_ads.py
git commit -m "feat: harden linkedin_ads to 3-call flow with env-var token auth"
```

---

## Self-Review

**Spec coverage:**
- ✅ `LINKEDIN_ACCESS_TOKEN` env var: `_get_access_token()` in Task 2
- ✅ `LINKEDIN_ACCOUNT_ID` env var: read in `activate_linkedin()` in Task 2
- ✅ `_get_access_token()` — accepts explicit arg, falls back to env, raises if both missing: Task 2
- ✅ Headers — `Authorization`, `Content-Type`, `LinkedIn-Version`, `X-Restli-Protocol-Version`: Task 2
- ✅ Call 1 — `POST /rest/adCampaignGroups` with name, status, account URN: Task 2
- ✅ Call 2 — `POST /rest/adCampaigns` with group URN, budget, targeting from platform_config: Task 2
- ✅ Call 3 — `POST /rest/adCreatives` with campaign URN, content: Task 2
- ✅ Return dict: `{campaign_id, ad_id, status, error}`: Task 2
- ✅ Security fix — structured logger: Task 2
- ✅ 6 tests — success, api_failure, required_fields, missing_token, auth_header, token_override: Task 1
- ✅ TDD — red phase (Task 1) → green phase (Task 2)

**Placeholder scan:** None found. All steps contain complete code.

**Type consistency:**
- `_get_access_token(token: Optional[str] = None) -> str` — defined and called with `_get_access_token(access_token)` in Task 2 ✓
- `campaign_id = str(r2.json()["id"])` → `result["campaign_id"] == "222"` in test (str(222) == "222") ✓
- `ad_id = str(r3.json()["id"])` → `result["ad_id"] == "333"` in test (str(333) == "333") ✓
- `_get_access_token` patched at `backend.app.tools.linkedin_ads._get_access_token` in all tests that use it ✓
