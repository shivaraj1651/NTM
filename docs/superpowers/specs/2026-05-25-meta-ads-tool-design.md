# Meta Ads Tool Design Spec

**Date:** 2026-05-25  
**Task:** TASK-017  
**Module:** `backend/app/tools/meta_ads.py`

---

## Goal

Rewrite `meta_ads.py` to expose 6 discrete async functions for the Meta Marketing API v21.0, fix the broken base URL and hardcoded token, and rewire `activate_meta` as a clean orchestrator that chains the 6 functions. Keep existing competitor-research functions (`lookup_meta_ads` and helpers) untouched.

---

## Scope

**In scope:**
- Fix `META_BASE` constant (`graph.instagram.com/v19.0` → `graph.facebook.com/v21.0`)
- Add `_get_access_token()` reading `META_SYSTEM_USER_TOKEN` env var
- Add 6 new async functions: `create_campaign`, `create_ad_set`, `create_ad`, `get_ad_insights`, `pause_ad`, `update_ad_budget`
- Rewrite `activate_meta` as orchestrator calling the 6 functions
- 11 tests in `backend/app/tools/tests/test_meta_ads.py`

**Out of scope:**
- `lookup_meta_ads`, `_parse_spend_range`, `_extract_placements`, `_extract_primary_audiences` — no changes
- OAuth2 flow (Meta uses long-lived System User Token, no refresh needed)
- Pagination handling for insights (single-page response only)

---

## Architecture

### Constants

```python
META_BASE = "https://graph.facebook.com/v21.0"
```

### Auth

```python
def _get_access_token() -> str:
    token = os.getenv("META_SYSTEM_USER_TOKEN", "")
    if not token:
        raise RuntimeError("META_SYSTEM_USER_TOKEN must be set")
    return token
```

System User Token is a long-lived token — no refresh cycle needed, unlike Google OAuth2.

### Env Vars

| Variable | Required By | Purpose |
|----------|-------------|---------|
| `META_SYSTEM_USER_TOKEN` | all functions | Bearer token |
| `META_AD_ACCOUNT_ID` | `create_ad_set`, `create_ad`, `activate_meta` | Ad account (`act_<id>`) |
| `META_PAGE_ID` | `create_ad` | Facebook Page ID for ad creative |

---

## 6 New Functions

### 1. `create_campaign`

```python
async def create_campaign(
    ad_account_id: str,
    name: str,
    objective: str,
    budget: float,       # daily budget in USD
    schedule: dict,      # {"start_time": unix_ts, "stop_time": unix_ts (optional)}
) -> str:               # returns campaign_id
```

**Endpoint:** `POST {META_BASE}/act_{ad_account_id}/campaigns`

**Request body:**
```json
{
  "name": "<name>",
  "objective": "<objective>",
  "status": "PAUSED",
  "daily_budget": "<int(budget * 100)>",
  "start_time": "<schedule.start_time>",
  "access_token": "<token>"
}
```

**Returns:** `data["id"]` (str)  
**Raises:** `httpx.HTTPStatusError` on API error, `RuntimeError` if token missing

Common `objective` values: `LINK_CLICKS`, `REACH`, `VIDEO_VIEWS`, `BRAND_AWARENESS`

---

### 2. `create_ad_set`

```python
async def create_ad_set(
    campaign_id: str,
    name: str,
    audience_spec: dict,   # {age_min, age_max, geo_locations, interests}
    placements: list[str], # ["FACEBOOK_FEED", "INSTAGRAM_FEED", ...]
    budget: float,         # daily budget in USD
) -> str:                  # returns ad_set_id
```

**Endpoint:** `POST {META_BASE}/act_{META_AD_ACCOUNT_ID}/adsets`

**Request body:**
```json
{
  "name": "<name>",
  "campaign_id": "<campaign_id>",
  "status": "PAUSED",
  "daily_budget": "<int(budget * 100)>",
  "billing_event": "IMPRESSIONS",
  "optimization_goal": "REACH",
  "targeting": {
    "age_min": "<audience_spec.age_min | 18>",
    "age_max": "<audience_spec.age_max | 65>",
    "geo_locations": "<audience_spec.geo_locations | {'countries': ['US']}>",
    "interests": "<audience_spec.interests | []>",
    "publisher_platforms": "<placements>"
  },
  "access_token": "<token>"
}
```

**Returns:** `data["id"]` (str)

---

### 3. `create_ad`

```python
async def create_ad(
    ad_set_id: str,
    creative_spec: dict,  # {image_hash, link, message, page_id (optional)}
    name: str,
) -> str:                 # returns ad_id
```

**Endpoint:** `POST {META_BASE}/act_{META_AD_ACCOUNT_ID}/ads`

**Request body:**
```json
{
  "name": "<name>",
  "adset_id": "<ad_set_id>",
  "status": "PAUSED",
  "creative": {
    "object_story_spec": {
      "page_id": "<creative_spec.page_id | META_PAGE_ID>",
      "link_data": {
        "image_hash": "<creative_spec.image_hash>",
        "link": "<creative_spec.link>",
        "message": "<creative_spec.message>"
      }
    }
  },
  "access_token": "<token>"
}
```

**Returns:** `data["id"]` (str)

---

### 4. `get_ad_insights`

```python
async def get_ad_insights(
    ad_id: str,
    date_range: dict,       # {"since": "YYYY-MM-DD", "until": "YYYY-MM-DD"}
    metrics_list: list[str], # ["impressions", "clicks", "spend", "reach", "ctr"]
) -> dict:                  # InsightsDict
```

**Endpoint:** `GET {META_BASE}/{ad_id}/insights`

**Query params:**
```
fields=<",".join(metrics_list)>
time_range={"since":"...","until":"..."}
access_token=<token>
```

**Returns:**
```json
{
  "ad_id": "<ad_id>",
  "date_range": {"since": "...", "until": "..."},
  "metrics": { "<metric>": "<value>", ... },
  "raw": [...]
}
```

---

### 5. `pause_ad`

```python
async def pause_ad(ad_id: str) -> bool:
```

**Endpoint:** `POST {META_BASE}/{ad_id}`

**Request body:** `{"status": "PAUSED", "access_token": "<token>"}`

**Returns:** `True` on success  
**Raises:** `httpx.HTTPStatusError` on failure

---

### 6. `update_ad_budget`

```python
async def update_ad_budget(ad_set_id: str, daily_budget: float) -> bool:
```

**Endpoint:** `POST {META_BASE}/{ad_set_id}`

**Request body:** `{"daily_budget": str(int(daily_budget * 100)), "access_token": "<token>"}`

**Returns:** `True` on success  
**Raises:** `httpx.HTTPStatusError` on failure

---

## `activate_meta` (Rewritten Orchestrator)

```python
async def activate_meta(
    activation: dict,
    platform_config: dict,
    creative_url: str,
    access_token: Optional[str] = None,
) -> dict:  # {campaign_id, ad_id, status, error}
```

**Logic:**
1. Read `META_AD_ACCOUNT_ID` from env
2. Build `audience_spec` from `platform_config`
3. Call `create_campaign` → campaign_id
4. Call `create_ad_set` → ad_set_id
5. Call `create_ad` → ad_id
6. Return `{campaign_id, ad_id, status: "live", error: None}`

**On any exception:** return `{campaign_id: None, ad_id: None, status: "failed", error: str(e)}`

Note: `access_token` param ignored (kept for signature compatibility) — token always comes from `META_SYSTEM_USER_TOKEN`.

---

## Tests (11 total)

**Keep (3 existing):**
- `test_activate_meta_success`
- `test_activate_meta_api_failure`
- `test_activate_meta_returns_required_fields`

**Add (8 new):**
- `test_create_campaign_success` — mocks POST, asserts campaign_id returned
- `test_create_campaign_raises_on_http_error` — mock raises HTTPStatusError
- `test_create_ad_set_success` — mocks POST, asserts ad_set_id returned
- `test_create_ad_success` — mocks POST, asserts ad_id returned
- `test_get_ad_insights_success` — mocks GET, asserts metrics dict returned
- `test_pause_ad_returns_true` — mocks POST, asserts True
- `test_update_ad_budget_returns_true` — mocks POST, asserts True
- `test_missing_token_raises` — no env var set, asserts RuntimeError

All tests use `unittest.mock.patch` + `AsyncMock` (matching linkedin pattern). No real HTTP calls.

---

## Error Handling Policy

| Layer | Behaviour |
|-------|-----------|
| `_get_access_token` | `RuntimeError` if env var missing |
| 6 new functions | Let `httpx.HTTPStatusError` propagate |
| `activate_meta` | `try/except Exception` → `{status: "failed", error: str(e)}` |
| `lookup_meta_ads` | Unchanged (internal try/except) |
