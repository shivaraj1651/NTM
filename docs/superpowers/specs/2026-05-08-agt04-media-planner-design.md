# Media Planner Agent (AGT-04) Design

**Date:** 2026-05-08  
**Task:** TASK-008  
**Status:** Design Review

## Overview

The Media Planner Agent (AGT-04) transforms an approved campaign concept and budget envelope into a detailed Activation Master Plan. Each activation specifies a concrete media placement with timing, geography, reach, cost, and messaging reference. The agent uses top-down budget allocation (phases → channels → geographies) to ensure budget accountability while respecting the campaign strategist's channel recommendations.

## Purpose

Generate an executable media plan that:
- Allocates budget across campaign phases (Awareness 40%, Engagement 40%, Conversion 20%)
- Respects the campaign's strategic channel mix while adapting to budget constraints
- Creates individual activation records for each channel/geography/phase combination
- Accounts for offline channel complexities (lead times, production constraints)
- Provides financial summary and allocation audit trail

## System Architecture

### Data Flow

```
Inputs:
  - campaign_concept: CampaignConcept (from AGT-03)
  - budget_envelope: float (total budget in currency units)
  - mandate_geography: List[str] (regions/markets from original mandate)
  - contingency_reserve_pct: float (default 0.10 = 10%)

Agent Processing:
  1. Parse and validate inputs
  2. Calculate phase budgets: Awareness 40%, Engagement 40%, Conversion 20%
  3. FOR each phase:
     a. Calculate phase budget allocation
     b. FOR each channel in campaign.channel_mix:
        i. Allocate budget by channel weight
        ii. FOR each geography in mandate_geography:
            - Generate activations (reach, cost, timing, message)
            - Apply offline lead times and constraints
     c. Track cumulative spend vs. allocation
  4. Reserve 10% contingency from remaining budget
  5. Return activations + budget summary + allocation log

Output:
  - activations: List[Activation] (up to 100+)
  - budget_summary: BudgetSummary (phase/channel breakdown)
  - validation_errors: List[str] (schema/constraint violations)
  - allocation_log: List[str] (audit trail of allocation decisions)
  - status: "success" | "partial" | "failed"
```

### Key Components

**BudgetAllocator:**
- Phase-based allocation (40/40/20)
- Channel weighting (from campaign.channel_mix)
- Geography distribution (equal or market-sized)
- Contingency reserve calculation

**ActivationGenerator:**
- Reach estimation (based on audience segment size × phase penetration target)
- CPM-based cost calculation (channel-specific pricing)
- Frequency determination (phase-appropriate: high for Awareness, targeted for Conversion)
- Message versioning (tone_board + channel-specific adaptations)
- Date scheduling (phase timelines + offline lead times)

**OfflineConstraintHandler:**
- Lead time enforcement (TV 4w, Print 2w, Cinema 3w, Radio/Events 1-2w, Direct Mail 2-3w)
- Production timeline validation
- Rescheduling logic (move activation to earlier phase if needed)

## Input Specification

### CampaignConcept (from AGT-03)

```python
{
  "name": str,
  "campaign_theme": str,
  "audience_segmentation": {
    "primary": str,
    "secondary": str,
    "tertiary": str
  },
  "channel_mix": [
    {
      "channel": str,  # e.g., "TikTok", "Google Ads", "Billboard"
      "rationale": str,
      "competitor_gap": str
    }
  ],
  "campaign_phasing": {
    "awareness": str,  # e.g., "Week 1-2: Influencer seeding"
    "engagement": str,  # e.g., "Week 3-6: UGC contests"
    "conversion": str   # e.g., "Week 7-12: Direct CTA"
  },
  "message_architecture": {
    "master_message": str,
    "channel_adaptations": Dict[str, str]
  },
  "tone_board": {
    "adjectives": List[str],
    "visual_direction": str
  }
}
```

### Budget Envelope

```python
{
  "total_budget": float,  # e.g., 100000.00
  "currency": str,  # e.g., "USD"
  "phase_allocation": {
    "awareness": float,  # default 0.40
    "engagement": float,  # default 0.40
    "conversion": float   # default 0.20
  },
  "contingency_pct": float  # default 0.10
}
```

### Mandate Geography

```python
{
  "regions": List[str],  # e.g., ["North America"]
  "markets": List[str],  # e.g., ["US", "Canada"]
  "country_list": List[str]  # e.g., ["US", "CA"]
}
```

## Output Specification

### Activation Schema

Each activation represents one specific media placement at a specific time/place/audience.

```json
{
  "id": "uuid (unique activation ID)",
  "channel_enum": "enum (Social|Search|Display|Email|WhatsApp|Influencer|Print|OOH|Radio|TV|Events|Cinema|DirectMail)",
  "sub_channel": "string (specific channel name, e.g., 'TikTok', 'Google Search', 'Billboard')",
  "format": "string (media format, e.g., 'Video 15s', 'Static Image', 'Radio Spot 30s')",
  "geography": "string (specific market or region, e.g., 'US', 'NYC')",
  "placement": "string (specific placement, e.g., 'Feed', 'Search Results', 'Peak Drive Time')",
  "phase": "enum (Awareness|Engagement|Conversion)",
  "scheduled_date": "ISO date (start date of activation)",
  "duration": "int (days activation runs)",
  "frequency": "string (delivery frequency, e.g., '3x daily', 'weekly', 'continuous')",
  "audience_segment": "enum (Primary|Secondary|Tertiary)",
  "estimated_reach": "int (estimated number of people reached)",
  "estimated_cpm": "float (cost per thousand impressions)",
  "cost_estimated": "float (total activation cost in currency units)",
  "message_version_ref": "string (reference to message_architecture + tone_board)",
  "lead_time_days": "int or null (for offline channels, production lead time required)",
  "offline_constraints": "string or null (e.g., 'Requires 4-week lead time for TV production')"
}
```

### BudgetSummary Schema

```json
{
  "total_budget": float,
  "currency": str,
  "phase_breakdown": {
    "awareness": {
      "allocated": float,
      "spent": float,
      "remaining": float
    },
    "engagement": {
      "allocated": float,
      "spent": float,
      "remaining": float
    },
    "conversion": {
      "allocated": float,
      "spent": float,
      "remaining": float
    }
  },
  "channel_breakdown": {
    "channel_name": {
      "allocated": float,
      "spent": float,
      "activations_count": int
    }
  },
  "contingency": {
    "allocated": float,
    "used": float,
    "remaining": float
  },
  "total_spent": float,
  "total_remaining": float,
  "utilization_pct": float
}
```

### Agent Response

```json
{
  "activations": [Activation, Activation, ...],
  "budget_summary": BudgetSummary,
  "validation_errors": [
    "Field 'cost_estimated' missing in Activation #5",
    "Total spend $105000 exceeds budget $100000"
  ],
  "allocation_log": [
    "Phase Awareness: allocated $40000",
    "Channel TikTok (Social): allocated $16000 (40% of phase budget)",
    "Geography US: 1 activation, cost $2500, reach 50000",
    "Contingency reserved: $10000"
  ],
  "status": "success|partial|failed"
}
```

## Budget Allocation Logic

### Phase Allocation

Budget is divided into three campaign phases:
- **Awareness Phase:** 40% of total budget (broad reach, high frequency)
- **Engagement Phase:** 40% of total budget (interaction, deeper engagement)
- **Conversion Phase:** 20% of total budget (sales-focused, targeted audience)
- **Contingency Reserve:** 10% of total budget (set aside for adjustments)

Example: $100,000 budget
- Awareness: $40,000
- Engagement: $40,000
- Conversion: $20,000
- Contingency: $10,000 (reserved from cumulative spend)

### Channel Allocation (per phase)

Each phase budget is allocated across channels based on the campaign's channel_mix.

**Algorithm:**
1. Extract channel_mix from CampaignConcept
2. Calculate total channel weight (sum of channel recommendation weights, or equal if no weights)
3. For each channel: `channel_budget = phase_budget × (channel_weight / total_weight)`

Example: Awareness phase $40,000 with channel_mix [TikTok 0.4, Instagram 0.3, Email 0.3]
- TikTok: $40,000 × 0.4 = $16,000
- Instagram: $40,000 × 0.3 = $12,000
- Email: $40,000 × 0.3 = $12,000

### Geography Allocation (per channel/phase)

Channel budget is distributed across mandate geographies. For MVP: equal distribution.

Example: TikTok budget $16,000 across 2 markets [US, Canada]
- US: $8,000
- Canada: $8,000

(Future: weight by market size, market penetration targets, etc.)

### Offline Channel Lead Times

Offline channels require production lead time before campaign phase start.

| Channel | Lead Time | Scheduling Adjustment |
|---------|-----------|----------------------|
| TV | 4 weeks | Schedule start 28 days before phase |
| Print | 2 weeks | Schedule start 14 days before phase |
| Cinema | 3 weeks | Schedule start 21 days before phase |
| Radio | 1-2 weeks | Schedule start 10-14 days before phase |
| Events | 1-2 weeks | Schedule start 14 days before phase |
| Direct Mail | 2-3 weeks | Schedule start 14-21 days before phase |
| OOH (Outdoor) | 1 week | Schedule start 7 days before phase |

If rescheduling is not possible (phase already started), activation is flagged for manual review.

## Activation Generation

### For each channel/phase/geography combination:

**1. Determine Activation Parameters**

```python
channel_enum = map_to_enum(sub_channel)  # "TikTok" → "Social"
phase = current_phase  # "Awareness", "Engagement", or "Conversion"
geography = current_market  # "US", "Canada", etc.
audience_segment = phase_audience_mapping(phase)  # Awareness → Primary, Conversion → Secondary/Tertiary
```

**2. Calculate Timing**

```python
# Parse phase timeline from campaign_phasing
phase_start_date = parse_phase_start(campaign_phasing[phase])
phase_duration = parse_phase_duration(campaign_phasing[phase])

# Apply offline lead time if needed
if is_offline_channel(sub_channel):
    lead_time = offline_lead_times[channel_enum]
    scheduled_date = phase_start_date - timedelta(days=lead_time)
else:
    scheduled_date = phase_start_date

duration = phase_duration  # e.g., 14 days for "Week 1-2"
frequency = phase_frequency_mapping(phase)  # Awareness: "3x daily", Engagement: "2x daily", Conversion: "1x daily"
```

**3. Calculate Reach & Cost**

```python
# Estimate audience size for segment
audience_size = estimate_segment_size(geography, audience_segment)

# Phase penetration target (what % of audience do we want to reach)
phase_penetration = phase_penetration_target[phase]  # Awareness: 60%, Engagement: 30%, Conversion: 10%

estimated_reach = audience_size × phase_penetration

# CPM varies by channel (cost per thousand impressions)
estimated_cpm = channel_cpm_rates[sub_channel]  # Social: $3-8, Search: $5-15, TV: $15-30, etc.

cost_calculated = (estimated_reach / 1000) × estimated_cpm

# Ensure activation cost doesn't exceed remaining channel budget
if cost_calculated > remaining_channel_budget:
    estimated_reach = (remaining_channel_budget / estimated_cpm) × 1000
    cost_estimated = remaining_channel_budget
else:
    cost_estimated = cost_calculated

update_spend_tracking(phase, channel, geography, cost_estimated)
```

**4. Apply Message Versioning**

```python
# Reference tone_board + channel-specific message from message_architecture
message_version_ref = f"{channel} ({', '.join(tone_board.adjectives)}) - {message_architecture.channel_adaptations[sub_channel]}"

# Example: "TikTok (authentic, bold, witty, inclusive, innovative) - 30-second storytelling format with trending sounds"
```

**5. Log Offline Constraints (if applicable)**

```python
if is_offline_channel(sub_channel):
    lead_time_days = offline_lead_times[channel_enum]
    offline_constraints = f"Requires {lead_time_days}-day lead time for {sub_channel} production; schedule start date {lead_time_days} days before phase start"
else:
    lead_time_days = None
    offline_constraints = None
```

## Error Handling & Validation

### Budget Validation

- **Over-budget:** If sum(activation costs) > budget_envelope:
  - Log error: "Total spend ${total} exceeds budget ${budget}"
  - Return status: "partial" (activations generated, but budget exceeded)
  - Suggest adjustments: reduce reach, lower CPM, fewer activations

- **Under-allocation:** If phase budget unfillable (not enough channels for phase):
  - Log warning: "Phase {phase} budget only ${allocated}, but requested ${phase_budget}"
  - Proceed with available channels, mark remaining budget as reserved

- **Contingency warning:** If contingency_reserve < 5% of total budget:
  - Log warning: "Contingency reserve {reserve}% is below recommended 10%"
  - Still allocate reserve, but flag for human review

### Constraint Violations

- **Offline lead time conflict:** If offline activation can't be scheduled before phase starts:
  - Log warning: "TV activation flagged: lead time 28 days exceeds phase start date"
  - Reschedule to earlier phase if possible, OR flag for manual review

- **Reach exceeds audience:** If estimated_reach > audience_segment_size:
  - Cap reach at audience_segment_size
  - Recalculate cost: `cost = (capped_reach / 1000) × cpm`
  - Log warning: "Reach capped to audience size for {geography}/{audience_segment}"

- **CPM estimate missing:** If channel CPM not in database:
  - Use fallback CPM ($10.00 default)
  - Log warning: "CPM missing for {sub_channel}, using fallback $10.00"

### Schema Validation (Strict)

Validate each Activation before returning:

**Required fields:** channel_enum, sub_channel, format, geography, placement, phase, scheduled_date, duration, frequency, audience_segment, estimated_reach, cost_estimated

**Data type checks:**
- scheduled_date: ISO date format
- duration, estimated_reach: positive integers
- cost_estimated, estimated_cpm: positive floats
- channel_enum, phase, audience_segment: valid enum values

**Logic checks:**
- scheduled_date + duration ≤ next phase start (no overlap)
- cost_estimated > 0
- estimated_reach > 0

**Validation errors:** Return list of field/message pairs for any violations.

### Output Response Structure

```json
{
  "activations": [valid Activation objects],
  "budget_summary": BudgetSummary,
  "validation_errors": [
    "Activation #7: Field 'cost_estimated' missing",
    "Total spend $105000 exceeds budget $100000"
  ],
  "allocation_log": [
    "Phase Awareness: allocated $40000.00",
    "Channel TikTok: allocated $16000.00 (40% of phase)",
    "Geography US: 4 activations, total cost $8000.00, reach 800000",
    "Offline constraint: TV activation scheduled 28 days before phase start",
    "Contingency reserved: $10000.00"
  ],
  "status": "success|partial|failed"
}
```

**Status meanings:**
- `success`: All activations valid, budget balanced, no constraint violations
- `partial`: Some activations valid, minor issues (reach capped, CPM fallback used, warnings logged)
- `failed`: Critical errors (over-budget, invalid schema, unsolvable constraints)

## Testing Strategy

### Unit Tests

**BudgetAllocator:**
- `test_phase_allocation_40_40_20()` — verify Awareness 40%, Engagement 40%, Conversion 20%
- `test_channel_weighting()` — allocate channel budget by weight
- `test_geography_equal_distribution()` — distribute channel budget equally across markets
- `test_contingency_reserve_10pct()` — reserve 10% of cumulative spend

**ActivationGenerator:**
- `test_reach_calculation()` — audience_size × phase_penetration = reach
- `test_cost_calculation()` — (reach / 1000) × cpm = cost
- `test_frequency_by_phase()` — Awareness high, Conversion targeted
- `test_message_version_ref()` — correct tone_board + channel adaptation reference

**OfflineConstraintHandler:**
- `test_tv_lead_time_4_weeks()` — TV activation scheduled 28 days early
- `test_print_lead_time_2_weeks()` — Print activation scheduled 14 days early
- `test_rescheduling_conflict()` — detect when lead time conflicts with phase start
- `test_reach_cap_at_audience_size()` — cap reach to segment size

**ActivationValidator:**
- `test_schema_validation_all_fields()` — all required fields present
- `test_enum_validation()` — channel_enum, phase, audience_segment valid
- `test_date_logic_no_overlap()` — activations don't overlap phases
- `test_cost_reach_positive()` — cost and reach > 0

### Integration Tests

- `test_full_flow_budget_to_activations()` — end-to-end: budget → phases → channels → geographies → activations
- `test_budget_balance()` — sum(activation costs) ≤ budget_envelope (before contingency)
- `test_constraint_scenarios()` — tight budget, complex geography, all offline channels, mixed online/offline
- `test_edge_cases()` — single-channel campaign, zero-budget phase, misaligned timeline

### Coverage Target

**>80%** (per CLAUDE.md Phase 1 requirement)

## Success Criteria

✅ Agent generates list of Activation objects with all required fields  
✅ Each activation has: channel, sub_channel, format, geography, placement, phase, timing, reach, cost, message_version_ref  
✅ BudgetSummary shows phase/channel/geography breakdown + contingency  
✅ Budget allocation respects campaign's channel_mix while adapting to constraints  
✅ Offline lead times enforced (TV 4w, Print 2w, Cinema 3w, Radio/Events 1-2w, Direct Mail 2-3w)  
✅ Schema validation strict (errors on missing fields, invalid enums, conflicting dates)  
✅ Allocation log auditable (trace every budget decision)  
✅ Test coverage >80%  
✅ No lint/type errors  
✅ Latency <6s per campaign (per session requirements)

## Next Steps

1. Write implementation plan (TASK-008 plan)
2. Implement agent module + validators + test suite
3. Verify schema compliance + error handling
4. Commit + PR review
