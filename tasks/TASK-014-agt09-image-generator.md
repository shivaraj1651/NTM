# TASK-014 — AGT-09 Image Generator Agent

## Goal
Implement `backend/app/agents/image_generator.py` and `backend/app/tools/stability_ai.py` — an image generator agent that takes a `CreativeBrief` from AGT-06, constructs an optimised text-to-image prompt, calls Stability AI SDXL (with DALL-E 3 fallback), uploads the result to S3/MinIO, and returns the asset URL.

## Input
`ImageGenerationBrief` assembled from AGT-06 output:
- `campaign_id`, `tenant_id`
- `visual_direction` (from AGT-06 `CoreConcept.visual_direction`)
- `brand_palette` (hex colours or colour names)
- `tone_adjectives` (from AGT-06 tone board)
- `campaign_theme`
- `image_format`: `"square"` | `"landscape"` | `"portrait"` (maps to dimensions)
- `style_notes` (optional free text)

## Output
`ImageGenerationOutput`:
- `asset_url`: S3/MinIO URL of the uploaded image
- `prompt_used`: the final text-to-image prompt sent to the model
- `model_used`: `"stability-sdxl"` | `"dall-e-3"`
- `generation_params`: dict (width, height, steps, cfg_scale, seed)
- `campaign_id`, `tenant_id`, `generation_id`

## Technical Requirements

### Tool — `backend/app/tools/stability_ai.py`
- `generate_image(prompt, width, height, steps, cfg_scale) -> bytes`
- Uses `STABILITY_AI_API_KEY` from environment / settings
- HTTP call to Stability AI SDXL endpoint
- Returns raw PNG bytes

### Agent — `backend/app/agents/image_generator.py`
- `ImageGeneratorAgent` plain async class (no LangGraph)
- `generate(brief: ImageGenerationBrief, storage_client=None) -> ImageGenerationOutput`
- Prompt builder: combines `visual_direction`, `brand_palette`, `tone_adjectives`, `style_notes` into a single optimised prompt string using Claude (`claude-haiku-4-5-20251001`, one call)
- Primary: call `stability_ai.generate_image()` → upload → return URL
- Fallback: if Stability raises, call DALL-E 3 via `openai.AsyncOpenAI`
- `MAX_RETRIES = 2` per provider before falling back
- Upload to S3/MinIO via `boto3` or `aiobotocore`; bucket from `IMAGE_BUCKET_NAME` env var

### Image dimensions
| `image_format` | width | height |
|---|---|---|
| `"square"` | 1024 | 1024 |
| `"landscape"` | 1344 | 768 |
| `"portrait"` | 768 | 1344 |

## DB Model
New SQLAlchemy model `GeneratedImage` in `backend/app/models/image.py`:
- `id`, `campaign_id`, `tenant_id` (indexed), `generation_id`, `asset_url`, `prompt_used`, `model_used`, `generation_params` (JSONB), `image_format`, `created_at`

## Tests
File: `backend/tests/agents/test_image_generator.py`
Target coverage: ≥ 90%
Mock: `stability_ai.generate_image`, `boto3`/aiobotocore upload, DALL-E client

| Test | Verifies |
|---|---|
| `test_generate_returns_asset_url` | Happy path: Stability succeeds, URL returned |
| `test_prompt_contains_visual_direction` | `prompt_used` includes `visual_direction` text |
| `test_prompt_contains_tone_adjectives` | `prompt_used` includes tone adjectives |
| `test_fallback_to_dalle_on_stability_failure` | Stability raises → DALL-E called |
| `test_model_used_is_stability_on_success` | `model_used == "stability-sdxl"` when primary succeeds |
| `test_model_used_is_dalle_on_fallback` | `model_used == "dall-e-3"` when fallback used |
| `test_square_format_uses_1024x1024` | `generation_params` has correct dimensions |
| `test_landscape_format_uses_1344x768` | Dimensions correct for landscape |
| `test_portrait_format_uses_768x1344` | Dimensions correct for portrait |
| `test_persist_creates_db_record_with_tenant_id` | `GeneratedImage` row saved with `tenant_id` |
| `test_both_providers_fail_raises` | `RuntimeError` when Stability + DALL-E both fail |

## Acceptance Criteria
- [x] All tests pass
- [x] Coverage ≥ 90%
- [x] `tenant_id` on every DB write
- [x] `STABILITY_AI_API_KEY` never hard-coded — always from env
