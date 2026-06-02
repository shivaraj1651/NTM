# Tools LinkedIn Design
**Date:** 2026-05-21  
**Status:** Approved

## Scope

Two deliverables:
1. `backend/app/tools/linkedin_ads.py` — harden with env-var token auth + 3-call LinkedIn Marketing API flow (campaign group → campaign → creative)
2. `backend/app/tools/tests/test_linkedin_ads.py` — 6 tests for `activate_linkedin()`

---

## 1. linkedin_ads.py

### Credentials

Two env vars required:

| Var | Purpose |
|-----|---------|
| `LINKEDIN_ACCESS_TOKEN` | OAuth Bearer token (managed externally, no refresh) |
| `LINKEDIN_ACCOUNT_ID` | Numeric ad account ID — wrapped as `urn:li:sponsoredAccount:{id}` |

### Token helper

```python
def _get_access_token(token: Optional[str] = None) -> str:
    t = token or os.getenv("LINKEDIN_ACCESS_TOKEN", "")
    if not t:
        raise RuntimeError("LINKEDIN_ACCESS_TOKEN must be set or access_token must be provided")
    return t
```

Accepts explicit `token` arg (for backward compat) — falls back to env var. Raises `RuntimeError` if both missing; caught by outer `except` and returned as `status: "failed"`.

### API headers (all 3 calls)

```python
{
    "Authorization": f"Bearer {token}",
    "Content-Type": "application/json",
    "LinkedIn-Version": "202401",
    "X-Restli-Protocol-Version": "2.0.0"
}
```

### Base URL

`https://api.linkedin.com/rest`

### 3-Call Flow

**Call 1 — Campaign Group** (`POST /rest/adCampaignGroups`)

Payload:
```json
{
  "name": "<activation name> - Group",
  "status": "ACTIVE",
  "account": "urn:li:sponsoredAccount:{account_id}"
}
```

Response: `id` (numeric) → `campaign_group_id`

**Call 2 — Campaign** (`POST /rest/adCampaigns`)

Payload:
```json
{
  "name": "<activation name>",
  "status": "ACTIVE",
  "type": "SPONSORED_UPDATE",
  "campaignGroup": "urn:li:adCampaignGroup:{campaign_group_id}",
  "costType": "CPM",
  "dailyBudget": {
    "amount": "<cost_estimated>",
    "currencyCode": "USD"
  },
  "targetingCriteria": {
    "include": {
      "and": [
        {"seniorities": "<platform_config.seniority>"},
        {"jobFunctions": "<platform_config.job_title>"},
        {"industries": "<platform_config.industries>"},
        {"locations": "<platform_config.locations or ['US']>"}
      ]
    }
  }
}
```

Response: `id` → `campaign_id` (returned in final dict)

**Call 3 — Creative** (`POST /rest/adCreatives`)

Payload:
```json
{
  "campaign": "urn:li:adCampaign:{campaign_id}",
  "status": "ACTIVE",
  "content": {
    "contentReference": "<creative_url>"
  }
}
```

Response: `id` → `ad_id`

### Return value (unchanged)

```python
{
    "campaign_id": str | None,
    "ad_id": str | None,
    "status": "live" | "failed",
    "error": str | None
}
```

### Security fix

Replace f-string logger with structured format:
```python
logger.error("LinkedIn activation failed: %s: %s", type(e).__name__, str(e))
```

### Fallback behaviour

If `_get_access_token()` raises (missing token), the `except` block catches and returns `status: "failed"` — consistent with all other tools.

---

## 2. test_linkedin_ads.py

6 tests for `activate_linkedin()`:

| # | Test | Verifies |
|---|------|----------|
| 1 | `test_activate_linkedin_success` | 3-call mock → `campaign_id`, `ad_id`, `status=="live"`, `error is None` |
| 2 | `test_activate_linkedin_api_failure` | First call raises → `status=="failed"`, `campaign_id is None`, `ad_id is None` |
| 3 | `test_activate_linkedin_returns_required_fields` | All 4 fields present: `campaign_id`, `ad_id`, `status`, `error` |
| 4 | `test_activate_linkedin_missing_token_returns_failed` | `_get_access_token` raises `RuntimeError` → `status=="failed"` |
| 5 | `test_activate_linkedin_sends_auth_header` | `Authorization: Bearer <token>` on all 3 calls, `call_count == 3` |
| 6 | `test_activate_linkedin_token_param_overrides_env` | Explicit `access_token` arg takes precedence over env var |

Mock response shape: `{"id": 123456}` (numeric ID from LinkedIn REST API).

### Test dependencies

- `pytest`, `pytest-asyncio` (already present)
- `unittest.mock.patch`, `AsyncMock`
- No real LinkedIn credentials required

---

## Files Modified / Created

| File | Action |
|------|--------|
| `backend/app/tools/linkedin_ads.py` | Rewrite — env-var auth, 3-call flow, security log fix |
| `backend/app/tools/tests/test_linkedin_ads.py` | Create — 6 tests |

## Files Unchanged

| File | Reason |
|------|--------|
| `backend/app/tools/tests/test_google_ads.py` | Unrelated |
| `backend/app/tools/tests/test_google_analytics.py` | Unrelated |
| `backend/app/tools/tests/test_meta_ads.py` | Unrelated |
