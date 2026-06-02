# AGT-07 Copywriter Agent — Design Spec

**Date:** 2026-05-11  
**Task:** TASK-011  
**Module:** `backend/app/agents/copywriter.py`  
**DB model:** `backend/app/models/copy.py`

---

## 1. Purpose

AGT-07 receives a `CreativeBrief` (derived from AGT-06's output) and generates marketing copy for 7 asset types, producing 2 A/B variants per asset. Output is persisted to PostgreSQL with multi-tenant isolation.

---

## 2. Architecture

```
CreativeBrief (input)
    ↓
CopywriterAgent.generate(brief)
    ↓ asyncio.gather — 7 concurrent LLM calls
    ├── _generate_asset("social_caption", brief)
    ├── _generate_asset("headline", brief)
    ├── _generate_asset("body_copy", brief)
    ├── _generate_asset("print_ad", brief)
    ├── _generate_asset("email", brief)
    ├── _generate_asset("ooh_billboard", brief)
    └── _generate_asset("influencer_brief", brief)
    ↓
CopyOutput (output, persisted via GeneratedCopy rows)
```

**Single file** `copywriter.py` contains: data models, `ASSET_CONFIGS`, `CopywriterAgent` class.  
**Constants:**
- `MODEL = "claude-sonnet-4-20250514"`
- `TEMPERATURE = 0.8`
- `MAX_RETRIES = 3`, exponential backoff: `2^n` seconds

---

## 3. Data Models

### 3.1 Input — `CreativeBrief`

```python
class CreativeBrief(BaseModel):
    campaign_id: str
    tenant_id: str
    core_concept: str           # AGT-06 CoreConcept.message
    tone_adjectives: list[str]  # ToneBoard.adjectives (5 items)
    visual_direction: str       # ToneBoard.visual_direction
    brand_voice: str            # BrandGuidelines.tone
    campaign_theme: str
    primary_cta: str
    target_audience: str        # flattened description
    product_details: str
    messaging_rules: list[str]  # BrandGuidelines.messaging_rules
```

### 3.2 Output — `CopyOutput`

```python
class CopyVariant(BaseModel):
    variant_id: str             # "A" or "B"
    content: dict[str, str]     # {"text": "..."} or structured sub-fields
    word_count: int
    rationale: str

class AssetCopy(BaseModel):
    asset_type: str             # one of 7 types
    variants: list[CopyVariant] # always exactly 2

class CopyOutput(BaseModel):
    campaign_id: str
    generation_id: str          # uuid4
    tenant_id: str
    generated_at: datetime
    assets: list[AssetCopy]     # 7 items
    model_used: str
    errors: list[str]
```

### 3.3 DB — `GeneratedCopy` (`backend/app/models/copy.py`)

| Column | Type | Notes |
|---|---|---|
| `id` | String PK | uuid4 |
| `campaign_id` | String | indexed |
| `tenant_id` | String | indexed, required for all queries |
| `generation_id` | String | indexed |
| `asset_type` | String | e.g. `"social_caption"` |
| `variant_id` | String | `"A"` or `"B"` |
| `content` | JSONB | asset-specific sub-fields |
| `word_count` | Integer | |
| `model_used` | String | |
| `created_at` | DateTime(tz) | UTC |

Unique constraint: `(campaign_id, generation_id, asset_type, variant_id)`

---

## 4. Asset Configurations (`ASSET_CONFIGS`)

| asset_type | Constraints | `content` fields |
|---|---|---|
| `social_caption` | ≤280 chars, hashtags encouraged | `text` |
| `headline` | ≤10 words, punchy hook | `text` |
| `body_copy` | 50–150 words, benefit-led | `text` |
| `print_ad` | headline + subhead + body (≤50w) + CTA | `headline`, `subhead`, `body`, `cta` |
| `email` | subject ≤60 chars + body 100–200w | `subject`, `body` |
| `ooh_billboard` | **max 7 words** headline + visual hook note | `headline`, `visual_note` |
| `influencer_brief` | 3 talking-point bullets + do/don't | `key_message`, `talking_points`, `dos`, `donts` |

---

## 5. Prompting Strategy

**Two-message structure per call:**

**System prompt** (shared across all 7 calls, built once per `generate()` invocation):
- Copywriter persona
- Tone board: 5 adjectives + visual direction
- Brand voice
- Messaging rules (mandatory)
- Campaign theme + core concept

**User message** (per asset type):
- Asset type name and constraints from `ASSET_CONFIGS`
- Product details + target audience
- Primary CTA
- Instruction to return exactly 2 variants as JSON

**Claude response format:**
```json
{
  "variants": [
    {"variant_id": "A", "content": {...}, "rationale": "..."},
    {"variant_id": "B", "content": {...}, "rationale": "..."}
  ]
}
```

**Error handling:**
- `json.JSONDecodeError` → retry up to 3× with exponential backoff
- After 3 failures → `AssetCopy` with empty `variants`, error appended to `CopyOutput.errors`
- No exception propagated; caller always receives a `CopyOutput`

---

## 6. Generation Flow

```python
async def generate(self, brief: CreativeBrief) -> CopyOutput:
    system_prompt = self._build_system_prompt(brief)
    results = await asyncio.gather(
        *[self._generate_asset(asset_type, brief, system_prompt)
          for asset_type in ASSET_CONFIGS],
        return_exceptions=True
    )
    # collect AssetCopy objects + errors
    # persist all variants to DB (GeneratedCopy rows, all include tenant_id)
    # return CopyOutput
```

`_generate_asset()` calls `_call_claude_with_retry()` which mirrors AGT-06's retry pattern.

---

## 7. Testing

**File:** `backend/tests/agents/test_copywriter.py`  
**Target coverage:** ≥90%

| Test | What it verifies |
|---|---|
| `test_generate_returns_7_assets` | All 7 asset types in output |
| `test_each_asset_has_2_variants` | A + B for every asset |
| `test_ooh_billboard_max_7_words` | `word_count` ≤7 enforced |
| `test_social_caption_max_280_chars` | char constraint |
| `test_print_ad_has_all_subfields` | `headline`, `subhead`, `body`, `cta` present |
| `test_email_has_subject_and_body` | `subject` + `body` present |
| `test_influencer_brief_structure` | `key_message`, `talking_points`, `dos`, `donts` |
| `test_messaging_rules_in_system_prompt` | rules injected |
| `test_tone_adjectives_in_system_prompt` | tone board injected |
| `test_json_parse_failure_retries` | retry on `JSONDecodeError` (fail×2, succeed×1) |
| `test_all_retries_exhausted_logs_error` | error in `CopyOutput.errors`, no exception raised |
| `test_db_persist_called_with_tenant_id` | `GeneratedCopy` rows have correct `tenant_id` |
| `test_concurrent_generation` | `asyncio.gather` called with 7 coroutines |

---

## 8. Integration Points

| Upstream | Contract |
|---|---|
| AGT-06 `CreativeDirectorOutput` | Caller extracts `core_concept`, `tone_board`, `brand_guidelines` to build `CreativeBrief` |
| AGT-03 `CampaignConcept` | `ToneBoard` + `MessageArchitecture` available via `CampaignConcept.tone_board` |

AGT-07 does **not** call AGT-06 directly — the brief is assembled by the caller (router/orchestrator).

---

## 9. Out of Scope

- FastAPI router endpoint (separate task)
- Image/video generation (AGT-06 handles that)
- Copy validation/refinement loop (not required per spec)
- Streaming responses
