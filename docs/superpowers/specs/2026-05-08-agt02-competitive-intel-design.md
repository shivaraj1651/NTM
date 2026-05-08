# AGT-02: Competitive Intelligence Agent — Design Specification

**Date:** 2026-05-08  
**Task:** TASK-005  
**Phase:** 1 (Mandate → Concept)  
**Model:** Sonnet 4.6  
**Status:** Design approved, ready for implementation planning

---

## Executive Summary

AGT-02 is a two-phase competitive intelligence agent that identifies 5-10 competitors from a mandate + client profile, gathers ad intel via SerpAPI and Meta Ad Library, and outputs a structured `CIReport` JSON to MongoDB.

**Key design principle:** Fast competitor identification (sync Phase 1) + detailed metrics gathering (async Phase 2 via Celery).

**Output:** CIReport with per-competitor metrics (channels, messaging, spend estimates, geographic focus) + whitespace opportunities for AGT-03 (strategist) to use in campaign planning.

---

## 1. Requirements & Success Criteria

### Functional Requirements

| Req | Description |
|-----|-------------|
| **REQ-1** | Accept mandate dict + client profile as input |
| **REQ-2** | Identify 5-10 competitors via LLM analysis in <2s (Phase 1) |
| **REQ-3** | Return CIReportInitial with job_id immediately (async start) |
| **REQ-4** | Fetch competitor metrics via SerpAPI + Meta Ad Library (Phase 2) |
| **REQ-5** | Cache competitor profiles for 30 days, refresh metrics weekly |
| **REQ-6** | Best-effort output: include all competitors with null placeholders for missing data |
| **REQ-7** | Store final CIReport in MongoDB (ntm.ci_reports) |
| **REQ-8** | Support 5-10 competitors per mandate (configurable max=15) |
| **REQ-9** | Extract specific metrics: estimated spend, channels, messaging themes, geography |
| **REQ-10** | Identify whitespace opportunities (untapped channels, messaging gaps) |

### Non-Functional Requirements

| Req | Description |
|-----|-------------|
| **NFR-1** | Phase 1 latency: <2s (sync LLM call only) |
| **NFR-2** | Phase 2 latency: <5min per 10 competitors (Celery async, includes API calls) |
| **NFR-3** | SerpAPI + Meta calls run in parallel per competitor (asyncio.gather) |
| **NFR-4** | Cache hit rate target: >70% for repeat mandates (same competitors) |
| **NFR-5** | Error resilience: handle 1-2 failed API sources gracefully (partial report OK) |
| **NFR-6** | Data freshness: weekly metric refresh via Celery Beat |

### Success Criteria

- ✓ Phase 1 completes in <2s, returns valid CIReportInitial JSON
- ✓ Phase 2 completes in <5min, stores valid CIReport in MongoDB
- ✓ All required fields present in CIReport (competitors[], whitespace_opportunities)
- ✓ Happy-path test passes (sync competitor identification with mocked LLM)
- ✓ Error-path tests pass (missing competitors, API failures handled gracefully)
- ✓ Output validated against CIReport schema before storage

---

## 2. Architecture & Data Flow

### System Diagram

```
┌─ REST API ─────────────────────────────────────────────┐
│  POST /api/v1/mandates/{id}/analyze-competitors       │
└────────────────────┬────────────────────────────────────┘
                     │
                     ▼
        ┌─ Router (mandate.py) ─┐
        │ tenant_id validation   │
        │ auth check             │
        └───────────┬────────────┘
                    │
                    ▼
    ┌──────────────────────────────────┐
    │ Phase 1: SYNC (LLM + Return)     │
    │                                  │
    │ identify_competitors_sync()      │
    │  ├─ Parse mandate + profile      │
    │  ├─ LLM: "Who are competitors?"  │
    │  ├─ Validate (5-15 names)        │
    │  └─ Return CIReportInitial       │
    │      {job_id, competitors[],     │
    │       status='pending'}          │
    │                                  │
    │ Response to caller:              │
    │  {job_id, competitors}           │
    │  (caller polls for full report)  │
    └──────────┬───────────────────────┘
               │
               ├─ Save CIReportInitial to MongoDB
               │
               ├─ Enqueue Celery task (non-blocking return)
               │
               ▼
    ┌──────────────────────────────────────────────┐
    │ Phase 2: ASYNC (Celery Background Task)     │
    │                                              │
    │ fetch_competitor_metrics(mandate_id, names) │
    │  ├─ For each competitor:                     │
    │  │  ├─ Cache lookup (ttl=30d)                │
    │  │  ├─ If miss:                              │
    │  │  │  ├─ SerpAPI search (parallel)          │
    │  │  │  ├─ Meta Ad Library lookup (parallel)  │
    │  │  │  └─ Store in cache                     │
    │  │  └─ Collect metrics                       │
    │  │                                           │
    │  ├─ LLM synthesis:                           │
    │  │  "Analyze all metrics → whitespace"       │
    │  │                                           │
    │  └─ Store full CIReport                      │
    │     {competitors[], whitespace_opportunities}│
    │     status='complete'                        │
    │                                              │
    │ On retry/failure:                            │
    │  - Partial results OK (best-effort)          │
    │  - status='partial' or 'failed'              │
    │  - Return what we have                       │
    └──────────────────────────────────────────────┘
               │
               ▼
    ┌─────────────────────────────────┐
    │ Client polls:                   │
    │ GET /api/v1/jobs/{job_id}       │
    │                                 │
    │ Returns:                        │
    │  {status, competitors[],        │
    │   whitespace_opportunities}     │
    └─────────────────────────────────┘
```

### Phase 1: Sync Competitor Identification

**Function:** `identify_competitors_sync(mandate: Dict, client_profile: Dict) -> CIReportInitial`

**Logic:**
1. Parse mandate fields: objective, target_audience, geography, budget
2. Parse client profile: industry, existing_competitors (if provided)
3. Construct LLM prompt:
   ```
   You are a competitive intelligence analyst.
   
   Based on this mandate and client profile, identify the 5-10 most likely competitors.
   
   Industry: {industry}
   Objective: {objective}
   Target Audience: {target_audience}
   Geography: {geography}
   
   Return ONLY a JSON list with name and confidence:
   [
     {"name": "Competitor A", "confidence": 95},
     {"name": "Competitor B", "confidence": 85}
   ]
   ```
4. Call Claude Sonnet: max_tokens=1000, temperature=0.3 (deterministic)
5. Parse response, validate: 5 ≤ count ≤ 15, all have names + confidence
6. Return `CIReportInitial` immediately
7. In router: enqueue Phase 2 Celery task (non-blocking)

**Execution time:** <2s (single LLM call, no external APIs)

---

### Phase 2: Async Metrics Gathering

**Celery Task:** `fetch_competitor_metrics(mandate_id: str, competitor_names: List[str], metadata: Dict) -> None`

**Logic per competitor (parallelized):**

1. **Cache lookup:**
   - Check `competitor_cache` collection for `{competitor_name, metrics_last_refreshed > today-7days}`
   - If found and fresh → use cached metrics, skip API calls
   - If found but stale (>7d) or missing → proceed to fetch

2. **Fetch from SerpAPI:**
   - Call `search_competitor_ads(competitor_name, geography, year=2026)`
   - Parse results:
     - Extract ad copy snippets (messaging themes)
     - Identify platform mentions (Google, Meta, LinkedIn, TikTok, etc.)
     - Extract estimated reach/impressions if present
     - Record search result count (proxy for ad spend intensity)

3. **Fetch from Meta Ad Library:**
   - If competitor has Meta presence (detected from SerpAPI or heuristic):
     - Call `lookup_meta_ads(advertiser_name, date_range_days=90)`
     - Extract: spend estimate, active ads count, placements, primary audiences
   - If no Meta presence detected → skip, set meta_spend=null

4. **Combine sources:**
   - Merge SerpAPI findings + Meta findings into structured competitor metrics
   - Update cache with timestamp

5. **After all competitors collected:**
   - Call LLM synthesis:
     ```
     You are a competitive intelligence analyst.
     
     Analyze these competitor profiles and metrics:
     {competitors_json}
     
     Output ONLY valid JSON:
     {
       "competitors": [
         {
           "name": "...",
           "channels": {
             "google_ads": {...},
             "facebook": {...},
             ...
           },
           "messaging_themes": [...],
           "estimated_annual_spend": N,
           ...
         }
       ],
       "whitespace_opportunities": {
         "untapped_channels": [...],
         "messaging_gaps": [...],
         "geographic_gaps": [...]
       },
       "market_concentration": "..."
     }
     ```
   - max_tokens=4000, temperature=0.2

6. **Store in MongoDB:**
   - Insert full `CIReport` into `ci_reports` collection
   - Update `CIReportInitial` job status: 'pending' → 'complete'
   - Log completion timestamp

**Execution time:** <5min for 10 competitors (SerpAPI + Meta calls parallelized via asyncio.gather)

**Error handling:**
- If SerpAPI fails for competitor X → set channels={}, continue
- If Meta Ad Library fails → skip Meta data, continue  
- If LLM synthesis fails → store raw metrics (unanalyzed), status='partial'
- If entire task fails → Celery retry 3x (exponential backoff)
- If task timeout → return partial results (best-effort)

---

## 3. Module Structure & Responsibilities

### `backend/app/agents/competitive_intel.py`

**Main entry point:**
```python
async def competitive_intel_agent(
    mandate: Dict[str, Any],
    client_profile: Dict[str, Any],
    mandate_id: str,
    tenant_id: str
) -> Dict[str, Any]:
    """
    AGT-02 Competitive Intelligence Agent.
    
    Phase 1 (sync):
      - Identify competitors from mandate + profile
      - Return CIReportInitial with job_id
    
    Phase 2 (async Celery):
      - Enqueue background task to fetch metrics
      - Return immediately (non-blocking)
    
    Returns:
      CIReportInitial {job_id, competitors[], status, created_at}
    """
```

**Sub-function:**
```python
async def identify_competitors_sync(
    mandate: Dict[str, Any],
    client_profile: Dict[str, Any]
) -> List[Dict]:
    """
    Phase 1: LLM-based competitor identification.
    
    Returns:
      [{"name": "...", "confidence": N}, ...]
    """
```

---

### `backend/app/tools/serpapi.py`

**Functions:**
```python
async def search_competitor_ads(
    competitor_name: str,
    geography: List[str],
    year: int = 2026
) -> Dict[str, Any]:
    """
    Call SerpAPI to find competitor ad campaigns.
    
    Args:
      competitor_name: "Nike"
      geography: ["US", "UK"]
      year: 2026
    
    Returns:
      {
        "channels_detected": ["google_ads", "facebook", "linkedin"],
        "messaging_samples": ["msg1", "msg2"],
        "estimated_search_volume": 1000,
        "raw_results": [...]  # Full SerpAPI response
      }
    """
```

**Implementation:**
- Use SerpAPI Python client
- Query: f"{competitor_name} advertising campaign {year}"
- Parse results for platform mentions (regex for "Google Ads", "Facebook", etc.)
- Extract text snippets (messaging themes)
- Handle rate limits: backoff + retry

---

### `backend/app/tools/meta_ads.py`

**Functions:**
```python
async def lookup_meta_ads(
    advertiser_name: str,
    date_range_days: int = 90
) -> Dict[str, Any]:
    """
    Query Meta Ad Library public endpoint.
    
    Args:
      advertiser_name: "Nike"
      date_range_days: 90
    
    Returns:
      {
        "ads_found": 42,
        "placements": ["feed", "stories", "reels"],
        "estimated_monthly_spend": 50000,
        "impressions": 2500000,
        "primary_audiences": ["18-24", "25-34"],
        "raw_ads": [...]
      }
    """
```

**Implementation:**
- Use Meta's public Ad Library API (no auth needed)
- Endpoint: `https://graph.facebook.com/ads_archive`
- Search by advertiser name
- Parse active ads, extract placements + audience data
- Estimate spend from available data (Meta provides ranges)

---

### `backend/app/schemas/competitive_intel.py`

**Data classes:**

```python
class CompetitorIdentity(BaseModel):
    name: str
    confidence: int  # 0-100

class CompetitorMetrics(BaseModel):
    name: str
    confidence_score: int
    channels: Dict[str, Optional[Dict]]  # {google_ads: {...}, facebook: {...}}
    messaging_themes: List[str]
    geographic_focus: List[str]
    estimated_annual_spend: Optional[float]
    data_sources: List[str]  # ["serpapi", "meta_ad_library"]

class CIReportInitial(BaseModel):
    job_id: str
    mandate_id: str
    competitors: List[CompetitorIdentity]
    status: Literal["pending"]
    created_at: str  # ISO timestamp

class CIReport(BaseModel):
    mandate_id: str
    job_id: str
    generated_at: str
    competitors: List[CompetitorMetrics]
    whitespace_opportunities: Dict[str, List[str]]
    market_concentration: str
    status: Literal["complete", "partial", "failed"]
```

---

### `backend/app/tasks/competitive_intel_tasks.py`

**Celery task:**
```python
@shared_task(bind=True, max_retries=3)
async def fetch_competitor_metrics(
    self,
    mandate_id: str,
    competitor_names: List[str],
    mandate_dict: Dict,
    tenant_id: str
) -> None:
    """
    Phase 2: Async metrics gathering for competitors.
    
    Runs in Celery worker.
    Retries up to 3x on failure.
    Stores results in MongoDB.
    """
```

---

## 4. Data Structures

### CIReport JSON (MongoDB)

```json
{
  "_id": "ObjectId",
  "mandate_id": "550e8400-e29b-41d4-a716-446655440000",
  "job_id": "job-550e8400-e29b-41d4-a716-446655440001",
  "generated_at": "2026-05-08T14:32:00Z",
  "tenant_id": "tenant-123",
  "competitors": [
    {
      "name": "Nike",
      "confidence_score": 95,
      "channels": {
        "google_ads": {
          "presence": true,
          "estimated_monthly_spend": 75000,
          "primary_keywords": ["running shoes", "performance"],
          "estimated_monthly_impressions": 2000000
        },
        "facebook": {
          "presence": true,
          "estimated_monthly_spend": 50000,
          "placements": ["feed", "stories", "reels"],
          "estimated_monthly_impressions": 5000000
        },
        "linkedin": {
          "presence": false
        },
        "tiktok": {
          "presence": true,
          "estimated_monthly_spend": 30000
        },
        "offline": {
          "presence": true,
          "channels": ["print", "ooh", "tv"],
          "estimated_annual_spend": 200000
        }
      },
      "messaging_themes": [
        "Performance and innovation",
        "Athlete empowerment",
        "Sustainability",
        "Lifestyle/aspiration"
      ],
      "geographic_focus": ["US", "UK", "EU", "APAC"],
      "estimated_annual_ad_spend": 1200000,
      "data_sources": ["serpapi", "meta_ad_library"],
      "data_confidence": "high"
    },
    {
      "name": "Adidas",
      "confidence_score": 92,
      "channels": { ... },
      "messaging_themes": [ ... ],
      "geographic_focus": [ ... ],
      "estimated_annual_ad_spend": 950000,
      "data_sources": ["serpapi"],
      "data_confidence": "medium"
    }
  ],
  "whitespace_opportunities": {
    "untapped_channels": [
      "WhatsApp Business",
      "Email marketing (minimal competitor presence)",
      "Podcast sponsorships"
    ],
    "messaging_gaps": [
      "Accessibility/inclusive design",
      "Local community focus",
      "Transparent supply chain"
    ],
    "geographic_gaps": [
      "Southeast Asia",
      "Latin America",
      "Africa"
    ]
  },
  "market_concentration": "Moderate (top 3 competitors control ~65% estimated spend)",
  "status": "complete",
  "created_at": "2026-05-08T14:32:00Z",
  "updated_at": "2026-05-08T14:37:15Z"
}
```

### Competitor Cache (MongoDB)

Collection: `competitor_cache`

```json
{
  "_id": "ObjectId",
  "competitor_name": "Nike",
  "profile": {
    "industry": "Athletic Apparel",
    "market_position": "Leader",
    "primary_geographies": ["US", "UK", "EU"]
  },
  "channels": {
    "google_ads": { ... },
    "facebook": { ... }
  },
  "metrics_last_refreshed": "2026-05-08",
  "next_refresh_due": "2026-05-15",
  "created_at": "2026-04-08",
  "expires_at": "2026-06-08",  // TTL index
  "refresh_count": 5
}
```

---

## 5. Caching Strategy

### Cache Scope
- **Profile cache (TTL=30 days):** Competitor identity, industry, market position
- **Metrics cache (TTL=7 days):** Channels, spend estimates, messaging (refreshed weekly via Celery Beat)

### Refresh Schedule
- **Weekly Celery Beat task:** `refresh_competitor_metrics.run()`
  - For all competitors in cache:
    - Check `metrics_last_refreshed < today - 7 days`
    - If true: re-fetch SerpAPI + Meta
    - Update cache + increment `refresh_count`

### Cache Hit Strategy
- Before Phase 2 API calls: check cache
- If competitor found + metrics_last_refreshed < 7 days → use cached data
- If missing or stale → fetch fresh, update cache
- Log cache hits/misses for monitoring

**Target:** >70% cache hit rate for repeat mandates (same competitors across campaigns)

---

## 6. Error Handling & Resilience

| Failure Mode | Handling | Output |
|---|---|---|
| Competitor not found (0 results) | Skip API calls, set channels={} | `confidence_score: 20`, no metrics |
| SerpAPI API key invalid/expired | Celery retry 3x, then fail gracefully | Use only Meta data if available |
| Meta Ad Library timeout | Skip Meta, continue with SerpAPI | `data_sources: ["serpapi"]` |
| LLM synthesis fails (bad JSON) | Store raw metrics (unanalyzed) | `status: "partial"` |
| Celery task timeout (>5min) | Return partial results (best-effort) | `status: "partial"`, competitors with available data |
| Database write fails | Celery retry 3x, log error | Task marked failed, caller polls sees `status: "pending"` |

**Best-effort principle:** Always return something (partial report) rather than total failure.

---

## 7. Testing Strategy

### Happy-Path Test (Required)

**Test:** `test_identify_competitors_sync_happy_path()`
- Input: complete mandate + client profile
- Mock: LLM returns valid competitor list
- Assertions:
  - Returns `CIReportInitial` with valid structure
  - job_id is UUID
  - competitors list length: 5-10
  - status='pending'
  - created_at is ISO timestamp

**No external API calls** (SerpAPI/Meta mocked or not called)

---

### Error-Path Tests (Recommended)

- **test_identify_competitors_sync_invalid_llm_response()** — LLM returns malformed JSON
- **test_identify_competitors_sync_too_many_competitors()** — LLM returns >15 names (should trim)
- **test_identify_competitors_sync_no_competitors()** — LLM returns empty list (should fail gracefully)

---

## 8. Integration Points

### Router Integration
```python
# backend/app/routers/mandate.py
@router.post("/api/v1/mandates/{mandate_id}/analyze-competitors")
async def trigger_competitive_analysis(
    mandate_id: str,
    current_tenant_id: str = Depends(get_tenant_id)
):
    """
    Trigger Phase 1 + 2 analysis.
    
    Returns immediately with CIReportInitial.
    Phase 2 runs async in Celery.
    """
    mandate = await get_mandate(mandate_id, current_tenant_id)
    client_profile = await get_client_profile(mandate.client_id, current_tenant_id)
    
    result = await competitive_intel_agent(
        mandate=mandate.dict(),
        client_profile=client_profile.dict(),
        mandate_id=mandate_id,
        tenant_id=current_tenant_id
    )
    
    # Enqueue Phase 2 (async, non-blocking)
    fetch_competitor_metrics.delay(
        mandate_id=mandate_id,
        competitor_names=[c["name"] for c in result["competitors"]],
        mandate_dict=mandate.dict(),
        tenant_id=current_tenant_id
    )
    
    return result  # CIReportInitial
```

### Job Status Polling
```python
# backend/app/routers/jobs.py (or mandate.py)
@router.get("/api/v1/jobs/{job_id}")
async def get_job_status(job_id: str, current_tenant_id: str = Depends(get_tenant_id)):
    """
    Poll for Phase 2 completion.
    
    Returns CIReportInitial (pending) or CIReport (complete).
    """
    doc = await db.ci_reports.find_one({"job_id": job_id, "tenant_id": current_tenant_id})
    if not doc:
        raise HTTPException(status_code=404)
    return doc
```

### Downstream: AGT-03 (Campaign Strategist)
- Input: Mandate Summary Card (from AGT-01) + CIReport (from AGT-02)
- Uses: `competitors[].whitespace_opportunities` to guide strategy
- Output: CampaignConcept with channel mix + messaging informed by competitive gaps

---

## 9. Configuration & Environment Variables

```env
# .env
SERPAPI_API_KEY=<key>
SERPAPI_RATE_LIMIT_CALLS=100  # Per day
SERPAPI_RATE_LIMIT_RESET=86400  # Seconds

MONGO_DB_NAME=ntm
MONGO_COLLECTION_CI_REPORTS=ci_reports
MONGO_COLLECTION_COMPETITOR_CACHE=competitor_cache

CELERY_BROKER_URL=redis://localhost:6379/0
CELERY_BROKER_QUEUE_NAME=competitive_intel

CACHE_TTL_PROFILE_DAYS=30
CACHE_TTL_METRICS_DAYS=7
CACHE_REFRESH_SCHEDULE=0 9 * * 1  # Weekly Monday 9am (Celery Beat cron)

MAX_COMPETITORS=15
MIN_COMPETITORS=5

LLM_MODEL=claude-sonnet-4-20250514
LLM_MAX_TOKENS_IDENTIFY=1000
LLM_MAX_TOKENS_SYNTHESIZE=4000
LLM_TEMPERATURE_IDENTIFY=0.3
LLM_TEMPERATURE_SYNTHESIZE=0.2
```

---

## 10. Success Metrics & Monitoring

### Metrics to Track

| Metric | Target | Tool |
|--------|--------|------|
| Phase 1 latency (p95) | <2s | CloudWatch/APM |
| Phase 2 latency (p95) | <5min | Celery task monitoring |
| Cache hit rate | >70% | MongoDB query count |
| API error rate | <5% | SerpAPI + Meta logs |
| Task success rate | >95% | Celery metrics |
| Data completeness (avg fields per competitor) | >80% | CIReport validation |

### Alerts
- Phase 2 task timeout: >5min
- SerpAPI API limit hit: daily quota exceeded
- Cache miss storm: >30% miss rate (indicates stale data)
- LLM synthesis failures: >5% of tasks

---

## 11. Deployment & Rollout

### Pre-Deployment Checklist
- [ ] All tests pass (happy-path + error-path)
- [ ] SerpAPI + Meta Ad Library credentials configured
- [ ] MongoDB indexes created (`competitor_name`, `metrics_last_refreshed`)
- [ ] Celery Beat task registered (`refresh_competitor_metrics`)
- [ ] Router endpoints tested (happy + error paths)
- [ ] Monitoring dashboards created

### Rollout Strategy
- Deploy Phase 1 (sync) first
- Verify <2s latency, happy-path tests passing
- Deploy Celery workers for Phase 2
- Monitor Phase 2 latency, error rates
- Enable cache refresh task once stable

---

## 12. Future Enhancements

- [ ] Support custom competitor lists (user-provided names)
- [ ] Competitor sentiment analysis (using Social Listening APIs)
- [ ] Budget estimation ML model (vs. simple heuristics)
- [ ] Real-time competitor alerts (Celery Beat + webhook)
- [ ] Competitive positioning map (visualization in frontend)
- [ ] ROI impact analysis (competitor tactics → brand impact)

---

## Appendix A: Example Workflow

```
1. Client submits mandate for "Q3 Athletic Apparel Campaign"
   
2. AGT-01 runs: validates mandate → CIReport.completeness_score=95

3. AGT-02 Phase 1 (sync):
   - LLM identifies: Nike (95), Adidas (92), Puma (88), Under Armour (82)
   - Return CIReportInitial {job_id: "job-123", competitors: [...], status: "pending"}
   - Router responds to client in <2s
   
4. AGT-02 Phase 2 (background):
   - Celery task enqueued
   - For Nike:
     - Cache miss (first time)
     - SerpAPI: find 150 results, extract channels: google_ads, facebook, tiktok, offline
     - Meta Ad Library: 42 active ads, $50k/month spend estimate
     - Store in cache
   - For Adidas, Puma, Under Armour: repeat (parallel)
   - LLM synthesis: "Nike dominates digital, Adidas strong in EU, gap in WhatsApp/Email"
   - Store CIReport in MongoDB, status='complete'
   
5. Client polls: GET /api/v1/jobs/job-123
   - First poll (5s later): status='pending'
   - Second poll (3min later): status='complete', full CIReport returned
   
6. AGT-03 (Strategist) uses CIReport:
   - Reads whitespace_opportunities: ["WhatsApp", "Email", "Podcast"]
   - Recommends channel mix: 40% Google, 30% TikTok (low competitor presence), 20% Email, 10% Podcast
   - Output: CampaignConcept informed by CI
```

---

## Sign-Off

**Reviewed by:** Agent (brainstorming phase)  
**Approved by:** User  
**Date approved:** 2026-05-08  
**Next step:** Implementation planning (invoke `writing-plans` skill)
