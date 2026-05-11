# TASK-015 AGT-10 Audio Generator Agent — Design Spec

**Date:** 2026-05-11
**Task:** TASK-015
**Module scope:** `backend/app/agents/audio_generator.py` + `backend/app/tools/elevenlabs.py`

---

## 1. Architecture

**Two files** following the AGT-09 pattern:

### `backend/app/tools/elevenlabs.py`
Thin async tool, one public function:
```
async generate_vo(script: str, voice_id: str, model: str = "eleven_multilingual_v2") -> bytes
```
Uses `httpx.AsyncClient.post()` to the ElevenLabs TTS REST endpoint. `ELEVENLABS_API_KEY` from `os.getenv`. Returns raw MP3 bytes. Raises `RuntimeError` on non-200 or missing key.

### `backend/app/agents/audio_generator.py`
`AudioGeneratorAgent` plain async class (no LangGraph):
```
generate(brief: AudioGenerationBrief, storage_client=None, db_session=None) -> AudioGenerationOutput
```

**Pipeline per call:**
1. `brief.voice_style` not in `VOICE_MAP` → `ValueError` immediately, no API call.
2. Look up `voice_id = VOICE_MAP[brief.voice_style]`.
3. Call `elevenlabs.generate_vo(brief.script_text, voice_id)` with `MAX_RETRIES=3`, exponential backoff (`2^attempt` seconds). Re-raises on exhaustion.
4. Estimate `duration_seconds = len(brief.script_text) / 150.0`.
5. Upload via `storage_client.upload(bytes, key) -> url` if provided.
6. Optionally persist `GeneratedAudio` row via `db_session`.

**Constants:**
```python
ELEVENLABS_MODEL = "eleven_multilingual_v2"
MAX_RETRIES = 3

VOICE_MAP = {
    "warm":          "21m00Tcm4TlvDq8ikWAM",  # Rachel
    "authoritative": "ErXwobaYiN019PkySvjV",  # Antoni
    "youthful":      "AZnzlk1XvdvUeBnXmlld",  # Domi
}
```

---

## 2. Data Models

### 2.1 Input

```python
class AudioGenerationBrief(BaseModel):
    campaign_id: str
    tenant_id: str
    script_text: str
    voice_style: str          # "warm" | "authoritative" | "youthful"
    script_format: str        # "radio" | "tvc_vo" | "social_video" (metadata only)
    campaign_theme: str = ""
```

### 2.2 Output

```python
class AudioGenerationOutput(BaseModel):
    campaign_id: str
    generation_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    tenant_id: str
    asset_url: str
    voice_id: str             # ElevenLabs voice ID used
    duration_seconds: float   # len(script_text) / 150.0
    model_used: str           # "eleven_multilingual_v2"
    script_format: str
    generated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
```

### 2.3 DB model — `backend/app/models/audio.py`

`GeneratedAudio` (SQLAlchemy, PostgreSQL). One row per generation:

| Column | Type | Notes |
|---|---|---|
| `id` | String (uuid4) | PK |
| `campaign_id` | String | indexed |
| `tenant_id` | String | indexed |
| `generation_id` | String | |
| `asset_url` | String | S3/MinIO URL |
| `voice_id` | String | ElevenLabs voice ID |
| `model_used` | String | `"eleven_multilingual_v2"` |
| `script_format` | String | `"radio"` / `"tvc_vo"` / `"social_video"` |
| `duration_seconds` | Float | estimated from char count |
| `created_at` | DateTime(tz) | |

Composite index: `(tenant_id, campaign_id)`.

---

## 3. ElevenLabs Tool

```python
ELEVENLABS_API_URL = "https://api.elevenlabs.io/v1/text-to-speech/{voice_id}"

async def generate_vo(script: str, voice_id: str, model: str = "eleven_multilingual_v2") -> bytes:
```

- Header: `xi-api-key: {ELEVENLABS_API_KEY}`
- POST JSON:
  ```json
  {
    "text": "<script>",
    "model_id": "<model>",
    "voice_settings": {"stability": 0.5, "similarity_boost": 0.75}
  }
  ```
- Returns `response.content` (raw MP3 bytes) on 200
- `RuntimeError("ELEVENLABS_API_KEY not set")` if key missing
- `RuntimeError(f"ElevenLabs returned {status}: {text}")` on non-200

---

## 4. Error Handling

| Condition | Behaviour |
|---|---|
| Unknown `voice_style` | `ValueError("Unknown voice_style: ...")` before any API call |
| ElevenLabs non-200 | `RuntimeError` with status + response body |
| Retries exhausted (3) | Re-raises last exception |
| Missing `ELEVENLABS_API_KEY` | `RuntimeError` at call time (not import time) |
| `storage_client` raises | Propagates — caller owns upload failure |

---

## 5. Testing

**File:** `backend/tests/agents/test_audio_generator.py`
**Target coverage:** ≥ 90%
**Mock pattern:** `patch("backend.app.agents.audio_generator.elevenlabs.generate_vo", new=AsyncMock(...))`; inject `FakeStorageClient` and `FakeSession`.

| Test | Verifies |
|---|---|
| `test_generate_returns_asset_url` | Happy path: ElevenLabs succeeds, URL returned |
| `test_warm_style_uses_rachel_voice` | `voice_id` == Rachel ID for `voice_style="warm"` |
| `test_authoritative_style_uses_antoni_voice` | `voice_id` == Antoni ID |
| `test_youthful_style_uses_domi_voice` | `voice_id` == Domi ID |
| `test_invalid_voice_style_raises` | `ValueError` before any API call |
| `test_retry_on_elevenlabs_failure` | Retries 3× then re-raises |
| `test_retry_succeeds_on_third_attempt` | 2 failures then success → returns output |
| `test_duration_seconds_estimated` | `duration_seconds == len(script_text) / 150.0` |
| `test_storage_client_receives_mp3_bytes` | Upload called with audio bytes |
| `test_persist_creates_db_record_with_tenant_id` | `GeneratedAudio` row with correct `tenant_id` |
| `test_no_persist_without_db_session` | No error when `db_session=None` |

---

## 6. Integration Points

| Upstream | What is consumed |
|---|---|
| AGT-08 `ScriptOutput` | Caller maps `script_text` + tone → `AudioGenerationBrief` |
| ElevenLabs TTS REST API | `ELEVENLABS_API_KEY` env var |
| Injected `storage_client` | `upload(bytes, key) -> url` |
| SQLAlchemy async session | `session.add()` + `session.commit()` |

---

## 7. Out of Scope

- Voice cloning or custom voice creation
- Streaming audio responses
- Multiple takes per call
- Audio post-processing (normalisation, compression)
- AGT-11 video integration
