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
