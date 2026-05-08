# Campaign Strategist Agent (AGT-03) Design

**Date:** 2026-05-08  
**Task:** TASK-006  
**Status:** Design Review

## Overview

The Campaign Strategist Agent (AGT-03) generates 3 comprehensive campaign concepts based on a mandate summary and competitive intelligence report. Each concept balances mandate alignment with competitive gap exploitation, filtered for legal/regulatory/sensitivity risks, and validated against the CampaignConcept schema.

## Purpose

Generate creative campaign ideas that:
- Exploit competitor whitespace gaps (untapped channels, messaging gaps, geographic gaps)
- Align with mandate constraints (budget, timeline, geography, target audience, brand guidelines)
- Are risk-filtered to remove legal, regulatory, or sensitivity concerns
- Provide strategic recommendations (not just creative ideas)

## System Architecture

### Data Flow

```
Inputs:
  - mandate_summary: MandateSummaryCard (from AGT-01)
  - ci_report: CIReport (from AGT-02)

Agent Processing:
  1. Parse + validate inputs
  2. FOR each of 3 campaigns:
     a. Generate campaign concept (iterative LLM calls)
     b. Risk filter: assess for legal/regulatory/sensitivity concerns
     c. If risk detected: regenerate concept (max 1 retry)
     d. If risk persists: skip campaign, log reason
  3. Validate all concepts match CampaignConcept schema
  4. Return structured JSON + validation errors + regeneration log

Output:
  - campaigns: List[CampaignConcept] (up to 3)
  - validation_errors: List[str]
  - regeneration_log: List[str]
```

## Input Specification

### MandateSummaryCard (from AGT-01)

```python
{
  "campaign_name": str,
  "objective": str,
  "target_audience": str,
  "timeline": str,  # e.g., "Q2 2026 (12 weeks)"
  "budget": {
    "total_amount": float,
    "currency": str,
    "allocation_strategy": str
  },
  "geography": {
    "regions": List[str],
    "markets": List[str],
    "country_list": List[str]
  },
  "brand_guidelines": {
    "tone": str,
    "voice": str,
    "style_constraints": str
  }
}
```

### CIReport (from AGT-02)

```python
{
  "competitors": List[CompetitorMetrics],
  "whitespace_opportunities": {
    "untapped_channels": List[str],
    "messaging_gaps": List[str],
    "geographic_gaps": List[str]
  }
}
```

Where `CompetitorMetrics` includes:
- name, confidence_score
- channels: Dict[channel_name, ChannelMetrics] (presence, spend, impressions, keywords, audiences)
- messaging_themes: List[str]
- geographic_focus: List[str]
- estimated_annual_spend: Optional[float]

## Output Specification

### CampaignConcept Schema

```json
{
  "id": "uuid",
  "name": "string",
  "tagline": "string",
  "strategic_narrative": "string (1-2 sentences explaining why this exploits competitor gaps)",
  "campaign_theme": "string",
  "audience_segmentation": {
    "primary": "string (primary target segment)",
    "secondary": "string (secondary segment)",
    "tertiary": "string (tertiary segment)"
  },
  "channel_mix": [
    {
      "channel": "string (e.g., 'TikTok', 'Email', 'LinkedIn')",
      "rationale": "string (why this channel aligns with audience)",
      "competitor_gap": "string (why this is a gap vs competitors)"
    }
  ],
  "message_architecture": {
    "master_message": "string (core campaign message)",
    "channel_adaptations": {
      "channel_name": "string (adaptation for specific channel)"
    }
  },
  "campaign_phasing": {
    "awareness": "string (tactics + timeline for awareness phase)",
    "engagement": "string (tactics + timeline for engagement phase)",
    "conversion": "string (tactics + timeline for conversion phase)"
  },
  "tone_board": {
    "adjectives": ["string", "string", "string", "string", "string"],
    "visual_direction": "string (description of visual style, color palette, etc.)"
  },
  "risk_flags": {
    "legal": "string or null (e.g., unsubstantiated claims, IP concerns)",
    "regulatory": "string or null (e.g., geographic compliance, data privacy)",
    "sensitivity": "string or null (e.g., controversial positioning, offensive targeting)"
  },
  "mandate_fit_score": "int (1-10, how well does this align with mandate)",
  "gap_exploitation_score": "int (1-10, how aggressively does this exploit competitor gaps)"
}
```

### Agent Response

```json
{
  "campaigns": [CampaignConcept, CampaignConcept, CampaignConcept],
  "validation_errors": [
    "Campaign #1: missing field 'message_architecture.master_message'",
    "Campaign #3: tone_board.adjectives has 3 items, expected 5"
  ],
  "regeneration_log": [
    "Campaign #1 regenerated: legal risk flagged (unsubstantiated claims)",
    "Campaign #2 regenerated: regulatory risk flagged (geo compliance issue)",
    "Campaign #3 skipped: legal risk persisted after 1 retry"
  ]
}
```

## Agent Flow

### Generation Strategy

**LLM Model:** Claude Sonnet (claude-sonnet-4-20250514)  
**Max Tokens:** 4000 per call  
**Generation Approach:** Iterative (1 campaign per LLM call, to isolate failures)

### Iterative Generation Loop (per Campaign)

1. **Generate Campaign**
   - Call Claude with system prompt (strategist role, constraints, schema)
   - User prompt: "Generate campaign #N that exploits these competitor gaps while respecting mandate constraints"
   - Provide: mandate summary, CI report, competitor context, whitespace opportunities

2. **Risk Assessment**
   - Extract risk_flags from LLM response
   - If any flag is non-null → Proceed to regeneration

3. **Regeneration (if risk detected)**
   - Log: "Campaign #X flagged for [risk_type]: [description]"
   - Call Claude again with revised prompt: "Previous concept flagged for [risk]. Revise to mitigate this concern while maintaining strategic relevance."
   - Re-assess risk flags
   - If still risky → Mark campaign as skipped, log reason
   - If cleared → Add to results

4. **Add to Results**
   - If valid (no risk or risk cleared): Add CampaignConcept to results list
   - If skipped: Log in regeneration_log, continue to next campaign

### Constraint Checking

**Hard Constraints (enforce - reject campaign if violated):**
- Budget allocation ≤ mandate total_amount
- Timeline ≤ mandate timeline
- Target audience aligns with mandate objective
- Geographic focus within mandate regions/markets/countries

**Soft Constraints (flag only - don't reject):**
- Tone significantly different from brand_guidelines → log as "Brand tone deviation" in regeneration_log, but don't regenerate
- Channel mix differs from historical patterns → note in campaign, don't regenerate

## Risk Filtering

### Risk Types & Detection

| Risk Type | Examples | Regeneration Prompt |
|-----------|----------|-------------------|
| **Legal** | Unsubstantiated claims, IP concerns, false advertising | "Remove unsubstantiated claims. Ensure all benefits can be substantiated. Focus on verifiable mandate-aligned messaging." |
| **Regulatory** | Geographic compliance (e.g., medical claims in restricted regions), data privacy concerns | "Ensure compliance with regulations in target geographies: [list]. Remove any messaging that violates regional constraints." |
| **Sensitivity** | Offensive audience targeting, controversial positioning, tone misalignment | "Adopt tone from brand guidelines: [tone/voice]. Avoid sensitive or controversial positioning. Ensure inclusive audience segmentation." |

### Risk Assessment Method

In the LLM system prompt, instruct Claude to self-assess each concept:

```
After generating the campaign, assess for risks:
- legal_risk: null or "brief description of concern"
- regulatory_risk: null or "brief description of concern"
- sensitivity_risk: null or "brief description of concern"

Include these fields in the JSON output. If any field is non-null, the orchestrator will request regeneration.
```

## Validation & Error Handling

### Schema Validation (Strict)

After all campaigns are generated, validate each CampaignConcept:

1. **Required Fields Check**
   - name, tagline, strategic_narrative, campaign_theme
   - audience_segmentation (primary, secondary, tertiary)
   - channel_mix (non-empty, each with channel, rationale, competitor_gap)
   - message_architecture (master_message, channel_adaptations)
   - campaign_phasing (awareness, engagement, conversion)
   - tone_board (5 adjectives, visual_direction)
   - mandate_fit_score, gap_exploitation_score

2. **Data Type Check**
   - adjectives: exactly 5 strings
   - scores: integers 1-10
   - channel_mix: non-empty list of objects
   - risk_flags: all fields null or string

3. **Validation Errors**
   - If any field missing or invalid → add error to validation_errors list
   - Example: "Campaign #1: missing field 'message_architecture.master_message'"

### Error Handling Strategy

- **Partial Success:** If <2 valid campaigns after regeneration attempts → return what's valid + error log (don't fail completely)
- **Parse Failure:** If LLM response unparseable → log error, skip that attempt, retry once with "Format as valid JSON only, no markdown or extra text"
- **Total Failure:** If all 3 campaigns fail validation → return empty campaigns array + detailed error log explaining why

### Response Format on Error

```json
{
  "campaigns": [],
  "validation_errors": [
    "Campaign #1: unparseable JSON response",
    "Campaign #2: missing field 'channel_mix'",
    "Campaign #3: all 5 adjectives required in tone_board"
  ],
  "regeneration_log": [
    "Campaign #1 skipped: LLM parse failure after 1 retry",
    "Campaign #2 regenerated: legal risk flagged (unsubstantiated benefit claim)",
    "Campaign #3 skipped: validation failed after regeneration"
  ]
}
```

## Implementation Details

### Module Structure

```
backend/app/agents/campaign_strategist.py
├── CampaignConceptValidator (class)
│   ├── validate_schema(concept: dict) → List[str] (error list)
│   ├── validate_required_fields() 
│   ├── validate_data_types()
│   └── validate_nested_objects()
├── RiskFilter (class)
│   ├── assess_risk(concept: dict, mandate: dict, ci_report: dict) → Dict[str, Optional[str]]
│   ├── should_regenerate(risk_flags: dict) → bool
│   └── get_regeneration_prompt(risk_type: str) → str
├── campaign_strategist_agent() (async main orchestrator)
│   ├── Validate inputs
│   ├── FOR each campaign (0-2):
│   │   ├── Generate campaign concept
│   │   ├── Assess risk
│   │   ├── Regenerate if needed (max 1 retry)
│   │   ├── Validate schema
│   │   └── Add to results
│   └── Return structured response
```

### System Prompt

```
You are a campaign strategist. Your role is to generate creative, mandate-aligned campaign concepts that exploit competitor whitespace gaps.

For each campaign concept, you will:
1. Generate a campaign name and tagline that are memorable and gap-exploiting
2. Define a strategic narrative (1-2 sentences) explaining why this concept is differentiated
3. Identify campaign theme, audience segments (primary/secondary/tertiary), and channel mix
4. Develop message architecture (master message + channel-specific adaptations)
5. Map campaign phasing (Awareness → Engagement → Conversion)
6. Create a tone board (5 adjectives + visual direction description)
7. Self-assess for legal, regulatory, and sensitivity risks

HARD CONSTRAINTS (reject if violated):
- Budget allocation must not exceed mandate total_amount
- Timeline must not exceed mandate timeline
- Target audience must align with mandate objective
- Geographic focus must be within mandate regions/markets/countries

SOFT CONSTRAINTS (flag only):
- Tone should align with brand_guidelines; deviations noted but not rejected
- Channel mix should balance untapped channels (gap exploitation) with established channels (mandate fit)

RISK ASSESSMENT:
After generating each campaign, assess these risks:
- legal_risk: null or "brief description" (unsubstantiated claims, IP issues, false advertising)
- regulatory_risk: null or "brief description" (geographic compliance, data privacy)
- sensitivity_risk: null or "brief description" (offensive targeting, controversial positioning, brand tone misalignment)

OUTPUT FORMAT:
Return valid JSON matching the CampaignConcept schema. Include all required fields. Format as pure JSON only, no markdown or extra text.
```

### Dependencies

- `anthropic.AsyncAnthropic` (Claude API)
- `backend/app/schemas/competitive_intel.py` (MandateSummaryCard, CIReport types)
- `pydantic.BaseModel` (CampaignConcept schema definition + validation)
- `uuid.uuid4()` (campaign IDs)
- `logging` (regeneration log tracking)
- `json` (parsing LLM responses)

## Testing Strategy

**Unit Tests:**
- `test_validator_required_fields()` - verify all required fields checked
- `test_validator_data_types()` - verify type validation (scores are int 1-10, adjectives list length)
- `test_risk_filter_legal()` - mock LLM response with legal risk, verify regeneration prompt
- `test_risk_filter_regulatory()` - mock LLM response with regulatory risk
- `test_risk_filter_sensitivity()` - mock LLM response with sensitivity risk
- `test_constraint_check_budget()` - verify hard constraint enforcement
- `test_constraint_check_timeline()` - verify hard constraint enforcement

**Integration Tests:**
- `test_campaign_strategist_full_flow()` - mock mandate + CI report, verify 3 valid concepts returned
- `test_campaign_strategist_risk_regeneration()` - mock risky concept, verify regeneration + success
- `test_campaign_strategist_validation_errors()` - mock schema violations, verify error reporting

**Coverage Target:** >80% (per CLAUDE.md Phase 1 requirement)

## Success Criteria

✅ Agent generates 3 campaign concepts per invocation (up to 3)  
✅ Each concept includes all required fields from CampaignConcept schema  
✅ Concepts are filtered for legal/regulatory/sensitivity risks (regenerated or skipped)  
✅ Concepts respect hard constraints (budget, timeline, geography, audience)  
✅ Soft constraints flagged but not enforced  
✅ Schema validation strict (errors logged if fields missing)  
✅ Regeneration log auditable (shows what was regenerated and why)  
✅ Test coverage >80%  
✅ No lint/type errors  
✅ Latency <2s per campaign (~6s total for 3 campaigns)

## Next Steps

1. Write implementation plan (TASK-006 plan)
2. Implement agent module + validators + risk filter
3. Write unit + integration tests
4. Verify schema compliance + error handling
5. Commit + PR review
