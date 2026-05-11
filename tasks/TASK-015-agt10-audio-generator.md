# TASK-015 — AGT-10 Audio Generator Agent (ElevenLabs)

## Goal
Implement `backend/app/agents/audio_generator.py` and `backend/app/tools/elevenlabs.py` — an audio generator agent that takes a radio/VO script from AGT-08, selects an appropriate ElevenLabs voice based on the tone board, calls ElevenLabs TTS API, uploads the resulting MP3 to S3/MinIO, and returns the asset URL.

## Input
`AudioGenerationBrief` assembled from AGT-08 output:
- `campaign_id`, `tenant_id`
- `script_text`: the VO/radio script text to synthesise
- `tone_adjectives`: from AGT-08 brief (drives voice selection)
- `campaign_theme`
- `voice_style`: `"warm"` | `"authoritative"` | `"youthful"` (derived from tone board)
- `script_format`: `"radio"` | `"tvc_vo"` | `"social_video"` (for metadata only)

## Output
`AudioGenerationOutput`:
- `asset_url`: S3/MinIO URL of the uploaded MP3
- `voice_id`: ElevenLabs voice ID used
- `duration_seconds`: estimated from character count (approx 150 chars/sec)
- `model_used`: ElevenLabs model name (e.g. `"eleven_multilingual_v2"`)
- `campaign_id`, `tenant_id`, `generation_id`

## Technical Requirements

### Tool — `backend/app/tools/elevenlabs.py`
- `async generate_vo(script: str, voice_id: str, model: str = "eleven_multilingual_v2") -> bytes`
- Uses `ELEVENLABS_API_KEY` from `os.getenv`
- HTTP POST to ElevenLabs TTS REST endpoint
- Returns raw MP3 bytes
- Raises `RuntimeError` on non-200

### Agent — `backend/app/agents/audio_generator.py`
- `AudioGeneratorAgent` plain async class (no LangGraph)
- `generate(brief: AudioGenerationBrief, storage_client=None, db_session=None) -> AudioGenerationOutput`
- Voice selection: map `voice_style` → ElevenLabs `voice_id` via `VOICE_MAP` dict constant
- `MAX_RETRIES = 3`, exponential backoff on ElevenLabs failures
- Upload via injected `storage_client.upload(bytes, key) -> url` (same duck-type as AGT-09)

### Voice map
| `voice_style` | `voice_id` |
|---|---|
| `"warm"` | `"21m00Tcm4TlvDq8ikWAM"` (Rachel) |
| `"authoritative"` | `"ErXwobaYiN019PkySvjV"` (Antoni) |
| `"youthful"` | `"AZnzlk1XvdvUeBnXmlld"` (Domi) |

## DB Model
New SQLAlchemy model `GeneratedAudio` in `backend/app/models/audio.py`:
- `id`, `campaign_id`, `tenant_id` (indexed), `generation_id`, `asset_url`, `voice_id`, `model_used`, `script_format`, `duration_seconds` (Float), `created_at`

## Tests
File: `backend/tests/agents/test_audio_generator.py`
Target coverage: ≥ 90%

| Test | Verifies |
|---|---|
| `test_generate_returns_asset_url` | Happy path: ElevenLabs succeeds, URL returned |
| `test_warm_style_uses_rachel_voice` | `voice_id` matches Rachel for `voice_style="warm"` |
| `test_authoritative_style_uses_antoni_voice` | `voice_id` matches Antoni |
| `test_youthful_style_uses_domi_voice` | `voice_id` matches Domi |
| `test_invalid_voice_style_raises` | `ValueError` for unknown `voice_style` |
| `test_retry_on_elevenlabs_failure` | Retries up to MAX_RETRIES then raises |
| `test_retry_succeeds_on_third_attempt` | Returns output when 3rd attempt succeeds |
| `test_duration_seconds_estimated` | `duration_seconds > 0` |
| `test_persist_creates_db_record_with_tenant_id` | `GeneratedAudio` saved with `tenant_id` |
| `test_storage_client_receives_mp3_bytes` | Storage client called with audio bytes |
| `test_no_persist_without_db_session` | No error when `db_session=None` |

## Acceptance Criteria
- [ ] All tests pass
- [ ] Coverage ≥ 90%
- [ ] `tenant_id` on every DB write
- [ ] `ELEVENLABS_API_KEY` never hard-coded
