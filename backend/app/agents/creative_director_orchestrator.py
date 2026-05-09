"""Creative Director Agent (AGT-06) Main Orchestrator.

Orchestrates the entire creative generation pipeline:
1. Input aggregation and validation
2. Core concept generation
3. Platform-specific creative generation
4. Validation and refinement
5. Output compilation
"""

import asyncio
import logging
import time
from typing import Dict, Any, Optional, List
from datetime import datetime, timezone

from backend.app.agents.creative_director.models import (
    CampaignInput,
    CreativeDirectorOutput,
    CoreConcept,
    GenerationMetadata,
    PlatformCreatives,
    Copy,
    ImagePrompt,
    VideoConcept,
    VoiceoverScript,
)
from backend.app.agents.creative_director.input_aggregator import InputAggregator
from backend.app.agents.creative_director.generator import CreativeGenerator
from backend.app.agents.creative_director.validator import Validator
from backend.app.agents.creative_director.refiner import Refiner

logger = logging.getLogger(__name__)


class CreativeDirectorAgent:
    """Main orchestrator for the Creative Director Agent."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: str = "claude-opus-4-7"
    ):
        """Initialize Creative Director Agent with components.

        Args:
            api_key: Optional Anthropic API key
            model: Claude model to use (default: claude-opus-4-7)
        """
        self.aggregator = InputAggregator()
        self.generator = CreativeGenerator(api_key=api_key, model=model)
        self.validator = Validator()
        self.refiner = Refiner(max_attempts=2)

        # Wire up refiner dependencies
        self.refiner.generator = self.generator
        self.refiner.validator = self.validator

    async def generate(
        self,
        campaign_input: CampaignInput
    ) -> CreativeDirectorOutput:
        """Generate platform-specific creatives for a campaign.

        Pipeline:
        1. Aggregate and validate inputs
        2. Generate core concept (unified across platforms)
        3. For each platform:
           a. Generate creatives (copy, images, video, voiceover)
           b. Validate creatives
           c. Refine if needed
        4. Compile output with metadata

        Args:
            campaign_input: Campaign input with all required context

        Returns:
            CreativeDirectorOutput with generated creatives or error

        Raises:
            ValueError: If input validation fails
        """
        start_time = time.time()
        errors = []
        platforms_dict: Dict[str, PlatformCreatives] = {}
        core_concept: Optional[CoreConcept] = None

        try:
            # Step 1: Aggregate inputs
            logger.info(f"Aggregating inputs for campaign {campaign_input.campaign_id}")
            campaign_input = self.aggregator.aggregate(campaign_input)

            # Step 2: Generate core concept
            logger.info("Generating core concept")
            campaign_data = {"campaign_input": campaign_input}
            core_concept_data = await self.generator.generate_core_concept(campaign_data)

            core_concept = CoreConcept(
                message=core_concept_data.get("message", ""),
                visual_direction=core_concept_data.get("visual_direction", ""),
                audio_direction=core_concept_data.get("audio_direction"),
                tone=core_concept_data.get("tone", "")
            )
            logger.info(f"Core concept generated: {core_concept.message}")

            # Step 3: Generate platform-specific creatives
            for platform in campaign_input.platforms:
                logger.info(f"Generating creatives for platform: {platform}")

                try:
                    platform_creatives = await self._generate_platform_creatives(
                        platform=platform,
                        core_concept=core_concept,
                        campaign_input=campaign_input,
                        campaign_data=campaign_data
                    )

                    # Validate platform creatives
                    platform_creatives = await self._validate_platform_creatives(
                        platform_creatives=platform_creatives,
                        platform=platform,
                        brand_rules=self._extract_brand_rules(campaign_input)
                    )

                    # Refine if needed
                    platform_creatives = await self._refine_platform_creatives(
                        platform_creatives=platform_creatives,
                        platform=platform,
                        brand_rules=self._extract_brand_rules(campaign_input)
                    )

                    platforms_dict[platform] = platform_creatives

                except Exception as e:
                    logger.error(f"Error generating creatives for {platform}: {e}")
                    errors.append(f"Failed to generate creatives for {platform}: {str(e)}")
                    # Continue with next platform instead of failing entirely
                    platforms_dict[platform] = PlatformCreatives(platform=platform)

            # Step 4: Compile output
            elapsed_ms = (time.time() - start_time) * 1000

            # Determine validation status
            validation_status = self._determine_validation_status(platforms_dict)
            validation_summary = self._generate_validation_summary(platforms_dict)

            output = CreativeDirectorOutput(
                campaign_id=campaign_input.campaign_id,
                tenant_id=campaign_input.tenant_id,
                platforms=platforms_dict,
                metadata=GenerationMetadata(
                    core_concept=core_concept or CoreConcept(
                        message="",
                        visual_direction="",
                        tone=""
                    ),
                    validation_status=validation_status,
                    validation_summary=validation_summary,
                    refinement_attempts=0,
                    generation_time_ms=elapsed_ms,
                    model_used=self.generator.model,
                    errors=errors
                ),
                error={"errors": errors} if errors else None
            )

            logger.info(f"Generation complete in {elapsed_ms:.0f}ms")
            return output

        except Exception as e:
            logger.error(f"Error in creative generation pipeline: {e}")
            elapsed_ms = (time.time() - start_time) * 1000

            return CreativeDirectorOutput(
                campaign_id=campaign_input.campaign_id,
                tenant_id=campaign_input.tenant_id,
                platforms=platforms_dict,
                metadata=GenerationMetadata(
                    core_concept=core_concept or CoreConcept(
                        message="",
                        visual_direction="",
                        tone=""
                    ),
                    validation_status="failed",
                    validation_summary="Generation failed",
                    generation_time_ms=elapsed_ms,
                    model_used=self.generator.model,
                    errors=[str(e)] + errors
                ),
                error={"error": str(e), "errors": errors}
            )

    async def _generate_platform_creatives(
        self,
        platform: str,
        core_concept: Dict[str, Any],
        campaign_input: CampaignInput,
        campaign_data: Dict[str, Any]
    ) -> PlatformCreatives:
        """Generate all creative types for a platform.

        Args:
            platform: Target platform
            core_concept: Core concept dict
            campaign_input: Campaign input
            campaign_data: Campaign data dict

        Returns:
            PlatformCreatives with all generated creatives
        """
        platform_creatives = PlatformCreatives(platform=platform)

        # Generate copy variations
        copy_variants = await self.generator.generate_platform_creatives(
            platform=platform,
            core_concept=core_concept.model_dump(),
            campaign_data=campaign_data,
            creative_type="copy"
        )

        if isinstance(copy_variants, list):
            for variant in copy_variants:
                if isinstance(variant, dict):
                    platform_creatives.copy.append(Copy(
                        content=variant.get("content", ""),
                        character_count=len(variant.get("content", "")),
                        tone=variant.get("tone", "")
                    ))

        # Generate image prompts
        image_variants = await self.generator.generate_platform_creatives(
            platform=platform,
            core_concept=core_concept.model_dump(),
            campaign_data=campaign_data,
            creative_type="image_prompt"
        )

        if isinstance(image_variants, list):
            for variant in image_variants:
                if isinstance(variant, dict):
                    platform_creatives.image_prompts.append(ImagePrompt(
                        prompt=variant.get("prompt", ""),
                        style=variant.get("style")
                    ))

        # Generate video concepts
        video_variants = await self.generator.generate_platform_creatives(
            platform=platform,
            core_concept=core_concept.model_dump(),
            campaign_data=campaign_data,
            creative_type="video_concept"
        )

        if isinstance(video_variants, list):
            for variant in video_variants:
                if isinstance(variant, dict):
                    shots = variant.get("shots", [])
                    if shots:
                        platform_creatives.video_concepts.append(VideoConcept(
                            title=variant.get("title", ""),
                            hook=variant.get("hook", ""),
                            shots=shots,
                            duration_seconds=variant.get("duration_seconds", 30)
                        ))

        # Generate voiceover scripts
        vo_variants = await self.generator.generate_platform_creatives(
            platform=platform,
            core_concept=core_concept.model_dump(),
            campaign_data=campaign_data,
            creative_type="voiceover_script"
        )

        if isinstance(vo_variants, list):
            for variant in vo_variants:
                if isinstance(variant, dict):
                    platform_creatives.voiceover_scripts.append(VoiceoverScript(
                        script=variant.get("script", ""),
                        duration_seconds=variant.get("duration_seconds"),
                        tone=variant.get("tone", ""),
                        pacing=variant.get("pacing")
                    ))

        return platform_creatives

    async def _validate_platform_creatives(
        self,
        platform_creatives: PlatformCreatives,
        platform: str,
        brand_rules: Dict[str, Any]
    ) -> PlatformCreatives:
        """Validate all creatives in a platform group.

        Args:
            platform_creatives: Platform creatives to validate
            platform: Target platform
            brand_rules: Brand guidelines

        Returns:
            Platform creatives with validation results populated
        """
        # Validate copy
        for copy in platform_creatives.copy:
            validation = self.validator.validate_copy(copy, platform, brand_rules)
            copy.validation = validation

        # Validate tone
        brand_tone = brand_rules.get("tone", "professional")
        for copy in platform_creatives.copy:
            tone_validation = self.validator.validate_tone(copy, brand_tone)
            if tone_validation.status == "failed":
                copy.validation = tone_validation

        # Validate image prompts
        for img_prompt in platform_creatives.image_prompts:
            validation = self.validator.validate_image_prompt(img_prompt, platform)
            img_prompt.validation = validation

        # Validate video concepts
        for video in platform_creatives.video_concepts:
            validation = self.validator.validate_video_concept(video, platform)
            video.validation = validation

        return platform_creatives

    async def _refine_platform_creatives(
        self,
        platform_creatives: PlatformCreatives,
        platform: str,
        brand_rules: Dict[str, Any]
    ) -> PlatformCreatives:
        """Refine creatives that failed validation.

        Args:
            platform_creatives: Platform creatives to refine
            platform: Target platform
            brand_rules: Brand guidelines

        Returns:
            Platform creatives with refinements applied
        """
        # Refine copy if needed
        for i, copy in enumerate(platform_creatives.copy):
            if copy.validation.status == "failed":
                result = await self.refiner.refine(
                    creative=copy.model_dump(),
                    validation_result=copy.validation.model_dump(),
                    platform=platform,
                    brand_rules=brand_rules
                )
                if result.get("content"):
                    platform_creatives.copy[i].validation.status = result.get("status", "failed")

        return platform_creatives

    def _extract_brand_rules(self, campaign_input: CampaignInput) -> Dict[str, Any]:
        """Extract brand rules from campaign input.

        Args:
            campaign_input: Campaign input

        Returns:
            Brand rules dict
        """
        bg = campaign_input.brand_guidelines
        return {
            "tone": bg.tone,
            "colors": bg.colors,
            "messaging_rules": bg.messaging_rules,
            "mandatory_ctas": bg.mandatory_ctas,
            "visual_style": bg.visual_style,
            "tagline": bg.tagline
        }

    def _determine_validation_status(
        self,
        platforms_dict: Dict[str, PlatformCreatives]
    ) -> str:
        """Determine overall validation status from all platforms.

        Args:
            platforms_dict: Dict of platform creatives

        Returns:
            "passed", "partial", or "failed"
        """
        if not platforms_dict:
            return "failed"

        all_passed = 0
        any_passed = False
        total_platforms = len(platforms_dict)

        for platform_creatives in platforms_dict.values():
            # Check if platform has any creatives
            has_creatives = (
                platform_creatives.copy or
                platform_creatives.image_prompts or
                platform_creatives.video_concepts or
                platform_creatives.voiceover_scripts
            )

            if not has_creatives:
                continue

            # Check if all creatives passed
            all_valid = True
            if platform_creatives.copy:
                all_valid = all_valid and all(c.validation.status == "passed" for c in platform_creatives.copy)
            if platform_creatives.image_prompts:
                all_valid = all_valid and all(c.validation.status == "passed" for c in platform_creatives.image_prompts)
            if platform_creatives.video_concepts:
                all_valid = all_valid and all(c.validation.status == "passed" for c in platform_creatives.video_concepts)

            if all_valid:
                all_passed += 1
            else:
                any_passed = True

        if all_passed == total_platforms:
            return "passed"
        elif any_passed or all_passed > 0:
            return "partial"
        else:
            return "failed"

    def _generate_validation_summary(
        self,
        platforms_dict: Dict[str, PlatformCreatives]
    ) -> str:
        """Generate human-readable validation summary.

        Args:
            platforms_dict: Dict of platform creatives

        Returns:
            Summary string
        """
        summaries = []
        for platform, creatives in platforms_dict.items():
            passed_count = 0
            total_count = 0

            for creative_list in [creatives.copy, creatives.image_prompts,
                                  creatives.video_concepts, creatives.voiceover_scripts]:
                if creative_list:
                    for creative in creative_list:
                        total_count += 1
                        if hasattr(creative, 'validation') and creative.validation.status == "passed":
                            passed_count += 1

            if total_count > 0:
                summaries.append(f"{platform}: {passed_count}/{total_count} passed")

        return "; ".join(summaries) if summaries else "No creatives generated"


async def creative_director_agent(
    campaign_input: CampaignInput
) -> CreativeDirectorOutput:
    """Public entry point for Creative Director Agent.

    Args:
        campaign_input: Campaign input with all required context

    Returns:
        CreativeDirectorOutput with generated creatives

    Raises:
        ValueError: If input validation fails
    """
    agent = CreativeDirectorAgent()
    return await agent.generate(campaign_input)
