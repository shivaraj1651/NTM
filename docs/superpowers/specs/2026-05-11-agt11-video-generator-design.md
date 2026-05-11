# TASK-016 AGT-11 Video Generator Agent — Design Spec

**Date:** 2026-05-11
**Task:** TASK-016
**Module scope:** `backend/app/agents/video_generator.py` + `backend/app/tools/runway.py`

---

## 1. Architecture

**Two files** following the AGT-09/AGT-10 pattern:

### `backend/app/tools/runway.py`
Two public async functions:
```python
async generate_video(prompt: str, image_url: str | None, duration: int) -> str
async get_video_status(job_id: str) -> dict
```
Uses `httpx.AsyncClient`. Routes to `image_to_video` endpoint when `image_url` is provided, `text_to_video` when `None`. Auth via `RUNWAY_API_KEY` from `os.getenv`. Raises `RuntimeError` on non-200 or missing key.

### `backend/app/agents/video_generator.py`
`VideoGeneratorAgent` plain async class (no LangGraph). Three methods:
```python
async generate(brief, storage_client=None, db_session=None) -> VideoGenerationOutput
async _poll_for_completion(job_id) -> str | None
async _persist(output, session)
```

**Pipeline per call:**
1. Submit via `runway.generate_video(prompt, image_url, duration)` — `MAX_RETRIES=2`, exponential backoff. Any failure after retries → `status="manual_production_required"`, return immediately.
2. `_poll_for_completion(job_id)` — `MAX_POLL_ATTEMPTS=10`, `POLL_INTERVAL_SECONDS=6`. Returns completion URL or `None`. `None` → `status="manual_production_required"`.
3. Download MP4 bytes from completion URL via `httpx.AsyncClient.get`.
4. Upload via `storage_client.upload(bytes, key) → url` if provided.
5. Persist `GeneratedVideo` row if `db_session` provided.

**Constants:**
```python
RUNWAY_MODEL          = "gen3a_turbo"
MAX_RETRIES           = 2
MAX_POLL_ATTEMPTS     = 10
POLL_INTERVAL_SECONDS = 6
```

---

## 2. Data Models

### 2.1 Input

```python
class VideoGenerationBrief(BaseModel):
    campaign_id: str
    tenant_id: str
    prompt: str                          # video scene description
    script_text: str                     # social video script (metadata)
    reference_image_url: str | None = None  # from AGT-09, drives image_to_video path
    duration_seconds: int = 5            # 5 or 10
    script_format: str = "social_video"
    campaign_theme: str = ""
```

### 2.2 Output

```python
class VideoGenerationOutput(BaseModel):
    campaign_id: str
    generation_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    tenant_id: str
    asset_url: str           # S3/MinIO URL; empty string if manual_production_required
    job_id: str              # Runway job ID; empty string if submit failed
    model_used: str          # "gen3a_turbo"
    duration_seconds: int
    status: str              # "completed" | "manual_production_required"
    script_format: str
    generated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
```

### 2.3 DB Model — `backend/app/models/video.py`

`GeneratedVideo` (SQLAlchemy, PostgreSQL). One row per generation:

| Column | Type | Notes |
|---|---|---|
| `id` | String (uuid4) | PK |
| `campaign_id` | String | indexed |
| `tenant_id` | String | indexed |
| `generation_id` | String | |
| `asset_url` | String | S3/MinIO URL or empty |
| `job_id` | String | Runway job ID |
| `model_used` | String | `"gen3a_turbo"` |
| `script_format` | String | `"social_video"` |
| `duration_seconds` | Float | |
| `status` | String | `"completed"` / `"manual_production_required"` |
| `created_at` | DateTime(tz) | |

Composite index: `(tenant_id, campaign_id)`.

---

## 3. Runway Tool

### API Endpoints

```python
RUNWAY_IMAGE_TO_VIDEO_URL = "https://api.dev.runwayml.com/v1/image_to_video"
RUNWAY_TEXT_TO_VIDEO_URL  = "https://api.dev.runwayml.com/v1/text_to_video"
RUNWAY_TASK_URL           = "https://api.dev.runwayml.com/v1/tasks/{job_id}"
```

### `generate_video` POST body
```json
{
  "model": "gen3a_turbo",
  "promptText": "<prompt>",
  "promptImage": "<image_url>",
  "duration": 5
}
```
`promptImage` omitted when `image_url is None`. Returns `response.json()["id"]` as `job_id`.

### `get_video_status` GET response shape
```json
{"status": "SUCCEEDED" | "FAILED" | "PENDING", "output": ["<url>"] | null}
```
Returns `{"status": "...", "url": "<url_or_None>"}`.

### Auth
Header: `Authorization: Bearer {RUNWAY_API_KEY}`

---

## 4. Error Handling

| Condition | Behaviour |
|---|---|
| `RUNWAY_API_KEY` missing | `RuntimeError` at call time |
| Non-200 on submit | `RuntimeError` with status + body |
| Submit fails after MAX_RETRIES | `status="manual_production_required"`, no raise |
| Poll returns `FAILED` | `status="manual_production_required"` |
| Poll timeout (10 attempts exhausted) | `status="manual_production_required"` |
| Download of completed video fails | Propagates — caller owns HTTP failures |
| `storage_client` raises | Propagates — caller owns upload failures |

---

## 5. Testing

**File:** `backend/tests/agents/test_video_generator.py`
**Target coverage:** ≥ 90%
**Mock pattern:**
- `patch("backend.app.agents.video_generator.runway.generate_video", new=AsyncMock(...))`
- `patch("backend.app.agents.video_generator.runway.get_video_status", new=AsyncMock(...))`
- `patch.object(agent, "_poll_for_completion", new=AsyncMock(...))` for timeout/failure tests
- Inject `FakeStorageClient` and `FakeSession`

| Class | Test | Verifies |
|---|---|---|
| `TestHappyPath` | `test_generate_returns_asset_url` | Runway completes, S3 URL returned |
| `TestHappyPath` | `test_generate_returns_video_generation_output` | Output type + fields correct |
| `TestHappyPath` | `test_storage_client_receives_mp4_bytes` | Upload called with bytes + correct key |
| `TestHappyPath` | `test_no_persist_without_db_session` | No error when `db_session=None` |
| `TestImageToVideo` | `test_image_url_passed_to_runway_tool` | `reference_image_url` forwarded |
| `TestImageToVideo` | `test_no_image_url_uses_text_to_video` | `None` image → text_to_video path |
| `TestPollBehavior` | `test_poll_timeout_returns_manual_status` | Timeout → `manual_production_required` |
| `TestPollBehavior` | `test_poll_failed_returns_manual_status` | `FAILED` status → `manual_production_required` |
| `TestFailureFallback` | `test_runway_unavailable_returns_manual_status` | RuntimeError on submit → no raise |
| `TestPersistence` | `test_persist_creates_db_record_with_tenant_id` | Row with correct `tenant_id` |
| `TestPersistence` | `test_persist_stores_job_id` | `job_id` written to DB |

---

## 6. Integration Points

| Upstream | What is consumed |
|---|---|
| AGT-08 `ScriptOutput` | Caller maps `script_text` → `VideoGenerationBrief.script_text` |
| AGT-09 `ImageGenerationOutput` | Caller maps `asset_url` → `VideoGenerationBrief.reference_image_url` (optional) |
| Runway ML Gen-3 REST API | `RUNWAY_API_KEY` env var |
| Injected `storage_client` | `upload(bytes, key) -> url` |
| SQLAlchemy async session | `session.add()` + `session.commit()` |

---

## 7. Out of Scope

- Streaming video generation
- Multiple takes per call
- Video editing or post-processing
- Audio track merging with AGT-10 output
- Celery task wrapping (agent is called synchronously; Celery integration is caller's responsibility)
