# AGT-06: Creative Director Agent — Design Specification

**Date:** 2026-05-09  
**Status:** Design Approved  
**Owner:** Creative Director Agent (AGT-06)

---

## 1. Overview

### Purpose
AGT-06 (Creative Director Agent) is an AI-powered agent that generates platform-specific marketing campaign creatives (ad copy, image prompts, video concepts, voiceover scripts, captions) using Claude API. It consumes outputs from upstream agents (Strategy, Media Planner, Budget Optimizer, Mandate Analyst, Competitive Intel), applies brand guidelines and platform constraints, and produces validated, version-tracked creative briefs ready for production or human review.

### Success Criteria
- Generates on-brand, platform-optimized creatives for all specified channels
- Validates output against brand guidelines and platform constraints before returning
- Auto-refines invalid creatives up to 2 attempts before escalating
- Stores complete version history for audit trail and A/B analysis
- Handles API failures gracefully with exponential backoff retry
- Maintains <5s latency for typical generation request (not including API wait time)

---

## 2. Inputs

AGT-06 receives inputs from multiple sources:

| Input | Source | Description |
|-------|--------|-------------|
| **Campaign Objectives** | Strategy/Media Planning agents | Goals, KPIs, success metrics |
| **Target Audience** | Media Planner (AGT-04) | Demographics, psychographics, segments |
| **Competitor Insights** | Competitive Intel (AGT-02) | Market trends, competitor messaging, positioning gaps |
| **Brand Guidelines** | Campaign Configuration Module | Tone, colors, messaging rules, visual identity, mandatory CTAs |
| **Budget Allocation** | Budget Optimizer (AGT-05) | Channel spend, timeline, phase allocation |
| **Platform Targets** | Campaign Configuration | Instagram, LinkedIn, YouTube, Meta Ads, TikTok, Twitter, etc. |
| **Product/Service Details** | Campaign Configuration | Description, key features, benefits, USPs |
| **Campaign Theme** | Mandate Analyst (AGT-01) / User Input | Core message, storytelling angle, campaign name |
| **Call-to-Action (CTA)** | Campaign Configuration | Primary action (Learn More, Shop Now, Sign Up, etc.) |
| **Optional Assets** | User Upload | Logos, product images, reference materials, brand templates |

---

## 3. Outputs

### Output Schema
Creatives organized by platform, with all creative types co-located:

```json
{
  "campaign_id": "string (UUID)",
  "generated_at": "ISO 8601 timestamp",
  "tenant_id": "string (required, from input)",
  "platforms": {
    "instagram": {
      "copy": [
        {
          "type": "post_caption",
          "content": "string",
          "character_count": "integer",
          "validation": {"status": "passed", "warnings": []}
        }
      ],
      "image_prompts": [
        {
          "prompt": "string (detailed DALL-E style prompt)",
          "style": "string",
          "validation": {"status": "passed", "warnings": []}
        }
      ],
      "video_concepts": [
        {
          "title": "string",
          "shot_list": ["string"],
          "duration_seconds": "integer",
          "pacing_notes": "string",
          "validation": {"status": "passed", "warnings": []}
        }
      ],
      "captions": [
        {
          "content": "string",
          "character_count": "integer",
          "tone": "string",
          "validation": {"status": "passed", "warnings": []}
        }
      ]
    },
    "linkedin": { /* similar structure */ },
    "youtube": { /* similar structure */ },
    "meta_ads": { /* similar structure */ },
    "tiktok": { /* similar structure */ }
  },
  "metadata": {
    "core_concept": {
      "message": "string",
      "visual_direction": "string",
      "audio_direction": "string",
      "tone": "string"
    },
    "validation_status": "passed|failed|partial",
    "validation_summary": "string",
    "refinement_attempts": "integer (0-2)",
    "generation_time_ms": "integer",
    "model_used": "claude-opus-4.7 (or current version)"
  },
  "error": null
}
```

### Creative Types per Platform

| Platform | Copy | Images | Video | Voiceover | Captions | Notes |
|----------|------|--------|-------|-----------|----------|-------|
| **Instagram** | Post captions | Reels, story frames | Reel concepts | Optional (via captions) | Post/reel captions | Short-form, visual-first |
| **LinkedIn** | Article/post copy | Featured image prompts | Video concepts | Optional (via captions) | Post captions | Professional tone, B2B focus |
| **YouTube** | Video titles, descriptions | Thumbnail prompts | Full video concepts | Voiceover scripts | Video descriptions | Long-form, storytelling |
| **Meta Ads** | Ad copy variants | Ad image prompts | Video ad concepts | Voiceover scripts (if video) | Ad headlines/descriptions | Conversion-focused |
| **TikTok** | Hook/CTA lines | Trend-based prompts | Challenge concepts | Voiceover scripts | Hashtag/sound recs | Trending, authentic tone |

---

## 4. Architecture

### Component Design

#### 4.1 Input Aggregator
- **Responsibility:** Consolidate inputs from upstream agents and campaign config modules
- **Inputs:** Campaign strategy, brand guidelines, competitor insights, platform list, uploads
- **Outputs:** Normalized input object with validation
- **Constraints:** 
  - All inputs must include `tenant_id`
  - Brand guidelines required (tone, colors, messaging rules)
  - At least one platform target required
- **Error Handling:** Missing required fields → return detailed validation error before generation

#### 4.2 Creative Brief Generator
- **Responsibility:** Generate platform-specific creative briefs using Claude API
- **Algorithm:**
  1. **Stage 1 (Core Concept):** Single Claude call generates unified brand message, visual direction, tone, core narrative
  2. **Stage 2 (Platform Branching):** For each target platform, Claude generates platform-specific creatives (copy, image prompts, video concepts, voiceovers, captions) optimized for:
     - Platform format/length constraints (Instagram 150 chars caption, LinkedIn 3000 chars, etc.)
     - Platform culture (Instagram = visual, LinkedIn = professional, TikTok = trending)
     - Audience expectations (B2B vs. B2C tone shifts)
  3. **Inputs to Claude:**
     - Core campaign narrative (from Stage 1)
     - Brand guidelines (tone, colors, mandatory CTAs, voice)
     - Platform specs (character limits, format requirements, audience)
     - Target audience (demographics, psychographics)
     - Product/service details
     - Competitor positioning (what NOT to copy)
  4. **Output:** JSON struct with all creative types per platform

- **Implementation Detail:** Use prompt templates with placeholders for dynamic inputs; maintain version-controlled templates for consistency

#### 4.3 Validation Engine
- **Responsibility:** Validate generated creatives against constraints
- **Validation Rules:**
  - **Brand Compliance:** 
    - Tone matches brand voice (check for brand keyword alignment, sentiment)
    - Colors mentioned align with brand palette (if applicable)
    - Mandatory CTAs present and phrased correctly
  - **Platform Constraints:**
    - Copy under platform character limits (Instagram ≤150 for caption, LinkedIn ≤3000, etc.)
    - Required fields filled (image prompts not empty, video duration reasonable, etc.)
    - Format compliance (hashtags for Instagram/TikTok, no emojis if brand restricts, etc.)
  - **Campaign Alignment:**
    - KPIs mentioned (if campaign specifies measurable goals)
    - Target audience language matches brief
    - CTAs align with campaign objective (lead gen, sales, awareness, etc.)

- **Output:** Validation report per creative
  ```json
  {
    "status": "passed|failed",
    "violations": [
      {
        "rule": "string",
        "severity": "error|warning",
        "creative_id": "string",
        "suggestion": "string"
      }
    ]
  }
  ```

#### 4.4 Refinement Loop
- **Responsibility:** Auto-refine invalid creatives
- **Algorithm:**
  1. If validation fails, surface violations to Claude with refinement prompt
  2. Claude generates corrected version (or admits if constraint impossible to meet)
  3. Re-validate corrected creative
  4. **Max attempts:** 2 refinement loops (3 generations total: initial + 2 refinements)
  5. **Escalation:** If still invalid after 2 attempts, include violation details in metadata and return as-is with warning

- **Refinement Prompt Template:**
  ```
  The following creative did not pass validation:
  [Original creative]
  
  Violations:
  [Validation report]
  
  Please regenerate the creative to fix these violations while maintaining the core message and brand voice.
  ```

#### 4.5 Data Layer
- **Storage:** PostgreSQL table `generated_creatives` with schema:
  ```sql
  CREATE TABLE generated_creatives (
    id UUID PRIMARY KEY,
    campaign_id UUID NOT NULL REFERENCES campaigns(id),
    tenant_id UUID NOT NULL,
    generation_id UUID NOT NULL (groups all platforms from one request),
    platform VARCHAR(50) NOT NULL,
    creative_type VARCHAR(50) NOT NULL (copy, image_prompt, video_concept, voiceover_script, caption),
    content JSONB NOT NULL (full creative object),
    validation_status VARCHAR(20),
    refinement_attempts INT,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(campaign_id, generation_id, platform, creative_type)
  );
  ```
- **Versioning:** generation_id groups all creatives from one request; multiple generation_ids per campaign_id creates version history
- **Querying:** Always filter by `tenant_id` to ensure multi-tenant isolation

#### 4.6 Error Handler
- **Responsibility:** Graceful handling of external API failures (Claude API, rate limits)
- **Strategy:** Exponential backoff retry
  - **Max Retries:** 3
  - **Backoff:** 2^n seconds (2s, 4s, 8s)
  - **Total Max Wait:** ~14 seconds before failure
  - **Logging:** Log retry attempts with timestamps and error details
- **Failure Response:**
  ```json
  {
    "error": {
      "type": "api_failure",
      "message": "Claude API unavailable after 3 retries",
      "retry_count": 3,
      "last_error": "rate_limit_exceeded",
      "suggestion": "Retry in 30 seconds"
    }
  }
  ```

---

## 5. Data Flow

```
┌─────────────────────────────────────────────────────────┐
│  Upstream Inputs                                        │
│  - Campaign strategy (Media Planner)                    │
│  - Brand guidelines (Config)                            │
│  - Budget allocation (Budget Optimizer)                 │
│  - Competitor insights (Competitive Intel)              │
│  - Platform targets, product details, theme, CTA        │
└────────────────────────┬────────────────────────────────┘
                         │
                         ▼
                  ┌──────────────┐
                  │ Input        │
                  │ Aggregator   │
                  └──────┬───────┘
                         │
                         ▼
         ┌───────────────────────────────┐
         │ Creative Brief Generator      │
         │ Stage 1: Core Concept (Claude)│
         │ Stage 2: Platform Branches    │
         │         (Claude per platform) │
         └───────────────┬───────────────┘
                         │
                         ▼
              ┌──────────────────────┐
              │ Validation Engine    │
              │ - Brand compliance   │
              │ - Platform constraints
              │ - Campaign alignment │
              └──────┬───────────────┘
                     │
           ┌─────────┴──────────┐
           │                    │
      [Valid]            [Invalid]
           │                    │
           ▼                    ▼
        [Output]    ┌──────────────────┐
                    │ Refinement Loop  │
                    │ (Max 2 attempts) │
                    └────────┬─────────┘
                             │
                    ┌────────┴────────┐
                    │                 │
               [Valid]           [Still Invalid]
                    │                 │
                    └────────┬────────┘
                             │
                             ▼
                  ┌──────────────────────┐
                  │ Data Layer           │
                  │ Store with version   │
                  │ history & audit      │
                  └──────────┬───────────┘
                             │
                             ▼
                      ┌─────────────┐
                      │ Return to   │
                      │ User/Client │
                      └─────────────┘
```

---

## 6. Integration Points

### Upstream Dependencies
- **Media Planner (AGT-04):** Provides campaign objectives, target audience, platform allocation
- **Budget Optimizer (AGT-05):** Provides channel spend and timeline for context (e.g., "Instagram gets 40% budget, emphasize this platform")
- **Competitive Intel (AGT-02):** Provides market insights and competitor positioning
- **Mandate Analyst (AGT-01):** Provides campaign mandate, constraints, compliance rules
- **Campaign Config Module:** Provides brand guidelines, platform list, CTA, product details

### Downstream Dependents
- **Campaign Execution Engine:** Receives creatives, routes to platform-specific campaign builders
- **Content Calendar:** Pulls creatives to populate publishing schedule
- **A/B Testing Framework:** Uses version history to compare creative performance
- **Analytics Dashboard:** Tracks which creatives perform best by platform

### API Dependencies
- **Claude API (Anthropic):** Primary generative AI for copy, concepts, scripts
- **PostgreSQL 16:** Persistent storage with pgvector (reserved for future embedding-based search)
- **Tenant-ID validation:** Must verify tenant_id against user's organization before generation

---

## 7. Error Handling & Edge Cases

| Scenario | Handling |
|----------|----------|
| Missing brand guidelines | Return validation error; require guidelines before generation |
| No platform targets specified | Return validation error; at least one platform required |
| Claude API rate-limited | Retry with exponential backoff (3 attempts, 2-4-8s) |
| Claude API down (persistent) | Return error response after 3 retries; suggest retry later |
| Validation fails after 2 refinements | Return creatives with violation warnings; mark as "partial" validation status |
| Invalid tenant_id | Reject request; log security event |
| Oversized input (>10MB assets) | Reject; return size limit error |
| Platform target not recognized | Warn; skip unknown platform, continue with valid ones |

---

## 8. Testing Strategy

### Unit Tests
- **Input Aggregator:** Valid/invalid inputs, missing required fields, tenant_id validation
- **Validation Engine:** Brand compliance rules, platform constraints, campaign alignment
- **Refinement Loop:** Max attempts enforcement, violation fixing, escalation logic
- **Error Handler:** Retry logic, backoff calculation, persistent failure handling

### Integration Tests
- **End-to-end:** Campaign config → creative generation → validation → storage → retrieval
- **Multi-platform:** Single request generates creatives for all platforms simultaneously
- **Version history:** Multiple generations tracked correctly with generation_id
- **Data consistency:** Tenant isolation enforced; no cross-tenant leakage

### Performance Tests
- **Latency:** Generation completes within SLA (excluding Claude API wait time)
- **Concurrent requests:** Multiple simultaneous generation requests don't block each other
- **Storage:** Creatives stored and retrieved efficiently; version history queries fast

### Mock/Fixtures
- Mock Claude API responses (cached fixture responses for fast tests)
- Fixture campaign data (complete input sets for end-to-end tests)
- Fixture brand guidelines and platform configs

---

## 9. Future Enhancements (Out of Scope - Phase 2)

- **Actual Media Generation:** Integrate DALL-E for image generation, Eleven Labs for voiceovers, Synthesia for video
- **Embedding-Based Search:** Use pgvector to find similar creatives across past campaigns
- **A/B Testing:** Automated variant generation and performance tracking
- **Multi-language Support:** Generate creatives in non-English languages
- **Real-time Feedback:** User feedback loop to retrain/improve generation patterns
- **Brand Asset Sync:** Automatic logo/color extraction from uploaded brand assets

---

## 10. Success Metrics

- **Quality:** 90%+ of generated creatives pass validation on first attempt
- **Performance:** <5s generation time (excluding Claude API latency) for typical request
- **Reliability:** 99%+ uptime; API failures handled gracefully with <1% generation loss
- **Coverage:** Creatives generated for all target platforms simultaneously
- **Auditability:** 100% of creatives versioned, traceable to source inputs
- **User Satisfaction:** Creatives require <2 refinement rounds on average; minimal human rework needed

---

## Appendix: Platform-Specific Constraints

| Platform | Max Caption Length | Video Format | Optimal Image Ratio | Key Tone | CTA Style |
|----------|-------------------|---------------|---------------------|----------|-----------|
| **Instagram** | 150–2,200 chars | 15–60s reel | 1:1 square | Casual, authentic | Swipe-up, link-in-bio |
| **LinkedIn** | 3,000 chars | 1–10 min article | 1.91:1 landscape | Professional, thought-leading | LinkedIn article, document |
| **YouTube** | 5,000 chars (description) | 10s–10 min | 16:9 landscape | Storytelling, value-driven | Subscribe, watch full |
| **Meta Ads** | 125 chars (primary) | 15s–30s | 1:1, 4:5, 9:16 | Direct, benefit-focused | Learn More, Shop Now, Sign Up |
| **TikTok** | 150 chars | 15s–10 min | 9:16 vertical | Trendy, authentic, humorous | Trending sound, hashtag challenge |

