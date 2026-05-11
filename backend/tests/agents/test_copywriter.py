"""Tests for Copywriter Agent (AGT-07)."""

import asyncio
import json
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from backend.app.agents.copywriter import (
    ASSET_CONFIGS,
    CopyOutput,
    CopyVariant,
    CopywriterAgent,
    CreativeBrief,
)


@pytest.fixture
def sample_brief():
    return CreativeBrief(
        campaign_id="camp-001",
        tenant_id="tenant-001",
        core_concept="Empower professionals to work smarter with AI",
        tone_adjectives=["bold", "innovative", "trustworthy", "energetic", "inclusive"],
        visual_direction="Clean whites with electric blue accents",
        brand_voice="professional yet approachable",
        campaign_theme="Work Smarter",
        primary_cta="Get Started Free",
        target_audience="B2B professionals aged 25-45",
        product_details="AI-powered productivity platform",
        messaging_rules=["Always mention 'AI-powered'", "Never use superlatives"],
    )


def _mock_response_for(asset_type: str) -> dict:
    """Build a valid mock Claude response for the given asset_type."""
    config = ASSET_CONFIGS[asset_type]
    variants = []
    for vid in ("A", "B"):
        content = {f: f"Sample {f} text {vid}" for f in config.content_fields}
        variants.append({"variant_id": vid, "content": content, "rationale": f"Rationale {vid}"})
    return {"variants": variants}


def _make_client(asset_type_override: str | None = None):
    """Return a mock AsyncAnthropic client that routes responses by asset type."""
    client = MagicMock()

    async def mock_create(**kwargs):
        user_msg = kwargs["messages"][0]["content"]
        matched = asset_type_override
        if matched is None:
            for atype in ASSET_CONFIGS:
                if atype.upper().replace("_", " ") in user_msg:
                    matched = atype
                    break
            if matched is None:
                matched = "headline"
        response = MagicMock()
        response.content = [MagicMock(text=json.dumps(_mock_response_for(matched)))]
        return response

    client.messages.create = mock_create
    return client


@pytest.fixture
def agent():
    a = CopywriterAgent()
    a.client = _make_client()
    return a


# ---------------------------------------------------------------------------
# Structure tests
# ---------------------------------------------------------------------------

class TestOutputStructure:

    async def test_generate_returns_7_assets(self, agent, sample_brief):
        output = await agent.generate(sample_brief)
        assert len(output.assets) == 7

    async def test_generate_returns_all_asset_types(self, agent, sample_brief):
        output = await agent.generate(sample_brief)
        returned_types = {a.asset_type for a in output.assets}
        assert returned_types == set(ASSET_CONFIGS.keys())

    async def test_each_asset_has_2_variants(self, agent, sample_brief):
        output = await agent.generate(sample_brief)
        for asset in output.assets:
            assert len(asset.variants) == 2, f"{asset.asset_type} must have 2 variants"
            ids = {v.variant_id for v in asset.variants}
            assert ids == {"A", "B"}

    async def test_output_carries_campaign_and_tenant(self, agent, sample_brief):
        output = await agent.generate(sample_brief)
        assert output.campaign_id == "camp-001"
        assert output.tenant_id == "tenant-001"


# ---------------------------------------------------------------------------
# Per-asset content field tests
# ---------------------------------------------------------------------------

class TestAssetContentFields:

    async def test_social_caption_has_text_field(self, agent, sample_brief):
        output = await agent.generate(sample_brief)
        asset = next(a for a in output.assets if a.asset_type == "social_caption")
        for v in asset.variants:
            assert "text" in v.content

    async def test_headline_has_text_field(self, agent, sample_brief):
        output = await agent.generate(sample_brief)
        asset = next(a for a in output.assets if a.asset_type == "headline")
        for v in asset.variants:
            assert "text" in v.content

    async def test_body_copy_has_text_field(self, agent, sample_brief):
        output = await agent.generate(sample_brief)
        asset = next(a for a in output.assets if a.asset_type == "body_copy")
        for v in asset.variants:
            assert "text" in v.content

    async def test_print_ad_has_all_subfields(self, agent, sample_brief):
        output = await agent.generate(sample_brief)
        asset = next(a for a in output.assets if a.asset_type == "print_ad")
        for v in asset.variants:
            for field in ("headline", "subhead", "body", "cta"):
                assert field in v.content, f"print_ad missing field: {field}"

    async def test_email_has_subject_and_body(self, agent, sample_brief):
        output = await agent.generate(sample_brief)
        asset = next(a for a in output.assets if a.asset_type == "email")
        for v in asset.variants:
            assert "subject" in v.content
            assert "body" in v.content

    async def test_ooh_billboard_has_headline_and_visual_note(self, agent, sample_brief):
        output = await agent.generate(sample_brief)
        asset = next(a for a in output.assets if a.asset_type == "ooh_billboard")
        for v in asset.variants:
            assert "headline" in v.content
            assert "visual_note" in v.content

    async def test_influencer_brief_has_required_fields(self, agent, sample_brief):
        output = await agent.generate(sample_brief)
        asset = next(a for a in output.assets if a.asset_type == "influencer_brief")
        for v in asset.variants:
            for field in ("key_message", "talking_points", "dos", "donts"):
                assert field in v.content, f"influencer_brief missing field: {field}"


# ---------------------------------------------------------------------------
# Prompt content tests
# ---------------------------------------------------------------------------

class TestPromptContent:

    async def test_messaging_rules_in_system_prompt(self, agent, sample_brief):
        captured = []
        orig = agent._call_with_retry

        async def spy(system_prompt, user_message):
            captured.append(system_prompt)
            return await orig(system_prompt, user_message)

        agent._call_with_retry = spy
        await agent.generate(sample_brief)

        assert captured
        for prompt in captured:
            assert "Always mention 'AI-powered'" in prompt
            assert "Never use superlatives" in prompt

    async def test_tone_adjectives_in_system_prompt(self, agent, sample_brief):
        captured = []
        orig = agent._call_with_retry

        async def spy(system_prompt, user_message):
            captured.append(system_prompt)
            return await orig(system_prompt, user_message)

        agent._call_with_retry = spy
        await agent.generate(sample_brief)

        assert captured
        for prompt in captured:
            for adj in sample_brief.tone_adjectives:
                assert adj in prompt

    async def test_ooh_billboard_prompt_mentions_7_word_constraint(self, agent, sample_brief):
        captured_user_msgs = {}
        orig = agent._call_with_retry

        async def spy(system_prompt, user_message):
            # Identify asset type from user_message header
            for atype in ASSET_CONFIGS:
                if atype.upper().replace("_", " ") in user_message:
                    captured_user_msgs[atype] = user_message
            return await orig(system_prompt, user_message)

        agent._call_with_retry = spy
        await agent.generate(sample_brief)

        assert "ooh_billboard" in captured_user_msgs
        assert "7" in captured_user_msgs["ooh_billboard"]


# ---------------------------------------------------------------------------
# Retry / error handling tests
# ---------------------------------------------------------------------------

class TestRetryBehavior:

    async def test_json_parse_failure_retries_up_to_3_times(self, sample_brief):
        call_count = 0
        target_asset = "headline"

        async def flaky_create(**kwargs):
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                resp = MagicMock()
                resp.content = [MagicMock(text="not valid json {{")]
                return resp
            resp = MagicMock()
            resp.content = [MagicMock(text=json.dumps(_mock_response_for(target_asset)))]
            return resp

        agent = CopywriterAgent()
        agent.client = MagicMock()
        agent.client.messages.create = flaky_create

        system_prompt = agent._build_system_prompt(sample_brief)
        result = await agent._generate_asset(target_asset, sample_brief, system_prompt)

        assert call_count == 3
        assert len(result.variants) == 2

    async def test_all_retries_exhausted_does_not_raise(self, sample_brief):
        async def always_invalid(**kwargs):
            resp = MagicMock()
            resp.content = [MagicMock(text="not json")]
            return resp

        agent = CopywriterAgent()
        agent.client = MagicMock()
        agent.client.messages.create = always_invalid

        output = await agent.generate(sample_brief)

        assert len(output.errors) > 0
        failed_types = {e.split(":")[0] for e in output.errors}
        for asset in output.assets:
            if asset.asset_type in failed_types:
                assert asset.variants == []


# ---------------------------------------------------------------------------
# DB persistence test
# ---------------------------------------------------------------------------

class TestPersistence:

    async def test_db_persist_stores_rows_with_tenant_id(self, agent, sample_brief):
        persisted = []

        class FakeSession:
            def add(self, row):
                persisted.append(row)

            async def commit(self):
                pass

        output = await agent.generate(sample_brief, db_session=FakeSession())

        assert len(persisted) > 0
        for row in persisted:
            assert row.tenant_id == "tenant-001"
            assert row.campaign_id == "camp-001"

    async def test_db_persist_creates_14_rows(self, agent, sample_brief):
        persisted = []

        class FakeSession:
            def add(self, row):
                persisted.append(row)

            async def commit(self):
                pass

        await agent.generate(sample_brief, db_session=FakeSession())
        assert len(persisted) == 14  # 7 asset types × 2 variants


# ---------------------------------------------------------------------------
# Concurrency test
# ---------------------------------------------------------------------------

class TestConcurrency:

    async def test_all_7_asset_types_generated(self, agent, sample_brief):
        generated_types = []
        orig = agent._generate_asset

        async def tracking(asset_type, brief, system_prompt):
            generated_types.append(asset_type)
            return await orig(asset_type, brief, system_prompt)

        agent._generate_asset = tracking
        await agent.generate(sample_brief)

        assert set(generated_types) == set(ASSET_CONFIGS.keys())
        assert len(generated_types) == 7
