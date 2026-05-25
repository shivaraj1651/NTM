# Meta Ads Tool Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Rewrite `meta_ads.py` to expose 6 discrete Meta Marketing API v21.0 functions and a clean `activate_meta` orchestrator, with 11 passing tests.

**Architecture:** Fix the broken base URL and placeholder token, add `_get_access_token()` reading `META_SYSTEM_USER_TOKEN`, implement 6 granular async functions that raise on error, rewire `activate_meta` to chain them. Keep competitor-research functions untouched.

**Tech Stack:** Python 3.12, httpx (async), pytest-asyncio, unittest.mock

---

## File Map

| File | Action | Responsibility |
|------|--------|----------------|
| `backend/app/tools/meta_ads.py` | Modify | Fix constants, add auth helper, add 6 functions, rewrite `activate_meta` |
| `backend/app/tools/tests/test_meta_ads.py` | Modify | Add 8 new test cases (keep 3 existing) |

---

## Task 1: Fix Constants and Add Auth Helper

**Files:**
- Modify: `backend/app/tools/meta_ads.py`

- [ ] **Step 1: Write the failing test for missing token**

In `backend/app/tools/tests/test_meta_ads.py`, add at the top of the file after existing imports:

```python
import os
from unittest.mock import patch
from backend.app.tools.meta_ads import _get_access_token


@pytest.mark.asyncio
async def test_missing_token_raises():
    with patch.dict(os.environ, {}, clear=True):
        # Remove META_SYSTEM_USER_TOKEN if present
        env = {k: v for k, v in os.environ.items() if k != "META_SYSTEM_USER_TOKEN"}
        with patch.dict(os.environ, env, clear=True):
            with pytest.raises(RuntimeError, match="META_SYSTEM_USER_TOKEN must be set"):
                _get_access_token()
```

- [ ] **Step 2: Run to confirm FAIL**

```
cd D:\staging\ntm
pytest backend/app/tools/tests/test_meta_ads.py::test_missing_token_raises -v
```

Expected: `ImportError` or `AttributeError` — `_get_access_token` not yet defined.

- [ ] **Step 3: Fix constants and add `_get_access_token`**

In `backend/app/tools/meta_ads.py`, replace:
```python
META_ADS_API_ENDPOINT = "https://graph.instagram.com/v19.0/act_1234"
```
With:
```python
import os

META_BASE = "https://graph.facebook.com/v21.0"


def _get_access_token() -> str:
    token = os.getenv("META_SYSTEM_USER_TOKEN", "")
    if not token:
        raise RuntimeError("META_SYSTEM_USER_TOKEN must be set")
    return token
```

Keep all existing imports (`import httpx`, `import logging`, `from typing import ...`, `import re`). Add `import os` after `import httpx`.

- [ ] **Step 4: Run to confirm PASS**

```
pytest backend/app/tools/tests/test_meta_ads.py::test_missing_token_raises -v
```

Expected: PASS

- [ ] **Step 5: Commit**

```
git add backend/app/tools/meta_ads.py backend/app/tools/tests/test_meta_ads.py
git commit -m "[TASK-017] feat: fix META_BASE constant and add _get_access_token

Co-authored-by: katharguppe <katharguppe@users.noreply.github.com>"
```

---

## Task 2: Implement `create_campaign`

**Files:**
- Modify: `backend/app/tools/meta_ads.py`
- Modify: `backend/app/tools/tests/test_meta_ads.py`

- [ ] **Step 1: Write the failing tests**

Add to `test_meta_ads.py`:

```python
import json
from backend.app.tools.meta_ads import create_campaign


def _mock_post_response(response_id: str):
    m = AsyncMock()
    m.json = lambda: {"id": response_id}
    m.raise_for_status = lambda: None
    return m


@pytest.mark.asyncio
async def test_create_campaign_success():
    with patch.dict(os.environ, {"META_SYSTEM_USER_TOKEN": "test-token"}), \
         patch("backend.app.tools.meta_ads.httpx.AsyncClient") as mock_cls:

        mock_client = AsyncMock()
        mock_client.post = AsyncMock(return_value=_mock_post_response("camp_001"))
        mock_cls.return_value.__aenter__.return_value = mock_client

        result = await create_campaign(
            ad_account_id="123456789",
            name="Test Campaign",
            objective="LINK_CLICKS",
            budget=100.0,
            schedule={"start_time": 1700000000},
        )

    assert result == "camp_001"


@pytest.mark.asyncio
async def test_create_campaign_raises_on_http_error():
    with patch.dict(os.environ, {"META_SYSTEM_USER_TOKEN": "test-token"}), \
         patch("backend.app.tools.meta_ads.httpx.AsyncClient") as mock_cls:

        mock_client = AsyncMock()
        mock_client.post.side_effect = httpx.HTTPStatusError(
            "400 Bad Request", request=AsyncMock(), response=AsyncMock()
        )
        mock_cls.return_value.__aenter__.return_value = mock_client

        with pytest.raises(httpx.HTTPStatusError):
            await create_campaign(
                ad_account_id="123456789",
                name="Bad Campaign",
                objective="LINK_CLICKS",
                budget=100.0,
                schedule={},
            )
```

Add `import httpx` to the test file imports.

- [ ] **Step 2: Run to confirm FAIL**

```
pytest backend/app/tools/tests/test_meta_ads.py::test_create_campaign_success backend/app/tools/tests/test_meta_ads.py::test_create_campaign_raises_on_http_error -v
```

Expected: `ImportError` — `create_campaign` not yet defined.

- [ ] **Step 3: Implement `create_campaign`**

Add after `_get_access_token` in `meta_ads.py`:

```python
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
    payload: Dict[str, Any] = {
        "name": name,
        "objective": objective,
        "status": "PAUSED",
        "daily_budget": str(int(budget * 100)),
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
```

- [ ] **Step 4: Run to confirm PASS**

```
pytest backend/app/tools/tests/test_meta_ads.py::test_create_campaign_success backend/app/tools/tests/test_meta_ads.py::test_create_campaign_raises_on_http_error -v
```

Expected: 2 PASS

- [ ] **Step 5: Commit**

```
git add backend/app/tools/meta_ads.py backend/app/tools/tests/test_meta_ads.py
git commit -m "[TASK-017] feat: add create_campaign

Co-authored-by: katharguppe <katharguppe@users.noreply.github.com>"
```

---

## Task 3: Implement `create_ad_set`

**Files:**
- Modify: `backend/app/tools/meta_ads.py`
- Modify: `backend/app/tools/tests/test_meta_ads.py`

- [ ] **Step 1: Write the failing test**

Add to `test_meta_ads.py`:

```python
from backend.app.tools.meta_ads import create_ad_set


@pytest.mark.asyncio
async def test_create_ad_set_success():
    with patch.dict(os.environ, {
        "META_SYSTEM_USER_TOKEN": "test-token",
        "META_AD_ACCOUNT_ID": "999888777",
    }), patch("backend.app.tools.meta_ads.httpx.AsyncClient") as mock_cls:

        mock_client = AsyncMock()
        mock_client.post = AsyncMock(return_value=_mock_post_response("adset_042"))
        mock_cls.return_value.__aenter__.return_value = mock_client

        result = await create_ad_set(
            campaign_id="camp_001",
            name="Test AdSet",
            audience_spec={"age_min": 25, "age_max": 54, "geo_locations": {"countries": ["US"]}},
            placements=["FACEBOOK_FEED", "INSTAGRAM_FEED"],
            budget=50.0,
        )

    assert result == "adset_042"
```

- [ ] **Step 2: Run to confirm FAIL**

```
pytest backend/app/tools/tests/test_meta_ads.py::test_create_ad_set_success -v
```

Expected: `ImportError` — `create_ad_set` not yet defined.

- [ ] **Step 3: Implement `create_ad_set`**

Add after `create_campaign` in `meta_ads.py`:

```python
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
```

- [ ] **Step 4: Run to confirm PASS**

```
pytest backend/app/tools/tests/test_meta_ads.py::test_create_ad_set_success -v
```

Expected: PASS

- [ ] **Step 5: Commit**

```
git add backend/app/tools/meta_ads.py backend/app/tools/tests/test_meta_ads.py
git commit -m "[TASK-017] feat: add create_ad_set

Co-authored-by: katharguppe <katharguppe@users.noreply.github.com>"
```

---

## Task 4: Implement `create_ad`

**Files:**
- Modify: `backend/app/tools/meta_ads.py`
- Modify: `backend/app/tools/tests/test_meta_ads.py`

- [ ] **Step 1: Write the failing test**

Add to `test_meta_ads.py`:

```python
from backend.app.tools.meta_ads import create_ad


@pytest.mark.asyncio
async def test_create_ad_success():
    with patch.dict(os.environ, {
        "META_SYSTEM_USER_TOKEN": "test-token",
        "META_AD_ACCOUNT_ID": "999888777",
        "META_PAGE_ID": "111000222",
    }), patch("backend.app.tools.meta_ads.httpx.AsyncClient") as mock_cls:

        mock_client = AsyncMock()
        mock_client.post = AsyncMock(return_value=_mock_post_response("ad_007"))
        mock_cls.return_value.__aenter__.return_value = mock_client

        result = await create_ad(
            ad_set_id="adset_042",
            creative_spec={
                "image_hash": "abc123",
                "link": "https://example.com",
                "message": "Check this out!",
            },
            name="Test Ad",
        )

    assert result == "ad_007"
```

- [ ] **Step 2: Run to confirm FAIL**

```
pytest backend/app/tools/tests/test_meta_ads.py::test_create_ad_success -v
```

Expected: `ImportError` — `create_ad` not yet defined.

- [ ] **Step 3: Implement `create_ad`**

Add after `create_ad_set` in `meta_ads.py`:

```python
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
```

- [ ] **Step 4: Run to confirm PASS**

```
pytest backend/app/tools/tests/test_meta_ads.py::test_create_ad_success -v
```

Expected: PASS

- [ ] **Step 5: Commit**

```
git add backend/app/tools/meta_ads.py backend/app/tools/tests/test_meta_ads.py
git commit -m "[TASK-017] feat: add create_ad

Co-authored-by: katharguppe <katharguppe@users.noreply.github.com>"
```

---

## Task 5: Implement `get_ad_insights`

**Files:**
- Modify: `backend/app/tools/meta_ads.py`
- Modify: `backend/app/tools/tests/test_meta_ads.py`

- [ ] **Step 1: Write the failing test**

Add to `test_meta_ads.py`:

```python
from backend.app.tools.meta_ads import get_ad_insights


@pytest.mark.asyncio
async def test_get_ad_insights_success():
    mock_insights_data = {
        "data": [{"impressions": "5000", "clicks": "120", "spend": "45.50"}],
        "paging": {}
    }

    with patch.dict(os.environ, {"META_SYSTEM_USER_TOKEN": "test-token"}), \
         patch("backend.app.tools.meta_ads.httpx.AsyncClient") as mock_cls:

        mock_get_response = AsyncMock()
        mock_get_response.json = lambda: mock_insights_data
        mock_get_response.raise_for_status = lambda: None

        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=mock_get_response)
        mock_cls.return_value.__aenter__.return_value = mock_client

        result = await get_ad_insights(
            ad_id="ad_007",
            date_range={"since": "2026-05-01", "until": "2026-05-25"},
            metrics_list=["impressions", "clicks", "spend"],
        )

    assert result["ad_id"] == "ad_007"
    assert "metrics" in result
    assert result["metrics"]["impressions"] == "5000"
    assert result["metrics"]["clicks"] == "120"
```

- [ ] **Step 2: Run to confirm FAIL**

```
pytest backend/app/tools/tests/test_meta_ads.py::test_get_ad_insights_success -v
```

Expected: `ImportError` — `get_ad_insights` not yet defined.

- [ ] **Step 3: Implement `get_ad_insights`**

Add after `create_ad` in `meta_ads.py`:

```python
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
```

- [ ] **Step 4: Run to confirm PASS**

```
pytest backend/app/tools/tests/test_meta_ads.py::test_get_ad_insights_success -v
```

Expected: PASS

- [ ] **Step 5: Commit**

```
git add backend/app/tools/meta_ads.py backend/app/tools/tests/test_meta_ads.py
git commit -m "[TASK-017] feat: add get_ad_insights

Co-authored-by: katharguppe <katharguppe@users.noreply.github.com>"
```

---

## Task 6: Implement `pause_ad` and `update_ad_budget`

**Files:**
- Modify: `backend/app/tools/meta_ads.py`
- Modify: `backend/app/tools/tests/test_meta_ads.py`

- [ ] **Step 1: Write the failing tests**

Add to `test_meta_ads.py`:

```python
from backend.app.tools.meta_ads import pause_ad, update_ad_budget


def _mock_bool_response():
    m = AsyncMock()
    m.json = lambda: {"success": True}
    m.raise_for_status = lambda: None
    return m


@pytest.mark.asyncio
async def test_pause_ad_returns_true():
    with patch.dict(os.environ, {"META_SYSTEM_USER_TOKEN": "test-token"}), \
         patch("backend.app.tools.meta_ads.httpx.AsyncClient") as mock_cls:

        mock_client = AsyncMock()
        mock_client.post = AsyncMock(return_value=_mock_bool_response())
        mock_cls.return_value.__aenter__.return_value = mock_client

        result = await pause_ad(ad_id="ad_007")

    assert result is True


@pytest.mark.asyncio
async def test_update_ad_budget_returns_true():
    with patch.dict(os.environ, {"META_SYSTEM_USER_TOKEN": "test-token"}), \
         patch("backend.app.tools.meta_ads.httpx.AsyncClient") as mock_cls:

        mock_client = AsyncMock()
        mock_client.post = AsyncMock(return_value=_mock_bool_response())
        mock_cls.return_value.__aenter__.return_value = mock_client

        result = await update_ad_budget(ad_set_id="adset_042", daily_budget=75.0)

    assert result is True
```

- [ ] **Step 2: Run to confirm FAIL**

```
pytest backend/app/tools/tests/test_meta_ads.py::test_pause_ad_returns_true backend/app/tools/tests/test_meta_ads.py::test_update_ad_budget_returns_true -v
```

Expected: `ImportError` — functions not yet defined.

- [ ] **Step 3: Implement `pause_ad` and `update_ad_budget`**

Add after `get_ad_insights` in `meta_ads.py`:

```python
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
```

- [ ] **Step 4: Run to confirm PASS**

```
pytest backend/app/tools/tests/test_meta_ads.py::test_pause_ad_returns_true backend/app/tools/tests/test_meta_ads.py::test_update_ad_budget_returns_true -v
```

Expected: 2 PASS

- [ ] **Step 5: Commit**

```
git add backend/app/tools/meta_ads.py backend/app/tools/tests/test_meta_ads.py
git commit -m "[TASK-017] feat: add pause_ad and update_ad_budget

Co-authored-by: katharguppe <katharguppe@users.noreply.github.com>"
```

---

## Task 7: Rewrite `activate_meta` Orchestrator

**Files:**
- Modify: `backend/app/tools/meta_ads.py`
- Verify: `backend/app/tools/tests/test_meta_ads.py` (3 existing tests must still pass)

- [ ] **Step 1: Confirm existing 3 tests currently pass**

```
pytest backend/app/tools/tests/test_meta_ads.py::test_activate_meta_success backend/app/tools/tests/test_meta_ads.py::test_activate_meta_api_failure backend/app/tools/tests/test_meta_ads.py::test_activate_meta_returns_required_fields -v
```

Note the current pass/fail state — these tests mock `httpx.AsyncClient` directly. After rewriting `activate_meta` to call the 6 new functions, those mocks still work because the 6 functions each open their own `httpx.AsyncClient`. The existing tests patch at the `httpx.AsyncClient` class level, so all 3 `post` calls inside the orchestrator are still captured.

- [ ] **Step 2: Rewrite `activate_meta`**

In `meta_ads.py`, replace the entire existing `activate_meta` function with:

```python
async def activate_meta(
    activation: Dict[str, Any],
    platform_config: Dict[str, Any],
    creative_url: str,
    access_token: Optional[str] = None,
) -> Dict[str, Any]:
    """Activate a campaign on Meta (Facebook/Instagram).

    Orchestrates create_campaign → create_ad_set → create_ad.
    The access_token param is accepted for signature compatibility but ignored;
    token always comes from META_SYSTEM_USER_TOKEN env var.

    Args:
        activation: Activation record with name, cost_estimated
        platform_config: Meta targeting: age_min, age_max, geo_locations, interests
        creative_url: URL used as ad link; image_hash left empty (upload separately)
        access_token: Ignored — kept for API compatibility

    Returns:
        {campaign_id, ad_id, status: "live"|"failed", error: str|None}
    """
    account_id = os.getenv("META_AD_ACCOUNT_ID", "")
    campaign_name = activation.get("name", "Campaign")
    daily_budget = float(activation.get("cost_estimated", 0))

    try:
        if not account_id:
            raise RuntimeError("META_AD_ACCOUNT_ID must be set")

        campaign_id = await create_campaign(
            ad_account_id=account_id,
            name=campaign_name,
            objective="LINK_CLICKS",
            budget=daily_budget,
            schedule={},
        )

        audience_spec = {
            "age_min": platform_config.get("age_min", 18),
            "age_max": platform_config.get("age_max", 65),
            "geo_locations": {"countries": ["US"]},
            "interests": platform_config.get("interests", []),
        }
        ad_set_id = await create_ad_set(
            campaign_id=campaign_id,
            name=f"{campaign_name} - AdSet",
            audience_spec=audience_spec,
            placements=["facebook", "instagram"],
            budget=daily_budget,
        )

        ad_id = await create_ad(
            ad_set_id=ad_set_id,
            creative_spec={"link": creative_url, "message": campaign_name},
            name=f"{campaign_name} - Ad",
        )

        logger.info("Meta campaign %s activated successfully", campaign_id)
        return {"campaign_id": campaign_id, "ad_id": ad_id, "status": "live", "error": None}

    except Exception as e:
        logger.error("Meta activation failed: %s: %s", type(e).__name__, str(e))
        return {"campaign_id": None, "ad_id": None, "status": "failed", "error": str(e)}
```

- [ ] **Step 3: Run all 11 tests**

```
pytest backend/app/tools/tests/test_meta_ads.py -v
```

Expected: 11 PASS

If the 3 existing `activate_meta` tests fail because they mock `httpx.AsyncClient` but the orchestrator now makes 3 separate client calls, fix by checking mock setup: `mock_client.post = AsyncMock(side_effect=[campaign_resp, adset_resp, ad_resp])` — the side_effect list is consumed across all 3 `post` calls regardless of how many `AsyncClient` instances are opened, because `mock_cls.return_value.__aenter__.return_value` returns the same mock client each time.

- [ ] **Step 4: Run full tool test suite**

```
pytest backend/app/tools/tests/ -v
```

Expected: all existing google, linkedin, meta tests pass.

- [ ] **Step 5: Commit**

```
git add backend/app/tools/meta_ads.py
git commit -m "[TASK-017] feat: rewrite activate_meta as orchestrator

Co-authored-by: katharguppe <katharguppe@users.noreply.github.com>"
```

---

## Task 8: Final Verification

- [ ] **Step 1: Run full meta test suite with coverage**

```
pytest backend/app/tools/tests/test_meta_ads.py -v --tb=short
```

Expected: 11 passed, 0 failed.

- [ ] **Step 2: Run all tool tests**

```
pytest backend/app/tools/tests/ -v --tb=short
```

Expected: all pass (google, linkedin, meta).

- [ ] **Step 3: Verify no import errors**

```
python -c "from backend.app.tools.meta_ads import create_campaign, create_ad_set, create_ad, get_ad_insights, pause_ad, update_ad_budget, activate_meta, lookup_meta_ads; print('OK')"
```

Expected: `OK`

- [ ] **Step 4: Final commit**

```
git add docs/superpowers/specs/2026-05-25-meta-ads-tool-design.md docs/superpowers/plans/2026-05-25-meta-ads-tool.md
git commit -m "[TASK-017] docs: add meta ads tool spec and plan

Co-authored-by: katharguppe <katharguppe@users.noreply.github.com>"
```

---

## Self-Review Checklist

- [x] All 6 functions have test coverage
- [x] `activate_meta` orchestrator test coverage (3 existing tests)
- [x] `_get_access_token` missing-token test
- [x] `create_campaign` HTTP error raise test
- [x] All function signatures match spec exactly
- [x] `META_AD_ACCOUNT_ID` env var required by `create_ad_set`, `create_ad`, `activate_meta`
- [x] `META_PAGE_ID` fallback in `create_ad`
- [x] Budget × 100 (USD → cents) in `create_campaign`, `create_ad_set`, `update_ad_budget`
- [x] `lookup_meta_ads` and helpers not touched
- [x] Imports: `os` added to `meta_ads.py`, `httpx` + `os` in test file
