# TASK-014 AGT-09 Image Generator Agent — Design Spec

**Date:** 2026-05-11
**Task:** TASK-014
**Module scope:** `backend/app/agents/image_generator.py` + `backend/app/tools/stability_ai.py`

---

## 1. Architecture

**Two files:**

### `backend/app/tools/stability_ai.py`
Thin async tool with one public function:
```
async generate_image(prompt, width, height, steps=30, cfg_scale=7.0) -> bytes
```
Uses `httpx.AsyncClient.post()` to the Stability AI SDXL REST endpoint. `STABILITY_AI_API_KEY` read from `os.getenv`. Returns raw PNG bytes. Raises `RuntimeError` on non-200 or missing artifact.

### `backend/app/agents/image_generator.py`
`ImageGeneratorAgent` plain async class (no LangGraph):

```
generate(brief: ImageGenerationBrief, storage_client=None, db_session=None) -> ImageGenerationOutput
```

**Pipeline per call:**
1. `_build_prompt(brief)` — assembles base template, then one Claude Haiku call to enrich with T2I style keywords. Returns `prompt_used` string.
2. Look up `(width, height)` from `IMAGE_DIMENSIONS[brief.image_format]`.
3. **Primary:** call `stability_ai.generate_image(prompt, w, h)` with `MAX_RETRIES=2` (exponential backoff). On success → `storage_client.upload(bytes, key) -> url`.
4. **Fallback:** if Stability exhausts retries → call DALL-E 3 via `openai.AsyncOpenAI` with same prompt, `MAX_RETRIES=2`.
5. If both fail → `raise RuntimeError("All image generation providers failed")`.
6. Optionally persist `GeneratedImage` row via `db_session`.

`storage_client` is duck-typed: `upload(data: bytes, key: str) -> str`. Injected by caller — real boto3 wrapper in production, mock in tests. Same pattern as `db_session` in AGT-07/08.

**Constants:**
```python
HAIKU_MODEL = "claude-haiku-4-5-20251001"
DALLE_MODEL = "dall-e-3"
STABILITY_MODEL = "stability-sdxl"
MAX_RETRIES = 2
STABILITY_API_URL = "https://api.stability.ai/v1/generation/stable-diffusion-xl-1024-v1-0/text-to-image"
```

---

## 2. Data Models

### 2.1 Input

```python
class ImageGenerationBrief(BaseModel):
    campaign_id: str
    tenant_id: str
    image_format: Literal["square", "landscape", "portrait"]
    visual_direction: str
    brand_palette: list[str]     # hex codes or colour names
    tone_adjectives: list[str]
    campaign_theme: str
    style_notes: str = ""        # optional free text
```

### 2.2 Dimensions lookup

```python
IMAGE_DIMENSIONS: dict[str, tuple[int, int]] = {
    "square":    (1024, 1024),
    "landscape": (1344, 768),
    "portrait":  (768, 1344),
}
```

### 2.3 Output

```python
class ImageGenerationOutput(BaseModel):
    campaign_id: str
    generation_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    tenant_id: str
    asset_url: str
    prompt_used: str
    model_used: Literal["stability-sdxl", "dall-e-3"]
    generation_params: dict      # width, height, steps, cfg_scale, seed
    image_format: str
    generated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
```

### 2.4 DB model — `backend/app/models/image.py`

`GeneratedImage` (SQLAlchemy, PostgreSQL). One row per generation:

| Column | Type | Notes |
|---|---|---|
| `id` | String (uuid4) | PK |
| `campaign_id` | String | indexed |
| `tenant_id` | String | indexed |
| `generation_id` | String | |
| `asset_url` | String | S3/MinIO URL |
| `prompt_used` | Text | enriched prompt |
| `model_used` | String | `"stability-sdxl"` / `"dall-e-3"` |
| `generation_params` | JSONB | width, height, steps, cfg_scale, seed |
| `image_format` | String | `"square"` / `"landscape"` / `"portrait"` |
| `created_at` | DateTime(tz) | |

Composite index: `(tenant_id, campaign_id)`.

---

## 3. Prompt Builder & Stability AI Tool

### 3.1 `_build_prompt(brief)` — hybrid approach

**Step 1 — programmatic base template:**
```
{visual_direction}. Brand palette: {brand_palette_csv}.
Tone: {tone_adjectives_csv}. {style_notes}
```

**Step 2 — Claude Haiku enrichment (one call):**
```
System: "You are a text-to-image prompt engineer. Take the base description
and add precise photographic/artistic style tokens: lighting type, camera
angle, texture quality, render style, aspect ratio hint. Return ONLY the
enriched prompt string, no explanation, under 200 words."

User: {base_template}
```

If Haiku call fails for any reason: log warning, fall back to base template. No retry on this call.

### 3.2 `stability_ai.py` tool

```python
async def generate_image(
    prompt: str,
    width: int = 1024,
    height: int = 1024,
    steps: int = 30,
    cfg_scale: float = 7.0,
) -> bytes:
```

- `Authorization: Bearer {STABILITY_AI_API_KEY}` header
- POST JSON: `{"text_prompts": [{"text": prompt, "weight": 1}], "width": w, "height": h, "steps": steps, "cfg_scale": cfg_scale}`
- Response: JSON `artifacts[0].base64` → `base64.b64decode()` → bytes
- Raises `RuntimeError` on non-200 or empty artifacts

### 3.3 DALL-E 3 fallback (inside agent)

```python
client = openai.AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))
response = await client.images.generate(
    model="dall-e-3",
    prompt=prompt,
    size=f"{width}x{height}",
    response_format="b64_json",
)
```

Decodes `response.data[0].b64_json` → bytes.

---

## 4. Error Handling

| Condition | Behaviour |
|---|---|
| Stability non-200 | `RuntimeError` with status + message |
| Stability retries exhausted (2) | Fall through to DALL-E 3 |
| DALL-E retries exhausted (2) | `raise RuntimeError("All image generation providers failed")` |
| Haiku prompt enrichment fails | Log warning, use base template — no crash |
| `storage_client` raises | Propagates — caller owns upload failure |
| Unknown `image_format` | `ValueError` before any API call |
| Missing `STABILITY_AI_API_KEY` | `RuntimeError` at call time (not import time) |

---

## 5. Testing

**File:** `backend/tests/agents/test_image_generator.py`
**Target coverage:** ≥ 90%
**Mock pattern:** mock `stability_ai.generate_image` at module level via `patch`; mock `openai.AsyncOpenAI`; inject `FakeStorageClient` and `FakeSession`.

| Test | Verifies |
|---|---|
| `test_generate_returns_asset_url` | Happy path: Stability succeeds, URL returned |
| `test_prompt_contains_visual_direction` | `prompt_used` includes `visual_direction` text |
| `test_prompt_enrichment_fails_gracefully` | Haiku failure → base template used, no crash |
| `test_fallback_to_dalle_on_stability_failure` | Stability raises → DALL-E called, succeeds |
| `test_model_used_stability_on_success` | `model_used == "stability-sdxl"` |
| `test_model_used_dalle_on_fallback` | `model_used == "dall-e-3"` when fallback used |
| `test_square_format_dimensions` | `generation_params` has `width=1024, height=1024` |
| `test_landscape_format_dimensions` | `width=1344, height=768` |
| `test_portrait_format_dimensions` | `width=768, height=1344` |
| `test_both_providers_fail_raises` | `RuntimeError` when Stability + DALL-E both fail |
| `test_invalid_format_raises_value_error` | `ValueError` for unknown format, no API call |
| `test_persist_creates_db_record_with_tenant_id` | `GeneratedImage` saved with `tenant_id` |
| `test_storage_client_upload_called_with_bytes` | Storage client receives PNG bytes |

---

## 6. Integration Points

| Upstream | What is consumed |
|---|---|
| AGT-06 `CreativeDirectorOutput` | Caller maps `visual_direction`, `tone`, palette to `ImageGenerationBrief` |
| Stability AI SDXL REST API | `STABILITY_API_URL` + `STABILITY_AI_API_KEY` env var |
| OpenAI DALL-E 3 | `OPENAI_API_KEY` env var (fallback only) |
| Claude Haiku | `ANTHROPIC_API_KEY` (prompt enrichment) |
| Injected `storage_client` | `upload(bytes, key) -> url` |
| SQLAlchemy async session | `session.add()` + `session.commit()` |

---

## 7. Out of Scope

- Image resizing or post-processing
- Multiple images per call (single image per `generate()` call)
- Image variation / img2img
- CDN invalidation
- Rate limiting / quota management
- AGT-10 audio integration
