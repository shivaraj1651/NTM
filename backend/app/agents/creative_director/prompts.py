"""Reusable Claude prompt templates for Creative Director Agent (AGT-06).

This module provides static methods for generating structured prompts
for different stages of creative generation:
- Stage 1: Core concept generation (unified across all platforms)
- Stage 2: Platform-specific creative variations
- Refinement: Fixing violations and improving creatives
"""


from backend.app.agents.creative_director.models import CampaignInput


class CreativePrompts:
    """Reusable prompt templates for creative generation stages."""

    @staticmethod
    def core_concept_prompt(campaign_input: CampaignInput) -> str:
        """Generate prompt for Stage 1: unified core concept.

        Takes campaign context and generates a prompt asking Claude to produce
        a unified creative concept that will serve as the foundation for
        platform-specific variations.

        Args:
            campaign_input: Complete campaign input with objectives, audience,
                brand guidelines, product details, theme, and competitor insights

        Returns:
            Prompt string asking Claude to generate:
            - message: Core creative message/angle
            - visual_direction: Visual style guidance
            - audio_direction: Audio/voiceover style guidance
            - tone: Brand tone for the creative
        """
        # Extract key fields from campaign_input
        objectives = "\n".join(f"- {obj}" for obj in campaign_input.objectives)
        messaging_rules = "\n".join(f"- {rule}" for rule in campaign_input.brand_guidelines.messaging_rules)
        colors = ", ".join(campaign_input.brand_guidelines.colors)

        # Build audience summary
        audience_summary = f"""
Demographics: {campaign_input.target_audience.demographics}
Psychographics: {campaign_input.target_audience.psychographics}
Segments: {', '.join(campaign_input.target_audience.segments or [])}
"""

        prompt = f"""You are a world-class creative director tasked with developing a unified creative concept for a multi-platform campaign.

## Campaign Objectives
{objectives}

## Target Audience
{audience_summary}

## Brand Guidelines
- Tone: {campaign_input.brand_guidelines.tone}
- Colors: {colors}
- Tagline: {campaign_input.brand_guidelines.tagline or 'Not specified'}
- Visual Style: {campaign_input.brand_guidelines.visual_style or 'Modern and professional'}

## Messaging Rules (MUST follow all)
{messaging_rules}

## Campaign Context
- Theme: {campaign_input.campaign_theme}
- Product/Service: {campaign_input.product_details}
- Primary CTA: {campaign_input.primary_cta}
- Competitor Insights: {campaign_input.competitor_insights or 'None provided'}

## Your Task
Generate a UNIFIED CORE CONCEPT that will serve as the creative foundation for this campaign across all platforms (Instagram, LinkedIn, YouTube, Meta Ads, TikTok).

The core concept should:
1. Capture the essence of the brand and campaign theme
2. Be flexible enough to adapt to different platforms
3. Follow all brand messaging rules
4. Appeal to the target audience
5. Differentiate from competitors
6. Support the primary CTA

## Required Output Format
Return ONLY valid JSON (no markdown, no code blocks) with this structure:
{{
    "message": "The core creative message/angle that unifies the campaign. 1-2 sentences.",
    "visual_direction": "Detailed description of visual style, composition, color treatment, mood, and aesthetic that should be used across platform creatives.",
    "audio_direction": "Voiceover style, pacing, tone, music direction, and audio mood for videos/audio content.",
    "tone": "The specific brand tone to use (e.g., 'professional yet approachable')."
}}

Ensure the output is valid JSON that can be parsed by a JSON parser."""

        return prompt

    @staticmethod
    def platform_specific_prompt(
        core_concept: dict,
        platform: str,
        campaign_input: CampaignInput,
        creative_type: str
    ) -> str:
        """Generate prompt for Stage 2: platform-specific creative variations.

        Takes the unified core concept and generates platform-optimized creative
        variations. Each platform has specific constraints and best practices.

        Args:
            core_concept: Dict with keys: message, visual_direction, audio_direction, tone
            platform: Target platform (instagram, linkedin, youtube, meta_ads, tiktok, twitter)
            campaign_input: Original campaign input for context
            creative_type: Type of creative to generate (copy, image_prompt, video_concept, voiceover_script)

        Returns:
            Prompt string asking Claude to generate 2-3 variations of the specified
            creative_type optimized for the platform, based on the core concept
        """
        # Platform-specific guidance
        platform_guidance = {
            "instagram": {
                "description": "Instagram is highly visual and social",
                "guidance": "Focus on eye-catching visuals, authentic storytelling, and community engagement. Use clear CTAs and hashtags. Keep copy concise. Emphasize visual elements over text.",
                "constraints": "Images: max 300 characters caption, visual-first storytelling. Reels: 15-90 seconds, attention-grabbing first 3 seconds, trending audio/music.",
                "tone_hint": "Casual, authentic, aspirational"
            },
            "linkedin": {
                "description": "LinkedIn is professional and B2B focused",
                "guidance": "Emphasize business value, professional credibility, and thought leadership. Use industry language and insights. Focus on ROI and business outcomes.",
                "constraints": "Copy: 150-300 characters optimal, professional tone, strong CTAs. Videos: 30-60 seconds, talking head or product demo format.",
                "tone_hint": "Professional, authoritative, business-focused"
            },
            "youtube": {
                "description": "YouTube rewards storytelling, hooks, and longer-form content",
                "guidance": "Lead with a strong hook (first 3 seconds critical). Tell a compelling story. Use pattern interrupts and visual variety. Deliver value. End with clear CTA.",
                "constraints": "Optimal length: 6-15 minutes for views, but start with 30-90 second versions. Strong hook, clear narrative arc, professional editing.",
                "tone_hint": "Engaging, narrative-driven, educational"
            },
            "meta_ads": {
                "description": "Meta Ads prioritize conversion and engagement",
                "guidance": "Focus on immediate value proposition and CTAs. Use scarcity, urgency, or curiosity. Test multiple angles. Emphasize benefits over features.",
                "constraints": "Copy: 125 characters for headline, 27 for link description. Images: vertical format (9:16), no more than 20% text. Fast-paced if video.",
                "tone_hint": "Direct, benefit-focused, conversion-oriented"
            },
            "tiktok": {
                "description": "TikTok is entertainment-first and trending",
                "guidance": "Follow trends and use trending sounds. Authentic, unpolished feel often performs better. Speed and entertainment value matter most. Show personality.",
                "constraints": "Videos: 9-60 seconds optimal, trending music/sounds, trending hashtags. Vertical format (9:16). Quick cuts and transitions.",
                "tone_hint": "Casual, trendy, authentic, playful"
            },
            "twitter": {
                "description": "Twitter/X is conversation-driven",
                "guidance": "Spark conversation and engagement. Use wit, timely references, and relevant hashtags. Keep it conversational. Encourage discourse.",
                "constraints": "280 characters per tweet (or up to 4000 for longer tweets). Threading common for stories. Threads work well for narratives.",
                "tone_hint": "Conversational, witty, timely"
            }
        }

        platform_info = platform_guidance.get(platform, {
            "description": platform,
            "guidance": "Adapt the core concept for this platform.",
            "constraints": "Follow platform best practices.",
            "tone_hint": "Appropriate for the platform"
        })

        # Build messaging rules reference
        messaging_rules = "\n".join(f"- {rule}" for rule in campaign_input.brand_guidelines.messaging_rules)
        mandatory_ctas = "\n".join(f"- {cta}" for cta in campaign_input.brand_guidelines.mandatory_ctas)

        prompt = f"""You are a creative specialist generating platform-optimized content variations based on a unified core concept.

## Core Creative Concept
- Message: {core_concept['message']}
- Visual Direction: {core_concept['visual_direction']}
- Audio Direction: {core_concept.get('audio_direction', 'Not specified')}
- Tone: {core_concept['tone']}

## Platform: {platform.upper()}
{platform_info['description']}

Platform Guidance:
{platform_info['guidance']}

Platform Constraints:
{platform_info['constraints']}

Recommended Tone: {platform_info['tone_hint']}

## Brand Context
- Brand Tone: {campaign_input.brand_guidelines.tone}
- Mandatory CTAs (must include at least one):
{mandatory_ctas}

## Messaging Rules (MUST follow all)
{messaging_rules}

## Campaign Context
- Target Audience: {campaign_input.target_audience.demographics}
- Primary CTA: {campaign_input.primary_cta}
- Theme: {campaign_input.campaign_theme}

## Your Task
Generate 2-3 variations of {creative_type} creatives optimized for {platform}, grounded in the core concept above.

Each variation should:
1. Stay true to the core concept message and tone
2. Follow ALL mandatory messaging rules and include mandatory CTAs
3. Be optimized for {platform} (follow the platform guidance and constraints)
4. Be distinctive from each other while serving the same purpose
5. Drive toward the primary CTA: "{campaign_input.primary_cta}"

## Required Output Format
Return ONLY valid JSON (no markdown, no code blocks) with this structure:
{{
    "variations": [
        {{
            "variation_id": 1,
            "content": "The actual {creative_type} content (copy text, image prompt, video storyboard, etc.)",
            "notes": "Why this variation works for {platform} and how it connects to core concept",
            "ctas_included": ["List", "of", "CTAs", "included"]
        }},
        {{
            "variation_id": 2,
            "content": "Alternative variation",
            "notes": "Why this variation is different and effective",
            "ctas_included": ["List", "of", "CTAs"]
        }},
        {{
            "variation_id": 3,
            "content": "Third variation for comparison",
            "notes": "Unique angle or approach",
            "ctas_included": ["List", "of", "CTAs"]
        }}
    ]
}}

Ensure the output is valid JSON that can be parsed by a JSON parser. All 3 variations are required."""

        return prompt

    @staticmethod
    def refinement_prompt(original_creative: str, violations: list[dict]) -> str:
        """Generate prompt to fix invalid creatives.

        Takes original creative and list of validation violations, then generates
        a prompt asking Claude to regenerate the creative fixing all violations.

        Args:
            original_creative: The original creative content that failed validation
            violations: List of violation dicts with keys:
                - rule: Name of the rule that was violated
                - severity: "high", "medium", or "low"
                - message: Human-readable violation description
                - suggestion: Suggested fix

        Returns:
            Prompt string asking Claude to regenerate the creative fixing violations
        """
        # Format violations for display
        violations_formatted = []
        for i, violation in enumerate(violations, 1):
            severity = violation.get("severity", "medium").upper()
            rule = violation.get("rule", "Unknown")
            message = violation.get("message", "No message")
            suggestion = violation.get("suggestion", "No suggestion")

            violations_formatted.append(
                f"{i}. [{severity}] {rule}\n"
                f"   Issue: {message}\n"
                f"   Fix: {suggestion}"
            )

        violations_text = "\n".join(violations_formatted)

        prompt = f"""You are a creative refinement specialist tasked with fixing validation issues in marketing creative content.

## Original Creative Content
{original_creative}

## Validation Violations Found
{violations_text}

## Your Task
Regenerate the creative content to fix ALL violations above while:
1. Maintaining the core message and intent
2. Addressing each violation with the suggested fix
3. Ensuring HIGH severity violations are fixed first
4. Following all brand guidelines and rules

Pay special attention to HIGH severity violations - they are critical and must be resolved.

## Requirements
- Fix the creative, don't remove it
- Keep the original intent and value proposition
- Address each violation explicitly
- The regenerated creative should pass validation

## Output Format
Return ONLY the improved creative content (no markdown, no explanations, no JSON).
The output should be clean, ready-to-use creative text that addresses all violations."""

        return prompt
