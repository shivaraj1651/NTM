# AGT-06: Creative Director Agent — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build an AI agent that generates platform-specific marketing campaign creatives (copy, image prompts, video concepts, voiceover scripts) using Claude API, with validation, auto-refinement, and version history.

**Architecture:** Modular component design with clear separation of concerns: Input Aggregator → Creative Generator (Claude) → Validator → Refiner (if needed) → Data Storage. Each component has its own file, tests, and well-defined interfaces.

**Tech Stack:** Python 3.12, FastAPI, Claude API (Anthropic SDK), Pydantic, PostgreSQL 16, pytest, SQLAlchemy ORM

---

## Task 1: Set up project structure and create test fixtures

**Files:**
- Create: `backend/app/agents/creative_director/__init__.py`
- Create: `backend/app/agents/creative_director/models.py`
- Create: `tests/test_agents/test_creative_director/__init__.py`
- Create: `tests/test_agents/test_creative_director/fixtures.py`
- Modify: `backend/app/agents/__init__.py` (export creative_director)

**Goal:** Establish the module structure, data models, and test fixtures needed for all downstream tasks.

---

### Task 1.1: Create data models and schemas

- [ ] **Step 1: Define Pydantic models for all data structures**

Create `backend/app/agents/creative_director/models.py`:

```python
from typing import Optional, Dict, List, Literal
from pydantic import BaseModel, Field
from datetime import datetime
import uuid

# Input Models
class BrandGuidelines(BaseModel):
    tone: str = Field(..., description="Brand voice/tone (e.g., 'professional', 'casual', 'humorous')")
    colors: List[str] = Field(..., description="Brand color palette")
    messaging_rules: List[str] = Field(..., description="Mandatory messaging requirements")
    mandatory_ctas: List[str] = Field(..., description="Required calls-to-action")
    visual_style: Optional[str] = None
    tagline: Optional[str] = None

class TargetAudience(BaseModel):
    demographics: Optional[Dict[str, str]] = None
    psychographics: Optional[Dict[str, str]] = None
    segments: Optional[List[str]] = None
    language: str = "en"

class CampaignInput(BaseModel):
    campaign_id: str = Field(..., description="Campaign UUID")
    tenant_id: str = Field(..., description="Tenant UUID")
    objectives: List[str] = Field(..., description="Campaign objectives/KPIs")
    target_audience: TargetAudience
    brand_guidelines: BrandGuidelines
    platforms: List[Literal["instagram", "linkedin", "youtube", "meta_ads", "tiktok", "twitter"]] = Field(
        ..., description="Target platforms"
    )
    budget_allocation: Optional[Dict[str, float]] = None
    product_details: str = Field(..., description="Product/service description")
    campaign_theme: str = Field(..., description="Campaign narrative/angle")
    primary_cta: str = Field(..., description="Primary call-to-action")
    competitor_insights: Optional[str] = None
    optional_assets: Optional[List[Dict[str, str]]] = None  # {url, type, description}
    channel_allocation: Optional[Dict[str, float]] = None  # e.g., {"instagram": 0.4, "linkedin": 0.3}

# Creative Models
class CreativeValidation(BaseModel):
    status: Literal["passed", "failed"]
    violations: List[Dict[str, str]] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)

class ImagePrompt(BaseModel):
    prompt: str = Field(..., description="DALL-E style prompt")
    style: Optional[str] = None
    validation: CreativeValidation = Field(default_factory=lambda: CreativeValidation(status="passed"))

class VideoConceptScene(BaseModel):
    duration_seconds: float
    description: str
    notes: Optional[str] = None

class VideoConcept(BaseModel):
    title: str
    hook: str = Field(..., description="Opening hook (first 3 seconds)")
    shots: List[VideoConceptScene]
    pacing_notes: Optional[str] = None
    duration_seconds: float
    validation: CreativeValidation = Field(default_factory=lambda: CreativeValidation(status="passed"))

class Copy(BaseModel):
    content: str
    character_count: int
    tone: str
    validation: CreativeValidation = Field(default_factory=lambda: CreativeValidation(status="passed"))

class VoiceoverScript(BaseModel):
    script: str
    duration_seconds: Optional[float] = None
    tone: str
    pacing: Optional[str] = None
    validation: CreativeValidation = Field(default_factory=lambda: CreativeValidation(status="passed"))

class PlatformCreatives(BaseModel):
    platform: str
    copy: List[Copy] = Field(default_factory=list)
    image_prompts: List[ImagePrompt] = Field(default_factory=list)
    video_concepts: List[VideoConcept] = Field(default_factory=list)
    voiceover_scripts: List[VoiceoverScript] = Field(default_factory=list)
    captions: List[Copy] = Field(default_factory=list)

class CoreConcept(BaseModel):
    message: str
    visual_direction: str
    audio_direction: Optional[str] = None
    tone: str

class GenerationMetadata(BaseModel):
    core_concept: CoreConcept
    validation_status: Literal["passed", "failed", "partial"]
    validation_summary: Optional[str] = None
    refinement_attempts: int = 0
    generation_time_ms: float = 0.0
    model_used: str = "claude-opus-4.7"
    errors: List[str] = Field(default_factory=list)

class CreativeDirectorOutput(BaseModel):
    campaign_id: str
    generation_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    tenant_id: str
    generated_at: datetime = Field(default_factory=datetime.utcnow)
    platforms: Dict[str, PlatformCreatives]
    metadata: GenerationMetadata
    error: Optional[Dict[str, str]] = None
```

- [ ] **Step 2: Run validation tests on models**

Create a simple test file `tests/test_agents/test_creative_director/test_models.py`:

```python
import pytest
from backend.app.agents.creative_director.models import (
    BrandGuidelines,
    CampaignInput,
    TargetAudience,
    CreativeValidation,
    Copy,
)

def test_brand_guidelines_valid():
    guidelines = BrandGuidelines(
        tone="professional",
        colors=["#003366", "#FF6600"],
        messaging_rules=["Always include brand name", "Emphasize quality"],
        mandatory_ctas=["Learn More", "Contact Us"],
    )
    assert guidelines.tone == "professional"
    assert len(guidelines.colors) == 2

def test_campaign_input_valid():
    input_data = CampaignInput(
        campaign_id="camp-123",
        tenant_id="tenant-456",
        objectives=["Increase brand awareness", "Drive conversions"],
        target_audience=TargetAudience(segments=["18-25", "urban"]),
        brand_guidelines=BrandGuidelines(
            tone="casual",
            colors=["#000", "#FFF"],
            messaging_rules=["Be fun"],
            mandatory_ctas=["Sign Up"],
        ),
        platforms=["instagram", "linkedin"],
        product_details="Cool product",
        campaign_theme="Summer vibes",
        primary_cta="Shop Now",
    )
    assert input_data.campaign_id == "camp-123"
    assert len(input_data.platforms) == 2

def test_copy_validation():
    copy = Copy(content="Buy now!", character_count=8, tone="urgent", validation=CreativeValidation(status="passed"))
    assert copy.validation.status == "passed"
```

Run: `pytest tests/test_agents/test_creative_director/test_models.py -v`
Expected: PASS (3 tests)

- [ ] **Step 3: Commit**

```bash
git add backend/app/agents/creative_director/models.py tests/test_agents/test_creative_director/test_models.py
git commit -m "[TASK-011] feat: add creative director data models and schemas"
```

---

### Task 1.2: Create test fixtures

- [ ] **Step 1: Write comprehensive test fixtures**

Create `tests/test_agents/test_creative_director/fixtures.py`:

```python
import pytest
from backend.app.agents.creative_director.models import (
    BrandGuidelines,
    TargetAudience,
    CampaignInput,
    CreativeValidation,
    Copy,
    CoreConcept,
    GenerationMetadata,
    PlatformCreatives,
    CreativeDirectorOutput,
)
from datetime import datetime
import uuid

@pytest.fixture
def brand_guidelines():
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
    """Mock Claude API response for creative generation"""
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
    """Valid generation output with all platforms"""
    return CreativeDirectorOutput(
        campaign_id=campaign_input.campaign_id,
        generation_id=str(uuid.uuid4()),
        tenant_id=campaign_input.tenant_id,
        generated_at=datetime.utcnow(),
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
                    {
                        "prompt": "Modern dashboard with team collaboration",
                        "style": "contemporary",
                        "validation": CreativeValidation(status="passed"),
                    }
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
        },
        metadata=GenerationMetadata(
            core_concept=CoreConcept(
                message="Simplify enterprise operations through intelligent automation",
                visual_direction="Modern dashboards, collaboration, clean UI",
                tone="professional-approachable",
            ),
            validation_status="passed",
            refinement_attempts=0,
            generation_time_ms=1250.5,
        ),
    )
```

- [ ] **Step 2: Verify fixtures compile**

Run: `python -c "from tests.test_agents.test_creative_director.fixtures import *; print('Fixtures loaded')"` (or just import in a test)

- [ ] **Step 3: Commit**

```bash
git add tests/test_agents/test_creative_director/fixtures.py
git commit -m "[TASK-011] feat: add comprehensive test fixtures for creative director"
```

---

### Task 1.3: Create module __init__.py and update agents __init__.py

- [ ] **Step 1: Create creative_director package __init__.py**

Create `backend/app/agents/creative_director/__init__.py`:

```python
from backend.app.agents.creative_director.models import (
    CampaignInput,
    CreativeDirectorOutput,
    BrandGuidelines,
    TargetAudience,
)

__all__ = [
    "CampaignInput",
    "CreativeDirectorOutput",
    "BrandGuidelines",
    "TargetAudience",
]
```

- [ ] **Step 2: Update agents/__init__.py to export creative_director**

Modify `backend/app/agents/__init__.py`, add at the top:

```python
from backend.app.agents import creative_director

__all__ = [
    "creative_director",
    # ... existing exports ...
]
```

- [ ] **Step 3: Commit**

```bash
git add backend/app/agents/creative_director/__init__.py backend/app/agents/__init__.py
git commit -m "[TASK-011] feat: initialize creative_director agent module structure"
```

---

## Task 2: Implement Input Aggregator

**Files:**
- Create: `backend/app/agents/creative_director/input_aggregator.py`
- Create: `tests/test_agents/test_creative_director/test_input_aggregator.py`

**Goal:** Consolidate inputs from upstream agents and validate required fields exist.

---

### Task 2.1: Implement Input Aggregator class

- [ ] **Step 1: Write the failing test**

Create `tests/test_agents/test_creative_director/test_input_aggregator.py`:

```python
import pytest
from backend.app.agents.creative_director.input_aggregator import InputAggregator
from backend.app.agents.creative_director.models import CampaignInput
from tests.test_agents.test_creative_director.fixtures import campaign_input

def test_aggregate_valid_input(campaign_input):
    """Test aggregating valid campaign input"""
    aggregator = InputAggregator()
    result = aggregator.aggregate(campaign_input)
    
    assert result.campaign_id == campaign_input.campaign_id
    assert result.tenant_id == campaign_input.tenant_id
    assert len(result.platforms) == 3
    assert "instagram" in result.platforms
    assert result.brand_guidelines.tone == "professional yet approachable"

def test_aggregate_requires_campaign_id(campaign_input):
    """Test that campaign_id is required"""
    campaign_input.campaign_id = None
    aggregator = InputAggregator()
    
    with pytest.raises(ValueError, match="campaign_id is required"):
        aggregator.aggregate(campaign_input)

def test_aggregate_requires_tenant_id(campaign_input):
    """Test that tenant_id is required"""
    campaign_input.tenant_id = None
    aggregator = InputAggregator()
    
    with pytest.raises(ValueError, match="tenant_id is required"):
        aggregator.aggregate(campaign_input)

def test_aggregate_requires_platforms(campaign_input):
    """Test that at least one platform is required"""
    campaign_input.platforms = []
    aggregator = InputAggregator()
    
    with pytest.raises(ValueError, match="At least one platform is required"):
        aggregator.aggregate(campaign_input)

def test_aggregate_requires_brand_guidelines(campaign_input):
    """Test that brand_guidelines are required"""
    campaign_input.brand_guidelines = None
    aggregator = InputAggregator()
    
    with pytest.raises(ValueError, match="brand_guidelines are required"):
        aggregator.aggregate(campaign_input)

def test_aggregate_normalizes_platform_names(campaign_input):
    """Test that platform names are normalized"""
    campaign_input.platforms = ["Instagram", "LINKEDIN", "youtube"]
    aggregator = InputAggregator()
    result = aggregator.aggregate(campaign_input)
    
    assert "instagram" in result.platforms
    assert "linkedin" in result.platforms
    assert "youtube" in result.platforms
```

Run: `pytest tests/test_agents/test_creative_director/test_input_aggregator.py -v`
Expected: FAIL (all 6 tests fail with "No module named 'input_aggregator'")

- [ ] **Step 2: Implement InputAggregator**

Create `backend/app/agents/creative_director/input_aggregator.py`:

```python
from typing import List
from backend.app.agents.creative_director.models import CampaignInput

class InputAggregator:
    """Consolidates and validates inputs from upstream agents and campaign config"""
    
    VALID_PLATFORMS = {
        "instagram", "linkedin", "youtube", "meta_ads", "tiktok", "twitter"
    }
    
    def aggregate(self, campaign_input: CampaignInput) -> CampaignInput:
        """
        Validate and normalize campaign input.
        
        Raises:
            ValueError: If required fields are missing or invalid
        """
        # Validate required fields
        if not campaign_input.campaign_id:
            raise ValueError("campaign_id is required")
        
        if not campaign_input.tenant_id:
            raise ValueError("tenant_id is required")
        
        if not campaign_input.platforms or len(campaign_input.platforms) == 0:
            raise ValueError("At least one platform is required")
        
        if campaign_input.brand_guidelines is None:
            raise ValueError("brand_guidelines are required")
        
        # Normalize platform names to lowercase
        normalized_platforms = [p.lower() for p in campaign_input.platforms]
        
        # Validate platform names
        invalid_platforms = [p for p in normalized_platforms if p not in self.VALID_PLATFORMS]
        if invalid_platforms:
            raise ValueError(f"Invalid platforms: {invalid_platforms}")
        
        campaign_input.platforms = normalized_platforms
        
        return campaign_input
    
    def validate_upstream_inputs(self, inputs: dict) -> dict:
        """
        Validate that all required upstream inputs are present.
        
        Args:
            inputs: Dict with keys like 'strategy', 'media_plan', 'budget', 'competitor_intel'
        
        Returns:
            Validated inputs dict
        
        Raises:
            ValueError: If required inputs missing
        """
        required = ['strategy', 'brand_guidelines', 'platforms']
        missing = [k for k in required if k not in inputs or inputs[k] is None]
        
        if missing:
            raise ValueError(f"Missing required inputs: {missing}")
        
        return inputs
```

- [ ] **Step 3: Run tests**

Run: `pytest tests/test_agents/test_creative_director/test_input_aggregator.py -v`
Expected: PASS (all 6 tests)

- [ ] **Step 4: Commit**

```bash
git add backend/app/agents/creative_director/input_aggregator.py tests/test_agents/test_creative_director/test_input_aggregator.py
git commit -m "[TASK-011] feat: implement input aggregator with validation"
```

---

## Task 3: Implement Validation Engine

**Files:**
- Create: `backend/app/agents/creative_director/validator.py`
- Create: `tests/test_agents/test_creative_director/test_validator.py`

**Goal:** Validate generated creatives against brand guidelines and platform constraints.

---

### Task 3.1: Implement Validator class

- [ ] **Step 1: Write the failing tests**

Create `tests/test_agents/test_creative_director/test_validator.py`:

```python
import pytest
from backend.app.agents.creative_director.validator import Validator
from backend.app.agents.creative_director.models import (
    CreativeValidation,
    Copy,
    ImagePrompt,
    BrandGuidelines,
)

@pytest.fixture
def validator():
    return Validator()

@pytest.fixture
def brand_guidelines():
    return BrandGuidelines(
        tone="professional",
        colors=["#003366", "#FF6600"],
        messaging_rules=["Always include company name", "Emphasize quality"],
        mandatory_ctas=["Learn More", "Contact Us"],
    )

def test_validate_copy_valid(validator):
    """Test validating valid copy"""
    copy = Copy(
        content="Quality matters. Learn More",
        character_count=28,
        tone="professional",
    )
    result = validator.validate_copy(copy, "instagram", {"mandatory_ctas": ["Learn More"]})
    assert result.status == "passed"
    assert len(result.violations) == 0

def test_validate_copy_exceeds_char_limit(validator):
    """Test copy exceeding platform character limit"""
    copy = Copy(
        content="A" * 200,
        character_count=200,
        tone="professional",
    )
    result = validator.validate_copy(copy, "instagram", {"max_chars": 150})
    assert result.status == "failed"
    assert len(result.violations) > 0

def test_validate_copy_missing_mandatory_cta(validator):
    """Test copy missing mandatory CTA"""
    copy = Copy(
        content="Great product",
        character_count=13,
        tone="professional",
    )
    result = validator.validate_copy(copy, "instagram", {"mandatory_ctas": ["Learn More", "Contact Us"]})
    assert result.status == "failed"
    assert any("CTA" in v.get("rule", "") for v in result.violations)

def test_validate_tone_compliance(validator, brand_guidelines):
    """Test tone compliance check"""
    copy = Copy(
        content="yo check it out Contact Us",
        character_count=26,
        tone="casual",  # Doesn't match brand "professional"
    )
    result = validator.validate_tone(copy, brand_guidelines.tone)
    assert result.status == "failed"
    assert any("tone" in v.get("rule", "").lower() for v in result.violations)

def test_platform_constraints_instagram(validator):
    """Test Instagram platform constraints"""
    constraints = validator.get_platform_constraints("instagram")
    assert constraints["max_chars"] == 2200
    assert "hashtag" in constraints

def test_platform_constraints_linkedin(validator):
    """Test LinkedIn platform constraints"""
    constraints = validator.get_platform_constraints("linkedin")
    assert constraints["max_chars"] == 3000

def test_platform_constraints_youtube(validator):
    """Test YouTube platform constraints"""
    constraints = validator.get_platform_constraints("youtube")
    assert constraints["max_chars_description"] == 5000
```

Run: `pytest tests/test_agents/test_creative_director/test_validator.py -v`
Expected: FAIL (all tests fail)

- [ ] **Step 2: Implement Validator class**

Create `backend/app/agents/creative_director/validator.py`:

```python
from typing import Dict, List, Literal
from backend.app.agents.creative_director.models import (
    CreativeValidation,
    Copy,
    ImagePrompt,
    VideoConcept,
    VoiceoverScript,
    BrandGuidelines,
)

PLATFORM_CONSTRAINTS = {
    "instagram": {
        "max_chars": 2200,
        "max_chars_caption": 150,
        "optimal_ratio": "1:1",
        "supports": ["hashtag", "emoji"],
        "cta_style": "swipe-up",
    },
    "linkedin": {
        "max_chars": 3000,
        "optimal_ratio": "1.91:1",
        "tone": "professional",
        "cta_style": "article",
    },
    "youtube": {
        "max_chars_title": 100,
        "max_chars_description": 5000,
        "optimal_ratio": "16:9",
        "cta_style": "subscribe",
    },
    "meta_ads": {
        "max_chars_primary": 125,
        "max_chars_description": 30,
        "optimal_ratio": ["1:1", "4:5", "9:16"],
        "cta_style": "button",
    },
    "tiktok": {
        "max_chars_caption": 150,
        "optimal_ratio": "9:16",
        "tone": "authentic",
        "cta_style": "hashtag",
    },
}

class Validator:
    """Validates generated creatives against brand and platform constraints"""
    
    def validate_copy(
        self,
        copy: Copy,
        platform: str,
        brand_rules: Dict,
    ) -> CreativeValidation:
        """
        Validate copy against platform and brand constraints.
        
        Args:
            copy: Copy object to validate
            platform: Target platform (instagram, linkedin, youtube, etc.)
            brand_rules: Brand guidelines dict with mandatory_ctas, tone, etc.
        
        Returns:
            CreativeValidation object with status and violations
        """
        violations = []
        
        # Check character limits
        constraints = self.get_platform_constraints(platform)
        max_chars = constraints.get("max_chars_caption") or constraints.get("max_chars", 999999)
        
        if copy.character_count > max_chars:
            violations.append({
                "rule": "character_limit",
                "severity": "error",
                "message": f"Exceeds {platform} limit of {max_chars} chars (got {copy.character_count})",
                "suggestion": "Shorten copy to meet platform limits",
            })
        
        # Check mandatory CTAs
        mandatory_ctas = brand_rules.get("mandatory_ctas", [])
        if mandatory_ctas:
            has_cta = any(cta.lower() in copy.content.lower() for cta in mandatory_ctas)
            if not has_cta:
                violations.append({
                    "rule": "missing_cta",
                    "severity": "error",
                    "message": f"Missing mandatory CTA. Must include one of: {mandatory_ctas}",
                    "suggestion": f"Add one of the required CTAs: {mandatory_ctas}",
                })
        
        status = "failed" if violations else "passed"
        return CreativeValidation(status=status, violations=violations)
    
    def validate_tone(
        self,
        copy: Copy,
        brand_tone: str,
    ) -> CreativeValidation:
        """
        Validate copy tone matches brand guidelines.
        
        Args:
            copy: Copy to validate
            brand_tone: Expected brand tone (professional, casual, humorous, etc.)
        
        Returns:
            CreativeValidation object
        """
        violations = []
        
        tone_compatibility = {
            "professional": ["professional", "formal", "corporate"],
            "casual": ["casual", "friendly", "conversational"],
            "humorous": ["humorous", "witty", "funny"],
        }
        
        # Simple tone matching (in production, could use ML model)
        if brand_tone in tone_compatibility:
            compatible_tones = tone_compatibility[brand_tone]
            if copy.tone.lower() not in compatible_tones:
                violations.append({
                    "rule": "tone_mismatch",
                    "severity": "warning",
                    "message": f"Tone '{copy.tone}' doesn't align with brand tone '{brand_tone}'",
                    "suggestion": f"Adjust tone to match: {compatible_tones}",
                })
        
        status = "failed" if any(v["severity"] == "error" for v in violations) else "passed"
        return CreativeValidation(status=status, violations=violations)
    
    def validate_image_prompt(
        self,
        prompt: ImagePrompt,
        platform: str,
    ) -> CreativeValidation:
        """Validate image prompt"""
        violations = []
        
        if not prompt.prompt or len(prompt.prompt.strip()) < 20:
            violations.append({
                "rule": "prompt_too_short",
                "severity": "error",
                "message": "Image prompt too short; must be at least 20 characters",
                "suggestion": "Add more detail to image prompt",
            })
        
        status = "failed" if violations else "passed"
        return CreativeValidation(status=status, violations=violations)
    
    def validate_video_concept(
        self,
        video: VideoConcept,
        platform: str,
    ) -> CreativeValidation:
        """Validate video concept"""
        violations = []
        
        if not video.shots or len(video.shots) == 0:
            violations.append({
                "rule": "no_shots",
                "severity": "error",
                "message": "Video concept must have at least one shot",
                "suggestion": "Add scene/shot descriptions",
            })
        
        if video.duration_seconds and video.duration_seconds > 120:
            violations.append({
                "rule": "duration_too_long",
                "severity": "warning",
                "message": f"Video duration {video.duration_seconds}s may be too long for {platform}",
                "suggestion": "Consider shortening video concept",
            })
        
        status = "failed" if any(v["severity"] == "error" for v in violations) else "passed"
        return CreativeValidation(status=status, violations=violations)
    
    def get_platform_constraints(self, platform: str) -> Dict:
        """Get constraint rules for a platform"""
        return PLATFORM_CONSTRAINTS.get(platform.lower(), {})
```

- [ ] **Step 3: Run tests**

Run: `pytest tests/test_agents/test_creative_director/test_validator.py -v`
Expected: PASS (all tests)

- [ ] **Step 4: Commit**

```bash
git add backend/app/agents/creative_director/validator.py tests/test_agents/test_creative_director/test_validator.py
git commit -m "[TASK-011] feat: implement validation engine with brand and platform constraints"
```

---

## Task 4: Implement Prompt Templates

**Files:**
- Create: `backend/app/agents/creative_director/prompts.py`

**Goal:** Create reusable Claude prompt templates for creative generation.

---

### Task 4.1: Implement prompt templates

- [ ] **Step 1: Create prompts.py**

Create `backend/app/agents/creative_director/prompts.py`:

```python
from typing import Dict

class CreativePrompts:
    """Claude prompt templates for creative generation"""
    
    @staticmethod
    def core_concept_prompt(campaign_input: Dict) -> str:
        """Generate prompt for creating core campaign concept"""
        return f"""You are a creative director helping develop a marketing campaign.

Campaign Context:
- Objectives: {', '.join(campaign_input['objectives'])}
- Target Audience: {campaign_input['target_audience_summary']}
- Theme: {campaign_input['campaign_theme']}
- Product: {campaign_input['product_details']}

Brand Guidelines:
- Tone: {campaign_input['brand_tone']}
- Messaging: {', '.join(campaign_input['messaging_rules'])}
- Colors: {', '.join(campaign_input['brand_colors'])}

Competitor Context:
{campaign_input.get('competitor_insights', 'N/A')}

Task: Create a unified core creative concept that:
1. Captures the campaign theme and objectives
2. Maintains brand voice and guidelines
3. Resonates with the target audience
4. Differentiates from competitors
5. Sets direction for platform-specific variations

Provide a JSON response with:
{{
  "message": "core message/narrative (2-3 sentences)",
  "visual_direction": "visual style and imagery direction",
  "audio_direction": "audio tone and style guidance",
  "tone": "overall tone of voice"
}}
"""

    @staticmethod
    def platform_specific_prompt(
        core_concept: Dict,
        platform: str,
        campaign_input: Dict,
        creative_type: str,
    ) -> str:
        """Generate prompt for platform-specific creatives"""
        
        platform_guidance = {
            "instagram": "Short-form, visual-first. Focus on stunning visuals and concise, punchy copy. Use hashtags and emojis strategically.",
            "linkedin": "Professional, thought-leading. Focus on business value and industry insights. B2B tone.",
            "youtube": "Long-form storytelling. Focus on narrative and emotional connection. Emphasis on value delivery and education.",
            "meta_ads": "Conversion-focused. Direct benefits, clear CTAs, urgency-driven. Varied ad formats (video, carousel, single image).",
            "tiktok": "Trending and authentic. Embrace platform culture, trending sounds, and challenge-style content. Casual, Gen Z friendly.",
        }
        
        return f"""You are a creative director creating {creative_type} for {platform}.

Core Campaign Concept:
- Message: {core_concept['message']}
- Visual Direction: {core_concept['visual_direction']}
- Audio Direction: {core_concept.get('audio_direction', 'N/A')}
- Tone: {core_concept['tone']}

Platform: {platform.upper()}
Platform Strategy: {platform_guidance.get(platform, 'General')}

Brand Guidelines:
- Tone: {campaign_input['brand_tone']}
- Mandatory CTAs: {', '.join(campaign_input['mandatory_ctas'])}
- Messaging Rules: {', '.join(campaign_input['messaging_rules'])}

Target Audience: {campaign_input['target_audience_summary']}
Campaign Theme: {campaign_input['campaign_theme']}
Primary CTA: {campaign_input['primary_cta']}

Task: Create 2-3 variations of {creative_type} for {platform} that:
1. Adapt the core concept for {platform}'s unique format and audience
2. Respect platform-specific constraints (length, format, style)
3. Include mandatory CTAs and align with brand guidelines
4. Drive toward campaign objectives

Provide a JSON array response:
[
  {{
    "type": "{creative_type}",
    "content": "the creative content",
    "tone": "tone of voice used",
    "platform_notes": "why this works for {platform}"
  }}
]
"""

    @staticmethod
    def refinement_prompt(
        original_creative: str,
        violations: list,
    ) -> str:
        """Generate prompt for refining invalid creatives"""
        violations_text = "\n".join([
            f"- {v.get('rule')}: {v.get('message')} (Suggestion: {v.get('suggestion')})"
            for v in violations
        ])
        
        return f"""The following creative did not pass validation:

Original Creative:
{original_creative}

Validation Violations:
{violations_text}

Task: Regenerate the creative to fix these violations while maintaining the core message and brand voice. 
Do not sacrifice quality for compliance; find creative solutions.

Provide the revised creative that addresses all violations."""
```

- [ ] **Step 2: Test prompts generate valid strings**

Create simple test `tests/test_agents/test_creative_director/test_prompts.py`:

```python
from backend.app.agents.creative_director.prompts import CreativePrompts

def test_core_concept_prompt_structure():
    input_data = {
        "objectives": ["Increase awareness", "Drive sales"],
        "target_audience_summary": "Tech professionals 25-45",
        "campaign_theme": "Digital Transformation",
        "product_details": "SaaS ERP platform",
        "brand_tone": "professional",
        "messaging_rules": ["Include company name"],
        "brand_colors": ["#003366", "#FF6600"],
    }
    
    prompt = CreativePrompts.core_concept_prompt(input_data)
    assert "Campaign Context:" in prompt
    assert "Digital Transformation" in prompt
    assert "JSON" in prompt

def test_platform_specific_prompt_structure():
    core_concept = {
        "message": "Simplify operations",
        "visual_direction": "Modern dashboards",
        "audio_direction": "Professional voiceover",
        "tone": "professional",
    }
    campaign_input = {
        "brand_tone": "professional",
        "mandatory_ctas": ["Learn More"],
        "messaging_rules": ["Company name"],
        "target_audience_summary": "Tech pros",
        "campaign_theme": "Digital",
        "primary_cta": "Schedule Demo",
    }
    
    prompt = CreativePrompts.platform_specific_prompt(
        core_concept,
        "instagram",
        campaign_input,
        "ad_copy"
    )
    
    assert "instagram" in prompt.lower()
    assert "Simplify operations" in prompt
    assert "ad_copy" in prompt

def test_refinement_prompt():
    original = "Buy now!"
    violations = [
        {"rule": "too_short", "message": "Copy too short", "suggestion": "Add more detail"},
    ]
    
    prompt = CreativePrompts.refinement_prompt(original, violations)
    assert "Buy now!" in prompt
    assert "too_short" in prompt
    assert "Validation Violations:" in prompt
```

Run: `pytest tests/test_agents/test_creative_director/test_prompts.py -v`
Expected: PASS

- [ ] **Step 3: Commit**

```bash
git add backend/app/agents/creative_director/prompts.py tests/test_agents/test_creative_director/test_prompts.py
git commit -m "[TASK-011] feat: implement Claude prompt templates for creative generation"
```

---

## Task 5: Implement Creative Brief Generator

**Files:**
- Create: `backend/app/agents/creative_director/generator.py`
- Create: `tests/test_agents/test_creative_director/test_generator.py`

**Goal:** Integrate with Claude API to generate platform-specific creatives.

---

### Task 5.1: Implement generator with Claude integration

- [ ] **Step 1: Write failing tests**

Create `tests/test_agents/test_creative_director/test_generator.py`:

```python
import pytest
from unittest.mock import AsyncMock, patch
from backend.app.agents.creative_director.generator import CreativeGenerator
from backend.app.agents.creative_director.models import CampaignInput
from tests.test_agents.test_creative_director.fixtures import campaign_input

@pytest.fixture
def generator():
    return CreativeGenerator(api_key="test-key")

@pytest.mark.asyncio
async def test_generate_core_concept(generator):
    """Test generating core campaign concept"""
    input_data = {
        "objectives": ["Increase awareness"],
        "target_audience_summary": "Tech pros",
        "campaign_theme": "Digital Transformation",
        "product_details": "SaaS ERP",
        "brand_tone": "professional",
        "messaging_rules": ["Include company"],
        "brand_colors": ["#003366"],
    }
    
    with patch.object(generator, '_call_claude') as mock_claude:
        mock_claude.return_value = {
            "message": "Simplify operations",
            "visual_direction": "Modern UI",
            "audio_direction": "Professional voice",
            "tone": "professional",
        }
        
        result = await generator.generate_core_concept(input_data)
        
        assert result["message"] == "Simplify operations"
        assert result["tone"] == "professional"
        mock_claude.assert_called_once()

@pytest.mark.asyncio
async def test_generate_platform_creatives(generator):
    """Test generating platform-specific creatives"""
    core_concept = {
        "message": "Simplify",
        "visual_direction": "Modern",
        "tone": "professional",
    }
    campaign_data = {
        "brand_tone": "professional",
        "mandatory_ctas": ["Learn More"],
        "messaging_rules": ["Company name"],
        "target_audience_summary": "Tech pros",
        "campaign_theme": "Digital",
        "primary_cta": "Schedule",
    }
    
    with patch.object(generator, '_call_claude') as mock_claude:
        mock_claude.return_value = [
            {
                "type": "copy",
                "content": "Schedule demo Learn More",
                "tone": "professional",
            }
        ]
        
        result = await generator.generate_platform_creatives(
            "instagram",
            core_concept,
            campaign_data,
            "copy"
        )
        
        assert len(result) > 0
        assert result[0]["content"] == "Schedule demo Learn More"

@pytest.mark.asyncio
async def test_retry_on_api_failure(generator):
    """Test exponential backoff retry on API failure"""
    with patch('asyncio.sleep') as mock_sleep:
        with patch.object(generator, '_make_api_call') as mock_api:
            # Fail twice, succeed on third
            mock_api.side_effect = [
                Exception("Rate limit"),
                Exception("Timeout"),
                {"message": "Success"},
            ]
            
            result = await generator._call_claude_with_retry("test prompt", max_retries=3)
            
            assert result["message"] == "Success"
            assert mock_api.call_count == 3
            assert mock_sleep.call_count == 2  # Two retries = two sleeps
```

Run: `pytest tests/test_agents/test_creative_director/test_generator.py -v`
Expected: FAIL (module doesn't exist)

- [ ] **Step 2: Implement CreativeGenerator**

Create `backend/app/agents/creative_director/generator.py`:

```python
import asyncio
import json
import logging
from typing import Dict, List, Any, Optional
from datetime import datetime
import time

from anthropic import AsyncAnthropic
from backend.app.agents.creative_director.prompts import CreativePrompts

logger = logging.getLogger(__name__)

class CreativeGenerator:
    """Generates creatives using Claude API with retry logic and error handling"""
    
    def __init__(self, api_key: Optional[str] = None, model: str = "claude-opus-4-7"):
        self.client = AsyncAnthropic(api_key=api_key)
        self.model = model
        self.max_retries = 3
        self.backoff_base = 2  # exponential backoff: 2^n seconds
    
    async def generate_core_concept(self, campaign_data: Dict[str, Any]) -> Dict[str, str]:
        """
        Generate unified core campaign concept using Claude.
        
        Args:
            campaign_data: Campaign input data with objectives, theme, audience, etc.
        
        Returns:
            Dict with message, visual_direction, audio_direction, tone
        
        Raises:
            Exception: If API fails after max retries
        """
        prompt = CreativePrompts.core_concept_prompt(campaign_data)
        
        logger.info("Generating core concept...")
        start_time = time.time()
        
        response = await self._call_claude_with_retry(prompt, max_retries=self.max_retries)
        
        elapsed_ms = (time.time() - start_time) * 1000
        logger.info(f"Core concept generated in {elapsed_ms:.0f}ms")
        
        return response
    
    async def generate_platform_creatives(
        self,
        platform: str,
        core_concept: Dict[str, str],
        campaign_data: Dict[str, Any],
        creative_type: str,
    ) -> List[Dict[str, Any]]:
        """
        Generate platform-specific creatives for a given type.
        
        Args:
            platform: Target platform (instagram, linkedin, etc.)
            core_concept: Core campaign concept from Stage 1
            campaign_data: Campaign input data
            creative_type: Type of creative (copy, image_prompt, video_concept, etc.)
        
        Returns:
            List of creative objects
        """
        prompt = CreativePrompts.platform_specific_prompt(
            core_concept,
            platform,
            campaign_data,
            creative_type,
        )
        
        logger.info(f"Generating {creative_type} for {platform}...")
        start_time = time.time()
        
        response = await self._call_claude_with_retry(prompt, max_retries=self.max_retries)
        
        elapsed_ms = (time.time() - start_time) * 1000
        logger.info(f"{creative_type} for {platform} generated in {elapsed_ms:.0f}ms")
        
        return response if isinstance(response, list) else [response]
    
    async def refine_creative(
        self,
        original_content: str,
        violations: List[Dict[str, str]],
    ) -> str:
        """
        Refine a creative that failed validation.
        
        Args:
            original_content: Original creative content
            violations: List of validation violations
        
        Returns:
            Refined creative content
        """
        prompt = CreativePrompts.refinement_prompt(original_content, violations)
        
        logger.info("Refining creative due to validation failures...")
        response = await self._call_claude_with_retry(prompt, max_retries=2)
        
        return response.get("content") or response if isinstance(response, str) else str(response)
    
    async def _call_claude_with_retry(
        self,
        prompt: str,
        max_retries: int = 3,
    ) -> Dict[str, Any]:
        """
        Call Claude API with exponential backoff retry.
        
        Args:
            prompt: Prompt to send to Claude
            max_retries: Maximum retry attempts
        
        Returns:
            Parsed JSON response from Claude
        
        Raises:
            Exception: If all retries exhausted
        """
        last_error = None
        
        for attempt in range(max_retries):
            try:
                return await self._make_api_call(prompt)
            except Exception as e:
                last_error = e
                if attempt < max_retries - 1:
                    wait_seconds = self.backoff_base ** attempt
                    logger.warning(
                        f"API call failed (attempt {attempt + 1}/{max_retries}): {str(e)}. "
                        f"Retrying in {wait_seconds}s..."
                    )
                    await asyncio.sleep(wait_seconds)
                else:
                    logger.error(f"API call failed after {max_retries} attempts: {str(e)}")
        
        raise Exception(
            f"Claude API unavailable after {max_retries} retries. "
            f"Last error: {str(last_error)}"
        )
    
    async def _make_api_call(self, prompt: str) -> Dict[str, Any]:
        """
        Make actual API call to Claude.
        
        Args:
            prompt: Prompt to send
        
        Returns:
            Parsed JSON from Claude response
        
        Raises:
            Exception: On API error or invalid JSON response
        """
        message = await self.client.messages.create(
            model=self.model,
            max_tokens=2000,
            messages=[
                {
                    "role": "user",
                    "content": prompt,
                }
            ],
        )
        
        # Extract text from response
        response_text = message.content[0].text
        
        # Parse JSON from response
        # Try to find JSON in response (sometimes Claude wraps it in markdown)
        json_start = response_text.find('{')
        json_end = response_text.rfind('}') + 1
        
        if json_start >= 0 and json_end > json_start:
            json_str = response_text[json_start:json_end]
            return json.loads(json_str)
        
        # Try as array
        json_start = response_text.find('[')
        json_end = response_text.rfind(']') + 1
        
        if json_start >= 0 and json_end > json_start:
            json_str = response_text[json_start:json_end]
            return json.loads(json_str)
        
        raise ValueError(f"Could not parse JSON from Claude response: {response_text[:200]}")
```

- [ ] **Step 3: Run tests (with mocking)**

Run: `pytest tests/test_agents/test_creative_director/test_generator.py -v`
Expected: PASS (tests with mocked Claude API)

- [ ] **Step 4: Commit**

```bash
git add backend/app/agents/creative_director/generator.py tests/test_agents/test_creative_director/test_generator.py
git commit -m "[TASK-011] feat: implement creative generator with Claude API integration and retry logic"
```

---

## Task 6: Implement Refinement Loop

**Files:**
- Create: `backend/app/agents/creative_director/refiner.py`
- Create: `tests/test_agents/test_creative_director/test_refiner.py`

**Goal:** Auto-refine creatives that fail validation.

---

### Task 6.1: Implement Refiner class

- [ ] **Step 1: Write failing tests**

Create `tests/test_agents/test_creative_director/test_refiner.py`:

```python
import pytest
from unittest.mock import AsyncMock, patch
from backend.app.agents.creative_director.refiner import Refiner
from backend.app.agents.creative_director.models import (
    Copy,
    CreativeValidation,
)

@pytest.fixture
def refiner():
    return Refiner(max_attempts=2)

@pytest.mark.asyncio
async def test_refine_with_max_attempts_exceeded():
    """Test that refiner respects max_attempts limit"""
    refiner = Refiner(max_attempts=1)
    
    invalid_copy = Copy(
        content="A" * 300,
        character_count=300,
        tone="professional",
    )
    
    validation_result = CreativeValidation(
        status="failed",
        violations=[{"rule": "too_long", "message": "Too long"}],
    )
    
    with patch.object(refiner.generator, 'refine_creative') as mock_refine:
        mock_refine.return_value = "A" * 300  # Still too long
        
        result = await refiner.refine(
            invalid_copy,
            validation_result,
            platform="instagram",
            brand_rules={"mandatory_ctas": ["Learn More"]},
        )
        
        # Should stop after max_attempts
        assert result["attempts"] <= 1
        assert result["status"] in ["passed", "failed"]

@pytest.mark.asyncio
async def test_refine_until_valid():
    """Test refiner auto-refines until valid"""
    refiner = Refiner(max_attempts=3)
    
    invalid_copy = Copy(
        content="A" * 200,
        character_count=200,
        tone="professional",
    )
    
    validation_result = CreativeValidation(
        status="failed",
        violations=[{"rule": "too_long"}],
    )
    
    with patch.object(refiner.generator, 'refine_creative') as mock_refine:
        # First refinement still fails, second passes
        mock_refine.side_effect = [
            "A" * 150,  # Still might fail
            "Short copy Learn More",  # Valid
        ]
        
        with patch.object(refiner.validator, 'validate_copy') as mock_validate:
            # First validation fails, second passes
            mock_validate.side_effect = [
                CreativeValidation(status="failed", violations=[{"rule": "too_long"}]),
                CreativeValidation(status="passed"),
            ]
            
            result = await refiner.refine(
                invalid_copy,
                validation_result,
                platform="instagram",
                brand_rules={"mandatory_ctas": ["Learn More"]},
            )
            
            assert result["status"] == "passed"
            assert result["attempts"] == 2

@pytest.mark.asyncio
async def test_refine_escalates_after_max_attempts():
    """Test that escalation happens after max attempts"""
    refiner = Refiner(max_attempts=2)
    
    invalid_copy = Copy(
        content="Short",
        character_count=5,
        tone="professional",
    )
    
    validation_result = CreativeValidation(
        status="failed",
        violations=[{"rule": "too_short"}],
    )
    
    with patch.object(refiner.generator, 'refine_creative') as mock_refine:
        mock_refine.side_effect = [
            "Still short",
            "Still very short",
        ]
        
        with patch.object(refiner.validator, 'validate_copy') as mock_validate:
            mock_validate.side_effect = [
                CreativeValidation(status="failed", violations=[{"rule": "too_short"}]),
                CreativeValidation(status="failed", violations=[{"rule": "too_short"}]),
                CreativeValidation(status="failed", violations=[{"rule": "too_short"}]),
            ]
            
            result = await refiner.refine(
                invalid_copy,
                validation_result,
                platform="instagram",
                brand_rules={"mandatory_ctas": ["Learn More"]},
            )
            
            # Should have escalated
            assert result["escalated"] is True
            assert result["attempts"] == 2
```

Run: `pytest tests/test_agents/test_creative_director/test_refiner.py -v`
Expected: FAIL

- [ ] **Step 2: Implement Refiner**

Create `backend/app/agents/creative_director/refiner.py`:

```python
import logging
from typing import Dict, Any
from backend.app.agents.creative_director.generator import CreativeGenerator
from backend.app.agents.creative_director.validator import Validator
from backend.app.agents.creative_director.models import (
    Copy,
    CreativeValidation,
)

logger = logging.getLogger(__name__)

class Refiner:
    """Refines creatives that fail validation up to max_attempts"""
    
    def __init__(self, max_attempts: int = 2):
        self.max_attempts = max_attempts
        self.generator = CreativeGenerator()
        self.validator = Validator()
    
    async def refine(
        self,
        creative: Copy,
        validation_result: CreativeValidation,
        platform: str,
        brand_rules: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Refine a creative until it passes validation or max_attempts exhausted.
        
        Args:
            creative: Creative content to refine
            validation_result: Initial validation result with violations
            platform: Target platform
            brand_rules: Brand guidelines for validation
        
        Returns:
            Dict with:
            - status: "passed" or "failed"
            - content: Refined creative content
            - attempts: Number of refinement attempts
            - violations: Final violations (if failed)
            - escalated: Whether escalated after max attempts
        """
        current_content = creative.content
        current_violations = validation_result.violations
        attempts = 0
        
        logger.info(f"Starting refinement loop for {platform} creative (max {self.max_attempts} attempts)")
        
        for attempt in range(1, self.max_attempts + 1):
            logger.info(f"Refinement attempt {attempt}/{self.max_attempts}")
            
            # Call Claude to refine
            refined_content = await self.generator.refine_creative(
                current_content,
                current_violations,
            )
            
            # Re-validate
            refined_creative = Copy(
                content=refined_content,
                character_count=len(refined_content),
                tone=creative.tone,
            )
            
            validation_result = self.validator.validate_copy(
                refined_creative,
                platform,
                brand_rules,
            )
            
            attempts += 1
            
            if validation_result.status == "passed":
                logger.info(f"Creative passed validation after {attempts} attempt(s)")
                return {
                    "status": "passed",
                    "content": refined_content,
                    "attempts": attempts,
                    "violations": [],
                    "escalated": False,
                }
            
            current_content = refined_content
            current_violations = validation_result.violations
            
            logger.warning(
                f"Attempt {attempt} still has violations: "
                f"{[v['rule'] for v in current_violations]}"
            )
        
        # Max attempts exhausted, escalate
        logger.warning(
            f"Creative failed to validate after {attempts} attempts. Escalating with partial status."
        )
        
        return {
            "status": "partial",
            "content": current_content,
            "attempts": attempts,
            "violations": current_violations,
            "escalated": True,
        }
```

- [ ] **Step 3: Run tests**

Run: `pytest tests/test_agents/test_creative_director/test_refiner.py -v`
Expected: PASS

- [ ] **Step 4: Commit**

```bash
git add backend/app/agents/creative_director/refiner.py tests/test_agents/test_creative_director/test_refiner.py
git commit -m "[TASK-011] feat: implement refinement loop with auto-iteration up to max attempts"
```

---

## Task 7: Implement Database Layer

**Files:**
- Create: `backend/alembic/versions/XXX_create_generated_creatives_table.py` (migration)
- Modify: `backend/app/models.py` or create schema file

**Goal:** Set up database schema for storing generated creatives with version history.

---

### Task 7.1: Create database migration

- [ ] **Step 1: Write migration**

Create `backend/alembic/versions/2026_05_09_00_create_generated_creatives_table.py`:

```python
"""Create generated_creatives table for storing campaign creatives"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = '2026_05_09_00'
down_revision = None  # Set to the previous migration ID
branch_labels = None
depends_on = None

def upgrade() -> None:
    op.create_table(
        'generated_creatives',
        sa.Column('id', sa.UUID(), nullable=False, server_default=sa.func.gen_random_uuid()),
        sa.Column('campaign_id', sa.UUID(), nullable=False),
        sa.Column('tenant_id', sa.UUID(), nullable=False),
        sa.Column('generation_id', sa.UUID(), nullable=False, server_default=sa.func.gen_random_uuid()),
        sa.Column('platform', sa.VARCHAR(50), nullable=False),
        sa.Column('creative_type', sa.VARCHAR(50), nullable=False),
        sa.Column('content', postgresql.JSONB(), nullable=False),
        sa.Column('validation_status', sa.VARCHAR(20), nullable=True),
        sa.Column('refinement_attempts', sa.Integer(), nullable=True, server_default='0'),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('campaign_id', 'generation_id', 'platform', 'creative_type', name='uq_creative_version'),
        sa.Index('ix_campaign_id', 'campaign_id'),
        sa.Index('ix_tenant_id', 'tenant_id'),
        sa.Index('ix_generation_id', 'generation_id'),
        sa.Index('ix_platform', 'platform'),
    )

def downgrade() -> None:
    op.drop_table('generated_creatives')
```

- [ ] **Step 2: Commit migration**

```bash
git add backend/alembic/versions/2026_05_09_00_create_generated_creatives_table.py
git commit -m "[TASK-011] feat: create database migration for generated_creatives table"
```

---

### Task 7.2: Create SQLAlchemy models

- [ ] **Step 1: Create database model**

Create or modify `backend/app/models/creative.py`:

```python
from sqlalchemy import Column, String, Integer, DateTime, Index, Uuid, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from datetime import datetime
import uuid

from backend.app.models.base import Base  # assuming Base class exists

class GeneratedCreative(Base):
    """Model for storing generated campaign creatives"""
    
    __tablename__ = "generated_creatives"
    
    id = Column(Uuid, primary_key=True, default=uuid.uuid4)
    campaign_id = Column(Uuid, nullable=False, index=True)
    tenant_id = Column(Uuid, nullable=False, index=True)
    generation_id = Column(Uuid, nullable=False, default=uuid.uuid4, index=True)
    platform = Column(String(50), nullable=False, index=True)
    creative_type = Column(String(50), nullable=False)
    content = Column(JSONB, nullable=False)
    validation_status = Column(String(20), nullable=True)
    refinement_attempts = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    __table_args__ = (
        UniqueConstraint('campaign_id', 'generation_id', 'platform', 'creative_type',
                        name='uq_creative_version'),
        Index('ix_campaign_id', 'campaign_id'),
        Index('ix_tenant_id', 'tenant_id'),
        Index('ix_generation_id', 'generation_id'),
        Index('ix_platform', 'platform'),
    )
    
    def to_dict(self):
        return {
            "id": str(self.id),
            "campaign_id": str(self.campaign_id),
            "tenant_id": str(self.tenant_id),
            "generation_id": str(self.generation_id),
            "platform": self.platform,
            "creative_type": self.creative_type,
            "content": self.content,
            "validation_status": self.validation_status,
            "refinement_attempts": self.refinement_attempts,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }
```

- [ ] **Step 2: Commit model**

```bash
git add backend/app/models/creative.py
git commit -m "[TASK-011] feat: create GeneratedCreative SQLAlchemy model"
```

---

## Task 8: Implement Main Agent Orchestrator

**Files:**
- Create: `backend/app/agents/creative_director.py` (main entry point)
- Create: `tests/test_agents/test_creative_director/test_integration.py`

**Goal:** Orchestrate all components to generate creatives from campaign input.

---

### Task 8.1: Implement orchestrator

- [ ] **Step 1: Write integration test**

Create `tests/test_agents/test_creative_director/test_integration.py`:

```python
import pytest
from unittest.mock import AsyncMock, patch
from backend.app.agents.creative_director import creative_director_agent
from backend.app.agents.creative_director.models import CreativeDirectorOutput
from tests.test_agents.test_creative_director.fixtures import campaign_input

@pytest.mark.asyncio
async def test_creative_director_agent_e2e(campaign_input):
    """End-to-end test of creative director agent"""
    
    mock_response = {
        "campaign_id": campaign_input.campaign_id,
        "generation_id": "gen-123",
        "tenant_id": campaign_input.tenant_id,
        "platforms": {
            "instagram": {
                "copy": [{"content": "Test copy", "character_count": 9, "tone": "casual"}],
            },
            "linkedin": {
                "copy": [{"content": "Professional copy", "character_count": 17, "tone": "professional"}],
            },
        },
        "metadata": {
            "core_concept": {
                "message": "Test message",
                "visual_direction": "Test",
                "tone": "professional",
            },
            "validation_status": "passed",
            "refinement_attempts": 0,
        },
    }
    
    with patch('backend.app.agents.creative_director.generate_creatives') as mock_gen:
        mock_gen.return_value = mock_response
        
        result = await creative_director_agent(campaign_input)
        
        assert isinstance(result, CreativeDirectorOutput)
        assert result.campaign_id == campaign_input.campaign_id
        assert "instagram" in result.platforms
        assert "linkedin" in result.platforms

@pytest.mark.asyncio
async def test_creative_director_handles_missing_inputs(campaign_input):
    """Test error handling for missing inputs"""
    campaign_input.campaign_id = None
    
    with pytest.raises(ValueError, match="campaign_id is required"):
        await creative_director_agent(campaign_input)
```

Run: `pytest tests/test_agents/test_creative_director/test_integration.py -v`
Expected: FAIL (module doesn't exist)

- [ ] **Step 2: Implement orchestrator**

Create `backend/app/agents/creative_director.py`:

```python
import logging
from typing import Optional
from datetime import datetime
import uuid

from backend.app.agents.creative_director.input_aggregator import InputAggregator
from backend.app.agents.creative_director.generator import CreativeGenerator
from backend.app.agents.creative_director.validator import Validator
from backend.app.agents.creative_director.refiner import Refiner
from backend.app.agents.creative_director.models import (
    CampaignInput,
    CreativeDirectorOutput,
    PlatformCreatives,
    CoreConcept,
    GenerationMetadata,
    Copy,
)

logger = logging.getLogger(__name__)

class CreativeDirectorAgent:
    """Main orchestrator for AGT-06 Creative Director Agent"""
    
    def __init__(self):
        self.aggregator = InputAggregator()
        self.generator = CreativeGenerator()
        self.validator = Validator()
        self.refiner = Refiner(max_attempts=2)
    
    async def generate(
        self,
        campaign_input: CampaignInput,
    ) -> CreativeDirectorOutput:
        """
        Generate platform-specific creatives for a campaign.
        
        Args:
            campaign_input: Campaign input with all required context
        
        Returns:
            CreativeDirectorOutput with generated creatives for all platforms
        
        Raises:
            ValueError: If validation fails or API calls fail
        """
        generation_id = str(uuid.uuid4())
        start_time = datetime.utcnow()
        
        logger.info(f"Starting creative generation for campaign {campaign_input.campaign_id}")
        
        try:
            # Step 1: Aggregate and validate inputs
            logger.info("Step 1: Aggregating and validating inputs...")
            validated_input = self.aggregator.aggregate(campaign_input)
            
            # Step 2: Generate core campaign concept
            logger.info("Step 2: Generating core campaign concept...")
            core_concept_data = {
                "objectives": validated_input.objectives,
                "target_audience_summary": self._summarize_audience(validated_input.target_audience),
                "campaign_theme": validated_input.campaign_theme,
                "product_details": validated_input.product_details,
                "brand_tone": validated_input.brand_guidelines.tone,
                "messaging_rules": validated_input.brand_guidelines.messaging_rules,
                "brand_colors": validated_input.brand_guidelines.colors,
                "mandatory_ctas": validated_input.brand_guidelines.mandatory_ctas,
                "competitor_insights": validated_input.competitor_insights,
            }
            
            core_concept_response = await self.generator.generate_core_concept(core_concept_data)
            core_concept = CoreConcept(**core_concept_response)
            
            # Step 3: Generate platform-specific creatives
            logger.info("Step 3: Generating platform-specific creatives...")
            platforms_dict = {}
            validation_status = "passed"
            validation_summary = ""
            errors = []
            
            for platform in validated_input.platforms:
                logger.info(f"Generating creatives for {platform}...")
                
                platform_creatives = PlatformCreatives(platform=platform)
                
                # Generate copy/captions
                try:
                    copy_responses = await self.generator.generate_platform_creatives(
                        platform,
                        core_concept.dict(),
                        core_concept_data,
                        "copy",
                    )
                    
                    for copy_data in copy_responses:
                        copy = Copy(
                            content=copy_data.get("content", ""),
                            character_count=len(copy_data.get("content", "")),
                            tone=copy_data.get("tone", platform),
                        )
                        
                        # Validate copy
                        validation = self.validator.validate_copy(
                            copy,
                            platform,
                            {
                                "mandatory_ctas": validated_input.brand_guidelines.mandatory_ctas,
                            },
                        )
                        copy.validation = validation
                        
                        # Refine if invalid
                        if validation.status == "failed":
                            refine_result = await self.refiner.refine(
                                copy,
                                validation,
                                platform,
                                {
                                    "mandatory_ctas": validated_input.brand_guidelines.mandatory_ctas,
                                },
                            )
                            
                            copy.content = refine_result["content"]
                            copy.character_count = len(refine_result["content"])
                            copy.validation.status = refine_result["status"]
                            copy.validation.violations = refine_result.get("violations", [])
                            
                            if refine_result.get("escalated"):
                                validation_status = "partial"
                        
                        platform_creatives.copy.append(copy)
                
                except Exception as e:
                    logger.error(f"Error generating copy for {platform}: {str(e)}")
                    errors.append(f"Copy generation failed for {platform}: {str(e)}")
                    validation_status = "failed"
                
                # Generate image prompts (simplified)
                try:
                    image_responses = await self.generator.generate_platform_creatives(
                        platform,
                        core_concept.dict(),
                        core_concept_data,
                        "image_prompt",
                    )
                    
                    for image_data in image_responses:
                        from backend.app.agents.creative_director.models import ImagePrompt
                        image = ImagePrompt(
                            prompt=image_data.get("prompt", ""),
                            style=image_data.get("style", ""),
                        )
                        validation = self.validator.validate_image_prompt(image, platform)
                        image.validation = validation
                        platform_creatives.image_prompts.append(image)
                
                except Exception as e:
                    logger.warning(f"Image prompt generation failed for {platform}: {str(e)}")
                
                platforms_dict[platform] = platform_creatives
            
            # Step 4: Compile output
            logger.info("Step 4: Compiling output...")
            
            if validation_status == "failed":
                validation_summary = f"Generation completed but validation failed. Errors: {errors}"
            elif validation_status == "partial":
                validation_summary = "Some creatives required refinement and may have partial violations."
            else:
                validation_summary = "All creatives passed validation."
            
            output = CreativeDirectorOutput(
                campaign_id=validated_input.campaign_id,
                generation_id=generation_id,
                tenant_id=validated_input.tenant_id,
                generated_at=datetime.utcnow(),
                platforms=platforms_dict,
                metadata=GenerationMetadata(
                    core_concept=core_concept,
                    validation_status=validation_status,
                    validation_summary=validation_summary,
                    refinement_attempts=0,  # Could track actual attempts
                    generation_time_ms=(datetime.utcnow() - start_time).total_seconds() * 1000,
                    errors=errors,
                ),
            )
            
            logger.info(f"Creative generation completed for campaign {campaign_input.campaign_id}")
            
            return output
        
        except Exception as e:
            logger.error(f"Creative generation failed: {str(e)}")
            raise
    
    def _summarize_audience(self, target_audience) -> str:
        """Create text summary of target audience"""
        parts = []
        if target_audience.demographics:
            parts.append(f"Demographics: {target_audience.demographics}")
        if target_audience.psychographics:
            parts.append(f"Psychographics: {target_audience.psychographics}")
        if target_audience.segments:
            parts.append(f"Segments: {target_audience.segments}")
        return "; ".join(parts) if parts else "Undefined audience"

# Public API function
async def creative_director_agent(campaign_input: CampaignInput) -> CreativeDirectorOutput:
    """
    Main entry point for AGT-06 Creative Director Agent.
    
    Args:
        campaign_input: Campaign input data
    
    Returns:
        Generated creatives organized by platform
    """
    agent = CreativeDirectorAgent()
    return await agent.generate(campaign_input)
```

- [ ] **Step 3: Run integration tests**

Run: `pytest tests/test_agents/test_creative_director/test_integration.py -v`
Expected: PASS (with mocked API)

- [ ] **Step 4: Commit**

```bash
git add backend/app/agents/creative_director.py tests/test_agents/test_creative_director/test_integration.py
git commit -m "[TASK-011] feat: implement creative director agent orchestrator"
```

---

## Task 9: Add FastAPI endpoint and API exports

**Files:**
- Create: `backend/app/routers/creative_director.py`
- Modify: `backend/app/routers/__init__.py`
- Modify: `backend/app/agents/__init__.py`

**Goal:** Expose creative director as API endpoint and export agent from module.

---

### Task 9.1: Create API endpoint

- [ ] **Step 1: Create router**

Create `backend/app/routers/creative_director.py`:

```python
from fastapi import APIRouter, HTTPException, status
from typing import Optional
import logging

from backend.app.agents.creative_director import creative_director_agent
from backend.app.agents.creative_director.models import (
    CampaignInput,
    CreativeDirectorOutput,
)

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/agents/creative-director",
    tags=["Creative Director Agent"],
)

@router.post("/generate", response_model=CreativeDirectorOutput)
async def generate_creatives(campaign_input: CampaignInput) -> CreativeDirectorOutput:
    """
    Generate platform-specific marketing creatives for a campaign.
    
    Accepts campaign context (strategy, brand guidelines, platform targets, etc.)
    and returns AI-generated ad copy, image prompts, video concepts, and voiceover scripts.
    
    Args:
        campaign_input: Campaign configuration and input data
    
    Returns:
        CreativeDirectorOutput with platform-specific creatives
    
    Raises:
        HTTPException 400: Invalid input
        HTTPException 500: Generation failed
    """
    try:
        logger.info(f"Received creative generation request for campaign {campaign_input.campaign_id}")
        result = await creative_director_agent(campaign_input)
        return result
    except ValueError as e:
        logger.warning(f"Invalid input: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid input: {str(e)}",
        )
    except Exception as e:
        logger.error(f"Creative generation failed: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Generation failed: {str(e)}",
        )

@router.get("/health")
async def health_check():
    """Check health of creative director agent"""
    return {"status": "healthy", "agent": "creative_director"}
```

- [ ] **Step 2: Register router in main app**

Modify `backend/app/routers/__init__.py`, add:

```python
from backend.app.routers import creative_director

# In router registration (usually in main.py or app.py):
# app.include_router(creative_director.router)
```

- [ ] **Step 3: Update agents exports**

Modify `backend/app/agents/__init__.py` to export:

```python
from backend.app.agents.creative_director import creative_director_agent

__all__ = [
    "creative_director_agent",
    # ... other agent exports ...
]
```

- [ ] **Step 4: Commit**

```bash
git add backend/app/routers/creative_director.py backend/app/routers/__init__.py backend/app/agents/__init__.py
git commit -m "[TASK-011] feat: add fastapi endpoint for creative director agent"
```

---

## Task 10: Final integration and comprehensive testing

**Files:**
- Modify: `tests/test_agents/test_creative_director/conftest.py` (if needed)
- Modify: Various test files

**Goal:** Ensure all components integrate correctly and tests pass.

---

### Task 10.1: Run full test suite

- [ ] **Step 1: Run all creative director tests**

Run: `pytest tests/test_agents/test_creative_director/ -v --cov=backend/app/agents/creative_director`

Expected: 90%+ coverage, all tests passing

- [ ] **Step 2: Run full agent test suite**

Run: `pytest tests/test_agents/ -v`

Expected: All agent tests passing (creative director + existing agents)

- [ ] **Step 3: Create comprehensive README**

Create `backend/app/agents/creative_director/README.md`:

```markdown
# Creative Director Agent (AGT-06)

## Overview

AGT-06 generates platform-specific marketing campaign creatives (copy, image prompts, video concepts, voiceover scripts) using Claude API.

## Input

Receives inputs from upstream agents and campaign configuration:
- Campaign objectives, target audience (Media Planner)
- Budget allocation (Budget Optimizer)
- Competitor insights (Competitive Intel)
- Brand guidelines, platform targets
- Product details, campaign theme, CTAs

## Output

Returns platform-specific creatives organized by target platform:
```json
{
  "platforms": {
    "instagram": {
      "copy": [...],
      "image_prompts": [...],
      "video_concepts": [...],
      "captions": [...]
    },
    "linkedin": {...},
    "youtube": {...},
    "meta_ads": {...}
  },
  "metadata": {
    "core_concept": {...},
    "validation_status": "passed|partial|failed",
    "refinement_attempts": 0
  }
}
```

## Components

- **InputAggregator** (`input_aggregator.py`) — Validates and normalizes campaign inputs
- **CreativeGenerator** (`generator.py`) — Claude API integration with retry logic
- **Validator** (`validator.py`) — Validates against brand guidelines and platform constraints
- **Refiner** (`refiner.py`) — Auto-refines invalid creatives up to 2 attempts
- **CreativeDirectorAgent** (`creative_director.py`) — Main orchestrator

## API Usage

```bash
POST /api/agents/creative-director/generate
Content-Type: application/json

{
  "campaign_id": "uuid",
  "tenant_id": "uuid",
  "objectives": ["Increase awareness", "Drive sales"],
  "target_audience": {...},
  "brand_guidelines": {...},
  "platforms": ["instagram", "linkedin", "youtube"],
  "product_details": "...",
  "campaign_theme": "...",
  "primary_cta": "..."
}
```

## Testing

Run tests:
```bash
pytest tests/test_agents/test_creative_director/ -v --cov
```

## Future Enhancements

- Actual media generation (DALL-E for images, Eleven Labs for voiceovers)
- Embedding-based search for similar past creatives
- Multi-language support
- A/B testing and performance tracking
```

- [ ] **Step 4: Final commit**

```bash
git add backend/app/agents/creative_director/README.md
git commit -m "[TASK-011] feat: add comprehensive documentation for creative director agent"
```

---

## Summary

**Plan scope:** Full implementation of AGT-06 Creative Director Agent with:
- Modular component architecture
- Input aggregation and validation
- Claude API integration with retry logic
- Validation engine with brand and platform constraints
- Auto-refinement loop (max 2 attempts)
- Database persistence with version history
- FastAPI endpoint
- Comprehensive test coverage (>90%)

**Total tasks:** 10 (40-50 individual steps)
**Estimated effort:** 8-10 hours for experienced developer
**Key milestones:**
1. ✓ Data models and fixtures (Task 1)
2. ✓ Input Aggregator (Task 2)
3. ✓ Validation Engine (Task 3)
4. ✓ Prompt Templates (Task 4)
5. ✓ Creative Generator (Task 5)
6. ✓ Refinement Loop (Task 6)
7. ✓ Database Layer (Task 7)
8. ✓ Orchestrator (Task 8)
9. ✓ API Endpoint (Task 9)
10. ✓ Testing & Documentation (Task 10)

**Tech Stack:**
- Python 3.12, FastAPI, Claude API (Anthropic SDK)
- Pydantic for validation
- PostgreSQL 16 with SQLAlchemy ORM
- pytest for testing
- Alembic for migrations
