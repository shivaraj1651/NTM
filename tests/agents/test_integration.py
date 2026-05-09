"""Integration tests for Creative Director Agent (AGT-06) orchestrator."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from backend.app.agents.creative_director_orchestrator import (
    CreativeDirectorAgent,
    creative_director_agent,
)
from backend.app.agents.creative_director.models import (
    CampaignInput,
    TargetAudience,
    BrandGuidelines,
    CreativeDirectorOutput,
)


@pytest.fixture
def sample_campaign_input():
    """Create a sample campaign input for testing."""
    return CampaignInput(
        campaign_id="camp-001",
        tenant_id="tenant-001",
        objectives=["Increase awareness", "Drive engagement"],
        target_audience=TargetAudience(
            demographics={"age": "18-45", "location": "urban"},
            psychographics={"interests": "Tech"},
            segments=["Early adopters"],
            language="en"
        ),
        brand_guidelines=BrandGuidelines(
            tone="Professional",
            colors=["#0066CC"],
            messaging_rules=["Include brand name"],
            mandatory_ctas=["Learn more"],
            visual_style="Modern",
            tagline="Innovation"
        ),
        platforms=["instagram", "linkedin"],
        product_details="Tech product",
        campaign_theme="Summer launch",
        primary_cta="Explore",
    )


@pytest.fixture
def agent():
    """Initialize agent with mocked dependencies."""
    agent = CreativeDirectorAgent(api_key="test-key")

    # Mock generator
    agent.generator.generate_core_concept = AsyncMock(
        return_value={
            "message": "Innovative tech",
            "visual_direction": "Modern",
            "audio_direction": "Upbeat",
            "tone": "Professional"
        }
    )
    agent.generator.generate_platform_creatives = AsyncMock(
        return_value=[
            {
                "content": "Explore our new product",
                "tone": "Professional",
                "type": "copy"
            }
        ]
    )

    # Mock validator
    agent.validator.validate_copy = MagicMock()
    agent.validator.validate_image_prompt = MagicMock()
    agent.validator.validate_video_concept = MagicMock()

    return agent


class TestCreativeDirectorAgentInit:
    """Tests for CreativeDirectorAgent initialization."""

    def test_agent_initializes_with_components(self):
        """Should initialize with all required components."""
        agent = CreativeDirectorAgent(api_key="test-key")

        assert agent.aggregator is not None
        assert agent.generator is not None
        assert agent.validator is not None
        assert agent.refiner is not None
        assert agent.refiner.generator == agent.generator
        assert agent.refiner.validator == agent.validator


class TestCreativeDirectorE2E:
    """End-to-end tests for creative generation pipeline."""

    @pytest.mark.asyncio
    async def test_creative_director_agent_e2e(self, agent, sample_campaign_input):
        """Should complete full pipeline with mocked components."""
        output = await agent.generate(sample_campaign_input)

        assert isinstance(output, CreativeDirectorOutput)
        assert output.campaign_id == "camp-001"
        assert output.tenant_id == "tenant-001"
        assert output.metadata is not None
        assert output.metadata.core_concept is not None
        assert output.platforms is not None

    @pytest.mark.asyncio
    async def test_creative_director_handles_missing_inputs(self):
        """Should handle missing inputs gracefully."""
        agent = CreativeDirectorAgent(api_key="test-key")

        # Create invalid input (empty platforms)
        invalid_input = CampaignInput(
            campaign_id="camp-002",
            tenant_id="tenant-001",
            objectives=["Awareness"],
            target_audience=TargetAudience(language="en"),
            brand_guidelines=BrandGuidelines(
                tone="Pro",
                colors=[],
                messaging_rules=[],
                mandatory_ctas=[]
            ),
            platforms=[],  # Empty platforms will trigger validation error
            product_details="Product",
            campaign_theme="Theme",
            primary_cta="Click"
        )

        # Should handle error gracefully
        try:
            output = await agent.generate(invalid_input)
            # If it doesn't throw, should have failed status
            assert output.metadata.validation_status in ["failed", "partial"]
        except ValueError:
            # Expected - aggregator will reject empty platforms
            pass


class TestPublicEntryPoint:
    """Tests for public creative_director_agent function."""

    @pytest.mark.asyncio
    async def test_public_entry_point(self, sample_campaign_input):
        """Should work as public function."""
        with patch(
            'backend.app.agents.creative_director_orchestrator.CreativeDirectorAgent'
        ) as MockAgent:
            mock_instance = AsyncMock()
            MockAgent.return_value = mock_instance
            from backend.app.agents.creative_director.models import GenerationMetadata, CoreConcept
            mock_instance.generate = AsyncMock(
                return_value=CreativeDirectorOutput(
                    campaign_id="camp-001",
                    tenant_id="tenant-001",
                    platforms={},
                    metadata=GenerationMetadata(
                        core_concept=CoreConcept(
                            message="test",
                            visual_direction="test",
                            tone="test"
                        ),
                        validation_status="passed"
                    )
                )
            )

            result = await creative_director_agent(sample_campaign_input)

            assert isinstance(result, CreativeDirectorOutput)
