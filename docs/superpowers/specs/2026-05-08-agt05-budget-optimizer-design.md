# Budget Optimizer Agent (AGT-05) Design

**Date:** 2026-05-08  
**Task:** TASK-009  
**Status:** Design Review

## Overview

The Budget Optimizer Agent (AGT-05) transforms the Media Planner's activation plan into a budget-optimized plan by reallocating spend across activations to maximize reach-weighted-by-conversion ROI. It respects mandate phase structure (40/40/20), locked lead times, and channel selection while optimizing financial allocation for maximum campaign efficiency.

## Purpose

Optimize budget allocation for maximum impact by:
- Estimating conversion likelihood per activation (historical + defaults + campaign context)
- Calculating reach-weighted-conversion score for each activation
- Reallocating budget to prioritize high-ROI activations
- Maintaining strategic structure (phases, channels, geographies) from AGT-04
- Providing transparent ROI analysis and budget shift reporting

## System Architecture

### Data Flow

```
Inputs:
  - activations: List[Activation] (from AGT-04 Media Planner)
  - budget_summary: BudgetSummary (from AGT-04)
  - campaign_context: CampaignConcept (from AGT-03)
  - historical_performance: Optional[Dict] (from database or defaults)

Agent Processing:
  1. Estimate conversion rates per activation
     - Query historical data by channel/segment/campaign type
     - Fallback to channel + segment defaults
     - Refine by campaign tone alignment
  2. Calculate reach-weighted-conversion score per activation
     - Score = estimated_reach × estimated_conversion_rate
  3. Optimize budget allocation
     - Respecting phase budgets (40/40/20 fixed)
     - Allow channel reallocation within phases
     - Deprioritize low-ROI activations
     - Preserve scheduled dates and lead times
  4. Generate ROI projections and optimization report
  5. Validate optimized activations against schema

Output:
  - optimized_activations: List[Activation] (with new cost_estimated)
  - roi_analysis: ROIAnalysis (phase/channel/total metrics)
  - optimization_report: OptimizationReport (budget shifts + reasoning)
  - validation_errors: List[str]
  - status: str (success|partial|failed)
```

## Input Specification

### Activations (from AGT-04)

```python
{
  "activations": [
    {
      "id": "uuid",
      "channel_enum": "Social",
      "sub_channel": "TikTok",
      "format": "Video 15s",
      "geography": "US",
      "placement": "Feed",
      "phase": "Awareness",
      "scheduled_date": "2026-06-01",
      "duration": 14,
      "frequency": "3x daily",
      "audience_segment": "Primary",
      "estimated_reach": 500000,
      "estimated_cpm": 5.0,
      "cost_estimated": 2500.0,  # WILL BE OPTIMIZED
      "message_version_ref": "TikTok (authentic, bold)",
      "lead_time_days": 0,  # LOCKED - won't change
      "offline_constraints": null
    },
    # ... more activations
  ]
}
```

### Campaign Context (from AGT-03)

```python
{
  "name": "Q2 Awareness Campaign",
  "campaign_theme": "Authentic storytelling",
  "tone_board": {
    "adjectives": ["authentic", "bold", "witty", "inclusive", "innovative"],
    "visual_direction": "Modern, relatable, high-energy"
  },
  "message_architecture": {
    "master_message": "Be yourself, own your story",
    "channel_adaptations": {
      "TikTok": "30-second storytelling",
      "Email": "Newsletter signup call-to-action"
    }
  },
  "target_audience": "18-35, urban, digitally native"
  # ... other fields
}
```

### Historical Performance (Optional)

```python
{
  "channel_conversion_rates": {
    "TikTok": 0.008,  # 0.8% conversion
    "Instagram": 0.006,
    "Email": 0.03,
    "TV": 0.002
  },
  "segment_multipliers": {
    "Primary": 1.0,  # baseline
    "Secondary": 0.7,  # 30% lower
    "Tertiary": 0.4   # 60% lower
  },
  "campaign_type_adjustments": {
    "awareness": 0.5,  # Awareness campaigns convert at 50% of engagement
    "engagement": 1.0,
    "conversion": 1.5   # Conversion phase activations convert higher
  }
}
```

If not provided, use safe defaults.

## Output Specification

### OptimizedActivation Schema

```json
{
  "id": "uuid",
  "channel_enum": "Social",
  "sub_channel": "TikTok",
  "format": "Video 15s",
  "geography": "US",
  "placement": "Feed",
  "phase": "Awareness",
  "scheduled_date": "2026-06-01",
  "duration": 14,
  "frequency": "3x daily",
  "audience_segment": "Primary",
  "estimated_reach": 500000,
  "estimated_cpm": 5.0,
  "original_cost_estimated": 2500.0,
  "optimized_cost_estimated": 3200.0,
  "message_version_ref": "TikTok (authentic, bold)",
  "lead_time_days": 0,
  "offline_constraints": null,
  "estimated_conversion_rate": 0.008,
  "reach_weighted_conversions": 4000,
  "roi_per_dollar": 1.25,
  "optimization_action": "prioritized",
  "reason": "High ROI for audience/phase combination, strong message fit"
}
```

### ROIAnalysis Schema

```json
{
  "phase_summary": {
    "Awareness": {
      "allocated_budget": 40000.0,
      "total_reach": 20000000,
      "total_reach_weighted_conversions": 80000,
      "average_roi": 2.0,
      "channel_breakdown": {
        "TikTok": 16000.0,
        "Instagram": 12000.0,
        "Email": 12000.0
      }
    },
    "Engagement": {
      "allocated_budget": 40000.0,
      "total_reach": 10000000,
      "total_reach_weighted_conversions": 120000,
      "average_roi": 3.0,
      "channel_breakdown": { ... }
    },
    "Conversion": {
      "allocated_budget": 20000.0,
      "total_reach": 2000000,
      "total_reach_weighted_conversions": 60000,
      "average_roi": 3.0,
      "channel_breakdown": { ... }
    }
  },
  "channel_summary": {
    "TikTok": {
      "total_allocated_budget": 28000.0,
      "activation_count": 6,
      "total_reach": 15000000,
      "total_reach_weighted_conversions": 120000,
      "average_roi": 4.3
    },
    "Email": {
      "total_allocated_budget": 26000.0,
      "activation_count": 5,
      "total_reach": 500000,
      "total_reach_weighted_conversions": 15000,
      "average_roi": 0.58
    },
    # ... more channels
  },
  "total_budget": 100000.0,
  "total_reach": 32500000,
  "total_reach_weighted_conversions": 260000,
  "campaign_roi": 2.6
}
```

### OptimizationReport Schema

```json
{
  "summary": "Budget reallocated to prioritize high-ROI channels (TikTok +12%, Email -8%)",
  "budget_shifts": [
    {
      "from_activation": "Instagram US Awareness",
      "to_activation": "TikTok US Awareness",
      "amount": 500.0,
      "reason": "TikTok has 40% higher ROI for Primary audience in Awareness phase"
    },
    {
      "from_activation": "Display US Conversion",
      "to_activation": "Email US Conversion",
      "amount": 300.0,
      "reason": "Email converts at 3% vs Display 0.5%, reallocated for efficiency"
    },
    # ... more shifts
  ],
  "prioritized_activations": [
    {
      "activation_id": "uuid-email-conversion",
      "activation_name": "Email US Conversion",
      "original_budget": 2000.0,
      "optimized_budget": 3200.0,
      "budget_increase_pct": 60,
      "roi_per_dollar": 3.5,
      "reason": "Highest ROI activation (3.5x). Strong conversion likelihood (3%) for Primary audience"
    }
  ],
  "deprioritized_activations": [
    {
      "activation_id": "uuid-display-awareness",
      "activation_name": "Display US Awareness",
      "original_budget": 1500.0,
      "optimized_budget": 800.0,
      "budget_decrease_pct": 47,
      "roi_per_dollar": 0.4,
      "reason": "Lowest ROI activation. Reallocated budget to higher-performing channels in Awareness phase"
    }
  ],
  "constraints_maintained": {
    "phase_budgets": "40% Awareness / 40% Engagement / 20% Conversion ✓",
    "scheduled_dates": "All dates locked (no changes) ✓",
    "channels": "All channels preserved from Media Planner ✓",
    "geographies": "All geographies preserved from Media Planner ✓"
  }
}
```

### Agent Response

```json
{
  "optimized_activations": [
    { ... OptimizedActivation ... },
    { ... more activations ... }
  ],
  "roi_analysis": { ... ROIAnalysis ... },
  "optimization_report": { ... OptimizationReport ... },
  "validation_errors": [],
  "status": "success"
}
```

**Status values:**
- `"success"` - Optimization complete, all validations passed
- `"partial"` - Optimization complete but some data gaps/fallbacks used (e.g., missing historical data)
- `"failed"` - Couldn't optimize, returned original plan with error details

## Optimization Algorithm

### Conversion Rate Estimation

**Step 1: Historical Data Lookup**
```
Query database: SELECT conversion_rate FROM campaign_performance 
WHERE channel = activation.channel_enum
  AND segment = activation.audience_segment
  AND campaign_type = phase.lower()
LIMIT 1
```

**Step 2: Fallback to Defaults**
If no historical data:
```
base_rate = CHANNEL_DEFAULTS[activation.sub_channel]  # e.g., TikTok 0.8%
segment_multiplier = SEGMENT_MULTIPLIERS[activation.audience_segment]
phase_multiplier = PHASE_ADJUSTMENTS[activation.phase]
estimated_rate = base_rate × segment_multiplier × phase_multiplier
```

**Step 3: Refine by Campaign Context**
If campaign tone aligns strongly with channel best practices:
```
tone_score = align_tone_to_channel(campaign.tone_board, activation.channel_enum)
# tone_score: 0.8-1.2 (0.8 = misaligned, 1.2 = perfectly aligned)
estimated_rate = estimated_rate × tone_score
```

**Clamp result:** 0.001 ≤ estimated_rate ≤ 0.10 (0.1% to 10%)

### Budget Optimization

**Algorithm: Greedy Reallocation**

1. Calculate reach-weighted-conversion score per activation:
   ```
   score = estimated_reach × estimated_conversion_rate
   roi_per_dollar = score / activation.cost_estimated
   ```

2. Sort activations by `roi_per_dollar` (highest first)

3. Reallocate budget within each phase:
   - Start with top-ROI activations, increase budget (up to available phase budget)
   - For low-ROI activations, reduce budget (down to minimum viable, e.g., $100)
   - Maintain phase total = original phase budget allocation

4. Track budget shifts for reporting:
   - Document any activation with budget change > 5%
   - Record source/destination of reallocation
   - Store reason (ROI comparison)

**Constraints enforced:**
- Total Awareness budget = original × 0.40
- Total Engagement budget = original × 0.40
- Total Conversion budget = original × 0.20
- Minimum activation budget = $100 (don't drop below)
- Maximum activation budget = activation's phase budget (don't overspend)
- Scheduled dates and lead times: NO CHANGES

### ROI Calculation

**Per Activation:**
```
roi_per_dollar = (estimated_reach × estimated_conversion_rate) / optimized_cost_estimated
```

**Per Channel:**
```
total_reach_weighted = SUM(estimated_reach × estimated_conversion_rate for all activations)
total_spend = SUM(optimized_cost_estimated for all activations)
channel_roi = total_reach_weighted / total_spend
```

**Per Phase:**
```
Same calculation as channel, grouped by phase instead
```

**Campaign Total:**
```
total_reach_weighted = SUM(reach_weighted conversions all activations)
total_budget = SUM(optimized_cost for all activations)
campaign_roi = total_reach_weighted / total_budget
```

## Validation & Error Handling

### Schema Validation

All optimized activations must match Activation schema:
- Required fields present (id, channel_enum, cost_estimated, etc.)
- Enum values valid (channel_enum in ChannelEnum, phase in PhaseEnum)
- Numeric constraints (cost >= 0, reach >= 1, estimated_conversion_rate 0.0-1.0)

### Budget Validation

- Sum of Awareness activations = original Awareness budget ± $1 (rounding tolerance)
- Sum of Engagement activations = original Engagement budget ± $1
- Sum of Conversion activations = original Conversion budget ± $1
- Total campaign budget = original total ± $1

### Data Gap Handling

**If conversion rate estimation fails for an activation:**
- Log warning: "Using conservative default for {activation_id}, historical data unavailable"
- Use conservative default: 0.5% conversion rate
- Mark status as "partial" (not "failed")

**If optimization algorithm fails:**
- Return original activation list unchanged
- Document reason in validation_errors
- Set status to "partial" or "failed"

**If ROI calculation invalid (e.g., zero cost):**
- Skip activation from optimization
- Log error
- Return it in results with original cost

## Implementation Details

### Module Structure

```
backend/app/agents/budget_optimizer.py
├── ConversionRateEstimator (class)
│   ├── estimate_rate(activation, campaign_context, historical_data) → float
│   ├── query_historical_data() → Dict[str, float]
│   └── apply_tone_alignment() → float (multiplier)
├── BudgetOptimizer (class)
│   ├── optimize(activations, phase_budgets) → List[OptimizedActivation]
│   ├── calculate_roi_per_dollar() → Dict[str, float]
│   └── allocate_budget_greedy() → List[OptimizedActivation]
├── ROIAnalyzer (class)
│   ├── analyze_roi(optimized_activations) → ROIAnalysis
│   ├── phase_summary() → Dict
│   └── channel_summary() → Dict
├── OptimizationReporter (class)
│   ├── generate_report(original, optimized) → OptimizationReport
│   ├── identify_shifts() → List[BudgetShift]
│   └── categorize_actions() → (prioritized, deprioritized)
└── budget_optimizer_agent() (async main)
    ├── Validate inputs
    ├── EstimationRateEstimator → estimate conversions
    ├── BudgetOptimizer → reallocate budget
    ├── ROIAnalyzer → calculate metrics
    ├── OptimizationReporter → generate report
    ├── Validate optimized activations
    └── Return structured response
```

### System Prompt

```
You are a budget optimization specialist. Your role is to reallocate media spend to maximize campaign ROI while respecting strategic constraints.

For the given activation plan and budget envelope:
1. Estimate conversion likelihood per activation (historical + defaults + campaign context)
2. Calculate reach-weighted-conversion ROI for each activation
3. Reallocate budget to prioritize high-ROI activations
4. Maintain phase budget structure (40% Awareness, 40% Engagement, 20% Conversion)
5. Do NOT change channels, geographies, scheduled dates, or lead times
6. Generate transparent ROI analysis and optimization report

CONSTRAINTS:
- Phase budgets are FIXED at 40/40/20 allocation
- Scheduled dates and lead times CANNOT change
- Channels and geographies are LOCKED from Media Planner
- Minimum activation spend: $100 (don't drop below)
- Total budget: Cannot exceed original allocation

OUTPUT:
Return valid JSON with:
- optimized_activations (with new cost_estimated, conversion_rate, ROI)
- roi_analysis (phase/channel/total metrics)
- optimization_report (budget shifts, prioritized/deprioritized activations)
- validation_errors (any data gaps or issues)
- status (success|partial|failed)
```

### Dependencies

- `anthropic.AsyncAnthropic` (Claude API) - for future LLM-based enhancements
- `backend/app/schemas/media_plan.py` (Activation, BudgetSummary)
- `backend/app/schemas/campaign_concept.py` (CampaignConcept)
- `pydantic.BaseModel` (validation)
- `uuid.uuid4()` (IDs)
- `logging` (tracking)
- `json` (serialization)
- `Database` (optional: historical performance queries)

## Testing Strategy

**Unit Tests:**
- `test_conversion_rate_historical_lookup()` - fetches and uses historical data
- `test_conversion_rate_fallback_defaults()` - falls back when no historical data
- `test_conversion_rate_tone_refinement()` - adjusts by campaign tone alignment
- `test_roi_calculation_correct()` - reach-weighted-conversions / cost math
- `test_budget_optimizer_respects_phase_budgets()` - 40/40/20 maintained
- `test_budget_optimizer_prioritizes_high_roi()` - high-ROI activations get more budget
- `test_budget_optimizer_deprioritizes_low_roi()` - low-ROI activations get less budget
- `test_optimization_preserves_dates_channels_geographies()` - locked constraints maintained
- `test_roi_analyzer_phase_summary()` - phase ROI calculations correct
- `test_roi_analyzer_channel_summary()` - channel ROI calculations correct
- `test_optimization_reporter_shifts()` - budget shift detection accurate
- `test_optimization_reporter_reasoning()` - shift explanations meaningful

**Integration Tests:**
- `test_budget_optimizer_full_flow()` - end-to-end: AGT-04 input → optimized activations
- `test_budget_optimizer_constraint_validation()` - phase budgets, dates, channels all preserved
- `test_budget_optimizer_improves_roi()` - optimized activations have higher total ROI than original

**Coverage Target:** >80% (per CLAUDE.md Phase 1)

## Success Criteria

✅ Agent takes AGT-04 activations + campaign context as input  
✅ Estimates conversion rates per activation (historical + defaults + context)  
✅ Optimizes budget allocation to maximize reach-weighted-by-conversion ROI  
✅ Maintains phase budget structure (40/40/20 fixed)  
✅ Preserves channels, geographies, scheduled dates, lead times  
✅ Generates transparent ROI analysis (activation, channel, phase, total)  
✅ Provides optimization report with budget shifts and reasoning  
✅ Validates optimized activations against schema  
✅ Handles data gaps gracefully (fallback to defaults)  
✅ Test coverage >80%  
✅ No lint/type errors  
✅ Latency <1s per optimization  

## Next Steps

1. Review this design spec
2. Write implementation plan (TASK-009 plan)
3. Implement agent module + components
4. Write unit + integration tests
5. Verify schema compliance + error handling
6. Commit + PR review
