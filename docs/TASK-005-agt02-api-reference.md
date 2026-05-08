# AGT-02 Competitive Intelligence API Reference

This document describes the API endpoints for triggering and polling competitive intelligence analysis. These endpoints orchestrate Phase 1 (competitor identification) and Phase 2 (metrics gathering) of the mandate analyst agent.

## Quick Start Workflow

```
1. POST /api/v1/mandates/{mandate_id}/analyze-competitors
   └─> Returns CIReportInitial with job_id (Phase 1 complete in <2s)

2. GET /api/v1/jobs/{job_id} (poll until complete)
   └─> Returns CIReportInitial (pending) or CIReport (complete)

3. Use CIReport.whitespace_opportunities in AGT-03
   └─> Feed into market strategy analysis
```

---

## Endpoint 1: POST /api/v1/mandates/{mandate_id}/analyze-competitors

**Trigger Phase 1 + Phase 2 analysis for a mandate**

### Request

```http
POST /api/v1/mandates/{mandate_id}/analyze-competitors
Authorization: Bearer <JWT_TOKEN>
Content-Type: application/json
```

### Path Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `mandate_id` | UUID | Yes | Unique identifier of the mandate to analyze |

### Authentication

- **Type:** JWT Bearer token
- **Required:** Yes
- **Header:** `Authorization: Bearer <token>`

### Request Body

No request body required. Analysis uses mandate and client profile from database.

### Response: 200 OK

Returns `CIReportInitial` immediately after Phase 1 completes (typically <2 seconds).

```json
{
  "job_id": "550e8400-e29b-41d4-a716-446655440000",
  "mandate_id": "123e4567-e89b-12d3-a456-426614174000",
  "competitors": [
    {
      "name": "TechCorp Inc",
      "confidence": 95
    },
    {
      "name": "Digital Innovations Ltd",
      "confidence": 87
    },
    {
      "name": "CloudFirst Solutions",
      "confidence": 72
    }
  ],
  "status": "pending",
  "created_at": "2026-05-08T14:32:45.123456Z"
}
```

### Response: 404 Not Found

**Case 1: Mandate not found**

```json
{
  "detail": "Mandate not found"
}
```

**Case 2: Client profile not found**

```json
{
  "detail": "Client profile not found"
}
```

### Response: 400 Bad Request

Competitor analysis failed during Phase 1.

```json
{
  "detail": "Competitor analysis failed: Unable to identify competitors from mandate description"
}
```

### Behavior

- **Phase 1 (sync):** Identifies competitors from mandate/client data using LLM analysis. Completes in <2 seconds.
- **Phase 2 (async):** Enqueued as Celery task to gather detailed metrics (channels, spend, placements, etc.). Runs asynchronously.
- **Return timing:** Endpoint returns immediately after Phase 1 with `status="pending"`.
- **Job tracking:** Use `job_id` from response to poll for Phase 2 completion.
- **Database:** Report saved to MongoDB `ci_reports` collection with `tenant_id` isolation.

### Example Usage (Python)

```python
import requests
import time

mandate_id = "123e4567-e89b-12d3-a456-426614174000"
headers = {"Authorization": f"Bearer {jwt_token}"}

# Step 1: Trigger analysis
response = requests.post(
    f"https://api.example.com/api/v1/mandates/{mandate_id}/analyze-competitors",
    headers=headers
)
assert response.status_code == 200
ci_report_initial = response.json()
job_id = ci_report_initial["job_id"]

print(f"Analysis started. Job ID: {job_id}")
print(f"Identified {len(ci_report_initial['competitors'])} competitors")
```

---

## Endpoint 2: GET /api/v1/jobs/{job_id}

**Poll for Phase 2 completion and retrieve full competitive intelligence report**

### Request

```http
GET /api/v1/jobs/{job_id}
Authorization: Bearer <JWT_TOKEN>
```

### Path Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `job_id` | UUID | Yes | Job identifier from POST `/analyze-competitors` response |

### Authentication

- **Type:** JWT Bearer token
- **Required:** Yes
- **Header:** `Authorization: Bearer <token>`

### Response: 200 OK - Pending (Phase 2 in progress)

Returns `CIReportInitial` when Phase 2 is still running.

```json
{
  "job_id": "550e8400-e29b-41d4-a716-446655440000",
  "mandate_id": "123e4567-e89b-12d3-a456-426614174000",
  "competitors": [
    {
      "name": "TechCorp Inc",
      "confidence": 95
    },
    {
      "name": "Digital Innovations Ltd",
      "confidence": 87
    },
    {
      "name": "CloudFirst Solutions",
      "confidence": 72
    }
  ],
  "status": "pending",
  "created_at": "2026-05-08T14:32:45.123456Z"
}
```

### Response: 200 OK - Complete (Phase 2 done)

Returns `CIReport` when Phase 2 has completed with full metrics.

```json
{
  "mandate_id": "123e4567-e89b-12d3-a456-426614174000",
  "job_id": "550e8400-e29b-41d4-a716-446655440000",
  "generated_at": "2026-05-08T14:35:22.654321Z",
  "tenant_id": "tenant-abc123",
  "competitors": [
    {
      "name": "TechCorp Inc",
      "confidence_score": 95,
      "channels": {
        "google_ads": {
          "presence": true,
          "estimated_monthly_spend": 45000,
          "estimated_monthly_impressions": 1200000,
          "placements": ["search", "display"],
          "primary_keywords": ["cloud solutions", "enterprise software", "digital transformation"],
          "primary_audiences": ["IT directors", "CIOs", "tech managers"]
        },
        "meta": {
          "presence": true,
          "estimated_monthly_spend": 32000,
          "estimated_monthly_impressions": 850000,
          "placements": ["feed"],
          "primary_keywords": [],
          "primary_audiences": ["tech enthusiasts", "business leaders", "startup founders"]
        },
        "linkedin": {
          "presence": true,
          "estimated_monthly_spend": 18000,
          "estimated_monthly_impressions": 280000,
          "placements": ["sponsored content"],
          "primary_keywords": ["B2B cloud", "enterprise solutions"],
          "primary_audiences": ["business decision makers", "enterprise buyers"]
        }
      },
      "messaging_themes": [
        "Enterprise-grade reliability",
        "Cost optimization",
        "Fast deployment",
        "Security and compliance"
      ],
      "geographic_focus": ["North America", "Western Europe", "APAC"],
      "estimated_annual_spend": 1200000,
      "data_sources": ["google_ads_library", "meta_ad_library", "serpapi", "semrush"],
      "data_confidence": "high"
    },
    {
      "name": "Digital Innovations Ltd",
      "confidence_score": 87,
      "channels": {
        "google_ads": {
          "presence": true,
          "estimated_monthly_spend": 28000,
          "estimated_monthly_impressions": 750000,
          "placements": ["search"],
          "primary_keywords": ["software development", "custom solutions", "tech consulting"],
          "primary_audiences": ["CTOs", "developers", "tech leads"]
        },
        "meta": {
          "presence": false,
          "estimated_monthly_spend": null,
          "estimated_monthly_impressions": null,
          "placements": [],
          "primary_keywords": [],
          "primary_audiences": []
        },
        "linkedin": {
          "presence": true,
          "estimated_monthly_spend": 12000,
          "estimated_monthly_impressions": 195000,
          "placements": ["sponsored content"],
          "primary_keywords": ["software consulting", "team augmentation"],
          "primary_audiences": ["engineering managers", "CTOs"]
        }
      },
      "messaging_themes": [
        "Expert engineering teams",
        "Rapid scaling",
        "Technical excellence"
      ],
      "geographic_focus": ["North America"],
      "estimated_annual_spend": 480000,
      "data_sources": ["google_ads_library", "serpapi"],
      "data_confidence": "medium"
    }
  ],
  "whitespace_opportunities": {
    "untapped_channels": [
      "TikTok",
      "YouTube advertising",
      "Programmatic display",
      "Reddit sponsored content"
    ],
    "messaging_gaps": [
      "Vertical-specific solutions",
      "Environmental/sustainability angle",
      "Developer experience focus",
      "Customer success stories"
    ],
    "geographic_gaps": [
      "Latin America",
      "Southeast Asia",
      "Middle East",
      "Eastern Europe"
    ]
  },
  "market_concentration": "concentrated",
  "status": "complete",
  "created_at": "2026-05-08T14:32:45.123456Z",
  "updated_at": "2026-05-08T14:35:22.654321Z"
}
```

### Response: 404 Not Found

Job not found in database.

```json
{
  "detail": "Job not found"
}
```

### Polling Behavior

- **Initial response:** `status="pending"` with `CIReportInitial` schema
- **Final response:** `status="complete"` (or `"partial"` / `"failed"`) with full `CIReport` schema
- **Check status field:** Use the `status` field to determine response type:
  - `pending` → Phase 2 still running
  - `complete` → Full metrics available
  - `partial` → Some metrics gathered but incomplete
  - `failed` → Phase 2 failed to complete

### Recommended Polling Strategy

```python
import time

job_id = ci_report_initial["job_id"]
max_attempts = 120  # 10 minutes with 5s intervals
attempt = 0

while attempt < max_attempts:
    response = requests.get(
        f"https://api.example.com/api/v1/jobs/{job_id}",
        headers=headers
    )
    assert response.status_code == 200
    
    report = response.json()
    status = report.get("status")
    
    if status == "pending":
        print(f"Attempt {attempt}: Still gathering metrics...")
        time.sleep(5)
        attempt += 1
    elif status == "complete":
        print("Analysis complete!")
        ci_report = report
        whitespace = report["whitespace_opportunities"]
        break
    else:  # partial or failed
        print(f"Analysis ended with status: {status}")
        ci_report = report
        break
else:
    print("Polling timeout after 10 minutes")
    ci_report = None
```

---

## JSON Schema Reference

### CIReportInitial

**Returned by:** `POST /analyze-competitors`, `GET /jobs/{job_id}` (pending)

```json
{
  "job_id": "string (UUID)",
  "mandate_id": "string (UUID)",
  "competitors": [
    {
      "name": "string",
      "confidence": "integer (0-100)"
    }
  ],
  "status": "pending",
  "created_at": "string (ISO 8601 timestamp)"
}
```

### CIReport

**Returned by:** `GET /jobs/{job_id}` (complete)

```json
{
  "mandate_id": "string (UUID)",
  "job_id": "string (UUID)",
  "generated_at": "string (ISO 8601 timestamp)",
  "tenant_id": "string",
  "competitors": [
    {
      "name": "string",
      "confidence_score": "integer (0-100)",
      "channels": {
        "channel_key": {
          "presence": "boolean",
          "estimated_monthly_spend": "number | null",
          "estimated_monthly_impressions": "integer | null",
          "placements": ["string"],
          "primary_keywords": ["string"],
          "primary_audiences": ["string"]
        }
      },
      "messaging_themes": ["string"],
      "geographic_focus": ["string"],
      "estimated_annual_spend": "number | null",
      "data_sources": ["string"],
      "data_confidence": "high | medium | low"
    }
  ],
  "whitespace_opportunities": {
    "untapped_channels": ["string"],
    "messaging_gaps": ["string"],
    "geographic_gaps": ["string"]
  },
  "market_concentration": "fragmented | concentrated | oligopoly",
  "status": "complete | partial | failed",
  "created_at": "string (ISO 8601 timestamp)",
  "updated_at": "string (ISO 8601 timestamp)"
}
```

### WhitespaceOpportunities

Identifies gaps in competitor coverage that your client can exploit.

- **untapped_channels:** Advertising channels not being used by competitors
- **messaging_gaps:** Unique messaging angles not covered by competitors
- **geographic_gaps:** Geographic regions not being targeted

### CompetitorMetrics

Detailed metrics for a single competitor.

- **name:** Competitor company name
- **confidence_score:** Overall confidence in data accuracy (0-100)
- **channels:** Per-channel advertising metrics (keys: `google_ads`, `meta`, `linkedin`, etc.)
- **messaging_themes:** Primary messaging angles observed across campaigns
- **geographic_focus:** Target regions/countries
- **estimated_annual_spend:** Total estimated ad spend across all channels
- **data_sources:** Where the data came from (e.g., `meta_ad_library`, `semrush`, `serpapi`)
- **data_confidence:** Overall confidence level in gathered data

---

## Error Codes

| Code | Scenario | Example Detail |
|------|----------|-----------------|
| 200 | Success (Phase 1 or polling result) | N/A |
| 400 | Competitor analysis failed in Phase 1 | `"Competitor analysis failed: Unable to identify competitors"` |
| 404 | Mandate not found | `"Mandate not found"` |
| 404 | Client profile not found | `"Client profile not found"` |
| 404 | Job not found | `"Job not found"` |
| 500 | Internal server error | `"Failed to save initial report"` |

---

## Integration with AGT-03

The `whitespace_opportunities` field from the completed `CIReport` feeds directly into AGT-03 (Market Strategy Analysis):

```python
ci_report = get_job_status(job_id)  # Retrieve completed report

if ci_report["status"] == "complete":
    whitespace = ci_report["whitespace_opportunities"]
    
    # Pass to AGT-03
    strategy = agt03_market_strategy_agent(
        whitespace_opportunities=whitespace,
        mandate=mandate,
        client_profile=client_profile,
        tenant_id=tenant_id
    )
```

---

## Rate Limits & Performance

- **POST /analyze-competitors:** Phase 1 completes in <2 seconds
- **GET /jobs/{job_id}:** Typically ready in 10-60 seconds (polling interval: 5s recommended)
- **Database:** All queries include `tenant_id` for multi-tenancy isolation
- **Authorization:** JWT token required for all endpoints

---

## Examples

### Complete Workflow (Python)

```python
import requests
import time
import json

BASE_URL = "https://api.example.com"
JWT_TOKEN = "your-jwt-token-here"

headers = {"Authorization": f"Bearer {JWT_TOKEN}"}

# Step 1: Trigger Phase 1 + enqueue Phase 2
mandate_id = "123e4567-e89b-12d3-a456-426614174000"

response = requests.post(
    f"{BASE_URL}/api/v1/mandates/{mandate_id}/analyze-competitors",
    headers=headers
)

if response.status_code != 200:
    print(f"Error: {response.status_code}")
    print(json.dumps(response.json(), indent=2))
    exit(1)

ci_report_initial = response.json()
job_id = ci_report_initial["job_id"]

print(f"✓ Phase 1 complete")
print(f"  Job ID: {job_id}")
print(f"  Competitors identified: {len(ci_report_initial['competitors'])}")
for competitor in ci_report_initial['competitors']:
    print(f"    - {competitor['name']} (confidence: {competitor['confidence']}%)")

# Step 2: Poll for Phase 2 completion
print("\n✓ Polling for Phase 2 completion...")

max_polls = 120
poll_interval = 5

for poll_num in range(max_polls):
    response = requests.get(
        f"{BASE_URL}/api/v1/jobs/{job_id}",
        headers=headers
    )
    
    if response.status_code != 200:
        print(f"Error: {response.status_code}")
        exit(1)
    
    report = response.json()
    status = report.get("status")
    
    if status == "pending":
        print(f"  [{poll_num + 1}/{max_polls}] Still gathering metrics...")
        time.sleep(poll_interval)
    else:
        print(f"✓ Analysis complete (status: {status})")
        break
else:
    print("⚠ Polling timeout")

# Step 3: Extract whitespace opportunities for AGT-03
ci_report = report

if ci_report.get("status") == "complete":
    whitespace = ci_report["whitespace_opportunities"]
    
    print(f"\n✓ Whitespace Opportunities (for AGT-03):")
    print(f"  Untapped channels: {whitespace['untapped_channels']}")
    print(f"  Messaging gaps: {whitespace['messaging_gaps']}")
    print(f"  Geographic gaps: {whitespace['geographic_gaps']}")
```

---

## Troubleshooting

### "Mandate not found"
- Verify mandate_id is correct and UUID format
- Ensure mandate belongs to your tenant
- Check mandate has not been deleted

### "Client profile not found"
- Verify mandate has a valid client_id
- Ensure client profile exists in database
- Check client belongs to your tenant

### "Competitor analysis failed"
- Check mandate/client data is complete
- Verify LLM service is accessible
- Review application logs for detailed error

### Job stuck in "pending" status
- Wait 10-30 seconds and poll again
- Check Phase 2 Celery task logs
- Verify MongoDB ci_reports collection is accessible

---

## Version History

| Version | Date | Notes |
|---------|------|-------|
| 1.0 | 2026-05-08 | Initial API reference for AGT-02 |
