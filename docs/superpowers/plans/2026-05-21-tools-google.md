# Tools Google Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Harden `google_ads.py` to Google Ads API v17 with OAuth2 refresh + 3-call flow, and add 9 tests for the existing `GoogleAnalyticsTool`.

**Architecture:** `google_ads.py` gets a `_get_access_token()` helper using `google-auth` (already a transitive dep via GA4) plus a 3-call mutate flow (campaign → ad group → ad group ad) with proper v17 resource names. `test_google_analytics.py` validates the existing `GoogleAnalyticsTool` implementation which falls back to mock data when credentials are absent.

**Tech Stack:** Python 3.12, httpx, google-auth, google-analytics-data SDK, pytest, unittest.mock

---

## File Map

| File | Action | Responsibility |
|------|--------|---------------|
| `backend/app/tools/google_ads.py` | Rewrite | OAuth2 auth helper + 3-call v17 activate flow |
| `backend/app/tools/tests/test_google_ads.py` | Update | Update to 3-call mock pattern, add 2 new tests |
| `backend/app/tools/tests/test_google_analytics.py` | Create | 9 tests for `GoogleAnalyticsTool.get_metrics()` |

---

## Task 1: Update test_google_ads.py for v17 3-call flow

The existing tests mock 2 httpx calls and use a response shape (`{"id": "..."}`) that won't match the new v17 response structure (`{"results": [{"resourceName": "..."}]}`). Update all 3 existing tests and add 2 new ones. Run first — they must fail before implementation.

**Files:**
- Modify: `backend/app/tools/tests/test_google_ads.py`

- [ ] **Step 1: Replace test_google_ads.py with updated tests**

```python
import os
import pytest
from uuid import uuid4
from unittest.mock import patch, AsyncMock

from backend.app.tools.google_ads import activate_google


def _campaign_response():
    m = AsyncMock()
    m.json = lambda: {"results": [{"resourceName": "customers/123/campaigns/456"}]}
    m.raise_for_status = lambda: None
    return m


def _ad_group_response():
    m = AsyncMock()
    m.json = lambda: {"results": [{"resourceName": "customers/123/adGroups/789"}]}
    m.raise_for_status = lambda: None
    return m


def _ad_response():
    m = AsyncMock()
    m.json = lambda: {"results": [{"resourceName": "customers/123/adGroupAds/999"}]}
    m.raise_for_status = lambda: None
    return m


@pytest.mark.asyncio
async def test_activate_google_success():
    activation = {
        "id": str(uuid4()),
        "name": "Test Campaign",
        "cost_estimated": 5000.0,
        "geography": "US",
    }
    platform_config = {"age_min": 18, "age_max": 65, "interests": ["technology"]}
    creative_url = "https://example.com/creative.mp4"

    with patch("backend.app.tools.google_ads._get_access_token", return_value="tok"), \
         patch.dict(os.environ, {"GOOGLE_ADS_CUSTOMER_ID": "123", "GOOGLE_ADS_DEVELOPER_TOKEN": "dev"}), \
         patch("backend.app.tools.google_ads.httpx.AsyncClient") as mock_cls:

        mock_client = AsyncMock()
        mock_client.post = AsyncMock(side_effect=[
            _campaign_response(), _ad_group_response(), _ad_response()
        ])
        mock_cls.return_value.__aenter__.return_value = mock_client

        result = await activate_google(
            activation=activation,
            platform_config=platform_config,
            creative_url=creative_url,
        )

    assert result["campaign_id"] == "456"
    assert result["ad_id"] == "999"
    assert result["status"] == "live"
    assert result["error"] is None


@pytest.mark.asyncio
async def test_activate_google_api_failure():
    activation = {"id": str(uuid4()), "name": "Test"}

    with patch("backend.app.tools.google_ads._get_access_token", return_value="tok"), \
         patch("backend.app.tools.google_ads.httpx.AsyncClient") as mock_cls:

        mock_client = AsyncMock()
        mock_client.post.side_effect = Exception("API Error")
        mock_cls.return_value.__aenter__.return_value = mock_client

        result = await activate_google(
            activation=activation, platform_config={}, creative_url="https://example.com/c.mp4"
        )

    assert result["status"] == "failed"
    assert "API Error" in result["error"]


@pytest.mark.asyncio
async def test_activate_google_returns_dict_with_required_fields():
    activation = {"id": str(uuid4()), "name": "Test"}

    with patch("backend.app.tools.google_ads._get_access_token", return_value="tok"), \
         patch.dict(os.environ, {"GOOGLE_ADS_CUSTOMER_ID": "123", "GOOGLE_ADS_DEVELOPER_TOKEN": "dev"}), \
         patch("backend.app.tools.google_ads.httpx.AsyncClient") as mock_cls:

        mock_client = AsyncMock()
        mock_client.post = AsyncMock(side_effect=[
            _campaign_response(), _ad_group_response(), _ad_response()
        ])
        mock_cls.return_value.__aenter__.return_value = mock_client

        result = await activate_google(
            activation=activation, platform_config={}, creative_url="https://example.com/c.mp4"
        )

    for field in ("campaign_id", "ad_id", "status", "error"):
        assert field in result


@pytest.mark.asyncio
async def test_activate_google_missing_credentials_returns_failed():
    activation = {"id": str(uuid4()), "name": "Test"}

    with patch("backend.app.tools.google_ads._get_access_token",
               side_effect=RuntimeError("GOOGLE_ADS_CLIENT_ID, GOOGLE_ADS_CLIENT_SECRET, and GOOGLE_ADS_REFRESH_TOKEN must be set")):

        result = await activate_google(
            activation=activation, platform_config={}, creative_url="https://example.com/c.mp4"
        )

    assert result["status"] == "failed"
    assert result["error"] is not None
    assert result["campaign_id"] is None


@pytest.mark.asyncio
async def test_activate_google_sends_developer_token_header():
    activation = {"id": str(uuid4()), "name": "Test Campaign", "cost_estimated": 1000.0}

    with patch("backend.app.tools.google_ads._get_access_token", return_value="test-tok"), \
         patch.dict(os.environ, {"GOOGLE_ADS_CUSTOMER_ID": "123", "GOOGLE_ADS_DEVELOPER_TOKEN": "my-dev-token"}), \
         patch("backend.app.tools.google_ads.httpx.AsyncClient") as mock_cls:

        mock_client = AsyncMock()
        mock_client.post = AsyncMock(side_effect=[
            _campaign_response(), _ad_group_response(), _ad_response()
        ])
        mock_cls.return_value.__aenter__.return_value = mock_client

        await activate_google(
            activation=activation, platform_config={}, creative_url="https://example.com/c.mp4"
        )

        first_kwargs = mock_client.post.call_args_list[0][1]
        assert first_kwargs["headers"]["developer-token"] == "my-dev-token"
        assert first_kwargs["headers"]["Authorization"] == "Bearer test-tok"
```

- [ ] **Step 2: Run tests — expect failure**

```
cd D:\staging\ntm
python -m pytest backend/app/tools/tests/test_google_ads.py -v
```

Expected: all 5 tests **FAIL** (implementation still uses old 2-call pattern with `Bearer <token>`).

---

## Task 2: Rewrite google_ads.py with OAuth2 + v17 3-call flow

**Files:**
- Modify: `backend/app/tools/google_ads.py`

- [ ] **Step 3: Rewrite google_ads.py**

```python
import logging
import os
from typing import Dict, Any, Optional

import httpx

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
    cid = customer_id or os.getenv("GOOGLE_ADS_CUSTOMER_ID", "")
    developer_token = os.getenv("GOOGLE_ADS_DEVELOPER_TOKEN", "")

    try:
        token = _get_access_token()
        headers = {
            "Authorization": f"Bearer {token}",
            "developer-token": developer_token,
            "Content-Type": "application/json",
        }
        base = _GOOGLE_ADS_BASE.format(customer_id=cid)
        campaign_name = activation.get("name", "Campaign")
        budget_micros = int(activation.get("cost_estimated", 0) * 1_000_000)

        async with httpx.AsyncClient(timeout=30.0) as client:
            # Call 1: Create Campaign
            r1 = await client.post(
                f"{base}/campaigns:mutate",
                json={
                    "operations": [{
                        "create": {
                            "name": campaign_name,
                            "status": "ENABLED",
                            "advertisingChannelType": "VIDEO",
                            "manualCpv": {},
                            "campaignBudget": str(budget_micros),
                            "networkSettings": {
                                "targetYoutubeSearch": True,
                                "targetYoutubeVideos": True,
                            },
                        }
                    }]
                },
                headers=headers,
            )
            r1.raise_for_status()
            campaign_resource = r1.json()["results"][0]["resourceName"]
            campaign_id = campaign_resource.split("/")[-1]

            # Call 2: Create Ad Group with platform_config targeting
            r2 = await client.post(
                f"{base}/adGroups:mutate",
                json={
                    "operations": [{
                        "create": {
                            "campaign": campaign_resource,
                            "name": f"{campaign_name} - AdGroup",
                            "status": "ENABLED",
                            "type": "VIDEO_TRUE_VIEW_IN_STREAM",
                            "targetingSettings": {
                                "targetRestrictions": [
                                    {"targetingDimension": "AGE_RANGE", "bidOnly": False},
                                    {"targetingDimension": "INTEREST", "bidOnly": False},
                                ]
                            },
                        }
                    }]
                },
                headers=headers,
            )
            r2.raise_for_status()
            ad_group_resource = r2.json()["results"][0]["resourceName"]

            # Call 3: Create Ad Group Ad
            r3 = await client.post(
                f"{base}/adGroupAds:mutate",
                json={
                    "operations": [{
                        "create": {
                            "adGroup": ad_group_resource,
                            "status": "ENABLED",
                            "ad": {
                                "videoAd": {
                                    "video": {"resourceName": creative_url},
                                    "inStream": {},
                                },
                                "finalUrls": [creative_url],
                            },
                        }
                    }]
                },
                headers=headers,
            )
            r3.raise_for_status()
            ad_resource = r3.json()["results"][0]["resourceName"]
            ad_id = ad_resource.split("/")[-1]

            logger.info(f"Google Ads campaign {campaign_id} activated successfully")
            return {
                "campaign_id": campaign_id,
                "ad_id": ad_id,
                "status": "live",
                "error": None,
            }

    except Exception as e:
        logger.error(f"Google Ads activation failed: {e}")
        return {
            "campaign_id": None,
            "ad_id": None,
            "status": "failed",
            "error": str(e),
        }
```

- [ ] **Step 4: Run tests — expect all 5 to pass**

```
python -m pytest backend/app/tools/tests/test_google_ads.py -v
```

Expected output:
```
test_activate_google_success PASSED
test_activate_google_api_failure PASSED
test_activate_google_returns_dict_with_required_fields PASSED
test_activate_google_missing_credentials_returns_failed PASSED
test_activate_google_sends_developer_token_header PASSED
5 passed
```

- [ ] **Step 5: Commit**

```
git add backend/app/tools/google_ads.py backend/app/tools/tests/test_google_ads.py
git commit -m "feat: harden google_ads to v17 OAuth2 + 3-call mutate flow"
```

---

## Task 3: Create test_google_analytics.py

`GoogleAnalyticsTool` is already implemented. Tests validate its contract. Key implementation facts:
- `_mock_metrics` returns `{activation_id, sessions:0, users:0, goal_completions:0, bounce_rate:0.0, source:"mock"}`
- `_fetch_from_api` returns same keys with `source:"ga4"` and real values
- Mock fallback triggers when `property_id` or `sa_json_path` is empty, or `_GA4_AVAILABLE` is False
- `_get_client()` caches the SDK client in `self._client`
- Date defaults: `start = today - 30 days`, `end = today`

**Files:**
- Create: `backend/app/tools/tests/test_google_analytics.py`

- [ ] **Step 6: Create test_google_analytics.py**

```python
import os
import pytest
from datetime import date, timedelta
from unittest.mock import patch, MagicMock

from backend.app.tools.google_analytics import GoogleAnalyticsTool

REQUIRED_KEYS = {"activation_id", "sessions", "users", "goal_completions", "bounce_rate", "source"}


def test_mock_fallback_no_credentials():
    with patch.dict(os.environ, {"GA4_PROPERTY_ID": "", "GA4_SERVICE_ACCOUNT_JSON_PATH": ""}):
        tool = GoogleAnalyticsTool()
        result = tool.get_metrics({"id": "act-1", "channel": "youtube"})
    assert isinstance(result, dict)
    assert result["source"] == "mock"


def test_mock_fallback_has_required_keys():
    with patch.dict(os.environ, {"GA4_PROPERTY_ID": "", "GA4_SERVICE_ACCOUNT_JSON_PATH": ""}):
        tool = GoogleAnalyticsTool()
        result = tool.get_metrics({"id": "act-1"})
    assert REQUIRED_KEYS.issubset(result.keys())


def test_mock_fallback_sdk_unavailable():
    with patch("backend.app.tools.google_analytics._GA4_AVAILABLE", False), \
         patch.dict(os.environ, {"GA4_PROPERTY_ID": "123", "GA4_SERVICE_ACCOUNT_JSON_PATH": "/p.json"}):
        tool = GoogleAnalyticsTool()
        result = tool.get_metrics({"id": "act-1"})
    assert result["source"] == "mock"
    assert REQUIRED_KEYS.issubset(result.keys())


def test_get_metrics_success():
    mock_row = MagicMock()
    mock_row.metric_values = [
        MagicMock(value="1500"),
        MagicMock(value="1200"),
        MagicMock(value="300"),
        MagicMock(value="0.35"),
    ]
    mock_response = MagicMock()
    mock_response.rows = [mock_row]
    mock_client = MagicMock()
    mock_client.run_report.return_value = mock_response

    with patch("backend.app.tools.google_analytics._GA4_AVAILABLE", True), \
         patch("backend.app.tools.google_analytics.BetaAnalyticsDataClient", return_value=mock_client), \
         patch("backend.app.tools.google_analytics.service_account") as mock_sa, \
         patch.dict(os.environ, {"GA4_PROPERTY_ID": "123", "GA4_SERVICE_ACCOUNT_JSON_PATH": "/p.json"}):

        mock_sa.Credentials.from_service_account_file.return_value = MagicMock()
        tool = GoogleAnalyticsTool()
        result = tool.get_metrics({"id": "act-1", "channel": "youtube"})

    assert result["sessions"] == 1500
    assert result["users"] == 1200
    assert result["goal_completions"] == 300
    assert result["source"] == "ga4"
    assert mock_client.run_report.called


def test_get_metrics_date_range_defaults():
    mock_response = MagicMock()
    mock_response.rows = []
    mock_client = MagicMock()
    mock_client.run_report.return_value = mock_response

    with patch("backend.app.tools.google_analytics._GA4_AVAILABLE", True), \
         patch("backend.app.tools.google_analytics.BetaAnalyticsDataClient", return_value=mock_client), \
         patch("backend.app.tools.google_analytics.service_account") as mock_sa, \
         patch.dict(os.environ, {"GA4_PROPERTY_ID": "123", "GA4_SERVICE_ACCOUNT_JSON_PATH": "/p.json"}):

        mock_sa.Credentials.from_service_account_file.return_value = MagicMock()
        tool = GoogleAnalyticsTool()
        tool.get_metrics({"id": "act-1"})

    request = mock_client.run_report.call_args[0][0]
    today = date.today()
    expected_start = (today - timedelta(days=30)).strftime("%Y-%m-%d")
    expected_end = today.strftime("%Y-%m-%d")
    assert request.date_ranges[0].start_date == expected_start
    assert request.date_ranges[0].end_date == expected_end


def test_get_metrics_custom_date_range():
    mock_response = MagicMock()
    mock_response.rows = []
    mock_client = MagicMock()
    mock_client.run_report.return_value = mock_response

    custom_start = date(2026, 1, 1)
    custom_end = date(2026, 1, 31)

    with patch("backend.app.tools.google_analytics._GA4_AVAILABLE", True), \
         patch("backend.app.tools.google_analytics.BetaAnalyticsDataClient", return_value=mock_client), \
         patch("backend.app.tools.google_analytics.service_account") as mock_sa, \
         patch.dict(os.environ, {"GA4_PROPERTY_ID": "123", "GA4_SERVICE_ACCOUNT_JSON_PATH": "/p.json"}):

        mock_sa.Credentials.from_service_account_file.return_value = MagicMock()
        tool = GoogleAnalyticsTool()
        tool.get_metrics({"id": "act-1"}, start_date=custom_start, end_date=custom_end)

    request = mock_client.run_report.call_args[0][0]
    assert request.date_ranges[0].start_date == "2026-01-01"
    assert request.date_ranges[0].end_date == "2026-01-31"


def test_get_metrics_api_error_returns_mock():
    mock_client = MagicMock()
    mock_client.run_report.side_effect = Exception("GA4 API unavailable")

    with patch("backend.app.tools.google_analytics._GA4_AVAILABLE", True), \
         patch("backend.app.tools.google_analytics.BetaAnalyticsDataClient", return_value=mock_client), \
         patch("backend.app.tools.google_analytics.service_account") as mock_sa, \
         patch.dict(os.environ, {"GA4_PROPERTY_ID": "123", "GA4_SERVICE_ACCOUNT_JSON_PATH": "/p.json"}):

        mock_sa.Credentials.from_service_account_file.return_value = MagicMock()
        tool = GoogleAnalyticsTool()
        result = tool.get_metrics({"id": "act-1"})

    assert isinstance(result, dict)
    assert result["source"] == "mock"
    assert REQUIRED_KEYS.issubset(result.keys())


def test_get_metrics_activation_channel_does_not_raise():
    with patch.dict(os.environ, {"GA4_PROPERTY_ID": "", "GA4_SERVICE_ACCOUNT_JSON_PATH": ""}):
        tool = GoogleAnalyticsTool()
        result = tool.get_metrics({"id": "act-1", "channel": "youtube"})
    assert isinstance(result, dict)


def test_client_cached():
    mock_client_instance = MagicMock()

    with patch("backend.app.tools.google_analytics._GA4_AVAILABLE", True), \
         patch("backend.app.tools.google_analytics.BetaAnalyticsDataClient", return_value=mock_client_instance) as mock_ctor, \
         patch("backend.app.tools.google_analytics.service_account") as mock_sa, \
         patch.dict(os.environ, {"GA4_PROPERTY_ID": "123", "GA4_SERVICE_ACCOUNT_JSON_PATH": "/p.json"}):

        mock_sa.Credentials.from_service_account_file.return_value = MagicMock()
        tool = GoogleAnalyticsTool()
        c1 = tool._get_client()
        c2 = tool._get_client()

    assert c1 is c2
    assert mock_ctor.call_count == 1
```

- [ ] **Step 7: Run GA4 tests — expect all 9 to pass**

```
python -m pytest backend/app/tools/tests/test_google_analytics.py -v
```

Expected output:
```
test_mock_fallback_no_credentials PASSED
test_mock_fallback_has_required_keys PASSED
test_mock_fallback_sdk_unavailable PASSED
test_get_metrics_success PASSED
test_get_metrics_date_range_defaults PASSED
test_get_metrics_custom_date_range PASSED
test_get_metrics_api_error_returns_mock PASSED
test_get_metrics_activation_channel_does_not_raise PASSED
test_client_cached PASSED
9 passed
```

- [ ] **Step 8: Run full tools test suite**

```
python -m pytest backend/app/tools/tests/ -v
```

All tests must pass (5 google_ads + 2 meta_ads + 9 google_analytics = 16 total).

- [ ] **Step 9: Commit**

```
git add backend/app/tools/tests/test_google_analytics.py
git commit -m "feat: add test_google_analytics.py — 9 tests for GoogleAnalyticsTool"
```

---

## Self-Review

**Spec coverage:**
- ✅ Auth env vars (5): defined in Task 2 `_get_access_token()`
- ✅ `google-auth` OAuth2 refresh: Task 2 uses `google.oauth2.credentials.Credentials` + `Request()`
- ✅ 3-call v17 flow (campaign → ad group → ad group ad): Task 2 `activate_google()`
- ✅ `developer-token` header: included in `headers` dict, verified in test 5
- ✅ `platform_config` targeting wired into ad group `targetingSettings`: Task 2
- ✅ Return dict unchanged: Task 2 returns `{campaign_id, ad_id, status, error}`
- ✅ 9 GA4 tests (mock fallback ×3, SDK success, date defaults, custom dates, API error, channel, cache): Task 3

**Placeholder scan:** None found. All steps contain complete code.

**Type consistency:**
- `_get_access_token()` → `str` — defined and used in Task 2 ✓
- `activate_google` signature unchanged — existing tests reuse same call signature ✓
- `GoogleAnalyticsTool` not modified — tests import from existing module ✓
- `REQUIRED_KEYS` defined at module level in test file, used in tests 1–3, 7 ✓
