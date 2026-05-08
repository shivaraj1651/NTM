# Mandate Analyst Agent (AGT-01) Design Spec

**Date:** 2026-05-08  
**Task:** TASK-004  
**Module:** `backend/app/agents/mandate_analyst.py` ONLY  
**Model:** Claude Sonnet 4-20250514 (max_tokens=2000)  

## 1. Overview

AGT-01 is the first agent in Phase 0. It validates incoming mandate dictionaries and produces a structured **Mandate Summary Card** with completeness scoring and contradiction detection.

**Input:** Raw mandate dict from API (nested structure with campaign_concept, budget, geography + metadata)  
**Output:** Pure JSON with validation results, contradictions, and mandate summary  
**Flow:** Python validation → LLM semantic analysis → merged output

---

## 2. Mandate Input Structure

```json
{
  "approval_date": "ISO string",
  "mandated_by": "string (role)",
  "version": "string",
  "status": "string",
  "campaign_concept": {
    "id": "string",
    "name": "string",
    "objective": "string",
    "description": "string",
    "target_audience": "string",
    "timeline": "string"
  },
  "budget": {
    "total_amount": "number",
    "currency": "string",
    "allocation_strategy": "string",
    "contingency_reserve": "string"
  },
  "geography": {
    "regions": "array of strings",
    "markets": "array of strings",
    "country_list": "array of strings"
  }
}
```

**Required fields (completeness check):**
- Top-level: `approval_date`, `mandated_by`, `version`, `status` (4 fields)
- campaign_concept: `id`, `name`, `objective`, `description`, `target_audience`, `timeline` (6 fields)
- budget: `total_amount`, `currency`, `allocation_strategy`, `contingency_reserve` (4 fields)
- geography: `regions`, `markets`, `country_list` (3 fields)
- **Total: 17 required fields**

---

## 3. Architecture: Hybrid Two-Phase Validation

### Phase 1: Python Validator (Synchronous)

**Class: `MandateValidator`**

Responsibilities:
- Check all required fields are present
- Validate basic types (numbers, strings, arrays, dates)
- Count missing fields
- Calculate raw completeness percentage: `(present_count / 17) * 100`

Returns dict:
```python
{
    "is_complete": bool,
    "missing_fields": list[str],  # e.g., ["budget.total_amount", "geography.markets"]
    "field_count": int,  # number of required fields present
    "field_total": int  # 17
}
```

### Phase 2: LLM Validator (Async)

**Function: `analyze_mandate_with_llm(mandate: dict, validation_result: dict) -> dict`**

Responsibilities:
- Detect contradictions (budget vs objective scope, timeline feasibility, geography-audience mismatch)
- Assess mandate quality and risk flags
- Synthesize Mandate Summary Card
- Return JSON with contradictions, summary, and final completeness_score

LLM prompt:
- System: "You are a mandate validation expert. Detect contradictions, assess quality, respond ONLY with JSON."
- User: Mandate dict + missing_fields list from Phase 1
- Max tokens: 2000
- Model: claude-sonnet-4-20250514

Returns dict:
```python
{
    "contradictions": list[str],  # e.g., ["budget too low for stated objective scope"]
    "mandate_summary": {
        "objective": "string",
        "budget_total": "number",
        "timeline": "string",
        "key_risks": list[str],
        "readiness": "Ready to proceed" | "Needs clarification"
    },
    "completeness_score": int  # 0-100, accounting for missing fields + contradictions
}
```

---

## 4. Main Agent Entry Point

**Function: `async def mandate_analyst_agent(mandate: dict) -> dict`**

Flow:
1. Instantiate `MandateValidator()`, call `validate(mandate)` → validation_result
2. Call `await analyze_mandate_with_llm(mandate, validation_result)` → llm_result
3. Merge results into final output
4. Return pure JSON

**Final Output Structure:**
```json
{
  "completeness_score": 85,
  "missing_fields": ["geography.markets"],
  "contradictions": ["budget allocation_strategy is too vague for stated objective"],
  "mandate_summary": {
    "objective": "Increase brand awareness among 18-45 urban demographic",
    "budget_total": 100000,
    "timeline": "2 months",
    "key_risks": [
      "Tight timeline for 50/50 digital/offline split",
      "Contingency reserve (10%) may be insufficient for offline execution"
    ],
    "readiness": "Ready to proceed with timeline clarification"
  },
  "validated_at": "2026-05-08T12:34:56Z"
}
```

**No markdown, no extra text. Pure JSON only.**

---

## 5. Implementation Details

### Dependencies
- `anthropic` SDK (AsyncAnthropic client)
- `pydantic` for type validation (optional, can use native Python)
- `json` for parsing LLM output
- `datetime` for timestamps

### Error Handling
- Missing top-level sections (campaign_concept, budget, geography): raise `ValueError`
- Invalid LLM JSON: log error, return fallback with `"error": "LLM parsing failed"`
- API call failure: propagate exception (Celery handles retry)

### Async Pattern
Uses `AsyncAnthropic()` for non-blocking LLM calls. Suitable for Celery task execution.

---

## 6. Testing Strategy

**File:** `backend/tests/agents/test_mandate_analyst.py`

**One happy-path test** (as required):
- Complete, valid mandate with all 17 required fields
- No contradictions
- Expected: `completeness_score = 100`, `missing_fields = []`, `contradictions = []`
- Verify output structure matches expected JSON shape

Additional test coverage (future):
- Missing required fields → missing_fields populated, score < 100
- Contradictory values → contradictions detected
- Invalid JSON from LLM → error handling
- Async execution with real API call

---

## 7. Integration Points

- **Input source:** FastAPI endpoint `POST /api/v1/mandates` (TASK-007, Phase 2)
- **Celery task:** Enqueued as async task after mandate creation
- **Output consumer:** Stored in database, returned to client via `GET /api/v1/mandates/{id}/summary-card`

---

## 8. Out of Scope

- Database persistence of mandate or summary card (handled by TASK-007)
- Multi-language support
- Complex financial modeling for budget contradictions
- User feedback loops for contradiction resolution

---

## Co-Author

Co-authored-by: katharguppe <katharguppe@users.noreply.github.com>
