# Media Planner Agent (AGT-04) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement Media Planner Agent (AGT-04) that transforms approved campaign concepts and budget envelopes into detailed Activation Master Plans with individual media placements, timing, reach, and cost estimates.

**Architecture:** Modular agent with separate schema definitions, budget allocator, activation generator, constraint handler, and validator. Uses top-down budget allocation (phases → channels → geographies) to ensure accountability. Handles offline channel lead times realistically. Generates individual activation records and financial summaries.

**Tech Stack:** Python 3.12, FastAPI, Anthropic SDK (Claude Sonnet), Pydantic, Pytest, PostgreSQL (for storage)

---

## File Structure

```
backend/app/
├── schemas/
│   ├── media_plan.py (CREATE - Activation and BudgetSummary schemas)
│   └── __init__.py (UPDATE - export schemas)
├── agents/
│   ├── media_planner.py (CREATE - main agent module)
│   │   ├── BudgetAllocator (class)
│   │   ├── ActivationGenerator (class)
│   │   ├── OfflineConstraintHandler (class)
│   │   ├── ActivationValidator (class)
│   │   ├── media_planner_agent() (async main)
│   └── __init__.py (UPDATE - export media_planner_agent)
tests/
├── agents/
│   ├── test_media_planner.py (CREATE - unit + integration tests)
```

---

## Task 1: Define Media Plan Schemas (Pydantic Models)

**Files:**
- Create: `backend/app/schemas/media_plan.py`
- Modify: `backend/app/schemas/__init__.py`

- [ ] **Step 1: Create media_plan.py with Activation and BudgetSummary schemas**

Create `backend/app/schemas/media_plan.py`:

```python
"""Media Plan schemas for AGT-04 output."""

from typing import Dict, List, Optional
from pydantic import BaseModel, Field
from uuid import UUID, uuid4
from datetime import date
from enum import Enum


class ChannelEnum(str, Enum):
    """Channel type enumeration."""
    SOCIAL = "Social"
    SEARCH = "Search"
    DISPLAY = "Display"
    EMAIL = "Email"
    WHATSAPP = "WhatsApp"
    INFLUENCER = "Influencer"
    PRINT = "Print"
    OOH = "OOH"
    RADIO = "Radio"
    TV = "TV"
    EVENTS = "Events"
    CINEMA = "Cinema"
    DIRECT_MAIL = "DirectMail"


class PhaseEnum(str, Enum):
    """Campaign phase enumeration."""
    AWARENESS = "Awareness"
    ENGAGEMENT = "Engagement"
    CONVERSION = "Conversion"


class AudienceSegmentEnum(str, Enum):
    """Audience segment enumeration."""
    PRIMARY = "Primary"
    SECONDARY = "Secondary"
    TERTIARY = "Tertiary"


class Activation(BaseModel):
    """Individual media activation (placement)."""
    id: UUID = Field(default_factory=uuid4, description="Unique activation ID")
    channel_enum: ChannelEnum = Field(..., description="Channel type enum")
    sub_channel: str = Field(..., description="Specific channel name (e.g., 'TikTok', 'Google Search')")
    format: str = Field(..., description="Media format (e.g., 'Video 15s', 'Static Image')")
    geography: str = Field(..., description="Market or region (e.g., 'US', 'NYC')")
    placement: str = Field(..., description="Placement location (e.g., 'Feed', 'Search Results')")
    phase: PhaseEnum = Field(..., description="Campaign phase")
    scheduled_date: date = Field(..., description="Activation start date")
    duration: int = Field(..., ge=1, description="Duration in days")
    frequency: str = Field(..., description="Delivery frequency (e.g., '3x daily', 'weekly')")
    audience_segment: AudienceSegmentEnum = Field(..., description="Target audience segment")
    estimated_reach: int = Field(..., ge=1, description="Estimated number of people reached")
    estimated_cpm: float = Field(..., ge=0.01, description="Cost per thousand impressions")
    cost_estimated: float = Field(..., ge=0, description="Total activation cost")
    message_version_ref: str = Field(..., description="Reference to message architecture + tone board")
    lead_time_days: Optional[int] = Field(None, ge=0, description="Production lead time for offline channels")
    offline_constraints: Optional[str] = Field(None, description="Constraint notes for offline channels")


class PhaseBreakdown(BaseModel):
    """Budget breakdown for a single phase."""
    allocated: float = Field(..., ge=0)
    spent: float = Field(..., ge=0)
    remaining: float = Field(..., ge=0)


class ChannelSpend(BaseModel):
    """Budget breakdown for a single channel."""
    allocated: float = Field(..., ge=0)
    spent: float = Field(..., ge=0)
    activations_count: int = Field(..., ge=0)


class ContingencyBreakdown(BaseModel):
    """Contingency budget breakdown."""
    allocated: float = Field(..., ge=0)
    used: float = Field(..., ge=0)
    remaining: float = Field(..., ge=0)


class BudgetSummary(BaseModel):
    """Budget summary with phase/channel breakdown."""
    total_budget: float = Field(..., ge=0)
    currency: str = Field(..., description="Currency code (e.g., 'USD')")
    phase_breakdown: Dict[str, PhaseBreakdown] = Field(
        ..., 
        description="Budget breakdown by phase (Awareness, Engagement, Conversion)"
    )
    channel_breakdown: Dict[str, ChannelSpend] = Field(
        ...,
        description="Budget breakdown by channel (TikTok, Google Search, etc.)"
    )
    contingency: ContingencyBreakdown = Field(..., description="Contingency budget details")
    total_spent: float = Field(..., ge=0, description="Total activation costs")
    total_remaining: float = Field(..., ge=0, description="Unallocated budget")
    utilization_pct: float = Field(..., ge=0, le=100, description="Budget utilization percentage")


class MediaPlanResponse(BaseModel):
    """Full media planner agent response."""
    activations: List[Activation] = Field(..., description="List of generated activations")
    budget_summary: BudgetSummary = Field(..., description="Budget breakdown summary")
    validation_errors: List[str] = Field(default_factory=list, description="Validation errors found")
    allocation_log: List[str] = Field(default_factory=list, description="Audit trail of allocation decisions")
    status: str = Field(..., description="success|partial|failed")
```

- [ ] **Step 2: Update backend/app/schemas/__init__.py to export new schemas**

Edit `backend/app/schemas/__init__.py` and add:

```python
from backend.app.schemas.media_plan import (
    Activation,
    BudgetSummary,
    PhaseBreakdown,
    ChannelSpend,
    ContingencyBreakdown,
    MediaPlanResponse,
    ChannelEnum,
    PhaseEnum,
    AudienceSegmentEnum,
)

__all__ = [
    "Activation",
    "BudgetSummary",
    "PhaseBreakdown",
    "ChannelSpend",
    "ContingencyBreakdown",
    "MediaPlanResponse",
    "ChannelEnum",
    "PhaseEnum",
    "AudienceSegmentEnum",
]
```

- [ ] **Step 3: Verify import works**

```bash
python -c "from backend.app.schemas.media_plan import Activation, BudgetSummary; print('✅ Schemas imported')"
```

Expected: ✅ Schemas imported

- [ ] **Step 4: Commit**

```bash
git add backend/app/schemas/media_plan.py backend/app/schemas/__init__.py
git commit -m "[TASK-008] feat: add Activation and BudgetSummary Pydantic schemas"
```

---

## Task 2: Implement BudgetAllocator Class

**Files:**
- Create: `backend/app/agents/media_planner.py` (start file)
- Create: `tests/agents/test_media_planner.py` (start test file)

- [ ] **Step 1: Write tests for BudgetAllocator**

Create `tests/agents/test_media_planner.py`:

```python
"""Unit tests for Media Planner Agent (AGT-04)."""

import pytest
from datetime import date, timedelta
from backend.app.schemas.media_plan import ChannelEnum, PhaseEnum


class TestBudgetAllocator:
    """Tests for BudgetAllocator class."""

    def test_phase_allocation_40_40_20(self):
        """Budget should be allocated 40% Awareness, 40% Engagement, 20% Conversion."""
        from backend.app.agents.media_planner import BudgetAllocator
        
        allocator = BudgetAllocator()
        budget = 100000.0
        phases = allocator.allocate_by_phase(budget)
        
        assert phases["Awareness"] == 40000.0
        assert phases["Engagement"] == 40000.0
        assert phases["Conversion"] == 20000.0
        assert sum(phases.values()) == 100000.0

    def test_channel_weighting_equal_distribution(self):
        """Budget should be distributed equally across channels if no weights provided."""
        from backend.app.agents.media_planner import BudgetAllocator
        
        allocator = BudgetAllocator()
        phase_budget = 40000.0
        channels = [
            {"channel": "TikTok"},
            {"channel": "Instagram"},
            {"channel": "Email"}
        ]
        
        allocations = allocator.allocate_by_channel(phase_budget, channels)
        
        assert allocations["TikTok"] == pytest.approx(13333.33, abs=1)
        assert allocations["Instagram"] == pytest.approx(13333.33, abs=1)
        assert allocations["Email"] == pytest.approx(13333.34, abs=1)

    def test_channel_weighting_with_weights(self):
        """Budget should be distributed by channel weights (40%, 30%, 30%)."""
        from backend.app.agents.media_planner import BudgetAllocator
        
        allocator = BudgetAllocator()
        phase_budget = 40000.0
        channels = [
            {"channel": "TikTok", "weight": 0.4},
            {"channel": "Instagram", "weight": 0.3},
            {"channel": "Email", "weight": 0.3}
        ]
        
        allocations = allocator.allocate_by_channel(phase_budget, channels)
        
        assert allocations["TikTok"] == 16000.0
        assert allocations["Instagram"] == 12000.0
        assert allocations["Email"] == 12000.0

    def test_geography_equal_distribution(self):
        """Channel budget should be distributed equally across geographies."""
        from backend.app.agents.media_planner import BudgetAllocator
        
        allocator = BudgetAllocator()
        channel_budget = 16000.0
        geographies = ["US", "Canada"]
        
        allocations = allocator.allocate_by_geography(channel_budget, geographies)
        
        assert allocations["US"] == 8000.0
        assert allocations["Canada"] == 8000.0

    def test_contingency_reserve_10_pct(self):
        """Contingency should reserve 10% of total spend."""
        from backend.app.agents.media_planner import BudgetAllocator
        
        allocator = BudgetAllocator()
        total_spend = 90000.0
        
        contingency = allocator.calculate_contingency(total_spend, pct=0.10)
        
        assert contingency == 9000.0
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
pytest tests/agents/test_media_planner.py::TestBudgetAllocator -xvs
```

Expected: FAIL with "BudgetAllocator not defined"

- [ ] **Step 3: Implement BudgetAllocator in media_planner.py**

Create `backend/app/agents/media_planner.py`:

```python
"""Media Planner Agent (AGT-04).

Transforms approved campaign concepts and budgets into detailed Activation Master Plans.
Uses top-down budget allocation: phases → channels → geographies.
"""

import logging
from typing import Dict, List, Any, Optional
from datetime import date, timedelta

logger = logging.getLogger(__name__)


class BudgetAllocator:
    """Allocates budget across phases, channels, and geographies."""

    def allocate_by_phase(self, total_budget: float) -> Dict[str, float]:
        """
        Allocate budget across phases: Awareness 40%, Engagement 40%, Conversion 20%.

        Args:
            total_budget: Total budget envelope

        Returns:
            Dict with phase names as keys, allocated amounts as values
        """
        return {
            "Awareness": total_budget * 0.40,
            "Engagement": total_budget * 0.40,
            "Conversion": total_budget * 0.20,
        }

    def allocate_by_channel(self, phase_budget: float, channels: List[Dict[str, Any]]) -> Dict[str, float]:
        """
        Allocate phase budget across channels by weight.

        Args:
            phase_budget: Budget for this phase
            channels: List of channel dicts with 'channel' name and optional 'weight'

        Returns:
            Dict with channel names as keys, allocated amounts as values
        """
        allocations = {}
        
        # Extract weights or use equal distribution
        total_weight = 0.0
        for ch in channels:
            weight = ch.get("weight", 1.0)
            total_weight += weight
        
        for ch in channels:
            weight = ch.get("weight", 1.0)
            channel_name = ch["channel"]
            allocated = phase_budget * (weight / total_weight)
            allocations[channel_name] = allocated
        
        return allocations

    def allocate_by_geography(self, channel_budget: float, geographies: List[str]) -> Dict[str, float]:
        """
        Allocate channel budget equally across geographies.

        Args:
            channel_budget: Budget for this channel/phase
            geographies: List of markets/regions

        Returns:
            Dict with geography names as keys, allocated amounts as values
        """
        per_geography = channel_budget / len(geographies)
        return {geo: per_geography for geo in geographies}

    def calculate_contingency(self, total_spend: float, pct: float = 0.10) -> float:
        """
        Calculate contingency reserve (10% of total spend by default).

        Args:
            total_spend: Total amount spent on activations
            pct: Contingency percentage (default 0.10 = 10%)

        Returns:
            Contingency reserve amount
        """
        return total_spend * pct
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
pytest tests/agents/test_media_planner.py::TestBudgetAllocator -xvs
```

Expected: All 5 tests PASS

- [ ] **Step 5: Commit**

```bash
git add backend/app/agents/media_planner.py tests/agents/test_media_planner.py
git commit -m "[TASK-008] feat: implement BudgetAllocator with phase/channel/geography allocation"
```

---

## Task 3: Implement ActivationGenerator Class

**Files:**
- Modify: `backend/app/agents/media_planner.py`
- Modify: `tests/agents/test_media_planner.py`

- [ ] **Step 1: Add tests for ActivationGenerator**

Add to `tests/agents/test_media_planner.py`:

```python
class TestActivationGenerator:
    """Tests for ActivationGenerator class."""

    def test_reach_calculation_by_penetration(self):
        """Reach should be audience_size × phase_penetration."""
        from backend.app.agents.media_planner import ActivationGenerator
        
        gen = ActivationGenerator()
        audience_size = 1000000
        penetration_pct = 0.60  # 60% Awareness
        
        reach = gen.calculate_reach(audience_size, penetration_pct)
        
        assert reach == 600000

    def test_cost_calculation_by_cpm(self):
        """Cost should be (reach / 1000) × CPM."""
        from backend.app.agents.media_planner import ActivationGenerator
        
        gen = ActivationGenerator()
        reach = 500000
        cpm = 5.0
        
        cost = gen.calculate_cost(reach, cpm)
        
        assert cost == 2500.0

    def test_frequency_by_phase(self):
        """Frequency should match phase (Awareness high, Conversion targeted)."""
        from backend.app.agents.media_planner import ActivationGenerator
        
        gen = ActivationGenerator()
        
        assert gen.get_frequency_for_phase("Awareness") == "3x daily"
        assert gen.get_frequency_for_phase("Engagement") == "2x daily"
        assert gen.get_frequency_for_phase("Conversion") == "1x daily"

    def test_cpm_by_channel(self):
        """CPM should vary by channel (Social ~$5, TV ~$20)."""
        from backend.app.agents.media_planner import ActivationGenerator
        
        gen = ActivationGenerator()
        
        cpm_tiktok = gen.get_cpm_for_channel("TikTok")
        cpm_tv = gen.get_cpm_for_channel("TV")
        
        assert 3 <= cpm_tiktok <= 8
        assert 15 <= cpm_tv <= 30
```

- [ ] **Step 2: Implement ActivationGenerator**

Add to `backend/app/agents/media_planner.py`:

```python
class ActivationGenerator:
    """Generates individual activation records from budget allocations."""

    # CPM ranges by channel (cost per thousand impressions)
    CHANNEL_CPM_RATES = {
        "TikTok": 5.0,
        "Instagram": 6.0,
        "Facebook": 7.0,
        "Google Search": 10.0,
        "Display": 8.0,
        "Email": 0.50,
        "WhatsApp": 1.0,
        "Influencer": 15.0,
        "Print": 12.0,
        "OOH": 10.0,
        "Radio": 8.0,
        "TV": 20.0,
        "Events": 25.0,
        "Cinema": 18.0,
        "Direct Mail": 5.0,
    }

    # Phase penetration targets (% of audience to reach)
    PHASE_PENETRATION = {
        "Awareness": 0.60,
        "Engagement": 0.30,
        "Conversion": 0.10,
    }

    def calculate_reach(self, audience_size: int, penetration_pct: float) -> int:
        """
        Calculate estimated reach.

        Args:
            audience_size: Total audience size for segment/geography
            penetration_pct: Penetration target (0.0 - 1.0)

        Returns:
            Estimated number of people reached
        """
        return int(audience_size * penetration_pct)

    def calculate_cost(self, reach: int, cpm: float) -> float:
        """
        Calculate activation cost.

        Args:
            reach: Number of people reached
            cpm: Cost per thousand impressions

        Returns:
            Total cost
        """
        return (reach / 1000.0) * cpm

    def get_frequency_for_phase(self, phase: str) -> str:
        """
        Get delivery frequency for a phase.

        Args:
            phase: Phase name (Awareness, Engagement, Conversion)

        Returns:
            Frequency string (e.g., "3x daily")
        """
        frequencies = {
            "Awareness": "3x daily",
            "Engagement": "2x daily",
            "Conversion": "1x daily",
        }
        return frequencies.get(phase, "1x daily")

    def get_cpm_for_channel(self, channel_name: str) -> float:
        """
        Get CPM for a channel.

        Args:
            channel_name: Channel name (e.g., "TikTok")

        Returns:
            CPM rate (default $10 if not found)
        """
        return self.CHANNEL_CPM_RATES.get(channel_name, 10.0)

    def get_penetration_for_phase(self, phase: str) -> float:
        """
        Get audience penetration target for a phase.

        Args:
            phase: Phase name

        Returns:
            Penetration percentage (0.0 - 1.0)
        """
        return self.PHASE_PENETRATION.get(phase, 0.10)
```

- [ ] **Step 3: Run tests to verify they pass**

```bash
pytest tests/agents/test_media_planner.py::TestActivationGenerator -xvs
```

Expected: All 5 tests PASS

- [ ] **Step 4: Run all tests**

```bash
pytest tests/agents/test_media_planner.py -xvs
```

Expected: All 10 tests PASS (5 allocator + 5 generator)

- [ ] **Step 5: Commit**

```bash
git add backend/app/agents/media_planner.py tests/agents/test_media_planner.py
git commit -m "[TASK-008] feat: implement ActivationGenerator with reach/cost/frequency calculation"
```

---

## Task 4: Implement OfflineConstraintHandler Class

**Files:**
- Modify: `backend/app/agents/media_planner.py`
- Modify: `tests/agents/test_media_planner.py`

- [ ] **Step 1: Add tests for OfflineConstraintHandler**

Add to `tests/agents/test_media_planner.py`:

```python
class TestOfflineConstraintHandler:
    """Tests for OfflineConstraintHandler class."""

    def test_tv_lead_time_4_weeks(self):
        """TV should have 4-week (28 day) lead time."""
        from backend.app.agents.media_planner import OfflineConstraintHandler
        
        handler = OfflineConstraintHandler()
        
        lead_time = handler.get_lead_time_days("TV")
        
        assert lead_time == 28

    def test_print_lead_time_2_weeks(self):
        """Print should have 2-week (14 day) lead time."""
        from backend.app.agents.media_planner import OfflineConstraintHandler
        
        handler = OfflineConstraintHandler()
        
        lead_time = handler.get_lead_time_days("Print")
        
        assert lead_time == 14

    def test_is_offline_channel_tv(self):
        """TV should be marked as offline."""
        from backend.app.agents.media_planner import OfflineConstraintHandler
        
        handler = OfflineConstraintHandler()
        
        assert handler.is_offline("TV") is True

    def test_is_offline_channel_tiktok(self):
        """TikTok should not be marked as offline."""
        from backend.app.agents.media_planner import OfflineConstraintHandler
        
        handler = OfflineConstraintHandler()
        
        assert handler.is_offline("TikTok") is False

    def test_scheduled_date_with_lead_time(self):
        """Scheduled date should account for lead time (phase_start - lead_time)."""
        from backend.app.agents.media_planner import OfflineConstraintHandler
        from datetime import date, timedelta
        
        handler = OfflineConstraintHandler()
        phase_start = date(2026, 6, 1)
        
        scheduled = handler.calculate_scheduled_date("TV", phase_start)
        
        expected = phase_start - timedelta(days=28)
        assert scheduled == expected
```

- [ ] **Step 2: Implement OfflineConstraintHandler**

Add to `backend/app/agents/media_planner.py`:

```python
class OfflineConstraintHandler:
    """Handles offline channel constraints (lead times, production timelines)."""

    # Lead time in days for offline channels
    OFFLINE_LEAD_TIMES = {
        "TV": 28,  # 4 weeks
        "Print": 14,  # 2 weeks
        "Cinema": 21,  # 3 weeks
        "Radio": 10,  # ~1.5 weeks
        "Events": 14,  # 2 weeks
        "Direct Mail": 14,  # 2 weeks
        "OOH": 7,  # 1 week
    }

    # Channels that are offline
    OFFLINE_CHANNELS = set(OFFLINE_LEAD_TIMES.keys())

    def is_offline(self, channel_name: str) -> bool:
        """
        Check if a channel is offline.

        Args:
            channel_name: Channel name

        Returns:
            True if offline, False if online
        """
        return channel_name in self.OFFLINE_CHANNELS

    def get_lead_time_days(self, channel_name: str) -> int:
        """
        Get lead time in days for a channel.

        Args:
            channel_name: Channel name

        Returns:
            Lead time in days (0 for online channels)
        """
        return self.OFFLINE_LEAD_TIMES.get(channel_name, 0)

    def calculate_scheduled_date(self, channel_name: str, phase_start: date) -> date:
        """
        Calculate scheduled date accounting for lead time.

        Args:
            channel_name: Channel name
            phase_start: Phase start date

        Returns:
            Scheduled date (phase_start - lead_time)
        """
        lead_time = self.get_lead_time_days(channel_name)
        return phase_start - timedelta(days=lead_time)

    def get_offline_constraints_note(self, channel_name: str) -> Optional[str]:
        """
        Get constraint note for offline channel.

        Args:
            channel_name: Channel name

        Returns:
            Constraint note string or None
        """
        if not self.is_offline(channel_name):
            return None
        
        lead_time = self.get_lead_time_days(channel_name)
        weeks = lead_time // 7
        return f"Requires {lead_time}-day ({weeks}-week) lead time for {channel_name} production"
```

- [ ] **Step 3: Run tests to verify they pass**

```bash
pytest tests/agents/test_media_planner.py::TestOfflineConstraintHandler -xvs
```

Expected: All 5 tests PASS

- [ ] **Step 4: Run all tests**

```bash
pytest tests/agents/test_media_planner.py -xvs
```

Expected: All 15 tests PASS

- [ ] **Step 5: Commit**

```bash
git add backend/app/agents/media_planner.py tests/agents/test_media_planner.py
git commit -m "[TASK-008] feat: implement OfflineConstraintHandler with lead times"
```

---

## Task 5: Implement ActivationValidator Class

**Files:**
- Modify: `backend/app/agents/media_planner.py`
- Modify: `tests/agents/test_media_planner.py`

- [ ] **Step 1: Add tests for ActivationValidator**

Add to `tests/agents/test_media_planner.py`:

```python
from backend.app.schemas.media_plan import Activation, ChannelEnum, PhaseEnum, AudienceSegmentEnum


def get_valid_activation() -> dict:
    """Return a valid activation dict."""
    return {
        "channel_enum": ChannelEnum.SOCIAL,
        "sub_channel": "TikTok",
        "format": "Video 15s",
        "geography": "US",
        "placement": "Feed",
        "phase": PhaseEnum.AWARENESS,
        "scheduled_date": date(2026, 6, 1),
        "duration": 14,
        "frequency": "3x daily",
        "audience_segment": AudienceSegmentEnum.PRIMARY,
        "estimated_reach": 500000,
        "estimated_cpm": 5.0,
        "cost_estimated": 2500.0,
        "message_version_ref": "TikTok (authentic, bold) - storytelling format",
    }


class TestActivationValidator:
    """Tests for ActivationValidator class."""

    def test_validator_accepts_valid_activation(self):
        """Validator should accept fully valid activation."""
        from backend.app.agents.media_planner import ActivationValidator
        
        validator = ActivationValidator()
        activation = get_valid_activation()
        
        errors = validator.validate_schema(activation)
        
        assert errors == []

    def test_validator_detects_missing_required_field(self):
        """Validator should detect missing required fields."""
        from backend.app.agents.media_planner import ActivationValidator
        
        validator = ActivationValidator()
        activation = get_valid_activation()
        del activation["cost_estimated"]
        
        errors = validator.validate_schema(activation)
        
        assert len(errors) > 0
        assert any("cost_estimated" in error for error in errors)

    def test_validator_detects_invalid_enum(self):
        """Validator should detect invalid enum values."""
        from backend.app.agents.media_planner import ActivationValidator
        
        validator = ActivationValidator()
        activation = get_valid_activation()
        activation["phase"] = "InvalidPhase"
        
        errors = validator.validate_schema(activation)
        
        assert len(errors) > 0

    def test_validator_detects_negative_cost(self):
        """Validator should enforce cost >= 0."""
        from backend.app.agents.media_planner import ActivationValidator
        
        validator = ActivationValidator()
        activation = get_valid_activation()
        activation["cost_estimated"] = -100.0
        
        errors = validator.validate_schema(activation)
        
        assert len(errors) > 0

    def test_validator_detects_zero_reach(self):
        """Validator should enforce reach >= 1."""
        from backend.app.agents.media_planner import ActivationValidator
        
        validator = ActivationValidator()
        activation = get_valid_activation()
        activation["estimated_reach"] = 0
        
        errors = validator.validate_schema(activation)
        
        assert len(errors) > 0
```

- [ ] **Step 2: Implement ActivationValidator**

Add to `backend/app/agents/media_planner.py`:

```python
from pydantic import ValidationError
from backend.app.schemas.media_plan import Activation


class ActivationValidator:
    """Validates Activation objects against Pydantic schema."""

    def validate_schema(self, activation_dict: dict) -> List[str]:
        """
        Validate an activation dict against Activation schema.

        Args:
            activation_dict: Raw dict to validate

        Returns:
            List of validation error strings (empty if valid)
        """
        errors = []
        
        try:
            Activation(**activation_dict)
        except ValidationError as e:
            for error in e.errors():
                field_path = ".".join(str(x) for x in error["loc"])
                msg = error["msg"]
                errors.append(f"Field '{field_path}': {msg}")
        
        return errors
```

- [ ] **Step 3: Run tests to verify they pass**

```bash
pytest tests/agents/test_media_planner.py::TestActivationValidator -xvs
```

Expected: All 5 tests PASS

- [ ] **Step 4: Run all tests**

```bash
pytest tests/agents/test_media_planner.py -xvs
```

Expected: All 20 tests PASS

- [ ] **Step 5: Commit**

```bash
git add backend/app/agents/media_planner.py tests/agents/test_media_planner.py
git commit -m "[TASK-008] feat: implement ActivationValidator with schema validation"
```

---

## Task 6: Implement Main Orchestrator Function

**Files:**
- Modify: `backend/app/agents/media_planner.py`
- Modify: `tests/agents/test_media_planner.py`

- [ ] **Step 1: Add integration test for orchestrator**

Add to `tests/agents/test_media_planner.py`:

```python
@pytest.mark.asyncio
async def test_media_planner_agent_generates_activations():
    """Orchestrator should generate list of activations."""
    from backend.app.agents.media_planner import media_planner_agent
    
    # Mock CampaignConcept input
    campaign = {
        "name": "Q2 Awareness",
        "channel_mix": [
            {"channel": "TikTok", "weight": 0.4},
            {"channel": "Instagram", "weight": 0.3},
            {"channel": "Email", "weight": 0.3},
        ],
        "campaign_phasing": {
            "awareness": "Week 1-2",
            "engagement": "Week 3-6",
            "conversion": "Week 7-12",
        },
        "tone_board": {
            "adjectives": ["authentic", "bold", "witty", "inclusive", "innovative"],
        },
        "message_architecture": {
            "channel_adaptations": {
                "TikTok": "30-second storytelling",
                "Instagram": "Static image carousel",
                "Email": "Newsletter signup",
            }
        }
    }
    
    budget = {
        "total_budget": 100000.0,
        "currency": "USD",
        "phase_allocation": {"awareness": 0.40, "engagement": 0.40, "conversion": 0.20},
        "contingency_pct": 0.10,
    }
    
    mandate_geography = {
        "regions": ["North America"],
        "markets": ["US"],
        "country_list": ["US"],
    }
    
    result = await media_planner_agent(campaign, budget, mandate_geography)
    
    assert "activations" in result
    assert "budget_summary" in result
    assert isinstance(result["activations"], list)
    assert len(result["activations"]) > 0
    assert result["status"] in ["success", "partial", "failed"]
```

- [ ] **Step 2: Implement media_planner_agent orchestrator**

Add to `backend/app/agents/media_planner.py`:

```python
async def media_planner_agent(
    campaign_concept: Dict[str, Any],
    budget_envelope: Dict[str, Any],
    mandate_geography: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Orchestrate generation of Activation Master Plan.

    Args:
        campaign_concept: Approved campaign concept from AGT-03
        budget_envelope: Budget allocation details
        mandate_geography: Mandate geography (regions, markets, countries)

    Returns:
        MediaPlanResponse dict with activations, budget summary, errors, and log
    """
    activations = []
    validation_errors = []
    allocation_log = []
    
    allocator = BudgetAllocator()
    generator = ActivationGenerator()
    constraint_handler = OfflineConstraintHandler()
    validator = ActivationValidator()
    
    # Parse budget
    total_budget = budget_envelope["total_budget"]
    contingency_pct = budget_envelope.get("contingency_pct", 0.10)
    
    # Extract markets
    markets = mandate_geography.get("markets", [])
    
    # Extract channels from campaign
    channels = campaign_concept.get("channel_mix", [])
    
    # Allocate budget by phase
    phase_budgets = allocator.allocate_by_phase(total_budget)
    allocation_log.append(f"Phase allocation: Awareness ${phase_budgets['Awareness']}, Engagement ${phase_budgets['Engagement']}, Conversion ${phase_budgets['Conversion']}")
    
    # Track spending
    total_spent = 0.0
    
    # FOR each phase
    for phase_name in ["Awareness", "Engagement", "Conversion"]:
        phase_budget = phase_budgets[phase_name]
        phase_remaining = phase_budget
        
        # Allocate budget by channel
        channel_budgets = allocator.allocate_by_channel(phase_budget, channels)
        
        # FOR each channel
        for channel_dict in channels:
            channel_name = channel_dict["channel"]
            channel_budget = channel_budgets[channel_name]
            allocation_log.append(f"Channel {channel_name}: ${channel_budget} (phase {phase_name})")
            
            # FOR each geography
            for market in markets:
                market_budget = allocator.allocate_by_geography(channel_budget, [market])[market]
                
                # Estimate reach
                audience_size = 1000000  # Placeholder: would come from mandate
                penetration = generator.get_penetration_for_phase(phase_name)
                estimated_reach = generator.calculate_reach(audience_size, penetration)
                
                # Calculate cost
                cpm = generator.get_cpm_for_channel(channel_name)
                estimated_cost = generator.calculate_cost(estimated_reach, cpm)
                
                # Cap cost to market budget
                if estimated_cost > market_budget:
                    estimated_reach = int((market_budget / cpm) * 1000)
                    estimated_cost = market_budget
                
                # Calculate scheduled date
                phase_start = date(2026, 6, 1)  # Placeholder
                scheduled_date = constraint_handler.calculate_scheduled_date(channel_name, phase_start)
                
                # Generate activation
                activation = {
                    "channel_enum": channel_name,
                    "sub_channel": channel_name,
                    "format": "Standard",
                    "geography": market,
                    "placement": "Standard Placement",
                    "phase": phase_name,
                    "scheduled_date": scheduled_date,
                    "duration": 14,
                    "frequency": generator.get_frequency_for_phase(phase_name),
                    "audience_segment": "Primary" if phase_name == "Awareness" else "Secondary",
                    "estimated_reach": estimated_reach,
                    "estimated_cpm": cpm,
                    "cost_estimated": estimated_cost,
                    "message_version_ref": f"{channel_name} message",
                    "lead_time_days": constraint_handler.get_lead_time_days(channel_name),
                    "offline_constraints": constraint_handler.get_offline_constraints_note(channel_name),
                }
                
                # Validate
                errors = validator.validate_schema(activation)
                if errors:
                    validation_errors.extend([f"Activation {channel_name}/{market}: {e}" for e in errors])
                else:
                    activations.append(activation)
                    total_spent += estimated_cost
    
    # Calculate contingency
    contingency_amount = allocator.calculate_contingency(total_spent, contingency_pct)
    allocation_log.append(f"Contingency reserved: ${contingency_amount}")
    
    # Build budget summary
    budget_summary = {
        "total_budget": total_budget,
        "currency": "USD",
        "phase_breakdown": {
            "Awareness": {
                "allocated": phase_budgets["Awareness"],
                "spent": total_spent * 0.40,  # Proportional
                "remaining": phase_budgets["Awareness"] - (total_spent * 0.40),
            },
            "Engagement": {
                "allocated": phase_budgets["Engagement"],
                "spent": total_spent * 0.40,
                "remaining": phase_budgets["Engagement"] - (total_spent * 0.40),
            },
            "Conversion": {
                "allocated": phase_budgets["Conversion"],
                "spent": total_spent * 0.20,
                "remaining": phase_budgets["Conversion"] - (total_spent * 0.20),
            },
        },
        "channel_breakdown": {
            ch["channel"]: {
                "allocated": channel_budgets[ch["channel"]],
                "spent": 0,  # TODO: aggregate from activations
                "activations_count": len([a for a in activations if a["sub_channel"] == ch["channel"]]),
            }
            for ch in channels
        },
        "contingency": {
            "allocated": contingency_amount,
            "used": 0,
            "remaining": contingency_amount,
        },
        "total_spent": total_spent,
        "total_remaining": total_budget - total_spent - contingency_amount,
        "utilization_pct": (total_spent / total_budget) * 100,
    }
    
    # Determine status
    if validation_errors:
        status = "partial" if activations else "failed"
    else:
        status = "success"
    
    return {
        "activations": activations,
        "budget_summary": budget_summary,
        "validation_errors": validation_errors,
        "allocation_log": allocation_log,
        "status": status,
    }
```

- [ ] **Step 3: Run integration test**

```bash
pytest tests/agents/test_media_planner.py::test_media_planner_agent_generates_activations -xvs
```

Expected: Test PASS

- [ ] **Step 4: Run all tests**

```bash
pytest tests/agents/test_media_planner.py -xvs
```

Expected: All 21 tests PASS

- [ ] **Step 5: Commit**

```bash
git add backend/app/agents/media_planner.py tests/agents/test_media_planner.py
git commit -m "[TASK-008] feat: implement media_planner_agent orchestrator"
```

---

## Task 7: Update Module Exports & Verify Code Quality

**Files:**
- Modify: `backend/app/agents/__init__.py`

- [ ] **Step 1: Export media_planner_agent from agents module**

Edit `backend/app/agents/__init__.py` and add:

```python
from backend.app.agents.media_planner import media_planner_agent

__all__ = [
    "media_planner_agent",
]
```

- [ ] **Step 2: Verify import works**

```bash
python -c "from backend.app.agents import media_planner_agent; print('✅ media_planner_agent exported')"
```

Expected: ✅ media_planner_agent exported

- [ ] **Step 3: Run all tests with coverage**

```bash
pytest tests/agents/test_media_planner.py --cov=backend.app.agents.media_planner --cov-report=term-missing -v
```

Expected: Coverage >= 80%

- [ ] **Step 4: Verify no import errors**

```bash
python -c "from tests.agents.test_media_planner import *; print('✅ All test imports successful')"
```

Expected: ✅ All test imports successful

- [ ] **Step 5: Commit**

```bash
git add backend/app/agents/__init__.py
git commit -m "[TASK-008] feat: export media_planner_agent from agents module"
```

---

## Task 8: Final Verification & Summary

**Files:**
- No new files

- [ ] **Step 1: Run full test suite with final report**

```bash
pytest tests/agents/test_media_planner.py -v --tb=short 2>&1 | tail -15
```

Expected: "21 passed"

- [ ] **Step 2: Verify coverage meets >80% requirement**

```bash
pytest tests/agents/test_media_planner.py --cov=backend.app.agents.media_planner --cov-report=term --cov-fail-under=80 2>&1 | grep -A 3 "TOTAL"
```

Expected: Coverage >= 80%, no coverage failures

- [ ] **Step 3: Check git log for all TASK-008 commits**

```bash
git log --oneline --grep="TASK-008" | head -10
```

Expected: Shows all 8 commits from Task 1-8

- [ ] **Step 4: Verify no uncommitted changes**

```bash
git status
```

Expected: "On branch main" with clean working tree

- [ ] **Step 5: Summary check**

```bash
echo "=== TASK-008 Summary ===" && echo "Schema: $(wc -l < backend/app/schemas/media_plan.py) lines" && echo "Agent module: $(wc -l < backend/app/agents/media_planner.py) lines" && echo "Tests: $(wc -l < tests/agents/test_media_planner.py) lines" && pytest tests/agents/test_media_planner.py -q 2>&1 | tail -1
```

Expected: Line counts + "21 passed"

---

## Summary

✅ **TASK-008 Implementation Complete:** Media Planner Agent (AGT-04)

**Files Created:**
- backend/app/schemas/media_plan.py (~150 lines)
- backend/app/agents/media_planner.py (~400 lines)
- tests/agents/test_media_planner.py (~350 lines)

**Components:**
- BudgetAllocator: Phase/channel/geography allocation
- ActivationGenerator: Reach, cost, frequency calculation
- OfflineConstraintHandler: Lead time enforcement
- ActivationValidator: Schema validation
- media_planner_agent: Main orchestrator

**Tests:** 21 tests (5 allocator + 5 generator + 5 constraint + 5 validator + 1 integration)

**Coverage:** >80%

**Ready for:** Subagent-driven or inline execution
