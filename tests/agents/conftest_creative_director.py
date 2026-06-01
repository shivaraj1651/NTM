"""Pytest fixtures for Creative Director Agent (AGT-06) tests."""

import uuid

import pytest

from backend.app.agents.creative_director.models import (
    BrandGuidelines,
    CampaignInput,
    Copy,
    CoreConcept,
    CreativeDirectorOutput,
    CreativeValidation,
    GenerationMetadata,
    ImagePrompt,
    PlatformCreatives,
    TargetAudience,
    VideoConcept,
    VideoConceptScene,
    VoiceoverScript,
    utc_now,
)


@pytest.fixture
def brand_guidelines():
    """Complete BrandGuidelines instance with realistic values."""
    return BrandGuidelines(
        tone="professional yet approachable",
        colors=["#1E40AF", "#F59E0B", "#FFFFFF"],
        messaging_rules=[
            "Always mention company name",
            "Emphasize innovation and reliability",
            "Avoid superlatives (best, greatest)",
        ],
        mandatory_ctas=["Learn More", "Get Started", "Schedule Demo"],
        visual_style="modern, clean, minimal",
        tagline="Your trusted innovation partner",
    )


@pytest.fixture
def target_audience():
    """Complete TargetAudience with demographics, psychographics, and segments."""
    return TargetAudience(
        demographics={
            "age_range": "25-45",
            "income": "75k-150k",
            "education": "bachelor+",
            "location": "urban/suburban",
        },
        psychographics={
            "values": "innovation, reliability, quality",
            "pain_points": "time constraints, overwhelming choices",
        },
        segments=["tech-savvy professionals", "decision makers"],
        language="en",
    )


@pytest.fixture
def campaign_input(brand_guidelines, target_audience):
    """Complete CampaignInput using fixtures."""
    return CampaignInput(
        campaign_id=str(uuid.uuid4()),
        tenant_id=str(uuid.uuid4()),
        objectives=[
            "Increase brand awareness by 25%",
            "Generate 100 qualified leads",
            "Improve engagement by 40%",
        ],
        target_audience=target_audience,
        brand_guidelines=brand_guidelines,
        platforms=["instagram", "linkedin", "youtube"],
        budget_allocation={"instagram": 0.4, "linkedin": 0.35, "youtube": 0.25},
        product_details="SaaS platform for enterprise resource planning; serves mid-to-large companies",
        campaign_theme="Digital Transformation: Simplify Your Operations",
        primary_cta="Schedule Free Demo",
        competitor_insights="Competitors focus on features; we differentiate on ease-of-use and support",
        channel_allocation={"instagram": 0.4, "linkedin": 0.35, "youtube": 0.25},
    )


@pytest.fixture
def mock_claude_response():
    """Mock response for Claude API (for later tasks)."""
    return {
        "core_concept": {
            "message": "Enterprise operations made simple through intuitive automation",
            "visual_direction": "Modern dashboards, people collaborating, clean interfaces",
            "audio_direction": "Professional, warm, confident voiceover; subtle tech ambient",
            "tone": "professional yet approachable",
        },
        "platforms": {
            "instagram": {
                "copy": [
                    {
                        "content": "Your team's time is valuable. Our platform automates the tedious parts of operations so you can focus on growth. Schedule your free demo today. 🚀",
                        "character_count": 156,
                        "tone": "casual-professional",
                    }
                ],
                "image_prompts": [
                    {
                        "prompt": "Modern tech dashboard showing data visualizations and charts on a large monitor, hands pointing to insights, bright blue and gold colors, clean minimalist design, warm lighting",
                        "style": "contemporary",
                    }
                ],
                "captions": [
                    {
                        "content": "#DigitalTransformation #EnterpriseAutomation #SimplifyOperations",
                        "character_count": 68,
                        "tone": "hashtag",
                    }
                ],
            },
            "linkedin": {
                "copy": [
                    {
                        "content": "Enterprise resource planning has traditionally been complex and time-consuming. Our platform is changing that. By automating routine operational tasks, we enable teams to focus on strategic initiatives. See how in our demo.",
                        "character_count": 232,
                        "tone": "professional",
                    }
                ],
            },
        },
    }


@pytest.fixture
def valid_output(campaign_input):
    """Valid CreativeDirectorOutput with all platforms."""
    return CreativeDirectorOutput(
        campaign_id=campaign_input.campaign_id,
        generation_id=str(uuid.uuid4()),
        tenant_id=campaign_input.tenant_id,
        generated_at=utc_now(),
        platforms={
            "instagram": PlatformCreatives(
                platform="instagram",
                copy=[
                    Copy(
                        content="Your team's time is valuable. Automate operations, focus on growth.",
                        character_count=79,
                        tone="casual",
                        validation=CreativeValidation(status="passed"),
                    )
                ],
                image_prompts=[
                    ImagePrompt(
                        prompt="Modern dashboard with team collaboration, bright colors, clean interface",
                        style="contemporary",
                        validation=CreativeValidation(status="passed"),
                    )
                ],
            ),
            "linkedin": PlatformCreatives(
                platform="linkedin",
                copy=[
                    Copy(
                        content="Enterprise operations made simple. Our platform automates routine tasks so your team focuses on strategy.",
                        character_count=118,
                        tone="professional",
                        validation=CreativeValidation(status="passed"),
                    )
                ],
            ),
            "youtube": PlatformCreatives(
                platform="youtube",
                copy=[
                    Copy(
                        content="See how modern companies transform their operations. Our platform makes enterprise automation simple.",
                        character_count=117,
                        tone="professional",
                        validation=CreativeValidation(status="passed"),
                    )
                ],
                video_concepts=[
                    VideoConcept(
                        title="Enterprise Automation Overview",
                        hook="See what 500+ companies are doing to transform operations",
                        shots=[
                            VideoConceptScene(
                                duration_seconds=3.0,
                                description="Opening: Modern office, team collaborating"
                            ),
                            VideoConceptScene(
                                duration_seconds=5.0,
                                description="Demo: Product dashboard showing automation",
                                notes="Highlight key features"
                            ),
                            VideoConceptScene(
                                duration_seconds=3.0,
                                description="Closing: CTA with demo link"
                            ),
                        ],
                        duration_seconds=11.0,
                        validation=CreativeValidation(status="passed"),
                    )
                ],
                voiceover_scripts=[
                    VoiceoverScript(
                        script="Enterprise resource planning has been complex. Until now. Our platform automates the tedious parts, freeing your team to focus on what matters. Schedule your free demo today.",
                        duration_seconds=12.0,
                        tone="professional-warm",
                        pacing="conversational",
                        validation=CreativeValidation(status="passed"),
                    )
                ],
            ),
        },
        metadata=GenerationMetadata(
            core_concept=CoreConcept(
                message="Simplify enterprise operations through intelligent automation",
                visual_direction="Modern dashboards, collaboration, clean UI",
                audio_direction="Professional, warm, confident tone",
                tone="professional-approachable",
            ),
            validation_status="passed",
            validation_summary="All creatives passed validation.",
            refinement_attempts=0,
            generation_time_ms=1250.5,
        ),
    )
