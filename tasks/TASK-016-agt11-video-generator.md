# TASK-016 — AGT-11 Video Generator Agent (Runway ML)

## Goal
Implement `backend/app/agents/video_generator.py` and `backend/app/tools/runway.py` — a video generator agent that takes a social video script from AGT-08 and an optional reference image from AGT-09, calls Runway ML Gen-3 API to generate an MP4, polls for completion, uploads to S3/MinIO, and returns the asset URL.

## Input
`VideoGenerationBrief`:
- `campaign_id`, `tenant_id`
- `script_text`: social video script from AGT-08
- `prompt`: text description of the video scene/action
- `reference_image_url`: optional URL of image from AGT-09 (image-to-video)
- `duration_seconds`: target video duration (5 or 10 seconds)
- `script_format`: `"social_video"` (metadata)
- `campaign_theme`: for prompt enrichment

## Output
`VideoGenerationOutput`:
- `asset_url`: S3/MinIO URL of the uploaded MP4
- `job_id`: Runway job ID
- `model_used`: e.g. `"gen3a_turbo"`
- `duration_seconds`: actual video duration
- `status`: `"completed"` | `"manual_production_required"`
- `campaign_id`, `tenant_id`, `generation_id`

## Technical Requirements

### Tool — `backend/app/tools/runway.py`
- `async generate_video(prompt: str, image_url: str | None, duration: int) -> str` — submits job, returns `job_id`
- `async get_video_status(job_id: str) -> dict` — polls status: `{"status": "...", "url": "..."|None}`
- Uses `RUNWAY_API_KEY` from `os.getenv`
- HTTP via `httpx.AsyncClient`
- Raises `RuntimeError` on non-200 or missing key

### Agent — `backend/app/agents/video_generator.py`
- `VideoGeneratorAgent` plain async class (no LangGraph)
- `generate(brief: VideoGenerationBrief, storage_client=None, db_session=None) -> VideoGenerationOutput`
- Submit job → poll `get_video_status` with `MAX_POLL_ATTEMPTS=10`, `POLL_INTERVAL_SECONDS=6`
- If Runway unavailable (RuntimeError on submit): set `status="manual_production_required"`, return output with empty `asset_url` — do NOT raise
- On poll timeout: set `status="manual_production_required"`
- Upload MP4 via injected `storage_client.upload(bytes, key) -> url`
- `MAX_RETRIES = 2` on submit, exponential backoff

### Runway API
- Submit: `POST https://api.dev.runwayml.com/v1/image_to_video` (or `text_to_video` if no image)
- Poll: `GET https://api.dev.runwayml.com/v1/tasks/{job_id}`
- Auth header: `Authorization: Bearer {RUNWAY_API_KEY}`
- Model: `"gen3a_turbo"`

## DB Model
New SQLAlchemy model `GeneratedVideo` in `backend/app/models/video.py`:
- `id`, `campaign_id`, `tenant_id` (indexed), `generation_id`, `asset_url`, `job_id`, `model_used`, `script_format`, `duration_seconds` (Float), `status`, `created_at`

## Tests
File: `backend/tests/agents/test_video_generator.py`
Target coverage: ≥ 90%

| Test | Verifies |
|---|---|
| `test_generate_returns_asset_url` | Happy path: Runway completes, URL returned |
| `test_generate_returns_video_generation_output` | Output type + fields correct |
| `test_storage_client_receives_mp4_bytes` | Upload called with video bytes + correct key |
| `test_no_persist_without_db_session` | No error when `db_session=None` |
| `test_runway_unavailable_returns_manual_status` | RuntimeError on submit → `status="manual_production_required"`, no raise |
| `test_poll_timeout_returns_manual_status` | Poll never completes → `status="manual_production_required"` |
| `test_image_url_passed_to_runway_tool` | `reference_image_url` forwarded to `generate_video` |
| `test_no_image_url_uses_text_to_video` | `None` image → text-to-video path |
| `test_retry_on_submit_failure` | Retries MAX_RETRIES then sets manual status |
| `test_persist_creates_db_record_with_tenant_id` | `GeneratedVideo` row with correct `tenant_id` |
| `test_persist_stores_job_id` | `job_id` written to DB |

## Acceptance Criteria
- [ ] All tests pass
- [ ] Coverage ≥ 90%
- [ ] `tenant_id` on every DB write
- [ ] `RUNWAY_API_KEY` never hard-coded
- [ ] Runway failure → `manual_production_required` status, never a crash
