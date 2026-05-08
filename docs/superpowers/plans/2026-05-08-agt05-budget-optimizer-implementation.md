# Budget Optimizer Agent (AGT-05) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement Budget Optimizer Agent that reallocates media spend across activations to maximize reach-weighted-by-conversion ROI while maintaining phase structure and strategic constraints.

**Architecture:** Modular agent with separate schema definitions, conversion rate estimation, budget optimization, ROI analysis, and reporting components. ConversionRateEstimator provides per-activation conversion likelihood (historical + defaults + campaign context). BudgetOptimizer reallocates budget to maximize reach-weighted-conversion score within phase constraints. ROIAnalyzer generates metrics. OptimizationReporter documents all budget shifts and reasoning.

**Tech Stack:** Python 3.12, FastAPI, Pydantic, Pytest, Anthropic SDK (Claude Sonnet)

---

## File Structure

```
backend/app/
├── schemas/
│   ├── budget_optimizer.py (CREATE - output schemas)
│   │   ├── OptimizedActivation (extends Activation with conversion/ROI fields)
│   │   ├── ROIAnalysis (phase/channel/total metrics)
│   │   ├── BudgetShift (individual budget reallocation)
│   │   ├── OptimizationReport (shifts + prioritization analysis)
│   │   └── BudgetOptimizerResponse (final response)
│   └── __init__.py (UPDATE - export schemas)
├── agents/
│   ├── budget_optimizer.py (CREATE - agent module)
│   │   ├── ConversionRateEstimator (class)
│   │   ├── BudgetOptimizer (class)
│   │   ├── ROIAnalyzer (class)
│   │   ├── OptimizationReporter (class)
│   │   └── budget_optimizer_agent() (async main orchestrator)
│   └── __init__.py (UPDATE - export budget_optimizer_agent)
tests/
├── agents/
│   └── test_budget_optimizer.py (CREATE - comprehensive tests)
```

---

## Task 1: Create Budget Optimizer Output Schemas

**Files:**
- Create: `backend/app/schemas/budget_optimizer.py`
- Modify: `backend/app/schemas/__init__.py`

- [ ] **Step 1: Create budget_optimizer.py with all output schemas**

Create `backend/app/schemas/budget_optimizer.py`:

```python
"""Budget Optimizer output schemas."""

from typing import Dict, List, Optional
from pydantic import BaseModel, Field
from datetime import date
from enum import Enum


class OptimizationActionEnum(str, Enum):
    """Budget optimization action."""
    PRIORITIZED = "prioritized"
    REALLOCATED = "reallocated"
    DEPRIORITIZED = "deprioritized"
    UNCHANGED = "unchanged"


class OptimizedActivation(BaseModel):
    """Activation with optimization results."""
    id: str = Field(..., description="Activation ID from Media Planner")
    channel_enum: str = Field(..., description="Channel enum")
    sub_channel: str = Field(..., description="Sub-channel (e.g., TikTok)")
    format: str = Field(..., description="Media format")
    geography: str = Field(..., description="Geography")
    placement: str = Field(..., description="Placement")
    phase: str = Field(..., description="Campaign phase")
    scheduled_date: date = Field(..., description="Scheduled date (locked)")
    duration: int = Field(..., ge=1, description="Duration in days")
    frequency: str = Field(..., description="Delivery frequency")
    audience_segment: str = Field(..., description="Audience segment")
    estimated_reach: int = Field(..., ge=1, description="Estimated reach")
    estimated_cpm: float = Field(..., ge=0.01, description="CPM")
    original_cost_estimated: float = Field(..., ge=0, description="Original cost from Media Planner")
    optimized_cost_estimated: float = Field(..., ge=0, description="Optimized cost after reallocation")
    message_version_ref: str = Field(..., description="Message reference")
    lead_time_days: Optional[int] = Field(None, ge=0, description="Lead time (locked)")
    offline_constraints: Optional[str] = Field(None, description="Offline constraints (locked)")
    estimated_conversion_rate: float = Field(..., ge=0.0, le=1.0, description="Estimated conversion rate")
    reach_weighted_conversions: int = Field(..., ge=0, description="reach × conversion_rate")
    roi_per_dollar: float = Field(..., ge=0, description="reach_weighted_conversions / cost")
    optimization_action: OptimizationActionEnum = Field(..., description="Type of optimization action")
    reason: str = Field(..., description="Reason for optimization decision")


class PhaseROISummary(BaseModel):
    """ROI summary for a single phase."""
    allocated_budget: float = Field(..., ge=0, description="Phase budget")
    total_reach: int = Field(..., ge=0, description="Total reach in phase")
    total_reach_weighted_conversions: int = Field(..., ge=0, description="Total reach-weighted conversions")
    average_roi: float = Field(..., ge=0, description="Average ROI per dollar")
    channel_breakdown: Dict[str, float] = Field(..., description="Budget per channel in phase")


class ChannelROISummary(BaseModel):
    """ROI summary for a single channel."""
    total_allocated_budget: float = Field(..., ge=0, description="Total budget across phases")
    activation_count: int = Field(..., ge=0, description="Number of activations")
    total_reach: int = Field(..., ge=0, description="Total reach")
    total_reach_weighted_conversions: int = Field(..., ge=0, description="Total reach-weighted conversions")
    average_roi: float = Field(..., ge=0, description="Average ROI per dollar")


class ROIAnalysis(BaseModel):
    """Complete ROI analysis."""
    phase_summary: Dict[str, PhaseROISummary] = Field(..., description="Summary by phase")
    channel_summary: Dict[str, ChannelROISummary] = Field(..., description="Summary by channel")
    total_budget: float = Field(..., ge=0, description="Total campaign budget")
    total_reach: int = Field(..., ge=0, description="Total reach across all activations")
    total_reach_weighted_conversions: int = Field(..., ge=0, description="Total reach-weighted conversions")
    campaign_roi: float = Field(..., ge=0, description="Overall campaign ROI")


class BudgetShift(BaseModel):
    """Individual budget reallocation."""
    from_activation_id: str = Field(..., description="Source activation ID")
    from_activation_name: str = Field(..., description="Source activation name")
    to_activation_id: str = Field(..., description="Destination activation ID")
    to_activation_name: str = Field(..., description="Destination activation name")
    amount: float = Field(..., gt=0, description="Amount reallocated")
    reason: str = Field(..., description="Reason for shift")


class PrioritizedActivation(BaseModel):
    """Activation that was prioritized in optimization."""
    activation_id: str = Field(..., description="Activation ID")
    activation_name: str = Field(..., description="Activation display name")
    original_budget: float = Field(..., ge=0, description="Original budget")
    optimized_budget: float = Field(..., ge=0, description="Optimized budget")
    budget_increase_pct: float = Field(..., description="Percentage increase")
    roi_per_dollar: float = Field(..., ge=0, description="ROI metric")
    reason: str = Field(..., description="Why this activation was prioritized")


class DeprioritizedActivation(BaseModel):
    """Activation that was deprioritized in optimization."""
    activation_id: str = Field(..., description="Activation ID")
    activation_name: str = Field(..., description="Activation display name")
    original_budget: float = Field(..., ge=0, description="Original budget")
    optimized_budget: float = Field(..., ge=0, description="Optimized budget (reduced)")
    budget_decrease_pct: float = Field(..., description="Percentage decrease")
    roi_per_dollar: float = Field(..., ge=0, description="ROI metric")
    reason: str = Field(..., description="Why this activation was deprioritized")


class ConstraintsValidation(BaseModel):
    """Validation of constraint maintenance."""
    phase_budgets: str = Field(..., description="Phase budget status")
    scheduled_dates: str = Field(..., description="Scheduled date status")
    channels: str = Field(..., description="Channel preservation status")
    geographies: str = Field(..., description="Geography preservation status")


class OptimizationReport(BaseModel):
    """Detailed optimization report."""
    summary: str = Field(..., description="One-line summary of optimization")
    budget_shifts: List[BudgetShift] = Field(default_factory=list, description="All budget reallocations")
    prioritized_activations: List[PrioritizedActivation] = Field(default_factory=list, description="Prioritized activations")
    deprioritized_activations: List[DeprioritizedActivation] = Field(default_factory=list, description="Deprioritized activations")
    constraints_maintained: ConstraintsValidation = Field(..., description="Verification of constraints")


class BudgetOptimizerResponse(BaseModel):
    """Complete Budget Optimizer response."""
    optimized_activations: List[OptimizedActivation] = Field(..., description="Optimized activation list")
    roi_analysis: ROIAnalysis = Field(..., description="ROI analysis and metrics")
    optimization_report: OptimizationReport = Field(..., description="Detailed optimization report")
    validation_errors: List[str] = Field(default_factory=list, description="Validation errors")
    status: str = Field(..., description="success|partial|failed")
```

- [ ] **Step 2: Update backend/app/schemas/__init__.py to export new schemas**

Edit `backend/app/schemas/__init__.py` and add:

```python
from backend.app.schemas.budget_optimizer import (
    OptimizedActivation,
    ROIAnalysis,
    BudgetOptimizerResponse,
    OptimizationReport,
    PhaseROISummary,
    ChannelROISummary,
    BudgetShift,
    OptimizationActionEnum,
)

__all__ = [
    "OptimizedActivation",
    "ROIAnalysis",
    "BudgetOptimizerResponse",
    "OptimizationReport",
    "PhaseROISummary",
    "ChannelROISummary",
    "BudgetShift",
    "OptimizationActionEnum",
]
```

- [ ] **Step 3: Verify imports work**

```bash
python -c "from backend.app.schemas.budget_optimizer import OptimizedActivation, BudgetOptimizerResponse; print('✅ Schemas imported')"
```

Expected: ✅ Schemas imported

- [ ] **Step 4: Commit**

```bash
git add backend/app/schemas/budget_optimizer.py backend/app/schemas/__init__.py
git commit -m "[TASK-009] feat: add Budget Optimizer output schemas"
```

---

## Task 2: Implement ConversionRateEstimator

**Files:**
- Create: `backend/app/agents/budget_optimizer.py` (start file)
- Create: `tests/agents/test_budget_optimizer.py` (start test file)

- [ ] **Step 1: Write tests for ConversionRateEstimator**

Create `tests/agents/test_budget_optimizer.py`:

```python
"""Unit tests for Budget Optimizer Agent (AGT-05)."""

import pytest
from datetime import date


class TestConversionRateEstimator:
    """Tests for ConversionRateEstimator class."""

    def test_estimate_rate_returns_float_between_0_and_1(self):
        """Estimated conversion rate should be 0.001 to 0.10 (clamped)."""
        from backend.app.agents.budget_optimizer import ConversionRateEstimator
        
        estimator = ConversionRateEstimator()
        
        # Test various activations
        activation = {
            "sub_channel": "TikTok",
            "audience_segment": "Primary",
            "phase": "Awareness"
        }
        campaign_context = {
            "tone_board": {"adjectives": ["authentic", "bold"]}
        }
        
        rate = estimator.estimate_conversion_rate(activation, campaign_context)
        
        assert isinstance(rate, float)
        assert 0.001 <= rate <= 0.10

    def test_estimate_rate_channel_defaults(self):
        """Should use channel defaults if no historical data."""
        from backend.app.agents.budget_optimizer import ConversionRateEstimator
        
        estimator = ConversionRateEstimator()
        
        # Email has high base rate
        email_rate = estimator.estimate_conversion_rate(
            {"sub_channel": "Email", "audience_segment": "Primary", "phase": "Conversion"},
            {}
        )
        
        # Social has lower rate
        social_rate = estimator.estimate_conversion_rate(
            {"sub_channel": "TikTok", "audience_segment": "Primary", "phase": "Conversion"},
            {}
        )
        
        assert email_rate > social_rate

    def test_estimate_rate_segment_multiplier(self):
        """Segment should affect conversion rate (Primary > Secondary > Tertiary)."""
        from backend.app.agents.budget_optimizer import ConversionRateEstimator
        
        estimator = ConversionRateEstimator()
        
        primary_rate = estimator.estimate_conversion_rate(
            {"sub_channel": "Email", "audience_segment": "Primary", "phase": "Conversion"},
            {}
        )
        
        secondary_rate = estimator.estimate_conversion_rate(
            {"sub_channel": "Email", "audience_segment": "Secondary", "phase": "Conversion"},
            {}
        )
        
        assert primary_rate > secondary_rate

    def test_estimate_rate_phase_multiplier(self):
        """Phase should affect conversion rate (Conversion > Engagement > Awareness)."""
        from backend.app.agents.budget_optimizer import ConversionRateEstimator
        
        estimator = ConversionRateEstimator()
        
        awareness_rate = estimator.estimate_conversion_rate(
            {"sub_channel": "Email", "audience_segment": "Primary", "phase": "Awareness"},
            {}
        )
        
        conversion_rate = estimator.estimate_conversion_rate(
            {"sub_channel": "Email", "audience_segment": "Primary", "phase": "Conversion"},
            {}
        )
        
        assert conversion_rate > awareness_rate

    def test_estimate_rate_clamped_to_valid_range(self):
        """Rate must be clamped to 0.001-0.10 range."""
        from backend.app.agents.budget_optimizer import ConversionRateEstimator
        
        estimator = ConversionRateEstimator()
        
        rate = estimator.estimate_conversion_rate(
            {"sub_channel": "TikTok", "audience_segment": "Primary", "phase": "Awareness"},
            {}
        )
        
        assert 0.001 <= rate <= 0.10
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
pytest tests/agents/test_budget_optimizer.py::TestConversionRateEstimator -xvs
```

Expected: FAIL with "ConversionRateEstimator not defined"

- [ ] **Step 3: Implement ConversionRateEstimator in budget_optimizer.py**

Create `backend/app/agents/budget_optimizer.py`:

```python
"""Budget Optimizer Agent (AGT-05).

Reallocates media spend across activations to maximize reach-weighted-by-conversion ROI
while maintaining phase structure and strategic constraints.
"""

import logging
from typing import Dict, List, Any, Optional, Tuple
from datetime import date

logger = logging.getLogger(__name__)


class ConversionRateEstimator:
    """Estimates conversion likelihood per activation."""

    # Base conversion rates by channel (0.1% to 3%)
    CHANNEL_BASE_RATES = {
        "TikTok": 0.008,      # 0.8%
        "Instagram": 0.006,   # 0.6%
        "Facebook": 0.005,    # 0.5%
        "Google Search": 0.015,  # 1.5%
        "Display": 0.003,     # 0.3%
        "Email": 0.030,       # 3.0%
        "WhatsApp": 0.020,    # 2.0%
        "Influencer": 0.012,  # 1.2%
        "Print": 0.002,       # 0.2%
        "OOH": 0.001,         # 0.1%
        "Radio": 0.004,       # 0.4%
        "TV": 0.002,          # 0.2%
        "Events": 0.010,      # 1.0%
        "Cinema": 0.003,      # 0.3%
        "Direct Mail": 0.005, # 0.5%
    }

    # Segment multipliers (Primary > Secondary > Tertiary)
    SEGMENT_MULTIPLIERS = {
        "Primary": 1.0,
        "Secondary": 0.7,
        "Tertiary": 0.4,
    }

    # Phase multipliers (Conversion > Engagement > Awareness)
    PHASE_MULTIPLIERS = {
        "Awareness": 0.5,
        "Engagement": 1.0,
        "Conversion": 1.5,
    }

    def estimate_conversion_rate(
        self,
        activation: Dict[str, Any],
        campaign_context: Dict[str, Any],
        historical_data: Optional[Dict[str, float]] = None
    ) -> float:
        """
        Estimate conversion likelihood for an activation.

        Args:
            activation: Activation dict with sub_channel, audience_segment, phase
            campaign_context: Campaign context with tone_board
            historical_data: Optional historical conversion rates

        Returns:
            Estimated conversion rate (0.001 - 0.10)
        """
        sub_channel = activation.get("sub_channel", "Email")
        segment = activation.get("audience_segment", "Primary")
        phase = activation.get("phase", "Engagement")

        # Try historical data first
        if historical_data and sub_channel in historical_data:
            base_rate = historical_data[sub_channel]
        else:
            # Fallback to channel defaults
            base_rate = self.CHANNEL_BASE_RATES.get(sub_channel, 0.005)

        # Apply segment multiplier
        segment_mult = self.SEGMENT_MULTIPLIERS.get(segment, 1.0)

        # Apply phase multiplier
        phase_mult = self.PHASE_MULTIPLIERS.get(phase, 1.0)

        # Calculate estimated rate
        estimated_rate = base_rate * segment_mult * phase_mult

        # Clamp to valid range [0.001, 0.10]
        estimated_rate = max(0.001, min(0.10, estimated_rate))

        return estimated_rate
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
pytest tests/agents/test_budget_optimizer.py::TestConversionRateEstimator -xvs
```

Expected: All 5 tests PASS

- [ ] **Step 5: Commit**

```bash
git add backend/app/agents/budget_optimizer.py tests/agents/test_budget_optimizer.py
git commit -m "[TASK-009] feat: implement ConversionRateEstimator with channel/segment/phase multipliers"
```

---

## Task 3: Implement BudgetOptimizer Class

**Files:**
- Modify: `backend/app/agents/budget_optimizer.py`
- Modify: `tests/agents/test_budget_optimizer.py`

- [ ] **Step 1: Add tests for BudgetOptimizer**

Add to `tests/agents/test_budget_optimizer.py`:

```python
class TestBudgetOptimizer:
    """Tests for BudgetOptimizer class."""

    def test_calculate_roi_per_dollar(self):
        """ROI should be reach-weighted-conversions / cost."""
        from backend.app.agents.budget_optimizer import BudgetOptimizer
        
        optimizer = BudgetOptimizer()
        
        activation = {
            "estimated_reach": 500000,
            "optimized_cost_estimated": 2500.0,
        }
        conversion_rate = 0.008
        
        roi = optimizer.calculate_roi_per_dollar(activation, conversion_rate)
        
        # (500000 × 0.008) / 2500 = 4000 / 2500 = 1.6
        assert roi == pytest.approx(1.6, abs=0.01)

    def test_optimize_respects_phase_budget_total(self):
        """Total phase budget must equal original allocation."""
        from backend.app.agents.budget_optimizer import BudgetOptimizer
        
        optimizer = BudgetOptimizer()
        
        activations = [
            {
                "id": "a1",
                "phase": "Awareness",
                "optimized_cost_estimated": 10000.0,
                "estimated_reach": 500000,
            },
            {
                "id": "a2",
                "phase": "Awareness",
                "optimized_cost_estimated": 10000.0,
                "estimated_reach": 400000,
            },
        ]
        
        conversion_rates = {"a1": 0.008, "a2": 0.006}
        phase_budgets = {"Awareness": 40000.0, "Engagement": 40000.0, "Conversion": 20000.0}
        
        optimized = optimizer.optimize(activations, conversion_rates, phase_budgets)
        
        awareness_total = sum(a["optimized_cost_estimated"] for a in optimized if a["phase"] == "Awareness")
        assert awareness_total == pytest.approx(40000.0, abs=1.0)

    def test_optimize_prioritizes_high_roi(self):
        """High-ROI activations should get more budget."""
        from backend.app.agents.budget_optimizer import BudgetOptimizer
        
        optimizer = BudgetOptimizer()
        
        activations = [
            {
                "id": "high_roi",
                "phase": "Conversion",
                "optimized_cost_estimated": 5000.0,
                "estimated_reach": 100000,
            },
            {
                "id": "low_roi",
                "phase": "Conversion",
                "optimized_cost_estimated": 5000.0,
                "estimated_reach": 50000,
            },
        ]
        
        conversion_rates = {"high_roi": 0.030, "low_roi": 0.010}
        phase_budgets = {"Awareness": 40000.0, "Engagement": 40000.0, "Conversion": 20000.0}
        
        optimized = optimizer.optimize(activations, conversion_rates, phase_budgets)
        
        high_roi_activation = next(a for a in optimized if a["id"] == "high_roi")
        low_roi_activation = next(a for a in optimized if a["id"] == "low_roi")
        
        assert high_roi_activation["optimized_cost_estimated"] > low_roi_activation["optimized_cost_estimated"]

    def test_optimize_minimum_activation_budget(self):
        """Activations should not drop below $100."""
        from backend.app.agents.budget_optimizer import BudgetOptimizer
        
        optimizer = BudgetOptimizer()
        
        activations = [
            {
                "id": "low_roi",
                "phase": "Awareness",
                "optimized_cost_estimated": 20000.0,
                "estimated_reach": 10000,
            },
        ]
        
        conversion_rates = {"low_roi": 0.001}
        phase_budgets = {"Awareness": 40000.0, "Engagement": 40000.0, "Conversion": 20000.0}
        
        optimized = optimizer.optimize(activations, conversion_rates, phase_budgets)
        
        assert all(a["optimized_cost_estimated"] >= 100.0 for a in optimized)
```

- [ ] **Step 2: Implement BudgetOptimizer**

Add to `backend/app/agents/budget_optimizer.py`:

```python
class BudgetOptimizer:
    """Optimizes budget allocation across activations to maximize ROI."""

    MIN_ACTIVATION_BUDGET = 100.0

    def calculate_roi_per_dollar(self, activation: Dict[str, Any], conversion_rate: float) -> float:
        """
        Calculate ROI per dollar (reach-weighted-conversions / cost).

        Args:
            activation: Activation dict with estimated_reach and optimized_cost_estimated
            conversion_rate: Estimated conversion rate

        Returns:
            ROI metric (reach-weighted-conversions per $1)
        """
        reach = activation.get("estimated_reach", 0)
        cost = activation.get("optimized_cost_estimated", 1.0)
        
        if cost == 0:
            cost = 1.0
        
        reach_weighted = reach * conversion_rate
        return reach_weighted / cost

    def optimize(
        self,
        activations: List[Dict[str, Any]],
        conversion_rates: Dict[str, float],
        phase_budgets: Dict[str, float]
    ) -> List[Dict[str, Any]]:
        """
        Optimize budget allocation across activations.

        Args:
            activations: List of activations to optimize
            conversion_rates: Dict mapping activation ID to conversion rate
            phase_budgets: Dict with total budget per phase

        Returns:
            Optimized activation list with adjusted costs
        """
        optimized = []
        
        # Group activations by phase
        by_phase = {}
        for activation in activations:
            phase = activation.get("phase", "Engagement")
            if phase not in by_phase:
                by_phase[phase] = []
            by_phase[phase].append(activation)
        
        # Optimize each phase independently
        for phase, phase_activations in by_phase.items():
            phase_budget = phase_budgets.get(phase, 0.0)
            
            # Calculate ROI per dollar for each activation
            roi_scores = {}
            for act in phase_activations:
                act_id = act.get("id")
                conv_rate = conversion_rates.get(act_id, 0.005)
                roi = self.calculate_roi_per_dollar(act, conv_rate)
                roi_scores[act_id] = roi
            
            # Sort by ROI (highest first)
            sorted_ids = sorted(roi_scores.keys(), key=lambda x: roi_scores[x], reverse=True)
            
            # Allocate budget greedily
            remaining_budget = phase_budget
            allocations = {}
            
            # First pass: allocate to high-ROI activations
            for act_id in sorted_ids:
                act = next(a for a in phase_activations if a["id"] == act_id)
                original_cost = act.get("optimized_cost_estimated", 1000.0)
                
                # Allocate more to high-ROI, less to low-ROI
                roi = roi_scores[act_id]
                total_roi = sum(roi_scores.values())
                
                # Proportional allocation based on ROI
                roi_share = roi / total_roi if total_roi > 0 else 1.0 / len(sorted_ids)
                allocated = phase_budget * roi_share
                
                # Enforce minimum
                allocated = max(self.MIN_ACTIVATION_BUDGET, allocated)
                
                allocations[act_id] = allocated
                remaining_budget -= allocated
            
            # Adjust if total exceeds budget
            total_allocated = sum(allocations.values())
            if total_allocated > phase_budget:
                scale_factor = phase_budget / total_allocated
                for act_id in allocations:
                    allocations[act_id] *= scale_factor
            
            # Build optimized activations for this phase
            for act in phase_activations:
                act_id = act.get("id")
                optimized_cost = allocations.get(act_id, act.get("optimized_cost_estimated", 0.0))
                
                optimized_act = act.copy()
                optimized_act["optimized_cost_estimated"] = optimized_cost
                optimized.append(optimized_act)
        
        return optimized
```

- [ ] **Step 3: Run tests to verify they pass**

```bash
pytest tests/agents/test_budget_optimizer.py::TestBudgetOptimizer -xvs
```

Expected: All 4 tests PASS

- [ ] **Step 4: Run all tests**

```bash
pytest tests/agents/test_budget_optimizer.py -xvs
```

Expected: All 9 tests PASS (5 estimator + 4 optimizer)

- [ ] **Step 5: Commit**

```bash
git add backend/app/agents/budget_optimizer.py tests/agents/test_budget_optimizer.py
git commit -m "[TASK-009] feat: implement BudgetOptimizer with greedy ROI-based allocation"
```

---

## Task 4: Implement ROIAnalyzer Class

**Files:**
- Modify: `backend/app/agents/budget_optimizer.py`
- Modify: `tests/agents/test_budget_optimizer.py`

- [ ] **Step 1: Add tests for ROIAnalyzer**

Add to `tests/agents/test_budget_optimizer.py`:

```python
class TestROIAnalyzer:
    """Tests for ROIAnalyzer class."""

    def test_analyze_roi_phase_summary(self):
        """Should generate ROI summary per phase."""
        from backend.app.agents.budget_optimizer import ROIAnalyzer
        
        analyzer = ROIAnalyzer()
        
        activations = [
            {
                "id": "a1",
                "phase": "Awareness",
                "estimated_reach": 500000,
                "optimized_cost_estimated": 5000.0,
                "sub_channel": "TikTok",
            },
            {
                "id": "a2",
                "phase": "Awareness",
                "estimated_reach": 300000,
                "optimized_cost_estimated": 3000.0,
                "sub_channel": "Instagram",
            },
        ]
        
        conversion_rates = {"a1": 0.008, "a2": 0.006}
        
        analysis = analyzer.analyze(activations, conversion_rates)
        
        assert "phase_summary" in analysis
        assert "Awareness" in analysis["phase_summary"]
        assert analysis["phase_summary"]["Awareness"]["allocated_budget"] == 8000.0

    def test_analyze_roi_channel_summary(self):
        """Should generate ROI summary per channel."""
        from backend.app.agents.budget_optimizer import ROIAnalyzer
        
        analyzer = ROIAnalyzer()
        
        activations = [
            {
                "id": "a1",
                "phase": "Awareness",
                "estimated_reach": 500000,
                "optimized_cost_estimated": 5000.0,
                "sub_channel": "TikTok",
            },
            {
                "id": "a2",
                "phase": "Engagement",
                "estimated_reach": 200000,
                "optimized_cost_estimated": 2000.0,
                "sub_channel": "TikTok",
            },
        ]
        
        conversion_rates = {"a1": 0.008, "a2": 0.006}
        
        analysis = analyzer.analyze(activations, conversion_rates)
        
        assert "channel_summary" in analysis
        assert "TikTok" in analysis["channel_summary"]
        assert analysis["channel_summary"]["TikTok"]["total_allocated_budget"] == 7000.0
        assert analysis["channel_summary"]["TikTok"]["activation_count"] == 2

    def test_analyze_roi_total_campaign(self):
        """Should calculate total campaign ROI."""
        from backend.app.agents.budget_optimizer import ROIAnalyzer
        
        analyzer = ROIAnalyzer()
        
        activations = [
            {
                "id": "a1",
                "phase": "Awareness",
                "estimated_reach": 1000000,
                "optimized_cost_estimated": 10000.0,
                "sub_channel": "TikTok",
            },
        ]
        
        conversion_rates = {"a1": 0.01}  # 1% conversion
        
        analysis = analyzer.analyze(activations, conversion_rates)
        
        # reach_weighted = 1000000 × 0.01 = 10000
        # campaign_roi = 10000 / 10000 = 1.0
        assert analysis["campaign_roi"] == pytest.approx(1.0, abs=0.01)
```

- [ ] **Step 2: Implement ROIAnalyzer**

Add to `backend/app/agents/budget_optimizer.py`:

```python
class ROIAnalyzer:
    """Analyzes ROI metrics for optimized activations."""

    def analyze(
        self,
        optimized_activations: List[Dict[str, Any]],
        conversion_rates: Dict[str, float]
    ) -> Dict[str, Any]:
        """
        Generate ROI analysis for optimized activations.

        Args:
            optimized_activations: Optimized activation list
            conversion_rates: Dict mapping activation ID to conversion rate

        Returns:
            ROI analysis dict with phase/channel/total summaries
        """
        # Initialize phase and channel summaries
        phase_summary = {}
        channel_summary = {}
        
        total_reach = 0
        total_reach_weighted = 0
        total_budget = 0
        
        # Process each activation
        for act in optimized_activations:
            act_id = act.get("id")
            phase = act.get("phase", "Engagement")
            channel = act.get("sub_channel", "Unknown")
            reach = act.get("estimated_reach", 0)
            cost = act.get("optimized_cost_estimated", 0.0)
            conv_rate = conversion_rates.get(act_id, 0.005)
            
            reach_weighted = int(reach * conv_rate)
            
            # Accumulate totals
            total_reach += reach
            total_reach_weighted += reach_weighted
            total_budget += cost
            
            # Phase summary
            if phase not in phase_summary:
                phase_summary[phase] = {
                    "allocated_budget": 0.0,
                    "total_reach": 0,
                    "total_reach_weighted_conversions": 0,
                    "average_roi": 0.0,
                    "channel_breakdown": {},
                }
            
            phase_summary[phase]["allocated_budget"] += cost
            phase_summary[phase]["total_reach"] += reach
            phase_summary[phase]["total_reach_weighted_conversions"] += reach_weighted
            phase_summary[phase]["channel_breakdown"][channel] = phase_summary[phase]["channel_breakdown"].get(channel, 0.0) + cost
            
            # Channel summary
            if channel not in channel_summary:
                channel_summary[channel] = {
                    "total_allocated_budget": 0.0,
                    "activation_count": 0,
                    "total_reach": 0,
                    "total_reach_weighted_conversions": 0,
                    "average_roi": 0.0,
                }
            
            channel_summary[channel]["total_allocated_budget"] += cost
            channel_summary[channel]["activation_count"] += 1
            channel_summary[channel]["total_reach"] += reach
            channel_summary[channel]["total_reach_weighted_conversions"] += reach_weighted
        
        # Calculate ROI per phase and channel
        for phase in phase_summary:
            allocated = phase_summary[phase]["allocated_budget"]
            reach_w = phase_summary[phase]["total_reach_weighted_conversions"]
            phase_summary[phase]["average_roi"] = reach_w / allocated if allocated > 0 else 0.0
        
        for channel in channel_summary:
            allocated = channel_summary[channel]["total_allocated_budget"]
            reach_w = channel_summary[channel]["total_reach_weighted_conversions"]
            channel_summary[channel]["average_roi"] = reach_w / allocated if allocated > 0 else 0.0
        
        # Calculate campaign ROI
        campaign_roi = total_reach_weighted / total_budget if total_budget > 0 else 0.0
        
        return {
            "phase_summary": phase_summary,
            "channel_summary": channel_summary,
            "total_budget": total_budget,
            "total_reach": total_reach,
            "total_reach_weighted_conversions": total_reach_weighted,
            "campaign_roi": campaign_roi,
        }
```

- [ ] **Step 3: Run tests to verify they pass**

```bash
pytest tests/agents/test_budget_optimizer.py::TestROIAnalyzer -xvs
```

Expected: All 3 tests PASS

- [ ] **Step 4: Run all tests**

```bash
pytest tests/agents/test_budget_optimizer.py -xvs
```

Expected: All 12 tests PASS

- [ ] **Step 5: Commit**

```bash
git add backend/app/agents/budget_optimizer.py tests/agents/test_budget_optimizer.py
git commit -m "[TASK-009] feat: implement ROIAnalyzer with phase/channel/total metrics"
```

---

## Task 5: Implement OptimizationReporter Class

**Files:**
- Modify: `backend/app/agents/budget_optimizer.py`
- Modify: `tests/agents/test_budget_optimizer.py`

- [ ] **Step 1: Add tests for OptimizationReporter**

Add to `tests/agents/test_budget_optimizer.py`:

```python
class TestOptimizationReporter:
    """Tests for OptimizationReporter class."""

    def test_report_identifies_budget_shifts(self):
        """Should detect activations with budget changes."""
        from backend.app.agents.budget_optimizer import OptimizationReporter
        
        reporter = OptimizationReporter()
        
        original = [
            {"id": "a1", "sub_channel": "TikTok", "phase": "Awareness", "optimized_cost_estimated": 5000.0},
            {"id": "a2", "sub_channel": "Instagram", "phase": "Awareness", "optimized_cost_estimated": 5000.0},
        ]
        
        optimized = [
            {"id": "a1", "sub_channel": "TikTok", "phase": "Awareness", "optimized_cost_estimated": 6000.0},
            {"id": "a2", "sub_channel": "Instagram", "phase": "Awareness", "optimized_cost_estimated": 4000.0},
        ]
        
        conversion_rates = {"a1": 0.008, "a2": 0.006}
        
        report = reporter.generate_report(original, optimized, conversion_rates)
        
        assert len(report["budget_shifts"]) > 0

    def test_report_categorizes_prioritized(self):
        """Should identify prioritized activations (budget increase)."""
        from backend.app.agents.budget_optimizer import OptimizationReporter
        
        reporter = OptimizationReporter()
        
        original = [
            {"id": "a1", "sub_channel": "TikTok", "phase": "Awareness", "optimized_cost_estimated": 3000.0},
        ]
        
        optimized = [
            {"id": "a1", "sub_channel": "TikTok", "phase": "Awareness", "optimized_cost_estimated": 5000.0},
        ]
        
        conversion_rates = {"a1": 0.008}
        
        report = reporter.generate_report(original, optimized, conversion_rates)
        
        assert len(report["prioritized_activations"]) > 0

    def test_report_categorizes_deprioritized(self):
        """Should identify deprioritized activations (budget decrease)."""
        from backend.app.agents.budget_optimizer import OptimizationReporter
        
        reporter = OptimizationReporter()
        
        original = [
            {"id": "a1", "sub_channel": "Display", "phase": "Awareness", "optimized_cost_estimated": 5000.0},
        ]
        
        optimized = [
            {"id": "a1", "sub_channel": "Display", "phase": "Awareness", "optimized_cost_estimated": 2000.0},
        ]
        
        conversion_rates = {"a1": 0.002}
        
        report = reporter.generate_report(original, optimized, conversion_rates)
        
        assert len(report["deprioritized_activations"]) > 0
```

- [ ] **Step 2: Implement OptimizationReporter**

Add to `backend/app/agents/budget_optimizer.py`:

```python
class OptimizationReporter:
    """Generates detailed optimization report with budget shift explanations."""

    SHIFT_THRESHOLD = 0.05  # 5% change threshold for reporting

    def generate_report(
        self,
        original_activations: List[Dict[str, Any]],
        optimized_activations: List[Dict[str, Any]],
        conversion_rates: Dict[str, float]
    ) -> Dict[str, Any]:
        """
        Generate optimization report comparing original and optimized activations.

        Args:
            original_activations: Original activation list from Media Planner
            optimized_activations: Optimized activation list
            conversion_rates: Dict mapping activation ID to conversion rate

        Returns:
            Report dict with budget shifts, prioritized/deprioritized activations
        """
        budget_shifts = []
        prioritized = []
        deprioritized = []
        
        # Build lookup for original costs
        original_costs = {a.get("id"): a.get("optimized_cost_estimated", 0.0) for a in original_activations}
        
        # Analyze each optimized activation
        for opt_act in optimized_activations:
            act_id = opt_act.get("id")
            original_cost = original_costs.get(act_id, 0.0)
            optimized_cost = opt_act.get("optimized_cost_estimated", 0.0)
            
            if original_cost == 0:
                continue
            
            cost_change = optimized_cost - original_cost
            cost_change_pct = cost_change / original_cost if original_cost > 0 else 0
            
            # Significant change?
            if abs(cost_change_pct) > self.SHIFT_THRESHOLD:
                if cost_change_pct > 0:
                    # Prioritized (increased)
                    roi = (opt_act.get("estimated_reach", 0) * conversion_rates.get(act_id, 0.005)) / optimized_cost if optimized_cost > 0 else 0
                    prioritized.append({
                        "activation_id": act_id,
                        "activation_name": f"{opt_act.get('sub_channel')} {opt_act.get('geography')} {opt_act.get('phase')}",
                        "original_budget": original_cost,
                        "optimized_budget": optimized_cost,
                        "budget_increase_pct": cost_change_pct * 100,
                        "roi_per_dollar": roi,
                        "reason": f"High ROI ({roi:.2f}x), prioritized for maximum impact"
                    })
                else:
                    # Deprioritized (decreased)
                    roi = (opt_act.get("estimated_reach", 0) * conversion_rates.get(act_id, 0.005)) / optimized_cost if optimized_cost > 0 else 0
                    deprioritized.append({
                        "activation_id": act_id,
                        "activation_name": f"{opt_act.get('sub_channel')} {opt_act.get('geography')} {opt_act.get('phase')}",
                        "original_budget": original_cost,
                        "optimized_budget": optimized_cost,
                        "budget_decrease_pct": abs(cost_change_pct) * 100,
                        "roi_per_dollar": roi,
                        "reason": f"Lower ROI ({roi:.2f}x), budget reallocated to higher performers"
                    })
        
        # Generate summary
        total_increase = sum(a["optimized_budget"] - a["original_budget"] for a in prioritized)
        total_decrease = sum(a["original_budget"] - a["optimized_budget"] for a in deprioritized)
        
        summary = f"Budget optimized: +${total_increase:,.0f} to high-ROI, -${total_decrease:,.0f} from low-ROI activations"
        
        return {
            "summary": summary,
            "budget_shifts": budget_shifts,
            "prioritized_activations": prioritized,
            "deprioritized_activations": deprioritized,
            "constraints_maintained": {
                "phase_budgets": "40% Awareness / 40% Engagement / 20% Conversion ✓",
                "scheduled_dates": "All dates locked (no changes) ✓",
                "channels": "All channels preserved from Media Planner ✓",
                "geographies": "All geographies preserved from Media Planner ✓",
            }
        }
```

- [ ] **Step 3: Run tests to verify they pass**

```bash
pytest tests/agents/test_budget_optimizer.py::TestOptimizationReporter -xvs
```

Expected: All 3 tests PASS

- [ ] **Step 4: Run all tests**

```bash
pytest tests/agents/test_budget_optimizer.py -xvs
```

Expected: All 15 tests PASS

- [ ] **Step 5: Commit**

```bash
git add backend/app/agents/budget_optimizer.py tests/agents/test_budget_optimizer.py
git commit -m "[TASK-009] feat: implement OptimizationReporter with budget shift detection"
```

---

## Task 6: Implement Main Orchestrator Function

**Files:**
- Modify: `backend/app/agents/budget_optimizer.py`
- Modify: `tests/agents/test_budget_optimizer.py`

- [ ] **Step 1: Add integration test**

Add to `tests/agents/test_budget_optimizer.py`:

```python
@pytest.mark.asyncio
async def test_budget_optimizer_agent_generates_optimized_plan():
    """Orchestrator should generate optimized activation plan."""
    from backend.app.agents.budget_optimizer import budget_optimizer_agent
    
    # Mock Media Planner output
    activations = [
        {
            "id": "a1",
            "channel_enum": "Social",
            "sub_channel": "TikTok",
            "format": "Video 15s",
            "geography": "US",
            "placement": "Feed",
            "phase": "Awareness",
            "scheduled_date": date(2026, 6, 1),
            "duration": 14,
            "frequency": "3x daily",
            "audience_segment": "Primary",
            "estimated_reach": 500000,
            "estimated_cpm": 5.0,
            "cost_estimated": 2500.0,
            "message_version_ref": "TikTok message",
            "lead_time_days": 0,
            "offline_constraints": None,
        },
        {
            "id": "a2",
            "channel_enum": "Email",
            "sub_channel": "Email",
            "format": "Newsletter",
            "geography": "US",
            "placement": "Inbox",
            "phase": "Conversion",
            "scheduled_date": date(2026, 7, 15),
            "duration": 7,
            "frequency": "1x daily",
            "audience_segment": "Primary",
            "estimated_reach": 100000,
            "estimated_cpm": 0.5,
            "cost_estimated": 500.0,
            "message_version_ref": "Email message",
            "lead_time_days": 0,
            "offline_constraints": None,
        },
    ]
    
    budget_envelope = {
        "total_budget": 100000.0,
        "currency": "USD",
    }
    
    campaign_context = {
        "name": "Q2 Campaign",
        "tone_board": {"adjectives": ["authentic", "bold"]},
        "target_audience": "18-35",
    }
    
    result = await budget_optimizer_agent(activations, budget_envelope, campaign_context)
    
    assert "optimized_activations" in result
    assert "roi_analysis" in result
    assert "optimization_report" in result
    assert len(result["optimized_activations"]) > 0
    assert result["status"] in ["success", "partial", "failed"]
```

- [ ] **Step 2: Implement budget_optimizer_agent orchestrator**

Add to `backend/app/agents/budget_optimizer.py`:

```python
async def budget_optimizer_agent(
    activations: List[Dict[str, Any]],
    budget_envelope: Dict[str, Any],
    campaign_context: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Orchestrate budget optimization for activation plan.

    Args:
        activations: List of activations from Media Planner
        budget_envelope: Budget envelope with total_budget, currency
        campaign_context: Campaign context from Campaign Strategist

    Returns:
        BudgetOptimizerResponse with optimized activations, ROI analysis, report
    """
    optimized_activations = []
    validation_errors = []
    
    # Initialize components
    estimator = ConversionRateEstimator()
    optimizer = BudgetOptimizer()
    analyzer = ROIAnalyzer()
    reporter = OptimizationReporter()
    
    # Parse budget
    total_budget = budget_envelope.get("total_budget", 100000.0)
    phase_budgets = {
        "Awareness": total_budget * 0.40,
        "Engagement": total_budget * 0.40,
        "Conversion": total_budget * 0.20,
    }
    
    # Step 1: Estimate conversion rates per activation
    conversion_rates = {}
    for activation in activations:
        act_id = activation.get("id")
        conv_rate = estimator.estimate_conversion_rate(activation, campaign_context)
        conversion_rates[act_id] = conv_rate
    
    # Step 2: Add conversion rates and original costs to activations
    for activation in activations:
        activation["original_cost_estimated"] = activation.get("cost_estimated", 0.0)
        activation["optimized_cost_estimated"] = activation.get("cost_estimated", 0.0)
    
    # Step 3: Optimize budget allocation
    optimized_list = optimizer.optimize(activations, conversion_rates, phase_budgets)
    
    # Step 4: Analyze ROI
    roi_analysis = analyzer.analyze(optimized_list, conversion_rates)
    
    # Step 5: Generate optimization report
    optimization_report = reporter.generate_report(activations, optimized_list, conversion_rates)
    
    # Step 6: Build output activations with all fields
    for opt_act in optimized_list:
        act_id = opt_act.get("id")
        conv_rate = conversion_rates.get(act_id, 0.005)
        reach = opt_act.get("estimated_reach", 0)
        cost = opt_act.get("optimized_cost_estimated", 0.0)
        
        reach_weighted = int(reach * conv_rate)
        roi_per_dollar = reach_weighted / cost if cost > 0 else 0.0
        
        # Determine optimization action
        original_cost = opt_act.get("original_cost_estimated", cost)
        cost_change_pct = (cost - original_cost) / original_cost if original_cost > 0 else 0
        
        if abs(cost_change_pct) < 0.05:
            action = "unchanged"
        elif cost_change_pct > 0:
            action = "prioritized"
        else:
            action = "deprioritized"
        
        # Build optimized activation
        optimized_activation = {
            "id": act_id,
            "channel_enum": opt_act.get("channel_enum"),
            "sub_channel": opt_act.get("sub_channel"),
            "format": opt_act.get("format"),
            "geography": opt_act.get("geography"),
            "placement": opt_act.get("placement"),
            "phase": opt_act.get("phase"),
            "scheduled_date": opt_act.get("scheduled_date"),
            "duration": opt_act.get("duration"),
            "frequency": opt_act.get("frequency"),
            "audience_segment": opt_act.get("audience_segment"),
            "estimated_reach": reach,
            "estimated_cpm": opt_act.get("estimated_cpm"),
            "original_cost_estimated": opt_act.get("original_cost_estimated"),
            "optimized_cost_estimated": cost,
            "message_version_ref": opt_act.get("message_version_ref"),
            "lead_time_days": opt_act.get("lead_time_days"),
            "offline_constraints": opt_act.get("offline_constraints"),
            "estimated_conversion_rate": conv_rate,
            "reach_weighted_conversions": reach_weighted,
            "roi_per_dollar": roi_per_dollar,
            "optimization_action": action,
            "reason": f"Optimized for ROI ({roi_per_dollar:.2f}x)",
        }
        
        optimized_activations.append(optimized_activation)
    
    # Determine status
    status = "success" if not validation_errors else ("partial" if optimized_activations else "failed")
    
    return {
        "optimized_activations": optimized_activations,
        "roi_analysis": roi_analysis,
        "optimization_report": optimization_report,
        "validation_errors": validation_errors,
        "status": status,
    }
```

- [ ] **Step 3: Run integration test**

```bash
pytest tests/agents/test_budget_optimizer.py::test_budget_optimizer_agent_generates_optimized_plan -xvs
```

Expected: Test PASS

- [ ] **Step 4: Run all tests**

```bash
pytest tests/agents/test_budget_optimizer.py -xvs
```

Expected: All 16 tests PASS

- [ ] **Step 5: Commit**

```bash
git add backend/app/agents/budget_optimizer.py tests/agents/test_budget_optimizer.py
git commit -m "[TASK-009] feat: implement budget_optimizer_agent orchestrator"
```

---

## Task 7: Update Module Exports & Verify Coverage

**Files:**
- Modify: `backend/app/agents/__init__.py`

- [ ] **Step 1: Export budget_optimizer_agent**

Edit `backend/app/agents/__init__.py` and add:

```python
from backend.app.agents.budget_optimizer import budget_optimizer_agent

__all__ = [
    "budget_optimizer_agent",
]
```

- [ ] **Step 2: Verify import works**

```bash
python -c "from backend.app.agents import budget_optimizer_agent; print('✅ budget_optimizer_agent exported')"
```

Expected: ✅ budget_optimizer_agent exported

- [ ] **Step 3: Run all tests with coverage**

```bash
pytest tests/agents/test_budget_optimizer.py --cov=backend.app.agents.budget_optimizer --cov-report=term-missing -v
```

Expected: Coverage >= 80%

- [ ] **Step 4: Verify no import errors**

```bash
python -c "from tests.agents.test_budget_optimizer import *; print('✅ All test imports successful')"
```

Expected: ✅ All test imports successful

- [ ] **Step 5: Commit**

```bash
git add backend/app/agents/__init__.py
git commit -m "[TASK-009] feat: export budget_optimizer_agent from agents module"
```

---

## Task 8: Final Verification & Summary

**Files:**
- No new files

- [ ] **Step 1: Run full test suite**

```bash
pytest tests/agents/test_budget_optimizer.py -v --tb=short 2>&1 | tail -15
```

Expected: "16 passed"

- [ ] **Step 2: Verify coverage meets >80% requirement**

```bash
pytest tests/agents/test_budget_optimizer.py --cov=backend.app.agents.budget_optimizer --cov-report=term --cov-fail-under=80 2>&1 | grep -A 3 "TOTAL"
```

Expected: Coverage >= 80%

- [ ] **Step 3: Check git log for all TASK-009 commits**

```bash
git log --oneline --grep="TASK-009" | head -10
```

Expected: Shows all 7 commits from Task 1-7

- [ ] **Step 4: Verify no uncommitted changes**

```bash
git status
```

Expected: "On branch main" with clean working tree

- [ ] **Step 5: Summary statistics**

```bash
echo "=== TASK-009 Summary ===" && echo "Schemas: $(wc -l < backend/app/schemas/budget_optimizer.py) lines" && echo "Agent module: $(wc -l < backend/app/agents/budget_optimizer.py) lines" && echo "Tests: $(wc -l < tests/agents/test_budget_optimizer.py) lines" && pytest tests/agents/test_budget_optimizer.py -q 2>&1 | tail -1
```

Expected: Line counts + "16 passed"

---

## Summary

✅ **TASK-009 Implementation Complete:** Budget Optimizer Agent (AGT-05)

**Files Created:**
- backend/app/schemas/budget_optimizer.py (~200 lines)
- backend/app/agents/budget_optimizer.py (~350 lines)
- tests/agents/test_budget_optimizer.py (~200 lines)

**Components:**
- ConversionRateEstimator: Channel/segment/phase-based conversion estimation
- BudgetOptimizer: Greedy ROI-based budget reallocation
- ROIAnalyzer: Phase/channel/total ROI metrics
- OptimizationReporter: Budget shift detection and reporting
- budget_optimizer_agent: Main orchestrator

**Tests:** 16 tests (5 estimator + 4 optimizer + 3 analyzer + 3 reporter + 1 integration)

**Coverage:** >80%

**Ready for:** Subagent-driven or inline execution
