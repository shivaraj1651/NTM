# Tools Google Design
**Date:** 2026-05-21  
**Status:** Approved

## Scope

Two deliverables:
1. `backend/app/tools/google_ads.py` — harden to Google Ads API v17 with OAuth2 refresh + proper 3-call flow
2. `backend/app/tools/tests/test_google_analytics.py` — 9 tests for the existing `GoogleAnalyticsTool`

---

## 1. google_ads.py

### Credentials

Five env vars required:

| Var | Purpose |
|-----|---------|
| `GOOGLE_ADS_CLIENT_ID` | OAuth2 client ID |
| `GOOGLE_ADS_CLIENT_SECRET` | OAuth2 client secret |
| `GOOGLE_ADS_REFRESH_TOKEN` | Long-lived refresh token |
| `GOOGLE_ADS_CUSTOMER_ID` | Default customer ID (overridable per-call) |
| `GOOGLE_ADS_DEVELOPER_TOKEN` | Required header for Google Ads API |

### Auth helper

```python
def _get_access_token() -> str
```

- Constructs `google.oauth2.credentials.Credentials(token=None, refresh_token=..., client_id=..., client_secret=..., token_uri="https://oauth2.googleapis.com/token")`
- Calls `.refresh(google.auth.transport.requests.Request())`
- Returns `.token`
- Raises `RuntimeError` if any env var is missing

### API headers (all 3 calls)

```python
{
    "Authorization": f"Bearer {token}",
    "developer-token": GOOGLE_ADS_DEVELOPER_TOKEN,
    "Content-Type": "application/json"
}
```

### 3-Call Flow

Base URL: `https://googleads.googleapis.com/v17/customers/{customer_id}`

**Call 1 — Campaign** (`POST /campaigns:mutate`)

Payload:
```json
{
  "operations": [{
    "create": {
      "name": "<activation name>",
      "status": "ENABLED",
      "advertisingChannelType": "VIDEO",
      "manualCpv": {},
      "campaignBudget": "<budget in micros = cost_estimated * 1_000_000>",
      "networkSettings": {
        "targetYoutubeSearch": true,
        "targetYoutubeVideos": true
      }
    }
  }]
}
```

Response: `results[0].resourceName` → `customers/X/campaigns/Y` → extract `Y` as `campaign_id`.

**Call 2 — Ad Group** (`POST /adGroups:mutate`)

Payload:
```json
{
  "operations": [{
    "create": {
      "campaign": "customers/{cid}/campaigns/{campaign_id}",
      "name": "<activation name> - AdGroup",
      "status": "ENABLED",
      "type": "VIDEO_TRUE_VIEW_IN_STREAM",
      "targetingSettings": {
        "targetRestrictions": [
          {"targetingDimension": "AGE_RANGE"},
          {"targetingDimension": "INTEREST"}
        ]
      }
    }
  }]
}
```

`platform_config` fields wired in: `age_min`, `age_max`, `interests`, `geography`.  
Response: `results[0].resourceName` → extract ad group id.

**Call 3 — Ad Group Ad** (`POST /adGroupAds:mutate`)

Payload:
```json
{
  "operations": [{
    "create": {
      "adGroup": "customers/{cid}/adGroups/{ag_id}",
      "status": "ENABLED",
      "ad": {
        "videoAd": {
          "video": {"resourceName": "<creative_url>"},
          "inStream": {}
        },
        "finalUrls": ["<creative_url>"]
      }
    }
  }]
}
```

Response: `results[0].resourceName` → extract as `ad_id`.

### Return value (unchanged)

```python
{
    "campaign_id": str | None,
    "ad_id": str | None,
    "status": "live" | "failed",
    "error": str | None
}
```

### Fallback behaviour

If `_get_access_token()` raises (missing env vars), the `except` block catches it and returns `status: "failed"` with the error message — consistent with current behaviour.

---

## 2. test_google_analytics.py

9 tests for `GoogleAnalyticsTool.get_metrics()`:

| # | Test | Verifies |
|---|------|----------|
| 1 | `test_mock_fallback_no_credentials` | Empty env vars → returns mock dict, no exception |
| 2 | `test_mock_fallback_sdk_unavailable` | `_GA4_AVAILABLE=False` → returns mock, not raises |
| 3 | `test_mock_fallback_has_required_keys` | Mock response has `sessions`, `users`, `goal_completions`, `bounce_rate`, `source_medium` |
| 4 | `test_get_metrics_success` | Mock `BetaAnalyticsDataClient`, verify `RunReportRequest` built, response parsed |
| 5 | `test_get_metrics_date_range_defaults` | No dates → start = 30 days ago, end = today |
| 6 | `test_get_metrics_custom_date_range` | Explicit `start_date`/`end_date` used in request |
| 7 | `test_get_metrics_api_error` | SDK raises → returns error-state dict, no crash |
| 8 | `test_get_metrics_uses_activation_channel` | `activation["channel"]` influences source_medium |
| 9 | `test_client_cached` | `_get_client()` called twice → same instance returned |

### Test dependencies

- `pytest`, `pytest-asyncio` (already present)
- `unittest.mock.patch`, `MagicMock`
- No real Google credentials required — all SDK calls mocked

---

## Files Modified / Created

| File | Action |
|------|--------|
| `backend/app/tools/google_ads.py` | Rewrite — OAuth2 auth, v17 3-call flow, targeting wired |
| `backend/app/tools/tests/test_google_analytics.py` | Create — 9 tests |

## Files Unchanged

| File | Reason |
|------|--------|
| `backend/app/tools/google_analytics.py` | Already complete from gap-closure session |
| `backend/app/tools/tests/test_google_ads.py` | Existing 3 tests remain valid; new implementation preserves same function signature |
