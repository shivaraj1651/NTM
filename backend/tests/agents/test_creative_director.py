"""Unit tests for CreativeDirectorAgent / creative_director_agent (AGT-06)."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from backend.app.agents.creative_director.models import (
    BrandGuidelines,
    CampaignInput,
    CoreConcept,
    CreativeDirectorOutput,
    PlatformCreatives,
    TargetAudience,
)
from backend.app.agents.creative_director_orchestrator import (
    CreativeDirectorAgent,
    creative_director_agent,
)


# ── fixtures ───────────────────────────────────────────────────────────────────

def make_campaign_input(**kwargs):
    defaults = dict(
        campaign_id="camp-001",
        tenant_id="tenant-001",
        objectives=["brand_awareness"],
        target_audience=TargetAudience(demographics={"age": "25-45"}),
        brand_guidelines=BrandGuidelines(
            tone="professional",
            colors=["#000", "#FFF"],
            messaging_rules=["Keep it simple"],
            mandatory_ctas=["Learn More"],
        ),
        platforms=["instagram"],
        product_details="AI-powered campaign platform",
        campaign_theme="Innovation at Scale",
        primary_cta="Get Started",
    )
    defaults.update(kwargs)
    return CampaignInput(**defaults)


STUB_CORE_CONCEPT = {
    "message": "Lead the market",
    "visual_direction": "Bold and clean",
    "audio_direction": None,
    "tone": "confident",
}

STUB_COPY_VARIANT = [{"content": "Innovation at scale.", "tone": "professional"}]
STUB_IMAGE_VARIANT = [{"prompt": "Bold cityscape at dawn", "style": "photorealistic"}]
STUB_VIDEO_VARIANT = []
STUB_VO_VARIANT = []


def patch_generator(
    core=None,
    platform_return=None,
):
    """Patch CreativeGenerator methods."""
    core = core or STUB_CORE_CONCEPT

    async def _gen_core(data):
        return core

    async def _gen_platform(platform, core_concept, campaign_data, creative_type):
        if creative_type == "copy":
            return platform_return or STUB_COPY_VARIANT
        if creative_type == "image_prompt":
            return STUB_IMAGE_VARIANT
        return []

    return _gen_core, _gen_platform


# ── stub mode ──────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_generate_stub_mode_returns_output():
    agent = CreativeDirectorAgent()
    inp = make_campaign_input()
    with patch("backend.app.agents.creative_director_orchestrator.stub_enabled", return_value=True):
        result = await agent.generate(inp)
    assert isinstance(result, CreativeDirectorOutput)
    assert result.campaign_id == "camp-001"
    assert result.tenant_id == "tenant-001"
    assert result.metadata.model_used == "stub"
    assert result.metadata.validation_status == "passed"
    assert result.error is None


@pytest.mark.asyncio
async def test_generate_stub_mode_skips_llm():
    agent = CreativeDirectorAgent()
    inp = make_campaign_input()
    with patch("backend.app.agents.creative_director_orchestrator.stub_enabled", return_value=True):
        with patch.object(agent.generator, "generate_core_concept", new=AsyncMock()) as mock_gen:
            await agent.generate(inp)
    mock_gen.assert_not_called()


@pytest.mark.asyncio
async def test_creative_director_agent_entry_point_stub():
    inp = make_campaign_input()
    with patch("backend.app.agents.creative_director_orchestrator.stub_enabled", return_value=True):
        result = await creative_director_agent(inp)
    assert isinstance(result, CreativeDirectorOutput)
    assert result.campaign_id == "camp-001"


# ── happy path ─────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_generate_returns_creative_director_output():
    agent = CreativeDirectorAgent()
    inp = make_campaign_input()
    gen_core, gen_platform = patch_generator()

    with patch("backend.app.agents.creative_director_orchestrator.stub_enabled", return_value=False):
        with patch.object(agent.aggregator, "aggregate", side_effect=lambda x: x):
            with patch.object(agent.generator, "generate_core_concept", new=AsyncMock(side_effect=gen_core)):
                with patch.object(agent.generator, "generate_platform_creatives", new=AsyncMock(side_effect=gen_platform)):
                    with patch.object(agent.validator, "validate_copy", return_value=MagicMock(status="passed", violations=[], warnings=[])):
                        with patch.object(agent.validator, "validate_tone", return_value=MagicMock(status="passed", violations=[], warnings=[])):
                            with patch.object(agent.validator, "validate_image_prompt", return_value=MagicMock(status="passed", violations=[], warnings=[])):
                                with patch.object(agent.validator, "validate_video_concept", return_value=MagicMock(status="passed", violations=[], warnings=[])):
                                    result = await agent.generate(inp)

    assert isinstance(result, CreativeDirectorOutput)
    assert result.campaign_id == "camp-001"
    assert result.tenant_id == "tenant-001"


@pytest.mark.asyncio
async def test_generate_includes_platform_in_output():
    agent = CreativeDirectorAgent()
    inp = make_campaign_input(platforms=["instagram"])
    gen_core, gen_platform = patch_generator()

    with patch("backend.app.agents.creative_director_orchestrator.stub_enabled", return_value=False):
        with patch.object(agent.aggregator, "aggregate", side_effect=lambda x: x):
            with patch.object(agent.generator, "generate_core_concept", new=AsyncMock(side_effect=gen_core)):
                with patch.object(agent.generator, "generate_platform_creatives", new=AsyncMock(side_effect=gen_platform)):
                    with patch.object(agent.validator, "validate_copy", return_value=MagicMock(status="passed", violations=[], warnings=[])):
                        with patch.object(agent.validator, "validate_tone", return_value=MagicMock(status="passed", violations=[], warnings=[])):
                            with patch.object(agent.validator, "validate_image_prompt", return_value=MagicMock(status="passed", violations=[], warnings=[])):
                                with patch.object(agent.validator, "validate_video_concept", return_value=MagicMock(status="passed", violations=[], warnings=[])):
                                    result = await agent.generate(inp)

    assert "instagram" in result.platforms


@pytest.mark.asyncio
async def test_generate_error_in_platform_continues_others():
    """Per-platform error must not abort other platforms."""
    agent = CreativeDirectorAgent()
    inp = make_campaign_input(platforms=["instagram", "linkedin"])
    gen_core, _ = patch_generator()

    async def gen_platform_raises(platform, core_concept, campaign_data, creative_type):
        if platform == "instagram":
            raise RuntimeError("Instagram API down")
        return STUB_COPY_VARIANT if creative_type == "copy" else []

    with patch("backend.app.agents.creative_director_orchestrator.stub_enabled", return_value=False):
        with patch.object(agent.aggregator, "aggregate", side_effect=lambda x: x):
            with patch.object(agent.generator, "generate_core_concept", new=AsyncMock(side_effect=gen_core)):
                with patch.object(agent.generator, "generate_platform_creatives", new=AsyncMock(side_effect=gen_platform_raises)):
                    with patch.object(agent.validator, "validate_copy", return_value=MagicMock(status="passed", violations=[], warnings=[])):
                        with patch.object(agent.validator, "validate_tone", return_value=MagicMock(status="passed", violations=[], warnings=[])):
                            with patch.object(agent.validator, "validate_image_prompt", return_value=MagicMock(status="passed", violations=[], warnings=[])):
                                with patch.object(agent.validator, "validate_video_concept", return_value=MagicMock(status="passed", violations=[], warnings=[])):
                                    result = await agent.generate(inp)

    # Both platforms present even though instagram errored
    assert "instagram" in result.platforms
    assert "linkedin" in result.platforms
    assert len(result.metadata.errors) >= 1


@pytest.mark.asyncio
async def test_generate_catastrophic_error_returns_output_with_error():
    """Top-level exception must return CreativeDirectorOutput with error field."""
    agent = CreativeDirectorAgent()
    inp = make_campaign_input()

    with patch("backend.app.agents.creative_director_orchestrator.stub_enabled", return_value=False):
        with patch.object(agent.aggregator, "aggregate", side_effect=RuntimeError("DB gone")):
            result = await agent.generate(inp)

    assert isinstance(result, CreativeDirectorOutput)
    assert result.error is not None
    assert result.metadata.validation_status == "failed"


# ── _determine_validation_status ───────────────────────────────────────────────

def test_determine_status_empty_platforms():
    agent = CreativeDirectorAgent()
    assert agent._determine_validation_status({}) == "failed"


def test_determine_status_all_passed():
    agent = CreativeDirectorAgent()
    from backend.app.agents.creative_director.models import Copy, CreativeValidation
    copy = Copy(content="x", character_count=1, tone="p",
                validation=CreativeValidation(status="passed"))
    pc = PlatformCreatives(platform="instagram", copy=[copy])
    assert agent._determine_validation_status({"instagram": pc}) == "passed"


def test_determine_status_partial():
    agent = CreativeDirectorAgent()
    from backend.app.agents.creative_director.models import Copy, CreativeValidation
    passed = Copy(content="x", character_count=1, tone="p",
                  validation=CreativeValidation(status="passed"))
    failed = Copy(content="y", character_count=1, tone="p",
                  validation=CreativeValidation(status="failed"))
    pc = PlatformCreatives(platform="instagram", copy=[passed, failed])
    status = agent._determine_validation_status({"instagram": pc})
    assert status in ("partial", "failed")


def test_determine_status_no_creatives_returns_failed():
    agent = CreativeDirectorAgent()
    pc = PlatformCreatives(platform="instagram")
    assert agent._determine_validation_status({"instagram": pc}) == "failed"


# ── _generate_validation_summary ───────────────────────────────────────────────

def test_generate_validation_summary_no_creatives():
    agent = CreativeDirectorAgent()
    pc = PlatformCreatives(platform="instagram")
    summary = agent._generate_validation_summary({"instagram": pc})
    assert summary == "No creatives generated"


def test_generate_validation_summary_with_creatives():
    agent = CreativeDirectorAgent()
    from backend.app.agents.creative_director.models import Copy, CreativeValidation
    copy = Copy(content="x", character_count=1, tone="p",
                validation=CreativeValidation(status="passed"))
    pc = PlatformCreatives(platform="instagram", copy=[copy])
    summary = agent._generate_validation_summary({"instagram": pc})
    assert "instagram" in summary
    assert "1/1" in summary


# ── entry point ────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_creative_director_agent_entry_calls_generate():
    inp = make_campaign_input()
    mock_result = MagicMock(spec=CreativeDirectorOutput)

    with patch("backend.app.agents.creative_director_orchestrator.stub_enabled", return_value=False):
        with patch.object(CreativeDirectorAgent, "generate", new=AsyncMock(return_value=mock_result)):
            result = await creative_director_agent(inp)

    assert result is mock_result
