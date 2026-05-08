# ==============================================================================
# ntm-sessions.ps1
# NTM — Nexus Tensor Meridian session launcher.
# Based on sessions-template.ps1 — pre-filled for all NTM phases and modules.
# Owner: Srinivas / SherpaVector
# Usage: .\scripts\ntm-sessions.ps1 -Session <name>
#        .\scripts\ntm-sessions.ps1 -Session list
# Jai Jagannath
# ==============================================================================

param(
    [Parameter(Mandatory=$true)]
    [ValidateSet(
        "list",
        # Phase 0
        "core","models","schemas",
        # Phase 1
        "agt-01-mandate","agt-02-ci","agt-03-strategist",
        # Phase 2
        "routers-mandate","routers-campaign",
        "agt-04-planner","agt-05-budget",
        # Phase 3
        "agt-06-creative-dir","agt-07-copywriter","agt-08-scriptwriter",
        "agt-09-image","agt-10-audio","agt-11-video",
        # Phase 4
        "agt-12-digital","tools-google","tools-meta","tools-linkedin",
        "agt-13-analytics","agt-14-replan","agt-15-report",
        # Frontend
        "fe-mandate","fe-campaign","fe-creative","fe-analytics","fe-kpi","fe-admin",
        # Evals
        "evals",
        # Debug
        "debug"
    )]
    [string]$Session
)

$PROJECT_ROOT = "D:\staging\ntm"
$HAIKU        = "claude-haiku-4-5-20251001"
$SONNET       = "claude-sonnet-4-6"

$STACK_BACKEND  = "Python 3.12, FastAPI, SQLAlchemy async, PostgreSQL 16 (pgvector), MongoDB 7, Redis 7, LangGraph, CrewAI, Celery, Anthropic SDK"
$STACK_FRONTEND = "React 18, TypeScript, Tailwind CSS, shadcn/ui, Zustand, React Query, Recharts"
$COAUTHOR       = "Co-authored-by: katharguppe <katharguppe@users.noreply.github.com>"

$sessions = @{

    # ════════════════════════════════════════════════════════════════════════
    # PHASE 0 — Scaffold + Auth + DB
    # ════════════════════════════════════════════════════════════════════════

    core = @{
        model = $HAIKU
        task  = "TASK-001"
        label = "Phase 0 · Core — Config, Auth, Middleware"
        prompt = @"
Stack: $STACK_BACKEND
Task file: tasks/TASK-001-core.md
Module scope: backend/app/core/ ONLY.

Key facts:
- Pydantic Settings class reads from .env
- FastAPI-Users for JWT auth (access + refresh tokens)
- RBAC roles: platform_admin, tenant_admin, brand_manager, cmo, creative_lead, campaign_manager, viewer
- All routes must enforce tenant_id from JWT claims
- No route should ever return data from another tenant

Context7: use for FastAPI, SQLAlchemy, fastapi-users docs.
PDCA: present plan before touching any file.
Co-author every commit: $COAUTHOR
"@
    }

    models = @{
        model = $HAIKU
        task  = "TASK-002"
        label = "Phase 0 · Models — SQLAlchemy DB Models"
        prompt = @"
Stack: $STACK_BACKEND
Task file: tasks/TASK-002-models.md
Module scope: backend/app/models/ ONLY.

Key entities to model:
Tenant, User, Client, Mandate, CIReport, CampaignConcept,
Activation, Budget, Creative, PerformanceMetric,
PhysicalActivationLog, KPI, ApprovalLog

Critical rules:
- Every model except Tenant MUST have tenant_id: Mapped[UUID] (FK to tenants.id)
- Use SQLAlchemy 2.0 async style (Mapped[], mapped_column())
- Use pgvector Column for brand_embedding fields (Client, CampaignConcept)
- Timestamps: created_at, updated_at on all models (auto via server_default)

Context7: use for SQLAlchemy 2.0, pgvector docs.
PDCA: present plan before touching any file.
Co-author every commit: $COAUTHOR
"@
    }

    schemas = @{
        model = $HAIKU
        task  = "TASK-003"
        label = "Phase 0 · Schemas — Pydantic Request/Response"
        prompt = @"
Stack: $STACK_BACKEND
Task file: tasks/TASK-003-schemas.md
Module scope: backend/app/schemas/ ONLY.

One schema file per domain: mandate.py, campaign.py, activation.py,
creative.py, analytics.py, budget.py, user.py, tenant.py

Each file needs: CreateSchema, UpdateSchema, ResponseSchema, ListResponseSchema
Use Pydantic v2 style (model_config, field validators).

Context7: use for Pydantic v2 docs.
PDCA: present plan before touching any file.
Co-author every commit: $COAUTHOR
"@
    }

    # ════════════════════════════════════════════════════════════════════════
    # PHASE 1 — Mandate to Concept (Agents 01-03)
    # ════════════════════════════════════════════════════════════════════════

    "agt-01-mandate" = @{
        model = $SONNET
        task  = "TASK-004"
        label = "Phase 1 · AGT-01 — Mandate Analyst Agent"
        prompt = @"
Stack: $STACK_BACKEND
Task file: tasks/TASK-004-agt01-mandate-analyst.md
Module scope: backend/app/agents/mandate_analyst.py ONLY.

Agent responsibility:
- Parse and validate incoming mandate dict
- Check completeness (required fields list in CLAUDE.md)
- Generate structured Mandate Summary Card (JSON)
- Return completeness_score 0-100 and list of missing_fields
- Flag contradictions (e.g. budget too low for stated objective)

LLM: claude-sonnet-4-20250514, max_tokens=2000
Output must be pure JSON — system prompt must say 'respond only with JSON, no markdown'
Write one happy-path test in backend/tests/agents/test_mandate_analyst.py

Context7: use for Anthropic SDK async docs.
PDCA: present plan before touching any file.
Co-author every commit: $COAUTHOR
"@
    }

    "agt-02-ci" = @{
        model = $SONNET
        task  = "TASK-005"
        label = "Phase 1 · AGT-02 — Competitive Intelligence Agent"
        prompt = @"
Stack: $STACK_BACKEND
Task file: tasks/TASK-005-agt02-competitive-intel.md
Module scope: backend/app/agents/competitive_intel.py + backend/app/tools/serpapi.py ONLY.

Agent responsibility:
- Identify top 5-10 competitors from mandate + client profile
- Use SerpAPI to search: '[competitor] advertising campaign [year]'
- Use Meta Ad Library public endpoint for competitor ad intel
- Analyse channel presence, messaging themes, geographic coverage
- Identify whitespace: channels + messages not owned by competitors
- Output: structured CIReport JSON

LLM: claude-sonnet-4-20250514 for analysis synthesis
Tool: SerpAPI (backend/app/tools/serpapi.py) — build this tool file first
Store results in MongoDB (ntm.ci_reports collection)

Context7: use for Anthropic SDK, motor (MongoDB async) docs.
PDCA: present plan before touching any file.
Co-author every commit: $COAUTHOR
"@
    }

    "agt-03-strategist" = @{
        model = $SONNET
        task  = "TASK-006"
        label = "Phase 1 · AGT-03 — Campaign Strategist Agent"
        prompt = @"
Stack: $STACK_BACKEND
Task file: tasks/TASK-006-agt03-campaign-strategist.md
Module scope: backend/app/agents/campaign_strategist.py ONLY.

Agent responsibility:
- Inputs: Mandate Summary Card + CIReport
- Generate 3 campaign name + tagline options
- Define: campaign theme, strategic narrative, audience segmentation (primary/secondary/tertiary)
- Produce: channel mix recommendation with rationale vs competitor gaps
- Produce: message architecture (master message + channel adaptations)
- Produce: campaign phasing (Awareness → Engagement → Conversion)
- Produce: tone board (5 adjectives), visual direction description
- Flag: legal/regulatory/sensitivity risks
- Output: structured CampaignConcept JSON

LLM: claude-sonnet-4-20250514, max_tokens=4000
Validation: cross-check output keys match CampaignConcept schema

Context7: use for Anthropic SDK docs.
PDCA: present plan before touching any file.
Co-author every commit: $COAUTHOR
"@
    }

    # ════════════════════════════════════════════════════════════════════════
    # PHASE 2 — Activation Planning + Budget
    # ════════════════════════════════════════════════════════════════════════

    "routers-mandate" = @{
        model = $HAIKU
        task  = "TASK-007"
        label = "Phase 2 · Routers — Mandate API endpoints"
        prompt = @"
Stack: $STACK_BACKEND
Task file: tasks/TASK-007-routers-mandate.md
Module scope: backend/app/routers/mandate.py + backend/app/services/mandate_service.py ONLY.

Endpoints to build:
POST   /api/v1/mandates                     Create mandate → trigger AGT-01 as Celery task
GET    /api/v1/mandates/{id}                Get mandate (tenant-scoped)
PUT    /api/v1/mandates/{id}                Update mandate (before AG-1 only)
POST   /api/v1/mandates/{id}/confirm        AG-1: client confirms summary card
GET    /api/v1/mandates/{id}/summary-card   Get AGT-01 output

Auth: JWT required on all routes. tenant_id from token claims.
Every DB query must include tenant_id filter — MANDATORY.

Context7: use for FastAPI, SQLAlchemy async docs.
PDCA: present plan before touching any file.
Co-author every commit: $COAUTHOR
"@
    }

    "agt-04-planner" = @{
        model = $SONNET
        task  = "TASK-008"
        label = "Phase 2 · AGT-04 — Media Planner Agent"
        prompt = @"
Stack: $STACK_BACKEND
Task file: tasks/TASK-008-agt04-media-planner.md
Module scope: backend/app/agents/media_planner.py ONLY.

Agent responsibility:
- Input: approved CampaignConcept + budget envelope + mandate geography
- Generate full Activation Master Plan — one record per activation
- Each activation must have: channel_enum, sub_channel, format, geography, placement,
  scheduled_date, duration, frequency, estimated_reach, cost_estimated, message_version_ref
- Channel taxonomy: full Online (Social/Search/Display/Email/WhatsApp/Influencer) +
  Offline (Print/OOH/Radio/TV/Events/Cinema/Direct Mail) — see PRD Section 6.4.2
- Apply budget allocation logic: objective-driven, phase-weighted, competitor-gap-aware
- Reserve 10% contingency always
- Output: list of Activation JSON objects + BudgetSummary JSON

LLM: claude-sonnet-4-20250514, max_tokens=6000
Context7: use for Anthropic SDK docs.
PDCA: present plan before touching any file.
Co-author every commit: $COAUTHOR
"@
    }

    "agt-05-budget" = @{
        model = $SONNET
        task  = "TASK-009"
        label = "Phase 2 · AGT-05 — Budget Optimiser Agent"
        prompt = @"
Stack: $STACK_BACKEND
Task file: tasks/TASK-009-agt05-budget-optimiser.md
Module scope: backend/app/agents/budget_optimiser.py ONLY.

Agent responsibility:
- Input: Activation Master Plan from AGT-04 + budget envelope
- Validate total estimated cost vs budget envelope (must not exceed max)
- If over budget: identify lowest-ROI activations and trim/scale
- Output: final BudgetBreakdown JSON with: total_approved, online_budget,
  offline_budget, contingency, per_channel_breakdown, per_phase_breakdown
- Also produce: Budget Change Order (CO) template for future amendments
- Trigger: email notification to approval_authority on budget ready

LLM: claude-sonnet-4-20250514
Context7: use for Anthropic SDK docs.
PDCA: present plan before touching any file.
Co-author every commit: $COAUTHOR
"@
    }

    # ════════════════════════════════════════════════════════════════════════
    # PHASE 3 — Creative Studio (Agents 06-11)
    # ════════════════════════════════════════════════════════════════════════

    "agt-06-creative-dir" = @{
        model = $SONNET
        task  = "TASK-010"
        label = "Phase 3 · AGT-06 — Creative Director Agent"
        prompt = @"
Stack: $STACK_BACKEND
Task file: tasks/TASK-010-agt06-creative-director.md
Module scope: backend/app/agents/creative_director.py ONLY.

Agent responsibility:
- Input: one Activation record + CampaignConcept + client brand guidelines
- Generate a per-asset Creative Brief JSON specifying:
  asset_type, format_specs, message_variant, tone, visual_direction,
  copy_brief, reference_images_description, production_notes
- Route brief to correct downstream agent: copywriter / scriptwriter / image / audio / video
- For assets requiring actual shoot/recording: flag production_brief_required=True
  and generate full Production Brief (actors type, locations, wardrobe, music direction)

LLM: claude-sonnet-4-20250514, max_tokens=3000
Context7: use for Anthropic SDK docs.
PDCA: present plan before touching any file.
Co-author every commit: $COAUTHOR
"@
    }

    "agt-07-copywriter" = @{
        model = $SONNET
        task  = "TASK-011"
        label = "Phase 3 · AGT-07 — Copywriter Agent"
        prompt = @"
Stack: $STACK_BACKEND
Task file: tasks/TASK-011-agt07-copywriter.md
Module scope: backend/app/agents/copywriter.py ONLY.

Agent responsibility:
- Input: Creative Brief from AGT-06
- Generate copy for: social media captions, headlines, body copy,
  print ad copy (headline + subhead + body + CTA), email subject + body,
  OOH billboard (ultra-concise, max 7 words headline), influencer brief
- Produce 2 variants per asset for A/B consideration
- Respect tone board and brand voice from CampaignConcept
- Output: CopyOutput JSON with variants array

LLM: claude-sonnet-4-20250514, temperature=0.8 for creative variance
Context7: use for Anthropic SDK docs.
PDCA: present plan before touching any file.
Co-author every commit: $COAUTHOR
"@
    }

    "agt-08-scriptwriter" = @{
        model = $SONNET
        task  = "TASK-012"
        label = "Phase 3 · AGT-08 — Scriptwriter Agent (TVC/Radio/Video)"
        prompt = @"
Stack: $STACK_BACKEND
Task file: tasks/TASK-012-agt08-scriptwriter.md
Module scope: backend/app/agents/scriptwriter.py ONLY.

Agent responsibility:
- Input: Creative Brief from AGT-06 specifying script format (TVC/radio/social video)
- TVC script: full scene-by-scene (scene description, dialogue, VO, SFX, duration)
- Radio script: line-by-line (VO text, SFX cues, music direction, timing marks)
- Social video: platform-specific format (hook, content, CTA, on-screen text)
- For all scripts: include Director's Note, talent type suggestions,
  location type suggestions, wardrobe notes, music/score direction, estimated duration
- Output: ScriptOutput JSON + Production Brief markdown text

LLM: claude-sonnet-4-20250514, max_tokens=4000
Context7: use for Anthropic SDK docs.
PDCA: present plan before touching any file.
Co-author every commit: $COAUTHOR
"@
    }

    "agt-09-image" = @{
        model = $HAIKU
        task  = "TASK-013"
        label = "Phase 3 · AGT-09 — Image Generator Agent"
        prompt = @"
Stack: $STACK_BACKEND + Stability AI API / DALL-E 3 API
Task file: tasks/TASK-013-agt09-image-generator.md
Module scope: backend/app/agents/image_generator.py + backend/app/tools/stability_ai.py ONLY.

Agent responsibility:
- Input: Creative Brief from AGT-06 (visual_direction field)
- Construct optimised text-to-image prompt from visual_direction + brand palette + tone
- Call Stability AI SDXL via backend/app/tools/stability_ai.py (build tool first)
- Fallback: DALL-E 3 if Stability fails
- Upload generated image to S3/MinIO, store URL in Creative record
- Return: asset_url, prompt_used, model_used, generation_params

Build stability_ai.py tool with: generate_image(prompt, width, height, steps) → bytes
Use STABILITY_AI_API_KEY from settings.

Context7: use for Stability AI, boto3 S3 docs.
PDCA: present plan before touching any file.
Co-author every commit: $COAUTHOR
"@
    }

    "agt-10-audio" = @{
        model = $HAIKU
        task  = "TASK-014"
        label = "Phase 3 · AGT-10 — Audio Generator Agent (ElevenLabs)"
        prompt = @"
Stack: $STACK_BACKEND + ElevenLabs API
Task file: tasks/TASK-014-agt10-audio-generator.md
Module scope: backend/app/agents/audio_generator.py + backend/app/tools/elevenlabs.py ONLY.

Agent responsibility:
- Input: radio/VO script from AGT-08
- Select appropriate ElevenLabs voice (warm/authoritative/youthful based on tone board)
- Call ElevenLabs text-to-speech API via backend/app/tools/elevenlabs.py
- Upload MP3 to S3/MinIO, store URL in Creative record
- Return: asset_url, voice_id, duration_seconds

Build elevenlabs.py tool with: generate_vo(script, voice_id, model) → bytes
Use ELEVENLABS_API_KEY from settings.

Context7: use for ElevenLabs Python SDK, boto3 docs.
PDCA: present plan before touching any file.
Co-author every commit: $COAUTHOR
"@
    }

    "agt-11-video" = @{
        model = $HAIKU
        task  = "TASK-015"
        label = "Phase 3 · AGT-11 — Video Generator Agent (Runway)"
        prompt = @"
Stack: $STACK_BACKEND + Runway ML API
Task file: tasks/TASK-015-agt11-video-generator.md
Module scope: backend/app/agents/video_generator.py + backend/app/tools/runway.py ONLY.

Agent responsibility:
- Input: social video script from AGT-08 + reference image from AGT-09 (optional)
- Call Runway ML Gen-3 API via backend/app/tools/runway.py
- Poll for completion (async with Celery task + retry logic)
- Upload MP4 to S3/MinIO, store URL in Creative record
- Return: asset_url, duration_seconds, model_used

Build runway.py tool with: generate_video(prompt, image_url, duration) → str (job_id)
                            get_video_status(job_id) → dict
Use RUNWAY_API_KEY from settings.
Failure mode: if Runway unavailable, set status=manual_production_required

Context7: use for Runway Python SDK, boto3 docs.
PDCA: present plan before touching any file.
Co-author every commit: $COAUTHOR
"@
    }

    # ════════════════════════════════════════════════════════════════════════
    # PHASE 4 — Digital Activation + Analytics
    # ════════════════════════════════════════════════════════════════════════

    "tools-google" = @{
        model = $SONNET
        task  = "TASK-016"
        label = "Phase 4 · Tools — Google Ads API integration"
        prompt = @"
Stack: $STACK_BACKEND + google-ads Python SDK
Task file: tasks/TASK-016-tools-google-ads.md
Module scope: backend/app/tools/google_ads.py ONLY.

Functions to build:
- create_campaign(client_id, name, budget, start_date, end_date) → campaign_id
- create_ad_group(campaign_id, name, targeting_params) → ad_group_id
- create_display_ad(ad_group_id, headline, description, image_url) → ad_id
- create_responsive_search_ad(ad_group_id, headlines, descriptions, keywords) → ad_id
- pause_campaign(campaign_id) → bool
- get_campaign_metrics(campaign_id, date_range) → MetricsDict
- set_campaign_budget(campaign_id, daily_budget) → bool

Use GOOGLE_ADS_DEVELOPER_TOKEN, CLIENT_ID, CLIENT_SECRET, REFRESH_TOKEN from settings.
Each function returns structured dict with success:bool + data/error.

Context7: use for google-ads Python SDK v24 docs.
PDCA: present plan before touching any file.
Co-author every commit: $COAUTHOR
"@
    }

    "tools-meta" = @{
        model = $SONNET
        task  = "TASK-017"
        label = "Phase 4 · Tools — Meta Marketing API integration"
        prompt = @"
Stack: $STACK_BACKEND + Meta Marketing API (via httpx)
Task file: tasks/TASK-017-tools-meta-ads.md
Module scope: backend/app/tools/meta_ads.py ONLY.

Functions to build:
- create_campaign(ad_account_id, name, objective, budget, schedule) → campaign_id
- create_ad_set(campaign_id, name, audience_spec, placements, budget) → ad_set_id
- create_ad(ad_set_id, creative_spec, name) → ad_id
- get_ad_insights(ad_id, date_range, metrics_list) → InsightsDict
- pause_ad(ad_id) → bool
- update_ad_budget(ad_set_id, daily_budget) → bool

Use META_APP_ID, META_APP_SECRET, META_SYSTEM_USER_TOKEN from settings.
API version: v21.0. Base URL: https://graph.facebook.com/v21.0/

Context7: use for Meta Marketing API docs.
PDCA: present plan before touching any file.
Co-author every commit: $COAUTHOR
"@
    }

    "tools-linkedin" = @{
        model = $SONNET
        task  = "TASK-018"
        label = "Phase 4 · Tools — LinkedIn Campaign Manager API"
        prompt = @"
Stack: $STACK_BACKEND + LinkedIn Marketing API (via httpx)
Task file: tasks/TASK-018-tools-linkedin.md
Module scope: backend/app/tools/linkedin_ads.py ONLY.

Functions to build:
- create_campaign_group(account_id, name, status) → group_id
- create_campaign(group_id, name, type, targeting, budget) → campaign_id
- create_sponsored_content(campaign_id, content_reference, variables) → creative_id
- get_campaign_analytics(campaign_id, date_range) → AnalyticsDict
- pause_campaign(campaign_id) → bool

Use LINKEDIN_CLIENT_ID, LINKEDIN_CLIENT_SECRET from settings.
API base: https://api.linkedin.com/v2/

Context7: use for LinkedIn Marketing API docs.
PDCA: present plan before touching any file.
Co-author every commit: $COAUTHOR
"@
    }

    "agt-12-digital" = @{
        model = $HAIKU
        task  = "TASK-019"
        label = "Phase 4 · AGT-12 — Digital Activator Agent"
        prompt = @"
Stack: $STACK_BACKEND
Task file: tasks/TASK-019-agt12-digital-activator.md
Module scope: backend/app/agents/digital_activator.py ONLY.

Agent responsibility:
- Input: approved Activation record with channel_enum + creative asset URL
- Route to correct tool based on channel:
    Google Ads → tools/google_ads.py
    Facebook/Instagram → tools/meta_ads.py
    LinkedIn → tools/linkedin_ads.py
- Set budget, targeting, schedule, creative from Activation record
- Store platform_campaign_id + platform_ad_id in Activation record
- Update Activation.status → 'live'
- Trigger confirmation notification (email + WhatsApp) to campaign manager

Run as Celery task (not blocking API). Retry up to 3x on API failure.
Context7: use for Celery docs.
PDCA: present plan before touching any file.
Co-author every commit: $COAUTHOR
"@
    }

    "agt-13-analytics" = @{
        model = $SONNET
        task  = "TASK-020"
        label = "Phase 4 · AGT-13 — Analytics Agent"
        prompt = @"
Stack: $STACK_BACKEND
Task file: tasks/TASK-020-agt13-analytics.md
Module scope: backend/app/agents/analytics_agent.py ONLY.

Agent responsibility (runs as Celery Beat task every 24h):
- For each Live activation: pull metrics from platform tool (Google/Meta/LinkedIn)
- Store in PerformanceMetric table (one row per activation per day)
- Compute KPI achievement: actual vs target (from KPI table)
- Flag activations in Red (below KPI threshold by >20%) or Amber (10-20% below)
- Generate structured analytics summary dict (used by dashboard API endpoint)
- Trigger alert notification if any KPI goes Red

Output: AnalyticsSummary JSON per mandate
Context7: use for Celery Beat, SQLAlchemy async docs.
PDCA: present plan before touching any file.
Co-author every commit: $COAUTHOR
"@
    }

    "agt-14-replan" = @{
        model = $SONNET
        task  = "TASK-021"
        label = "Phase 4 · AGT-14 — Replanning Agent"
        prompt = @"
Stack: $STACK_BACKEND
Task file: tasks/TASK-021-agt14-replanning.md
Module scope: backend/app/agents/replanning_agent.py ONLY.

Agent responsibility (runs weekly, triggered by Celery Beat):
- Input: AnalyticsSummary from AGT-13 + current ActivationPlan + KPI targets
- Identify top 3 underperforming activations (Red/Amber)
- Identify top 3 overperforming activations (exceeding KPI target)
- Generate specific, actionable ReplanRecommendation records:
  Types: pause | increase_budget | swap_creative | add_activation | adjust_targeting | extend_duration
- Each recommendation must include: rationale, expected_impact, estimated_cost_change
- Output: list of ReplanRecommendation JSON objects — pending AG-6 approval
- Do NOT implement changes — only generate recommendations for human approval

LLM: claude-sonnet-4-20250514
PDCA: present plan before touching any file.
Co-author every commit: $COAUTHOR
"@
    }

    "agt-15-report" = @{
        model = $SONNET
        task  = "TASK-022"
        label = "Phase 4 · AGT-15 — Report Generator Agent"
        prompt = @"
Stack: $STACK_BACKEND + WeasyPrint
Task file: tasks/TASK-022-agt15-report-generator.md
Module scope: backend/app/agents/report_generator.py ONLY.

Agent responsibility:
- Input: mandate_id + report_type (weekly | campaign_end | concept_deck)
- For weekly report: compile AnalyticsSummary → narrative intelligence report
- For campaign_end: full KPI achievement vs target, channel breakdown, learnings, recommendations
- For concept_deck: campaign concept + activation plan + budget summary
- LLM writes the narrative sections
- Render to PDF using WeasyPrint (HTML template → PDF)
- Upload PDF to S3/MinIO, store URL, email to approval_authority

LLM: claude-sonnet-4-20250514, max_tokens=4000
Context7: use for WeasyPrint, boto3 docs.
PDCA: present plan before touching any file.
Co-author every commit: $COAUTHOR
"@
    }

    # ════════════════════════════════════════════════════════════════════════
    # FRONTEND SESSIONS
    # ════════════════════════════════════════════════════════════════════════

    "fe-mandate" = @{
        model = $SONNET
        task  = "TASK-023"
        label = "Frontend · Mandate — Client onboarding + mandate capture UI"
        prompt = @"
Stack: $STACK_FRONTEND
Task file: tasks/TASK-023-fe-mandate.md
Module scope: frontend/src/pages/Onboarding/ + frontend/src/pages/Mandate/ ONLY.

Build:
- Multi-step onboarding form (client profile: org name, industry, logo upload, brand guidelines PDF, competitors)
- Mandate submission form (all fields from PRD Section 6.1.2, including objective enum, geography multi-select, budget range slider)
- Mandate Summary Card view (readonly, confirm/reject buttons → AG-1)
- Use shadcn/ui form components, React Hook Form, Zod validation
- API: POST /api/v1/mandates, GET /api/v1/mandates/{id}/summary-card, POST /api/v1/mandates/{id}/confirm

Context7: use for shadcn/ui, React Hook Form, Zod docs.
PDCA: present plan before touching any file.
Co-author every commit: $COAUTHOR
"@
    }

    "fe-campaign" = @{
        model = $SONNET
        task  = "TASK-024"
        label = "Frontend · Campaign — Concept deck + activation plan views"
        prompt = @"
Stack: $STACK_FRONTEND
Task file: tasks/TASK-024-fe-campaign.md
Module scope: frontend/src/pages/Campaign/ ONLY.

Build:
- Campaign Concept view: theme, taglines, message architecture, channel mix, phase timeline, mood board images
- Activation Master Plan: interactive Gantt chart (Recharts) + filterable table (by channel/date/geography/status)
- Budget breakdown: pie chart (online vs offline) + bar chart (by channel) + phase spend timeline
- Approve / Request Revision buttons for AG-3 and AG-4
- Revision comment modal with feedback submission

Context7: use for Recharts, shadcn/ui, React Query docs.
PDCA: present plan before touching any file.
Co-author every commit: $COAUTHOR
"@
    }

    "fe-creative" = @{
        model = $SONNET
        task  = "TASK-025"
        label = "Frontend · Creative Studio — Asset review + approval gallery"
        prompt = @"
Stack: $STACK_FRONTEND
Task file: tasks/TASK-025-fe-creative.md
Module scope: frontend/src/pages/CreativeStudio/ ONLY.

Build:
- Creative Showcase gallery: grid of all creative assets for a campaign
- Per-asset viewer: image preview / audio player / video player / script text view
- Status badges: AI Draft / Internal Review / Client Review / Approved / Revision Requested
- Approve / Request Revision / Reject buttons per asset (AG-5)
- Revision comment thread per asset
- Production Brief download button (for shoot/recording assets)
- Bulk approve all assets in a batch

Context7: use for shadcn/ui, React Query docs.
PDCA: present plan before touching any file.
Co-author every commit: $COAUTHOR
"@
    }

    "fe-analytics" = @{
        model = $SONNET
        task  = "TASK-026"
        label = "Frontend · Analytics — Campaign performance dashboard"
        prompt = @"
Stack: $STACK_FRONTEND
Task file: tasks/TASK-026-fe-analytics.md
Module scope: frontend/src/pages/Analytics/ ONLY.

Build:
- Campaign Overview: total reach, total spend, KPI achievement % (gauge charts)
- Channel Performance: side-by-side bar chart across all channels
- Geographic Performance: heatmap of engagement by city/region (use Recharts + custom map overlay)
- Creative Performance: ranked table of creative assets by CTR/engagement
- Timeline view: spend vs performance by week (dual-axis line chart)
- Funnel view: Awareness → Consideration → Conversion
- Physical activation log entry form (proof upload, actual cost, vendor, notes)
- Replan recommendations panel: list of AGT-14 outputs with Approve/Reject per item (AG-6)

Context7: use for Recharts, shadcn/ui docs.
PDCA: present plan before touching any file.
Co-author every commit: $COAUTHOR
"@
    }

    "fe-kpi" = @{
        model = $HAIKU
        task  = "TASK-027"
        label = "Frontend · KPI Dashboard — KPI/KRA tracking view"
        prompt = @"
Stack: $STACK_FRONTEND
Task file: tasks/TASK-027-fe-kpi.md
Module scope: frontend/src/pages/KPIDashboard/ ONLY.

Build:
- KPI definition form (set target value, unit, category, measurement method per KPI)
- KRA definition form (free text goal + linked KPIs)
- KPI status grid: Red/Amber/Green gauges, progress bars against targets, trend sparklines
- KRA achievement summary (% complete, on track / at risk / achieved)
- Weekly trend line per KPI (Recharts LineChart)
- Alert banner when any KPI enters Red status
- Campaign-end report download button

Context7: use for Recharts, shadcn/ui docs.
PDCA: present plan before touching any file.
Co-author every commit: $COAUTHOR
"@
    }

    "fe-admin" = @{
        model = $HAIKU
        task  = "TASK-028"
        label = "Frontend · Admin — Tenant + user management"
        prompt = @"
Stack: $STACK_FRONTEND
Task file: tasks/TASK-028-fe-admin.md
Module scope: frontend/src/pages/Admin/ ONLY.

Build (platform_admin role only):
- Tenant list + create tenant form
- User list per tenant + create user form
- Role assignment dropdown (7 roles from CLAUDE.md)
- Audit log viewer (filterable by entity type, actor, date range)
- System health panel: API status, Celery worker status, DB connection

Context7: use for shadcn/ui, React Query docs.
PDCA: present plan before touching any file.
Co-author every commit: $COAUTHOR
"@
    }

    # ════════════════════════════════════════════════════════════════════════
    # EVALS
    # ════════════════════════════════════════════════════════════════════════

    evals = @{
        model = $SONNET
        task  = "TASK-029"
        label = "Evals · Agent output quality benchmarking"
        prompt = @"
Stack: $STACK_BACKEND + pytest
Task file: tasks/TASK-029-evals.md
Module scope: backend/tests/agents/ + docs/golden/ ONLY.

Build an eval harness for NTM agents:
1. Golden datasets: load reference outputs from docs/golden/ (generated via Claude Marketing Plugin /campaign-plan, /competitive-brief)
2. For each agent (AGT-01 through AGT-05 first): run agent on test mandate → compare output to golden
3. Scoring: completeness_score (required fields present), coherence_score (LLM-as-judge via claude-haiku), format_score (JSON valid + correct schema)
4. Report: per-agent pass/fail table + overall score
5. Threshold: all agents must score ≥ 80 before Phase 4 begins

How to generate golden datasets:
- Use Claude Cowork Marketing Plugin: /campaign-plan on 3 test mandates
- Save outputs to docs/golden/mandate_[n]_concept.json
- These become the benchmark for AGT-03 outputs

Context7: use for pytest, Anthropic SDK docs.
PDCA: present plan before touching any file.
Co-author every commit: $COAUTHOR
"@
    }

    # ════════════════════════════════════════════════════════════════════════
    # DEBUG
    # ════════════════════════════════════════════════════════════════════════

    debug = @{
        model = $SONNET
        task  = "TASK-???"
        label = "Debug Session — one error, one file"
        prompt = @"
Stack: $STACK_BACKEND / $STACK_FRONTEND
Task: one error, one file, one session.

Paste in order:
  1. Full traceback / error message
  2. Only the function or component that threw it (not the whole file)
  3. The exact input that triggered it

Known NTM gotchas:
- All DB queries MUST include tenant_id — missing it is the #1 source of 404s
- Celery tasks must be imported in tasks/__init__.py or Beat won't find them
- pgvector column requires CREATE EXTENSION vector; in migration — not auto by alembic
- MinIO bucket must exist before S3 upload — seed script creates it
- Approval Gate status checks must use Enum values not raw strings
- agent outputs must be pure JSON — any markdown fences break JSON.loads()

Co-author every commit: $COAUTHOR
"@
    }

}

# ── List mode ─────────────────────────────────────────────────────────────────
if ($Session -eq "list") {
    Write-Host ""
    Write-Host "  NTM — Available Sessions" -ForegroundColor Cyan
    Write-Host ""
    Write-Host ("  {0,-28} {1,-48} {2}" -f "SESSION", "LABEL", "MODEL") -ForegroundColor DarkGray
    Write-Host ("  {0,-28} {1,-48} {2}" -f "-------", "-----", "-----") -ForegroundColor DarkGray
    foreach ($key in $sessions.Keys | Sort-Object) {
        $s = $sessions[$key]
        $tag = if ($s.model -like "*haiku*") { "Haiku  🟢" } else { "Sonnet 🔵" }
        Write-Host ("  {0,-28} {1,-48} [{2}]" -f $key, $s.label, $tag)
    }
    Write-Host ""
    Write-Host "  Usage: .\scripts\ntm-sessions.ps1 -Session <name>" -ForegroundColor Yellow
    Write-Host ""
    exit 0
}

# ── Launch session ────────────────────────────────────────────────────────────
$s = $sessions[$Session]
Write-Host ""
Write-Host "  ┌──────────────────────────────────────────────────────┐" -ForegroundColor Cyan
Write-Host ("  │  {0,-52}│" -f $s.label) -ForegroundColor Cyan
Write-Host ("  │  Task:  {0,-48}│" -f $s.task) -ForegroundColor Cyan
Write-Host ("  │  Model: {0,-48}│" -f $s.model) -ForegroundColor Cyan
Write-Host "  └──────────────────────────────────────────────────────┘" -ForegroundColor Cyan
Write-Host ""
Write-Host $s.prompt -ForegroundColor White
Write-Host ""
$s.prompt | Set-Clipboard
Write-Host "  ✓ Context copied to clipboard." -ForegroundColor Green
Write-Host "  Paste into Claude Code, then type: superpowers brainstorm" -ForegroundColor Yellow
Write-Host "  Remember: context limit is 50% — watch cc-status-line" -ForegroundColor DarkGray
Write-Host ""
Set-Location $PROJECT_ROOT
$env:ANTHROPIC_MODEL = $s.model
claude --model $s.model
