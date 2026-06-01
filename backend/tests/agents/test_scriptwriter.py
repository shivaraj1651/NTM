"""Tests for Scriptwriter Agent (AGT-08)."""

import json
from unittest.mock import MagicMock

import pytest

from backend.app.agents.scriptwriter import (
    ScriptwriterAgent,
    ScriptwriterBrief,
)

# ---------------------------------------------------------------------------
# Helpers & fixtures
# ---------------------------------------------------------------------------

def _tvc_response() -> dict:
    return {
        "tvc_scripts": [
            {
                "duration_label": "30s",
                "total_duration_seconds": 30,
                "scenes": [
                    {
                        "scene_number": 1,
                        "description": "Opening wide shot of a busy office",
                        "dialogue": None,
                        "vo": "Are you ready to work smarter?",
                        "sfx": None,
                        "duration_seconds": 10,
                    },
                    {
                        "scene_number": 2,
                        "description": "Close-up of hands on keyboard",
                        "dialogue": None,
                        "vo": "Introducing your AI partner.",
                        "sfx": "keyboard click",
                        "duration_seconds": 20,
                    },
                ],
                "directors_note": "Keep energy high throughout",
                "talent_suggestions": ["Young professional aged 28-35"],
                "location_suggestions": ["Modern open-plan office"],
                "wardrobe_notes": "Business casual, neutral tones",
                "music_direction": "Upbeat electronic, 120 BPM",
            },
            {
                "duration_label": "15s",
                "total_duration_seconds": 15,
                "scenes": [
                    {
                        "scene_number": 1,
                        "description": "Quick product UI reveal",
                        "dialogue": None,
                        "vo": "Work smarter. Get started free.",
                        "sfx": None,
                        "duration_seconds": 15,
                    },
                ],
                "directors_note": "Fast paced, logo hold at end",
                "talent_suggestions": ["Young professional aged 28-35"],
                "location_suggestions": ["Modern office"],
                "wardrobe_notes": "Business casual",
                "music_direction": "Same track, shorter edit",
            },
        ]
    }


def _radio_response() -> dict:
    return {
        "radio_scripts": [
            {
                "duration_label": "60s",
                "total_duration_seconds": 60,
                "lines": [
                    {
                        "line_number": 1,
                        "vo_text": "Are you tired of wasting hours on repetitive tasks?",
                        "sfx_cue": None,
                        "music_direction": "Fade in softly under VO",
                        "timing_mark_seconds": 0.0,
                    },
                    {
                        "line_number": 2,
                        "vo_text": "Introducing the AI-powered platform that professionals trust.",
                        "sfx_cue": "subtle chime",
                        "music_direction": None,
                        "timing_mark_seconds": 6.0,
                    },
                ],
                "directors_note": "Warm conversational tone, no rush",
                "music_direction": "Soft corporate jazz throughout",
            },
            {
                "duration_label": "30s",
                "total_duration_seconds": 30,
                "lines": [
                    {
                        "line_number": 1,
                        "vo_text": "Work smarter with AI. Get started free today.",
                        "sfx_cue": None,
                        "music_direction": "Upbeat opener",
                        "timing_mark_seconds": 0.0,
                    },
                ],
                "directors_note": "Punchy and direct",
                "music_direction": "Upbeat electronic",
            },
        ]
    }


def _social_video_response() -> dict:
    return {
        "social_video_scripts": [
            {
                "platform": "tiktok",
                "hook": "Stop scrolling — this will save you 3 hours a day",
                "content": "Here's exactly how AI can automate your busywork in under 60 seconds...",
                "cta": "Try it free — link in bio",
                "on_screen_text": ["3 hours saved daily", "AI-powered", "Try FREE"],
                "directors_note": "Fast cuts, trending audio, text overlay on each beat",
                "estimated_duration_seconds": 30,
            },
            {
                "platform": "reels",
                "hook": "Work smarter not harder",
                "content": "See how top professionals are using AI to reclaim their time...",
                "cta": "Get started free",
                "on_screen_text": ["AI-powered productivity", "Free trial"],
                "directors_note": "Clean aesthetic, minimal text overlays",
                "estimated_duration_seconds": 30,
            },
            {
                "platform": "youtube_shorts",
                "hook": "The future of work is already here",
                "content": "Discover how this AI platform transforms how you work every single day...",
                "cta": "Subscribe for more productivity tips",
                "on_screen_text": ["AI Platform", "Start Free Today"],
                "directors_note": "Educational tone, slightly longer pacing",
                "estimated_duration_seconds": 60,
            },
        ]
    }


def _make_client():
    """Mock AsyncAnthropic client that routes responses by script format keyword."""
    client = MagicMock()

    async def mock_create(**kwargs):
        user_msg = kwargs["messages"][0]["content"].lower()
        if "tvc" in user_msg:
            payload = _tvc_response()
        elif "radio" in user_msg:
            payload = _radio_response()
        else:
            payload = _social_video_response()
        response = MagicMock()
        response.content = [MagicMock(text=json.dumps(payload))]
        return response

    client.messages.create = mock_create
    return client


@pytest.fixture
def brief_tvc():
    return ScriptwriterBrief(
        campaign_id="camp-001",
        tenant_id="tenant-001",
        script_format="tvc",
        core_concept="Empower professionals with AI",
        campaign_theme="Work Smarter",
        tone_adjectives=["bold", "innovative", "trustworthy"],
        visual_direction="Clean whites with electric blue accents",
        brand_voice="Professional yet approachable",
        target_audience="B2B professionals aged 25-45",
        product_details="AI-powered productivity platform",
        primary_cta="Get Started Free",
        messaging_rules=["Always mention AI-powered", "Never use superlatives"],
    )


@pytest.fixture
def brief_radio(brief_tvc):
    return brief_tvc.model_copy(update={"script_format": "radio"})


@pytest.fixture
def brief_social(brief_tvc):
    return brief_tvc.model_copy(update={"script_format": "social_video"})


@pytest.fixture
def agent():
    a = ScriptwriterAgent()
    a.client = _make_client()
    return a


# ---------------------------------------------------------------------------
# TVC tests
# ---------------------------------------------------------------------------

class TestTVCOutput:

    async def test_generate_tvc_returns_two_durations(self, agent, brief_tvc):
        output = await agent.generate(brief_tvc)
        assert output.tvc_scripts is not None
        assert len(output.tvc_scripts) == 2
        labels = {s.duration_label for s in output.tvc_scripts}
        assert labels == {"30s", "15s"}

    async def test_tvc_scenes_have_required_fields(self, agent, brief_tvc):
        output = await agent.generate(brief_tvc)
        for script in output.tvc_scripts:
            for scene in script.scenes:
                assert scene.description
                assert scene.duration_seconds > 0

    async def test_tvc_script_has_directors_note(self, agent, brief_tvc):
        output = await agent.generate(brief_tvc)
        for script in output.tvc_scripts:
            assert script.directors_note

    async def test_tvc_output_fields_are_none_for_other_formats(self, agent, brief_tvc):
        output = await agent.generate(brief_tvc)
        assert output.radio_scripts is None
        assert output.social_video_scripts is None


# ---------------------------------------------------------------------------
# Radio tests
# ---------------------------------------------------------------------------

class TestRadioOutput:

    async def test_generate_radio_returns_two_durations(self, agent, brief_radio):
        output = await agent.generate(brief_radio)
        assert output.radio_scripts is not None
        assert len(output.radio_scripts) == 2
        labels = {s.duration_label for s in output.radio_scripts}
        assert labels == {"60s", "30s"}

    async def test_radio_lines_have_timing_marks(self, agent, brief_radio):
        output = await agent.generate(brief_radio)
        for script in output.radio_scripts:
            for line in script.lines:
                assert isinstance(line.timing_mark_seconds, float)

    async def test_radio_script_has_directors_note(self, agent, brief_radio):
        output = await agent.generate(brief_radio)
        for script in output.radio_scripts:
            assert script.directors_note

    async def test_radio_output_fields_are_none_for_other_formats(self, agent, brief_radio):
        output = await agent.generate(brief_radio)
        assert output.tvc_scripts is None
        assert output.social_video_scripts is None


# ---------------------------------------------------------------------------
# Social video tests
# ---------------------------------------------------------------------------

class TestSocialVideoOutput:

    async def test_generate_social_video_returns_three_platforms(self, agent, brief_social):
        output = await agent.generate(brief_social)
        assert output.social_video_scripts is not None
        assert len(output.social_video_scripts) == 3
        platforms = {s.platform for s in output.social_video_scripts}
        assert platforms == {"tiktok", "reels", "youtube_shorts"}

    async def test_social_video_has_hook_content_cta(self, agent, brief_social):
        output = await agent.generate(brief_social)
        for script in output.social_video_scripts:
            assert script.hook
            assert script.content
            assert script.cta

    async def test_social_video_has_directors_note(self, agent, brief_social):
        output = await agent.generate(brief_social)
        for script in output.social_video_scripts:
            assert script.directors_note

    async def test_social_output_fields_are_none_for_other_formats(self, agent, brief_social):
        output = await agent.generate(brief_social)
        assert output.tvc_scripts is None
        assert output.radio_scripts is None


# ---------------------------------------------------------------------------
# Production brief tests
# ---------------------------------------------------------------------------

class TestProductionBrief:

    async def test_tvc_production_brief_starts_with_header(self, agent, brief_tvc):
        output = await agent.generate(brief_tvc)
        assert output.production_brief.startswith("# Production Brief")

    async def test_radio_production_brief_starts_with_header(self, agent, brief_radio):
        output = await agent.generate(brief_radio)
        assert output.production_brief.startswith("# Production Brief")

    async def test_social_production_brief_starts_with_header(self, agent, brief_social):
        output = await agent.generate(brief_social)
        assert output.production_brief.startswith("# Production Brief")

    async def test_tvc_brief_contains_talent_and_location(self, agent, brief_tvc):
        output = await agent.generate(brief_tvc)
        assert "Talent" in output.production_brief
        assert "Location" in output.production_brief

    async def test_radio_brief_omits_talent_and_location(self, agent, brief_radio):
        output = await agent.generate(brief_radio)
        assert "Talent" not in output.production_brief
        assert "Location" not in output.production_brief

    async def test_social_brief_contains_on_screen_text(self, agent, brief_social):
        output = await agent.generate(brief_social)
        assert "On-Screen Text" in output.production_brief


# ---------------------------------------------------------------------------
# Retry / error handling tests
# ---------------------------------------------------------------------------

class TestRetryBehavior:

    async def test_retry_exhausted_raises(self, brief_tvc):
        call_count = 0

        async def always_fail(**kwargs):
            nonlocal call_count
            call_count += 1
            raise RuntimeError("API down")

        agent = ScriptwriterAgent()
        agent.client = MagicMock()
        agent.client.messages.create = always_fail

        with pytest.raises(RuntimeError, match="API down"):
            await agent.generate(brief_tvc)

        assert call_count == 3

    async def test_retry_succeeds_on_third_attempt(self, brief_tvc):
        call_count = 0

        async def flaky(**kwargs):
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise RuntimeError("transient failure")
            response = MagicMock()
            response.content = [MagicMock(text=json.dumps(_tvc_response()))]
            return response

        agent = ScriptwriterAgent()
        agent.client = MagicMock()
        agent.client.messages.create = flaky

        output = await agent.generate(brief_tvc)
        assert call_count == 3
        assert output.tvc_scripts is not None

    async def test_invalid_format_raises_value_error(self, brief_tvc):
        bad_brief = brief_tvc.model_copy(update={"script_format": "billboard"})
        agent = ScriptwriterAgent()
        agent.client = MagicMock()
        agent.client.messages.create = MagicMock()

        with pytest.raises(ValueError, match="Unknown script_format"):
            await agent.generate(bad_brief)

        agent.client.messages.create.assert_not_called()


# ---------------------------------------------------------------------------
# DB persistence tests
# ---------------------------------------------------------------------------

class TestPersistence:

    async def test_tvc_persist_creates_2_rows(self, agent, brief_tvc):
        persisted = []

        class FakeSession:
            def add(self, row):
                persisted.append(row)
            async def commit(self):
                pass

        await agent.generate(brief_tvc, db_session=FakeSession())
        assert len(persisted) == 2

    async def test_radio_persist_creates_2_rows(self, agent, brief_radio):
        persisted = []

        class FakeSession:
            def add(self, row):
                persisted.append(row)
            async def commit(self):
                pass

        await agent.generate(brief_radio, db_session=FakeSession())
        assert len(persisted) == 2

    async def test_social_persist_creates_3_rows(self, agent, brief_social):
        persisted = []

        class FakeSession:
            def add(self, row):
                persisted.append(row)
            async def commit(self):
                pass

        await agent.generate(brief_social, db_session=FakeSession())
        assert len(persisted) == 3

    async def test_persist_rows_have_tenant_id(self, agent, brief_tvc):
        persisted = []

        class FakeSession:
            def add(self, row):
                persisted.append(row)
            async def commit(self):
                pass

        await agent.generate(brief_tvc, db_session=FakeSession())
        for row in persisted:
            assert row.tenant_id == "tenant-001"
            assert row.campaign_id == "camp-001"
