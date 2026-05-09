# Creative Director Agent (AGT-06)

**Version:** 1.0.0  
**Status:** Production Ready  
**Last Updated:** 2026-05-09

## Overview

The Creative Director Agent (AGT-06) is a multi-stage AI-powered system that generates platform-specific marketing creatives for digital campaigns. It orchestrates a complete pipeline from brand guidelines and campaign context to validated, refined marketing content ready for publication.

### Key Capabilities

- **Multi-Platform Creative Generation** - Generates platform-optimized content for Instagram, LinkedIn, YouTube, Meta Ads, TikTok, and Twitter
- **Intelligent Validation** - Validates creatives against brand guidelines, platform constraints, and tone consistency
- **Automatic Refinement** - Iteratively refines creatives to meet validation requirements (up to 2 attempts)
- **Unified Core Concept** - Generates a single core creative concept that guides all platform variations
- **Error Graceful Degradation** - Continues generation for remaining platforms even if one platform fails

## Architecture

### Components

```
CreativeDirectorAgent (Orchestrator)
├── InputAggregator          (Input validation)
├── CreativeGenerator        (Claude API calls)
├── Validator                (Validation engine)
└── Refiner                  (Refinement loop)
```

### Pipeline Stages

1. **Input Aggregation** - Validates and normalizes campaign input
2. **Core Concept Generation** - Creates unified creative direction
3. **Platform-Specific Generation** - Generates creatives for each platform
4. **Validation** - Checks against brand rules and platform constraints
5. **Refinement** - Auto-refines failed creatives (max 2 attempts)
6. **Output Compilation** - Returns structured output with metadata

## Input Models

### CampaignInput

```python
{
    "campaign_id": str,                      # Campaign UUID
    "tenant_id": str,                        # Tenant UUID
    "objectives": List[str],                 # Campaign goals
    "target_audience": TargetAudience,       # Demographics & psychographics
    "brand_guidelines": BrandGuidelines,     # Brand rules
    "platforms": List[str],                  # Target platforms
    "product_details": str,                  # Product/service description
    "campaign_theme": str,                   # Campaign narrative
    "primary_cta": str,                      # Main call-to-action
    "competitor_insights": Optional[str],    # Competitive analysis
    "budget_allocation": Optional[Dict],     # Platform budget splits
    "channel_allocation": Optional[Dict],    # Channel splits
}
```

### BrandGuidelines

```python
{
    "tone": str,                    # Brand voice (e.g., "professional", "casual")
    "colors": List[str],            # Color palette
    "messaging_rules": List[str],   # Mandatory messaging requirements
    "mandatory_ctas": List[str],    # Required CTAs
    "visual_style": Optional[str],  # Visual aesthetic
    "tagline": Optional[str],       # Brand tagline
}
```

## Output Models

### CreativeDirectorOutput

```python
{
    "campaign_id": str,
    "generation_id": str,                    # Unique generation ID
    "tenant_id": str,
    "generated_at": datetime,
    "platforms": Dict[str, PlatformCreatives],
    "metadata": GenerationMetadata,
    "error": Optional[Dict]
}
```

### PlatformCreatives

```python
{
    "platform": str,
    "copy": List[Copy],                      # Marketing copy variations
    "image_prompts": List[ImagePrompt],      # Image generation prompts
    "video_concepts": List[VideoConcept],    # Video storyboards
    "voiceover_scripts": List[VoiceoverScript],  # VO scripts
    "captions": List[Copy],                  # Platform-specific captions
}
```

## Usage

### Python API

```python
from backend.app.agents.creative_director_orchestrator import creative_director_agent
from backend.app.agents.creative_director.models import CampaignInput, BrandGuidelines, TargetAudience

# Prepare input
campaign_input = CampaignInput(
    campaign_id="camp-001",
    tenant_id="tenant-001",
    objectives=["Increase brand awareness", "Drive engagement"],
    target_audience=TargetAudience(
        demographics={"age": "18-45", "location": "urban"},
        language="en"
    ),
    brand_guidelines=BrandGuidelines(
        tone="Professional",
        colors=["#0066CC"],
        messaging_rules=["Always include brand name"],
        mandatory_ctas=["Learn more", "Shop now"],
        visual_style="Modern and clean",
        tagline="Leading innovation"
    ),
    platforms=["instagram", "linkedin", "youtube"],
    product_details="Tech product launch",
    campaign_theme="Summer refresh",
    primary_cta="Explore the product",
)

# Generate creatives
output = await creative_director_agent(campaign_input)

# Access results
for platform, creatives in output.platforms.items():
    for copy in creatives.copy:
        print(f"{platform} copy: {copy.content}")
```

### FastAPI Endpoint

```
POST /api/agents/creative-director/generate
Content-Type: application/json

{
    "campaign_id": "camp-001",
    "tenant_id": "tenant-001",
    ...
}

Returns: CreativeDirectorOutput (200) or error (400/500)
```

Health Check:
```
GET /api/agents/creative-director/health
Returns: {"status": "healthy", "message": "..."}
```

## Testing

### Test Coverage

- **23 total tests** across all components
- **67% code coverage** for core modules
- **100% coverage** for models and prompts
- **Async test support** with pytest-asyncio

### Running Tests

```bash
# Run all Creative Director tests
pytest tests/agents/test_creative_director/ tests/agents/test_refiner.py tests/agents/test_integration.py -v

# With coverage
pytest tests/agents/ --cov=backend/app/agents/creative_director --cov=backend/app/agents/creative_director_orchestrator --cov-report=term-missing

# Specific component
pytest tests/agents/test_refiner.py -v  # Refiner tests
pytest tests/agents/test_integration.py -v  # Integration tests
pytest tests/agents/test_creative_director/test_prompts.py -v  # Prompt tests
```

## Validation Rules

### Platform Constraints

**Instagram**
- Max chars: 2,200
- Max caption: 150
- Optimal ratio: 1:1
- Max video: 60s

**LinkedIn**
- Max chars: 3,000
- Optimal ratio: 1.91:1
- Max video: 600s

**YouTube**
- Max title: 100 chars
- Max description: 5,000 chars
- Optimal ratio: 16:9
- Max video: 120s

**Meta Ads**
- Max primary: 125 chars
- Max description: 30 chars
- Optimal ratio: 1.2:1
- Max video: 120s

**TikTok**
- Max caption: 150 chars
- Optimal ratio: 9:16
- Max video: 60s

### Tone Compatibility

The validator enforces tone consistency:
- Professional ↔ Formal, Corporate
- Casual ↔ Friendly, Conversational, Informal
- Humorous ↔ Witty, Comedic, Funny

## Refinement Behavior

The refiner automatically improves creatives:

1. **Max Attempts:** 2 iterations by default
2. **Trigger:** Any validation failure (violations list non-empty)
3. **Process:** Generator receives violations context and refines
4. **Escalation:** After max_attempts exceeded with violations still present, status escalates to "partial"

## Database Schema

Generated creatives are stored in `generated_creatives` table:

```sql
CREATE TABLE generated_creatives (
    id UUID PRIMARY KEY,
    campaign_id VARCHAR NOT NULL,
    tenant_id VARCHAR NOT NULL,
    generation_id VARCHAR NOT NULL,
    platform VARCHAR NOT NULL,
    creative_type VARCHAR NOT NULL,
    content JSONB NOT NULL,
    validation_status VARCHAR NOT NULL,
    refinement_attempts INT DEFAULT 0,
    created_at TIMESTAMPTZ NOT NULL,
    updated_at TIMESTAMPTZ NOT NULL,
    
    UNIQUE(campaign_id, generation_id, platform, creative_type),
    INDEX campaign_id,
    INDEX tenant_id,
    INDEX generation_id,
    INDEX platform
);
```

## Error Handling

### Common Errors

| Status | Message | Cause | Resolution |
|--------|---------|-------|-----------|
| 400 | campaign_id is required | Missing input | Provide campaign_id |
| 400 | tenant_id is required | Missing input | Provide tenant_id |
| 400 | At least one platform required | Empty platforms | Add platforms |
| 400 | brand_guidelines are required | Missing guidelines | Provide guidelines |
| 500 | Creative generation failed | API error | Check logs |
| 500 | Service unhealthy | Component init error | Restart service |

### Graceful Degradation

- Generation continues for remaining platforms even if one fails
- Output includes error list with platform-specific failures
- Status degraded to "partial" when some platforms succeed
- Status "failed" only when no platforms generate successfully

## Performance Metrics

- **Core concept generation:** ~2-3 seconds (API call)
- **Per-platform generation:** ~2-3 seconds × number of creative types
- **Validation:** <100ms per creative
- **Refinement:** ~2-3 seconds per iteration
- **Total for 2 platforms:** ~15-20 seconds typical

## Future Enhancements

1. **Caching** - Cache core concepts and popular variations
2. **Batch Generation** - Generate multiple campaigns in parallel
3. **A/B Testing** - Generate multiple variants per creative
4. **Brand Analysis** - Auto-learn tone from historical creatives
5. **Performance Tracking** - Track which creatives perform best
6. **Custom Validation** - Pluggable validation rules per brand
7. **Multi-Language** - Generate creatives in multiple languages
8. **Asset Integration** - Accept pre-existing brand assets
9. **Real-time Optimization** - Adjust creatives based on live performance
10. **Webhook Callbacks** - Notify on generation completion

## Configuration

### Environment Variables

```bash
ANTHROPIC_API_KEY=<your-api-key>  # Required
CREATIVE_DIRECTOR_MODEL=claude-opus-4-7  # Optional, default shown
MAX_REFINEMENT_ATTEMPTS=2  # Optional, default shown
```

### Model Selection

Default: `claude-opus-4-7`

Alternative models:
- `claude-opus-4-20250514` - Faster, lower cost
- `claude-sonnet-4-20250514` - Balanced

## Logging

All operations are logged at INFO and ERROR levels:

```python
import logging
logger = logging.getLogger("backend.app.agents.creative_director_orchestrator")
logger.setLevel(logging.INFO)
```

## Contributing

When extending the Creative Director Agent:

1. Add tests with @pytest.mark.asyncio for async code
2. Update validation rules in Validator class
3. Add platform constraints to PLATFORM_CONSTRAINTS dict
4. Update this README with new features
5. Maintain min 90% code coverage for new code

## License

Proprietary - NTM Platform
