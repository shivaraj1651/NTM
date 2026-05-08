"""Tests for Mandate Analyst Agent (AGT-01)."""

import json
from unittest.mock import AsyncMock, patch

import pytest


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
            # Note: markets intentionally omitted for validation testing
        }
    }
    return mandate


def test_mandate_validator_complete_mandate(complete_mandate):
    """MandateValidator should pass complete mandate with score 100."""
    from backend.app.agents.mandate_analyst import MandateValidator

    validator = MandateValidator()
    result = validator.validate(complete_mandate)

    assert result["is_complete"] is True
    assert result["missing_fields"] == []
    assert result["field_count"] == 17
    assert result["field_total"] == 17


def test_mandate_validator_missing_fields(incomplete_mandate):
    """MandateValidator should detect missing fields."""
    from backend.app.agents.mandate_analyst import MandateValidator

    validator = MandateValidator()
    result = validator.validate(incomplete_mandate)

    assert result["is_complete"] is False
    assert "geography.markets" in result["missing_fields"]
    assert result["field_count"] == 16
    assert result["field_total"] == 17


@pytest.mark.asyncio
async def test_analyze_mandate_with_llm_happy_path(complete_mandate):
    """LLM analysis should return valid JSON with contradictions and summary."""
    from backend.app.agents.mandate_analyst import analyze_mandate_with_llm, MandateValidator

    validator = MandateValidator()
    validation_result = validator.validate(complete_mandate)

    # Mock LLM response
    mock_response = {
        "contradictions": [],
        "mandate_summary": {
            "objective": "Increase brand awareness among 18-45 urban demographic",
            "budget_total": "$100,000 USD",
            "timeline": "2 months (June-July 2026)",
            "key_risks": [],
            "readiness": "Ready to proceed"
        },
        "completeness_score": 100
    }

    mock_message = AsyncMock()
    mock_message.content = [AsyncMock(text=json.dumps(mock_response))]

    with patch("backend.app.agents.mandate_analyst.AsyncAnthropic") as mock_client_class:
        mock_client = AsyncMock()
        mock_client_class.return_value = mock_client
        mock_client.messages.create = AsyncMock(return_value=mock_message)

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


@pytest.mark.asyncio
async def test_mandate_analyst_agent_complete_mandate(complete_mandate):
    """Main agent should orchestrate validation and LLM analysis."""
    from backend.app.agents.mandate_analyst import mandate_analyst_agent

    # Mock LLM response
    mock_response = {
        "contradictions": [],
        "mandate_summary": {
            "objective": "Increase brand awareness among 18-45 urban demographic",
            "budget_total": "$100,000 USD",
            "timeline": "2 months (June-July 2026)",
            "key_risks": [],
            "readiness": "Ready to proceed"
        },
        "completeness_score": 100
    }

    mock_message = AsyncMock()
    mock_message.content = [AsyncMock(text=json.dumps(mock_response))]

    with patch("backend.app.agents.mandate_analyst.AsyncAnthropic") as mock_client_class:
        mock_client = AsyncMock()
        mock_client_class.return_value = mock_client
        mock_client.messages.create = AsyncMock(return_value=mock_message)

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


@pytest.mark.asyncio
async def test_mandate_analyst_agent_incomplete_mandate(incomplete_mandate):
    """Agent should detect missing fields and report in output."""
    from backend.app.agents.mandate_analyst import mandate_analyst_agent

    # Mock LLM response
    mock_response = {
        "contradictions": [],
        "mandate_summary": {
            "objective": "Increase brand awareness among 18-45 urban demographic",
            "budget_total": "$100,000 USD",
            "timeline": "2 months (June-July 2026)",
            "key_risks": ["Missing required geography.markets field"],
            "readiness": "Needs clarification"
        },
        "completeness_score": 94
    }

    mock_message = AsyncMock()
    mock_message.content = [AsyncMock(text=json.dumps(mock_response))]

    with patch("backend.app.agents.mandate_analyst.AsyncAnthropic") as mock_client_class:
        mock_client = AsyncMock()
        mock_client_class.return_value = mock_client
        mock_client.messages.create = AsyncMock(return_value=mock_message)

        result = await mandate_analyst_agent(incomplete_mandate)

    # Should detect missing field
    assert "geography.markets" in result["missing_fields"]
    assert len(result["missing_fields"]) == 1
    assert result["completeness_score"] < 100
