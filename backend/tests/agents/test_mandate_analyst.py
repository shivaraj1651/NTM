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
