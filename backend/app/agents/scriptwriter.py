"""Scriptwriter Agent (AGT-08).

Receives a ScriptwriterBrief and generates production-ready scripts for TVC,
radio, and social video formats via a single Claude API call per format.
"""

import asyncio
import json
import logging
from backend.app.agents.json_parsing import extract_json
import uuid
from datetime import datetime, timezone
from typing import Literal, Optional

from anthropic import AsyncAnthropic
from pydantic import BaseModel, Field
from backend.app.external.stubs import stub_enabled

logger = logging.getLogger(__name__)

MODEL = "claude-sonnet-4-6"
TEMPERATURE = 0.7
MAX_TOKENS = 4000
MAX_RETRIES = 3


# ---------------------------------------------------------------------------
# Input model
# ---------------------------------------------------------------------------

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


# ---------------------------------------------------------------------------
# Format-specific script models
# ---------------------------------------------------------------------------

class TVCScene(BaseModel):
    scene_number: int
    description: str
    dialogue: Optional[str] = None
    vo: Optional[str] = None
    sfx: Optional[str] = None
    duration_seconds: int


class TVCScript(BaseModel):
    duration_label: str
    total_duration_seconds: int
    scenes: list[TVCScene]
    directors_note: str
    talent_suggestions: list[str] = Field(default_factory=list)
    location_suggestions: list[str] = Field(default_factory=list)
    wardrobe_notes: str = ""
    music_direction: str = ""


class RadioLine(BaseModel):
    line_number: int
    vo_text: Optional[str] = None
    sfx_cue: Optional[str] = None
    music_direction: Optional[str] = None
    timing_mark_seconds: float


class RadioScript(BaseModel):
    duration_label: str
    total_duration_seconds: int
    lines: list[RadioLine]
    directors_note: str
    music_direction: str = ""


class SocialVideoScript(BaseModel):
    platform: Literal["tiktok", "reels", "youtube_shorts"]
    hook: str
    content: str
    cta: str
    on_screen_text: list[str] = Field(default_factory=list)
    directors_note: str
    estimated_duration_seconds: int


# ---------------------------------------------------------------------------
# Output model
# ---------------------------------------------------------------------------

class ScriptOutput(BaseModel):
    campaign_id: str
    generation_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    tenant_id: str
    script_format: str
    generated_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )
    tvc_scripts: Optional[list[TVCScript]] = None
    radio_scripts: Optional[list[RadioScript]] = None
    social_video_scripts: Optional[list[SocialVideoScript]] = None
    production_brief: str = ""
    model_used: str = MODEL
    errors: list[str] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Agent
# ---------------------------------------------------------------------------

class ScriptwriterAgent:
    """Generates production-ready scripts for TVC, radio, and social video."""

    def __init__(self, api_key: Optional[str] = None):
        self.client = AsyncAnthropic(api_key=api_key)
        self.model = MODEL

    async def generate(
        self, brief: ScriptwriterBrief, db_session=None
    ) -> ScriptOutput:
        if brief.script_format not in ("tvc", "radio", "social_video"):
            raise ValueError(f"Unknown script_format: {brief.script_format!r}")

        generation_id = str(uuid.uuid4())
        system_prompt = self._build_system_prompt(brief)

        output = ScriptOutput(
            campaign_id=brief.campaign_id,
            generation_id=generation_id,
            tenant_id=brief.tenant_id,
            script_format=brief.script_format,
        )

        if brief.script_format == "tvc":
            output = await self._generate_tvc(brief, system_prompt, output)
        elif brief.script_format == "radio":
            output = await self._generate_radio(brief, system_prompt, output)
        else:
            output = await self._generate_social_video(brief, system_prompt, output)

        output.production_brief = self._build_production_brief(output)

        if db_session is not None:
            await self._persist(output, db_session)

        return output

    # ------------------------------------------------------------------
    # Format generators
    # ------------------------------------------------------------------

    async def _generate_tvc(
        self, brief: ScriptwriterBrief, system_prompt: str, output: ScriptOutput
    ) -> ScriptOutput:
        user_message = f"""Generate a TVC script in TWO durations: 30 seconds and 15 seconds.

Primary CTA: {brief.primary_cta}

Return ONLY valid JSON (no markdown fences):
{{
  "tvc_scripts": [
    {{
      "duration_label": "30s",
      "total_duration_seconds": 30,
      "scenes": [
        {{
          "scene_number": 1,
          "description": "...",
          "dialogue": null,
          "vo": "...",
          "sfx": null,
          "duration_seconds": 10
        }}
      ],
      "directors_note": "...",
      "talent_suggestions": ["..."],
      "location_suggestions": ["..."],
      "wardrobe_notes": "...",
      "music_direction": "..."
    }},
    {{
      "duration_label": "15s",
      "total_duration_seconds": 15,
      "scenes": [...],
      "directors_note": "...",
      "talent_suggestions": [...],
      "location_suggestions": [...],
      "wardrobe_notes": "...",
      "music_direction": "..."
    }}
  ]
}}"""
        raw = await self._call_with_retry(system_prompt, user_message)
        output.tvc_scripts = [TVCScript(**s) for s in raw.get("tvc_scripts", [])]
        return output

    async def _generate_radio(
        self, brief: ScriptwriterBrief, system_prompt: str, output: ScriptOutput
    ) -> ScriptOutput:
        user_message = f"""Generate a radio script in TWO durations: 60 seconds and 30 seconds.

Primary CTA: {brief.primary_cta}

Return ONLY valid JSON (no markdown fences):
{{
  "radio_scripts": [
    {{
      "duration_label": "60s",
      "total_duration_seconds": 60,
      "lines": [
        {{
          "line_number": 1,
          "vo_text": "...",
          "sfx_cue": null,
          "music_direction": "...",
          "timing_mark_seconds": 0.0
        }}
      ],
      "directors_note": "...",
      "music_direction": "..."
    }},
    {{
      "duration_label": "30s",
      "total_duration_seconds": 30,
      "lines": [...],
      "directors_note": "...",
      "music_direction": "..."
    }}
  ]
}}"""
        raw = await self._call_with_retry(system_prompt, user_message)
        output.radio_scripts = [RadioScript(**s) for s in raw.get("radio_scripts", [])]
        return output

    async def _generate_social_video(
        self, brief: ScriptwriterBrief, system_prompt: str, output: ScriptOutput
    ) -> ScriptOutput:
        user_message = f"""Generate social video scripts for THREE platforms: TikTok, Instagram Reels, YouTube Shorts.

Primary CTA: {brief.primary_cta}

Return ONLY valid JSON (no markdown fences):
{{
  "social_video_scripts": [
    {{
      "platform": "tiktok",
      "hook": "...",
      "content": "...",
      "cta": "...",
      "on_screen_text": ["..."],
      "directors_note": "...",
      "estimated_duration_seconds": 30
    }},
    {{
      "platform": "reels",
      ...
    }},
    {{
      "platform": "youtube_shorts",
      ...
    }}
  ]
}}"""
        raw = await self._call_with_retry(system_prompt, user_message)
        output.social_video_scripts = [
            SocialVideoScript(**s) for s in raw.get("social_video_scripts", [])
        ]
        return output

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _build_system_prompt(self, brief: ScriptwriterBrief) -> str:
        rules = "\n".join(f"- {r}" for r in brief.messaging_rules)
        adjectives = ", ".join(brief.tone_adjectives)
        return f"""You are a world-class scriptwriter for advertising.

## Brand Voice
{brief.brand_voice}

## Tone Board
Adjectives: {adjectives}
Visual Direction: {brief.visual_direction}

## Campaign Context
Theme: {brief.campaign_theme}
Core Concept: {brief.core_concept}
Product/Service: {brief.product_details}
Target Audience: {brief.target_audience}

## Messaging Rules (MUST follow ALL)
{rules}

Return ONLY valid JSON — no markdown fences, no commentary."""

    def _build_production_brief(self, output: ScriptOutput) -> str:
        fmt = output.script_format.upper().replace("_", " ")
        lines = [f"# Production Brief — {output.campaign_id}", "", f"## Format", f"{fmt}"]

        if output.tvc_scripts:
            primary = output.tvc_scripts[0]
            labels = " + ".join(s.duration_label for s in output.tvc_scripts)
            lines[3] = f"TVC — {labels}"
            lines += [
                "",
                "## Director's Note",
                primary.directors_note,
            ]
            if primary.talent_suggestions:
                lines += ["", "## Talent"]
                lines += [f"- {t}" for t in primary.talent_suggestions]
            if primary.location_suggestions:
                lines += ["", "## Locations"]
                lines += [f"- {l}" for l in primary.location_suggestions]
            if primary.wardrobe_notes:
                lines += ["", "## Wardrobe", primary.wardrobe_notes]
            if primary.music_direction:
                lines += ["", "## Music & Score", primary.music_direction]

        elif output.radio_scripts:
            primary = output.radio_scripts[0]
            labels = " + ".join(s.duration_label for s in output.radio_scripts)
            lines[3] = f"RADIO — {labels}"
            lines += [
                "",
                "## Director's Note",
                primary.directors_note,
                "",
                "## Music & Score",
                primary.music_direction,
            ]

        elif output.social_video_scripts:
            platforms = " + ".join(s.platform for s in output.social_video_scripts)
            lines[3] = f"SOCIAL VIDEO — {platforms}"
            primary = next(
                s for s in output.social_video_scripts if s.platform == "tiktok"
            )
            lines += [
                "",
                "## Director's Note",
                primary.directors_note,
            ]
            all_text: list[str] = []
            for s in output.social_video_scripts:
                all_text.extend(s.on_screen_text)
            if all_text:
                lines += ["", "## On-Screen Text"]
                lines += [f"- {t}" for t in all_text]

        return "\n".join(lines)

    async def _call_with_retry(self, system_prompt: str, user_message: str) -> dict:
        # NTM_STUB_EXTERNAL: stubbed external call
        if stub_enabled():
            logger.info("Scriptwriter LLM stubbed (NTM_STUB_EXTERNAL)")
            return {"scenes": [{"scene_number": 1, "action": "Stub action.", "dialogue": "Stub dialogue.", "duration": "5s"}]}
        last_exc: Optional[Exception] = None
        for attempt in range(MAX_RETRIES):
            try:
                response = await self.client.messages.create(
                    model=self.model,
                    max_tokens=MAX_TOKENS,
                    temperature=TEMPERATURE,
                    system=system_prompt,
                    messages=[{"role": "user", "content": user_message}],
                )
                return extract_json(response.content[0].text)
            except Exception as exc:
                last_exc = exc
                if attempt < MAX_RETRIES - 1:
                    wait = 2 ** attempt
                    logger.warning(
                        "Attempt %d/%d failed (%s), retrying in %ds",
                        attempt + 1,
                        MAX_RETRIES,
                        exc,
                        wait,
                    )
                    await asyncio.sleep(wait)
        raise last_exc or Exception("API call failed after retries")

    async def _persist(self, output: ScriptOutput, session) -> None:
        from backend.app.models.script import GeneratedScript

        if output.tvc_scripts:
            for script in output.tvc_scripts:
                row = GeneratedScript(
                    campaign_id=output.campaign_id,
                    tenant_id=output.tenant_id,
                    generation_id=output.generation_id,
                    script_format=output.script_format,
                    variant_label=script.duration_label,
                    content=script.model_dump(mode="json"),
                    production_brief=output.production_brief,
                    model_used=output.model_used,
                )
                session.add(row)

        elif output.radio_scripts:
            for script in output.radio_scripts:
                row = GeneratedScript(
                    campaign_id=output.campaign_id,
                    tenant_id=output.tenant_id,
                    generation_id=output.generation_id,
                    script_format=output.script_format,
                    variant_label=script.duration_label,
                    content=script.model_dump(mode="json"),
                    production_brief=output.production_brief,
                    model_used=output.model_used,
                )
                session.add(row)

        elif output.social_video_scripts:
            for script in output.social_video_scripts:
                row = GeneratedScript(
                    campaign_id=output.campaign_id,
                    tenant_id=output.tenant_id,
                    generation_id=output.generation_id,
                    script_format=output.script_format,
                    variant_label=script.platform,
                    content=script.model_dump(mode="json"),
                    production_brief=output.production_brief,
                    model_used=output.model_used,
                )
                session.add(row)

        await session.commit()
