# TASK-013 AGT-08 Scriptwriter Agent — Design Spec

**Date:** 2026-05-11
**Task:** TASK-013
**Module scope:** `backend/app/agents/scriptwriter.py` + `backend/app/models/script.py`

---

## 1. Architecture

**Single file:** `backend/app/agents/scriptwriter.py`

`ScriptwriterAgent` class with one public method:

```
generate(brief: ScriptwriterBrief, db_session=None) -> ScriptOutput
```

Dispatches on `brief.script_format` to one of three private methods. Each method makes **one** `_call_with_retry()` call and parses the full response:

| Format | Private method | LLM call returns |
|---|---|---|
| `"tvc"` | `_generate_tvc(brief)` | 30s script + 15s script |
| `"radio"` | `_generate_radio(brief)` | 60s script + 30s script |
| `"social_video"` | `_generate_social_video(brief)` | TikTok + Reels + YouTube Shorts |

After dispatch, `_build_production_brief(output)` assembles markdown **programmatically** from the structured fields already present in the output — no additional LLM call.

`_call_with_retry()` uses `MAX_RETRIES=3` with exponential backoff (`2^attempt` seconds), identical to AGT-07.

**Constants:**
```python
MODEL = "claude-sonnet-4-20250514"
TEMPERATURE = 0.7
MAX_TOKENS = 4000
MAX_RETRIES = 3
```

---

## 2. Data Models

### 2.1 Input

```python
class ScriptwriterBrief(BaseModel):
    campaign_id: str
    tenant_id: str
    script_format: Literal["tvc", "radio", "social_video"]
    core_concept: str
    campaign_theme: str
    tone_adjectives: list[str]
    visual_direction: str
    brand_voice: str
    target_audience: str
    product_details: str
    primary_cta: str
    messaging_rules: list[str]
```

### 2.2 Format-specific script models

```python
class TVCScene(BaseModel):
    scene_number: int
    description: str        # what the viewer sees
    dialogue: str | None
    vo: str | None          # voiceover text
    sfx: str | None
    duration_seconds: int

class TVCScript(BaseModel):
    duration_label: str     # "30s" | "15s"
    total_duration_seconds: int
    scenes: list[TVCScene]
    directors_note: str
    talent_suggestions: list[str]
    location_suggestions: list[str]
    wardrobe_notes: str
    music_direction: str

class RadioLine(BaseModel):
    line_number: int
    vo_text: str | None
    sfx_cue: str | None
    music_direction: str | None
    timing_mark_seconds: float

class RadioScript(BaseModel):
    duration_label: str     # "60s" | "30s"
    total_duration_seconds: int
    lines: list[RadioLine]
    directors_note: str
    music_direction: str

class SocialVideoScript(BaseModel):
    platform: Literal["tiktok", "reels", "youtube_shorts"]
    hook: str               # 0–3s
    content: str            # 3–25s
    cta: str                # 25–30s
    on_screen_text: list[str]
    directors_note: str
    estimated_duration_seconds: int
```

### 2.3 Output

```python
class ScriptOutput(BaseModel):
    campaign_id: str
    generation_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    tenant_id: str
    script_format: str
    generated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    tvc_scripts: list[TVCScript] | None = None          # 2 items when format=tvc
    radio_scripts: list[RadioScript] | None = None      # 2 items when format=radio
    social_video_scripts: list[SocialVideoScript] | None = None  # 3 items when format=social_video
    production_brief: str                               # markdown, assembled programmatically
    model_used: str = MODEL
    errors: list[str] = Field(default_factory=list)
```

### 2.4 DB model — `backend/app/models/script.py`

`GeneratedScript` (SQLAlchemy, PostgreSQL). One row per variant/platform:

| Column | Type | Notes |
|---|---|---|
| `id` | String (uuid4) | PK |
| `campaign_id` | String | indexed |
| `tenant_id` | String | indexed |
| `generation_id` | String | groups variants from one call |
| `script_format` | String | `"tvc"` / `"radio"` / `"social_video"` |
| `variant_label` | String | `"30s"`, `"15s"`, `"60s"`, `"tiktok"`, `"reels"`, `"youtube_shorts"` |
| `content` | JSONB | full script dict |
| `production_brief` | Text | same value on all rows from one generation |
| `model_used` | String | |
| `created_at` | DateTime(tz) | |

Unique constraint: `(campaign_id, generation_id, script_format, variant_label)`.
Composite index: `(tenant_id, campaign_id)`.

**Row counts per call:**
- TVC → 2 rows (`"30s"`, `"15s"`)
- Radio → 2 rows (`"60s"`, `"30s"`)
- Social video → 3 rows (`"tiktok"`, `"reels"`, `"youtube_shorts"`)

---

## 3. Prompting Strategy

### 3.1 System prompt (shared)

```
You are a world-class scriptwriter for advertising.

## Brand Voice
{brand_voice}

## Tone Board
Adjectives: {tone_adjectives_csv}
Visual Direction: {visual_direction}

## Campaign Context
Theme: {campaign_theme}
Core Concept: {core_concept}
Product/Service: {product_details}
Target Audience: {target_audience}
Primary CTA: {primary_cta}

## Messaging Rules (MUST follow ALL)
{messaging_rules_bulleted}

Return ONLY valid JSON — no markdown fences, no commentary.
```

### 3.2 Per-format user messages

Each user message defines the exact expected JSON shape.

**TVC:**
```
Generate a TVC script in TWO durations: 30 seconds and 15 seconds.
Return JSON:
{
  "tvc_scripts": [
    {
      "duration_label": "30s",
      "total_duration_seconds": 30,
      "scenes": [{"scene_number":1,"description":"...","dialogue":null,"vo":"...","sfx":null,"duration_seconds":5}],
      "directors_note": "...",
      "talent_suggestions": ["..."],
      "location_suggestions": ["..."],
      "wardrobe_notes": "...",
      "music_direction": "..."
    },
    { "duration_label": "15s", ... }
  ]
}
```

**Radio:**
```
Generate a radio script in TWO durations: 60 seconds and 30 seconds.
Return JSON:
{
  "radio_scripts": [
    {
      "duration_label": "60s",
      "total_duration_seconds": 60,
      "lines": [{"line_number":1,"vo_text":"...","sfx_cue":null,"music_direction":null,"timing_mark_seconds":0.0}],
      "directors_note": "...",
      "music_direction": "..."
    },
    { "duration_label": "30s", ... }
  ]
}
```

**Social Video:**
```
Generate social video scripts for THREE platforms: TikTok, Instagram Reels, YouTube Shorts.
Return JSON:
{
  "social_video_scripts": [
    {
      "platform": "tiktok",
      "hook": "...",
      "content": "...",
      "cta": "...",
      "on_screen_text": ["..."],
      "directors_note": "...",
      "estimated_duration_seconds": 30
    },
    { "platform": "reels", ... },
    { "platform": "youtube_shorts", ... }
  ]
}
```

### 3.3 Production Brief assembly (`_build_production_brief`)

Pulls from the **primary variant** (30s for TVC, 60s for radio, TikTok for social video):

```markdown
# Production Brief — {campaign_theme}

## Format
{SCRIPT_FORMAT} — {variant_labels}

## Director's Note
{directors_note}

## Talent                        ← TVC only
{talent_suggestions as bullets}

## Locations                     ← TVC only
{location_suggestions as bullets}

## Wardrobe                      ← TVC only
{wardrobe_notes}

## Music & Score
{music_direction}

## On-Screen Text                ← social video only
{on_screen_text as bullets}
```

Radio omits Talent, Locations, Wardrobe, and On-Screen Text sections.

---

## 4. Error Handling

| Condition | Behaviour |
|---|---|
| API failure (any exception) | Retry up to `MAX_RETRIES=3` with `2^attempt`s backoff; re-raise on final failure |
| JSON parse error | Caught, logged, re-raised as `ValueError` |
| Unknown `script_format` | Immediate `ValueError("Unknown script_format: ...")` before any API call |
| Missing required brief fields | Pydantic `ValidationError` at construction time |

---

## 5. Testing

**File:** `backend/tests/agents/test_scriptwriter.py`
**Target coverage:** ≥ 90%
**Mock pattern:** `AsyncMock` client routed by format keyword in user message (same approach as AGT-07).

| Test | Verifies |
|---|---|
| `test_generate_tvc_returns_two_durations` | `tvc_scripts` has 30s and 15s variants |
| `test_tvc_scenes_have_required_fields` | Each scene has `description`, `duration_seconds` |
| `test_generate_radio_returns_two_durations` | `radio_scripts` has 60s and 30s variants |
| `test_radio_lines_have_timing_marks` | Each line has `timing_mark_seconds` |
| `test_generate_social_video_returns_three_platforms` | `social_video_scripts` has tiktok, reels, youtube_shorts |
| `test_social_video_has_hook_content_cta` | Each platform script has all three sections |
| `test_all_formats_have_directors_note` | `directors_note` non-empty for all formats |
| `test_production_brief_is_markdown` | `production_brief` starts with `# Production Brief` |
| `test_retry_exhausted_raises` | 3 failures → exception propagates |
| `test_retry_succeeds_on_third_attempt` | 2 failures then success → returns output |
| `test_invalid_format_raises_value_error` | `ValueError` for unknown format, no API call made |
| `test_persist_creates_rows_per_variant` | TVC→2 rows, radio→2 rows, social→3 rows, all with `tenant_id` |

---

## 6. Integration Points

| Upstream | What is consumed |
|---|---|
| AGT-06 `CreativeDirectorOutput` | Caller maps fields to `ScriptwriterBrief` |
| Anthropic SDK `AsyncAnthropic` | `client.messages.create()` |
| SQLAlchemy async session | `session.add()` + `session.commit()` |

AGT-08 does not call any other agent. It is invoked by the campaign service or a future router endpoint.

---

## 7. Out of Scope

- LangGraph orchestration
- Streaming responses
- Multiple simultaneous format generation in one call
- Script editing / refinement loop
- AGT-09 image or AGT-10 audio integration
