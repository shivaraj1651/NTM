# TASK-013 — AGT-08 Scriptwriter Agent

## Goal
Implement `backend/app/agents/scriptwriter.py` — a scriptwriter agent that takes a `CreativeBrief` from AGT-06 and generates production-ready scripts for TVC, radio, and social video formats.

## Input
`CreativeBrief` from AGT-06 specifying:
- `script_format`: `"tvc"` | `"radio"` | `"social_video"`
- `campaign_theme`, `tone_board`, `message_architecture`, `audience_segmentation`
- `selected_concept` (from AGT-03)

## Output

### TVC Script
- Scene-by-scene breakdown: scene description, dialogue, VO, SFX, duration (seconds)
- Director's Note
- Talent type suggestions
- Location type suggestions
- Wardrobe notes
- Music/score direction
- Total estimated duration

### Radio Script
- Line-by-line: VO text, SFX cues, music direction, timing marks
- Director's Note
- Total estimated duration (seconds)

### Social Video Script
- Platform-specific format (TikTok / Instagram Reels / YouTube Shorts)
- Hook (0–3s), Content (3–25s), CTA (25–30s)
- On-screen text overlays
- Director's Note
- Estimated duration

## Technical Requirements
- LLM: `claude-sonnet-4-20250514`, `max_tokens=4000`, `temperature=0.7`
- Single file: `backend/app/agents/scriptwriter.py`
- Pydantic v2 models for all I/O: `ScriptScene`, `TVCScript`, `RadioScript`, `SocialVideoScript`, `ScriptOutput`
- No LangGraph — plain async class `ScriptwriterAgent`
- `generate(brief) -> ScriptOutput` — dispatches to format-specific method
- `MAX_RETRIES = 3`, exponential backoff on API failure
- Structured JSON output via system prompt instruction

## DB Model
New SQLAlchemy model `GeneratedScript` in `backend/app/models/script.py`:
- `id`, `campaign_id`, `tenant_id` (indexed), `generation_id`, `script_format`, `content` (JSONB), `production_brief` (Text), `model_used`, `created_at`

## Tests
File: `backend/tests/agents/test_scriptwriter.py`
Target coverage: ≥90%

| Test | Verifies |
|---|---|
| `test_generate_tvc_returns_scenes` | TVC output has `scenes` list with correct fields |
| `test_generate_radio_returns_lines` | Radio output has `lines` list with timing marks |
| `test_generate_social_video_returns_sections` | Social video has hook/content/cta |
| `test_output_has_directors_note` | All formats include director's note |
| `test_output_has_production_brief` | `production_brief` markdown present |
| `test_retry_on_api_failure` | Retries up to MAX_RETRIES, then raises |
| `test_retry_succeeds_on_third_attempt` | Returns output when 3rd attempt succeeds |
| `test_persist_creates_db_record` | `GeneratedScript` row saved with tenant_id |
| `test_invalid_format_raises` | `ValueError` for unknown `script_format` |

## Acceptance Criteria
- [x] All tests pass (`pytest backend/tests/agents/test_scriptwriter.py`)
- [x] Coverage ≥ 90%
- [x] `ScriptOutput` round-trips through Pydantic `.model_dump()` cleanly
- [x] `tenant_id` present on every DB write
