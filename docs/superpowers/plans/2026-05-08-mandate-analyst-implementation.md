# Mandate Analyst Agent (AGT-01) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement AGT-01 Mandate Analyst Agent with hybrid two-phase validation (Python + LLM) and produce structured mandate summary cards.

**Architecture:** Two-phase validation where Python validates field completeness deterministically, then async LLM detects contradictions and synthesizes the summary card. Single entry point `mandate_analyst_agent()` orchestrates both phases and returns pure JSON output.

**Tech Stack:** Python 3.12, FastAPI, Anthropic SDK (AsyncAnthropic), pytest, Pydantic

---

## File Structure

```
backend/app/agents/
├── __init__.py (new)
└── mandate_analyst.py (new)

backend/tests/agents/
├── __init__.py (new)
└── test_mandate_analyst.py (new)
```

**Responsibilities:**
- `mandate_analyst.py`: MandateValidator class, analyze_mandate_with_llm() function, mandate_analyst_agent() entry point
- `test_mandate_analyst.py`: Unit tests for validator and agent (happy path + edge cases)

---

### Task 1: Set Up Package Structure

**Files:**
- Create: `backend/app/agents/__init__.py`
- Create: `backend/tests/agents/__init__.py`

- [ ] **Step 1: Create agents package init**

```bash
touch backend/app/agents/__init__.py
```

Content for `backend/app/agents/__init__.py`:
```python
"""
Agents module for NTM.

Agents are long-running AI-powered processes that analyze, validate, and
generate strategic content. Each agent has a single responsibility and
produces structured JSON output.
"""

__all__ = []
```

- [ ] **Step 2: Create tests/agents package init**

```bash
touch backend/tests/agents/__init__.py
```

Content for `backend/tests/agents/__init__.py`:
```python
"""Tests for agents module."""
```

- [ ] **Step 3: Commit**

```bash
git add backend/app/agents/__init__.py backend/tests/agents/__init__.py
git commit -m "feat: create agents package structure"
```

---

### Task 2: Write Test File with Imports

**Files:**
- Create: `backend/tests/agents/test_mandate_analyst.py`

- [ ] **Step 1: Create test file with imports and fixtures**

```bash
touch backend/tests/agents/test_mandate_analyst.py
```

Content for `backend/tests/agents/test_mandate_analyst.py`:
```python
"""Tests for Mandate Analyst Agent (AGT-01)."""

import pytest
import json
from datetime import datetime, timezone


@pytest.fixture
def complete_mandate():
    """Complete, valid mandate with all 17 required fields."""
    return {
        "approval_date": "2026-05-08",
        "mandated_by": "cmo",
        "version": "1.0",
        "status": "approved",
        "campaign_concept": {
            "id": "cc-001",
            "name": "Summer Refresh",
            "objective": "Increase brand awareness among 18-45 urban demographic",
            "description": "Q2 campaign refresh across digital and offline channels",
            "target_audience": "18-45, urban professionals",
            "timeline": "2 months (June-July 2026)"
        },
        "budget": {
            "total_amount": 100000,
            "currency": "USD",
            "allocation_strategy": "50% digital, 50% offline",
            "contingency_reserve": "10%"
        },
        "geography": {
            "regions": ["North America"],
            "markets": ["US", "Canada"],
            "country_list": ["US", "CA"]
        }
    }


@pytest.fixture
def incomplete_mandate():
    """Mandate missing geography.markets field."""
    mandate = {
        "approval_date": "2026-05-08",
        "mandated_by": "cmo",
        "version": "1.0",
        "status": "approved",
        "campaign_concept": {
            "id": "cc-001",
            "name": "Summer Refresh",
            "objective": "Increase brand awareness",
            "description": "Q2 campaign refresh",
            "target_audience": "18-45, urban",
            "timeline": "2 months"
        },
        "budget": {
            "total_amount": 100000,
            "currency": "USD",
            "allocation_strategy": "50% digital, 50% offline",
            "contingency_reserve": "10%"
        },
        "geography": {
            "regions": ["North America"],
            "country_list": ["US", "CA"]
            # Missing: markets
        }
    }
    return mandate
```

- [ ] **Step 2: Commit**

```bash
git add backend/tests/agents/test_mandate_analyst.py
git commit -m "test: create mandate analyst test file with fixtures"
```

---

### Task 3: Implement MandateValidator Class

**Files:**
- Create: `backend/app/agents/mandate_analyst.py`

- [ ] **Step 1: Write failing test for field validation**

Add to `backend/tests/agents/test_mandate_analyst.py`:
```python
def test_mandate_validator_complete_mandate(complete_mandate):
    """MandateValidator should pass complete mandate with score 100."""
    from backend.app.agents.mandate_analyst import MandateValidator
    
    validator = MandateValidator()
    result = validator.validate(complete_mandate)
    
    assert result["is_complete"] is True
    assert result["missing_fields"] == []
    assert result["field_count"] == 17
    assert result["field_total"] == 17
```

- [ ] **Step 2: Run test to verify it fails**

```bash
pytest backend/tests/agents/test_mandate_analyst.py::test_mandate_validator_complete_mandate -v
```

Expected output:
```
FAILED - ModuleNotFoundError: No module named 'backend.app.agents.mandate_analyst'
```

- [ ] **Step 3: Write MandateValidator class**

Create `backend/app/agents/mandate_analyst.py`:
```python
"""
Mandate Analyst Agent (AGT-01).

Validates mandates for completeness and contradictions, produces structured summary cards.
"""

from typing import Dict, List, Any


class MandateValidator:
    """
    Validates mandate dict for required fields and basic type checks.
    
    Required fields (17 total):
    - Top-level: approval_date, mandated_by, version, status (4)
    - campaign_concept: id, name, objective, description, target_audience, timeline (6)
    - budget: total_amount, currency, allocation_strategy, contingency_reserve (4)
    - geography: regions, markets, country_list (3)
    """
    
    REQUIRED_FIELDS = {
        "top_level": ["approval_date", "mandated_by", "version", "status"],
        "campaign_concept": ["id", "name", "objective", "description", "target_audience", "timeline"],
        "budget": ["total_amount", "currency", "allocation_strategy", "contingency_reserve"],
        "geography": ["regions", "markets", "country_list"]
    }
    
    def __init__(self):
        """Initialize validator."""
        self.total_required = sum(len(v) for v in self.REQUIRED_FIELDS.values())
    
    def validate(self, mandate: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate mandate for required fields.
        
        Args:
            mandate: Raw mandate dict
        
        Returns:
            Dict with is_complete, missing_fields, field_count, field_total
        """
        missing_fields: List[str] = []
        field_count = 0
        
        # Check top-level fields
        for field in self.REQUIRED_FIELDS["top_level"]:
            if field in mandate and mandate[field] is not None:
                field_count += 1
            else:
                missing_fields.append(field)
        
        # Check nested sections
        for section, fields in self.REQUIRED_FIELDS.items():
            if section == "top_level":
                continue
            
            if section not in mandate or mandate[section] is None:
                # Entire section missing
                for field in fields:
                    missing_fields.append(f"{section}.{field}")
            else:
                section_data = mandate[section]
                for field in fields:
                    if field in section_data and section_data[field] is not None:
                        field_count += 1
                    else:
                        missing_fields.append(f"{section}.{field}")
        
        return {
            "is_complete": len(missing_fields) == 0,
            "missing_fields": missing_fields,
            "field_count": field_count,
            "field_total": self.total_required
        }
```

- [ ] **Step 4: Run test to verify it passes**

```bash
pytest backend/tests/agents/test_mandate_analyst.py::test_mandate_validator_complete_mandate -v
```

Expected output:
```
PASSED test_mandate_validator_complete_mandate
```

- [ ] **Step 5: Write test for incomplete mandate**

Add to `backend/tests/agents/test_mandate_analyst.py`:
```python
def test_mandate_validator_missing_fields(incomplete_mandate):
    """MandateValidator should detect missing fields."""
    from backend.app.agents.mandate_analyst import MandateValidator
    
    validator = MandateValidator()
    result = validator.validate(incomplete_mandate)
    
    assert result["is_complete"] is False
    assert "geography.markets" in result["missing_fields"]
    assert result["field_count"] == 16
    assert result["field_total"] == 17
```

- [ ] **Step 6: Run test to verify it passes**

```bash
pytest backend/tests/agents/test_mandate_analyst.py::test_mandate_validator_missing_fields -v
```

Expected output:
```
PASSED test_mandate_validator_missing_fields
```

- [ ] **Step 7: Commit**

```bash
git add backend/app/agents/mandate_analyst.py backend/tests/agents/test_mandate_analyst.py
git commit -m "feat: implement MandateValidator class with field validation"
```

---

### Task 4: Implement LLM Analysis Function

**Files:**
- Modify: `backend/app/agents/mandate_analyst.py`
- Modify: `backend/tests/agents/test_mandate_analyst.py`

- [ ] **Step 1: Write failing test for LLM analysis**

Add to `backend/tests/agents/test_mandate_analyst.py`:
```python
@pytest.mark.asyncio
async def test_analyze_mandate_with_llm_happy_path(complete_mandate):
    """LLM analysis should return valid JSON with contradictions and summary."""
    from backend.app.agents.mandate_analyst import analyze_mandate_with_llm, MandateValidator
    
    validator = MandateValidator()
    validation_result = validator.validate(complete_mandate)
    
    result = await analyze_mandate_with_llm(complete_mandate, validation_result)
    
    # Verify output structure
    assert "contradictions" in result
    assert isinstance(result["contradictions"], list)
    assert "mandate_summary" in result
    assert "completeness_score" in result
    assert isinstance(result["completeness_score"], int)
    assert 0 <= result["completeness_score"] <= 100
    
    # Verify mandate_summary structure
    summary = result["mandate_summary"]
    assert "objective" in summary
    assert "budget_total" in summary
    assert "timeline" in summary
    assert "key_risks" in summary
    assert "readiness" in summary
```

- [ ] **Step 2: Run test to verify it fails**

```bash
pytest backend/tests/agents/test_mandate_analyst.py::test_analyze_mandate_with_llm_happy_path -v
```

Expected output:
```
FAILED - ImportError: cannot import name 'analyze_mandate_with_llm'
```

- [ ] **Step 3: Implement analyze_mandate_with_llm function**

Add to `backend/app/agents/mandate_analyst.py`:
```python
import json
from anthropic import AsyncAnthropic


async def analyze_mandate_with_llm(mandate: Dict[str, Any], validation_result: Dict[str, Any]) -> Dict[str, Any]:
    """
    Call Claude Sonnet to detect contradictions and produce summary card.
    
    Args:
        mandate: Full mandate dict
        validation_result: Output from MandateValidator
    
    Returns:
        Dict with contradictions, mandate_summary, completeness_score
    """
    client = AsyncAnthropic()
    
    system_prompt = """You are a mandate validation expert. Analyze the provided mandate for:
1. Contradictions between sections (budget vs timeline, geography vs audience)
2. Risk flags (unrealistic timelines, insufficient budget, scope creep)
3. Completeness and strategic intent clarity

Respond ONLY with valid JSON, no markdown. Do not wrap in code blocks.

Structure your response exactly as:
{
  "contradictions": ["list", "of", "contradiction", "strings"],
  "mandate_summary": {
    "objective": "clear statement of mandate objective",
    "budget_total": "budget amount and currency",
    "timeline": "timeline description",
    "key_risks": ["list", "of", "risk", "flags"],
    "readiness": "Ready to proceed" or "Needs clarification"
  },
  "completeness_score": <integer 0-100>
}"""

    user_prompt = f"""Analyze this mandate for contradictions and quality.

Missing fields: {validation_result['missing_fields']}

Mandate data:
{json.dumps(mandate, indent=2)}"""

    response = await client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=2000,
        system=system_prompt,
        messages=[{"role": "user", "content": user_prompt}]
    )
    
    # Parse LLM response
    response_text = response.content[0].text
    try:
        result = json.loads(response_text)
    except json.JSONDecodeError:
        # Fallback if LLM response isn't valid JSON
        return {
            "contradictions": [],
            "mandate_summary": {
                "objective": "Unable to parse LLM response",
                "budget_total": "N/A",
                "timeline": "N/A",
                "key_risks": ["LLM parsing failed"],
                "readiness": "Needs clarification"
            },
            "completeness_score": 0,
            "error": "LLM response was not valid JSON"
        }
    
    return result
```

- [ ] **Step 4: Run test to verify it passes**

```bash
pytest backend/tests/agents/test_mandate_analyst.py::test_analyze_mandate_with_llm_happy_path -v
```

Expected output:
```
PASSED test_analyze_mandate_with_llm_happy_path
```

Note: This test requires ANTHROPIC_API_KEY in environment. If not set, the test will fail with auth error. That's expected for now.

- [ ] **Step 5: Commit**

```bash
git add backend/app/agents/mandate_analyst.py backend/tests/agents/test_mandate_analyst.py
git commit -m "feat: implement LLM analysis function with async Anthropic SDK"
```

---

### Task 5: Implement Main Agent Entry Point

**Files:**
- Modify: `backend/app/agents/mandate_analyst.py`
- Modify: `backend/tests/agents/test_mandate_analyst.py`

- [ ] **Step 1: Write failing test for mandate_analyst_agent**

Add to `backend/tests/agents/test_mandate_analyst.py`:
```python
@pytest.mark.asyncio
async def test_mandate_analyst_agent_complete_mandate(complete_mandate):
    """Main agent should orchestrate validation and LLM analysis."""
    from backend.app.agents.mandate_analyst import mandate_analyst_agent
    
    result = await mandate_analyst_agent(complete_mandate)
    
    # Verify output structure
    assert "completeness_score" in result
    assert "missing_fields" in result
    assert "contradictions" in result
    assert "mandate_summary" in result
    assert "validated_at" in result
    
    # Verify types
    assert isinstance(result["completeness_score"], int)
    assert isinstance(result["missing_fields"], list)
    assert isinstance(result["contradictions"], list)
    assert isinstance(result["mandate_summary"], dict)
    assert isinstance(result["validated_at"], str)
    
    # For complete mandate, should have no missing fields
    assert result["missing_fields"] == []
```

- [ ] **Step 2: Run test to verify it fails**

```bash
pytest backend/tests/agents/test_mandate_analyst.py::test_mandate_analyst_agent_complete_mandate -v
```

Expected output:
```
FAILED - ImportError: cannot import name 'mandate_analyst_agent'
```

- [ ] **Step 3: Implement mandate_analyst_agent function**

Add to `backend/app/agents/mandate_analyst.py`:
```python
async def mandate_analyst_agent(mandate: Dict[str, Any]) -> Dict[str, Any]:
    """
    AGT-01 Mandate Analyst Agent entry point.
    
    Orchestrates two-phase validation:
    1. Python validator: checks required fields
    2. LLM validator: detects contradictions and synthesizes summary
    
    Args:
        mandate: Raw mandate dict from API
    
    Returns:
        Pure JSON output with validation results and summary card
    """
    # Phase 1: Python validation
    validator = MandateValidator()
    validation_result = validator.validate(mandate)
    
    # Phase 2: LLM analysis
    llm_result = await analyze_mandate_with_llm(mandate, validation_result)
    
    # Merge results
    final_output = {
        "completeness_score": llm_result["completeness_score"],
        "missing_fields": validation_result["missing_fields"],
        "contradictions": llm_result.get("contradictions", []),
        "mandate_summary": llm_result.get("mandate_summary", {}),
        "validated_at": datetime.now(timezone.utc).isoformat()
    }
    
    return final_output
```

- [ ] **Step 4: Run test to verify it passes**

```bash
pytest backend/tests/agents/test_mandate_analyst.py::test_mandate_analyst_agent_complete_mandate -v
```

Expected output:
```
PASSED test_mandate_analyst_agent_complete_mandate
```

- [ ] **Step 5: Write test for incomplete mandate through agent**

Add to `backend/tests/agents/test_mandate_analyst.py`:
```python
@pytest.mark.asyncio
async def test_mandate_analyst_agent_incomplete_mandate(incomplete_mandate):
    """Agent should detect missing fields and report in output."""
    from backend.app.agents.mandate_analyst import mandate_analyst_agent
    
    result = await mandate_analyst_agent(incomplete_mandate)
    
    # Should detect missing field
    assert "geography.markets" in result["missing_fields"]
    assert len(result["missing_fields"]) == 1
    assert result["completeness_score"] < 100
```

- [ ] **Step 6: Run test to verify it passes**

```bash
pytest backend/tests/agents/test_mandate_analyst.py::test_mandate_analyst_agent_incomplete_mandate -v
```

Expected output:
```
PASSED test_mandate_analyst_agent_incomplete_mandate
```

- [ ] **Step 7: Commit**

```bash
git add backend/app/agents/mandate_analyst.py backend/tests/agents/test_mandate_analyst.py
git commit -m "feat: implement mandate_analyst_agent entry point with orchestration"
```

---

### Task 6: Export Agent in Package __init__

**Files:**
- Modify: `backend/app/agents/__init__.py`

- [ ] **Step 1: Update __init__.py to export agent**

Update `backend/app/agents/__init__.py`:
```python
"""
Agents module for NTM.

Agents are long-running AI-powered processes that analyze, validate, and
generate strategic content. Each agent has a single responsibility and
produces structured JSON output.
"""

from backend.app.agents.mandate_analyst import (
    MandateValidator,
    analyze_mandate_with_llm,
    mandate_analyst_agent
)

__all__ = [
    "MandateValidator",
    "analyze_mandate_with_llm",
    "mandate_analyst_agent"
]
```

- [ ] **Step 2: Verify imports work**

```bash
python -c "from backend.app.agents import mandate_analyst_agent; print('Import successful')"
```

Expected output:
```
Import successful
```

- [ ] **Step 3: Run all agent tests to ensure nothing broke**

```bash
pytest backend/tests/agents/test_mandate_analyst.py -v
```

Expected output:
```
PASSED test_mandate_validator_complete_mandate
PASSED test_mandate_validator_missing_fields
PASSED test_analyze_mandate_with_llm_happy_path
PASSED test_mandate_analyst_agent_complete_mandate
PASSED test_mandate_analyst_agent_incomplete_mandate
```

- [ ] **Step 4: Commit**

```bash
git add backend/app/agents/__init__.py
git commit -m "feat: export mandate analyst agent components"
```

---

### Task 7: Final Verification and Summary

**Files:**
- No new files

- [ ] **Step 1: Run full test suite for agents**

```bash
pytest backend/tests/agents/ -v --tb=short
```

Expected: All tests pass (5 tests)

- [ ] **Step 2: Verify output is pure JSON (no markdown)**

Test that agent output contains no markdown by checking a quick manual test:
```bash
python -c "
import asyncio
from backend.app.agents import mandate_analyst_agent

mandate = {
    'approval_date': '2026-05-08',
    'mandated_by': 'cmo',
    'version': '1.0',
    'status': 'approved',
    'campaign_concept': {
        'id': 'cc-001',
        'name': 'Test',
        'objective': 'Test',
        'description': 'Test',
        'target_audience': 'Test',
        'timeline': '2 months'
    },
    'budget': {
        'total_amount': 100000,
        'currency': 'USD',
        'allocation_strategy': 'Test',
        'contingency_reserve': '10%'
    },
    'geography': {
        'regions': ['NA'],
        'markets': ['US'],
        'country_list': ['US']
    }
}

result = asyncio.run(mandate_analyst_agent(mandate))
print(type(result))  # Should be dict
print('validated_at' in result)  # Should be True
"
```

- [ ] **Step 3: Verify module structure matches spec**

Check:
- `backend/app/agents/mandate_analyst.py` exists ✓
- Contains `MandateValidator` class ✓
- Contains `analyze_mandate_with_llm()` function ✓
- Contains `mandate_analyst_agent()` function ✓
- Uses AsyncAnthropic for non-blocking calls ✓
- Returns pure JSON output ✓

- [ ] **Step 4: Final commit (if any uncommitted changes)**

```bash
git status
```

If clean, skip. If not, commit remaining changes.

---

## Self-Review Checklist

**Spec Coverage:**
- ✓ MandateValidator class (field validation, completeness scoring)
- ✓ analyze_mandate_with_llm function (LLM analysis, contradiction detection)
- ✓ mandate_analyst_agent entry point (orchestration)
- ✓ Pure JSON output with validated_at timestamp
- ✓ Error handling for invalid JSON from LLM
- ✓ Happy-path test with complete mandate

**Placeholder Scan:**
- ✓ No TBD, TODO, or "implement later" in plan
- ✓ All code steps include complete, functional code
- ✓ All test steps include actual test code
- ✓ All commands are exact with expected output

**Type Consistency:**
- ✓ MandateValidator.validate() returns dict with expected keys
- ✓ analyze_mandate_with_llm() returns dict matching LLM response structure
- ✓ mandate_analyst_agent() merges both correctly
- ✓ All field names consistent throughout (contradictions, missing_fields, completeness_score, mandate_summary, validated_at)

**No Gaps:**
- ✓ All 7 required fields defined and validated
- ✓ Test fixtures cover complete and incomplete mandates
- ✓ LLM integration tested
- ✓ Package exports tested
- ✓ Module boundary respected (TASK-004 scope)
