"""Tests for Competitive Intelligence Agent (AGT-02, Phase 1 - Competitor Identification)."""

import json
from datetime import datetime
from unittest.mock import AsyncMock, patch

import pytest


@pytest.fixture
def sample_mandate():
    """Complete, valid mandate for CI testing."""
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
def sample_client_profile():
    """Complete, valid client profile for CI testing."""
    return {
        "id": "client-001",
        "name": "ShoeNow Inc.",
        "industry": "Athletic Footwear",
        "existing_competitors": ["Nike", "Adidas", "Puma"],
        "annual_revenue": 500000000,
        "market_segment": "Premium athletic shoes"
    }


def test_identify_competitors_sync_happy_path(sample_mandate, sample_client_profile):
    """Competitor identification should return valid List[CompetitorIdentity] with correct structure."""
    import asyncio
    from backend.app.agents.competitive_intel import identify_competitors_sync

    # Mock LLM response with valid competitor list
    mock_response = {
        "competitors": [
            {"name": "Nike", "confidence": 95},
            {"name": "Adidas", "confidence": 92},
            {"name": "Puma", "confidence": 88},
            {"name": "New Balance", "confidence": 85},
            {"name": "Asics", "confidence": 82},
            {"name": "Saucony", "confidence": 78},
            {"name": "Brooks", "confidence": 75},
            {"name": "HOKA", "confidence": 72},
            {"name": "On Running", "confidence": 70},
            {"name": "Salomon", "confidence": 68},
        ]
    }

    mock_message = AsyncMock()
    mock_message.content = [AsyncMock(text=json.dumps(mock_response))]

    with patch("backend.app.agents.competitive_intel.AsyncAnthropic") as mock_client_class:
        mock_client = AsyncMock()
        mock_client_class.return_value = mock_client
        mock_client.messages.create = AsyncMock(return_value=mock_message)

        result = asyncio.run(
            identify_competitors_sync(sample_mandate, sample_client_profile)
        )

    # Verify output is List[CompetitorIdentity]
    assert isinstance(result, list)
    assert len(result) == 10

    # Verify each item is CompetitorIdentity with correct structure
    for competitor in result:
        assert hasattr(competitor, "name")
        assert hasattr(competitor, "confidence")
        assert isinstance(competitor.name, str)
        assert isinstance(competitor.confidence, int)
        assert 0 <= competitor.confidence <= 100

    # Verify specific expected values
    assert result[0].name == "Nike"
    assert result[0].confidence == 95
    assert result[1].name == "Adidas"
    assert result[1].confidence == 92


def test_identify_competitors_sync_invalid_llm_response(sample_mandate, sample_client_profile):
    """Competitor identification should raise ValueError when LLM returns malformed JSON."""
    import asyncio
    from backend.app.agents.competitive_intel import identify_competitors_sync

    # Mock invalid JSON response
    mock_message = AsyncMock()
    mock_message.content = [AsyncMock(text="not valid json {]")]

    with patch("backend.app.agents.competitive_intel.AsyncAnthropic") as mock_client_class:
        mock_client = AsyncMock()
        mock_client_class.return_value = mock_client
        mock_client.messages.create = AsyncMock(return_value=mock_message)

        with pytest.raises(ValueError) as exc_info:
            asyncio.run(
                identify_competitors_sync(sample_mandate, sample_client_profile)
            )

        assert "not valid JSON" in str(exc_info.value) or "LLM response was not valid JSON" in str(exc_info.value)


def test_identify_competitors_sync_too_many_competitors(sample_mandate, sample_client_profile):
    """Competitor identification should raise ValueError when LLM returns >15 competitors."""
    import asyncio
    from backend.app.agents.competitive_intel import identify_competitors_sync

    # Mock response with too many competitors (16 > 15 limit)
    competitors_list = [
        {"name": f"Competitor{i}", "confidence": 100 - i} for i in range(16)
    ]
    mock_response = {"competitors": competitors_list}

    mock_message = AsyncMock()
    mock_message.content = [AsyncMock(text=json.dumps(mock_response))]

    with patch("backend.app.agents.competitive_intel.AsyncAnthropic") as mock_client_class:
        mock_client = AsyncMock()
        mock_client_class.return_value = mock_client
        mock_client.messages.create = AsyncMock(return_value=mock_message)

        with pytest.raises(ValueError) as exc_info:
            asyncio.run(
                identify_competitors_sync(sample_mandate, sample_client_profile)
            )

        assert "Competitor count must be 5-15" in str(exc_info.value)


def test_identify_competitors_sync_too_few_competitors(sample_mandate, sample_client_profile):
    """Competitor identification should raise ValueError when LLM returns <5 competitors."""
    import asyncio
    from backend.app.agents.competitive_intel import identify_competitors_sync

    # Mock response with too few competitors (4 < 5 minimum)
    mock_response = {
        "competitors": [
            {"name": "Nike", "confidence": 95},
            {"name": "Adidas", "confidence": 92},
            {"name": "Puma", "confidence": 88},
            {"name": "New Balance", "confidence": 85},
        ]
    }

    mock_message = AsyncMock()
    mock_message.content = [AsyncMock(text=json.dumps(mock_response))]

    with patch("backend.app.agents.competitive_intel.AsyncAnthropic") as mock_client_class:
        mock_client = AsyncMock()
        mock_client_class.return_value = mock_client
        mock_client.messages.create = AsyncMock(return_value=mock_message)

        with pytest.raises(ValueError) as exc_info:
            asyncio.run(
                identify_competitors_sync(sample_mandate, sample_client_profile)
            )

        assert "Competitor count must be 5-15" in str(exc_info.value)


def test_identify_competitors_sync_missing_competitors_key(sample_mandate, sample_client_profile):
    """Competitor identification should raise ValueError when response missing 'competitors' key."""
    import asyncio
    from backend.app.agents.competitive_intel import identify_competitors_sync

    # Mock response missing 'competitors' key
    mock_response = {"data": [{"name": "Nike", "confidence": 95}]}

    mock_message = AsyncMock()
    mock_message.content = [AsyncMock(text=json.dumps(mock_response))]

    with patch("backend.app.agents.competitive_intel.AsyncAnthropic") as mock_client_class:
        mock_client = AsyncMock()
        mock_client_class.return_value = mock_client
        mock_client.messages.create = AsyncMock(return_value=mock_message)

        with pytest.raises(ValueError) as exc_info:
            asyncio.run(
                identify_competitors_sync(sample_mandate, sample_client_profile)
            )

        assert "missing 'competitors' key" in str(exc_info.value)


def test_identify_competitors_sync_invalid_confidence_score(sample_mandate, sample_client_profile):
    """Competitor identification should raise ValueError when confidence is not 0-100."""
    import asyncio
    from backend.app.agents.competitive_intel import identify_competitors_sync

    # Mock response with confidence > 100
    mock_response = {
        "competitors": [
            {"name": "Nike", "confidence": 105},  # Invalid: > 100
            {"name": "Adidas", "confidence": 92},
            {"name": "Puma", "confidence": 88},
            {"name": "New Balance", "confidence": 85},
            {"name": "Asics", "confidence": 82},
        ]
    }

    mock_message = AsyncMock()
    mock_message.content = [AsyncMock(text=json.dumps(mock_response))]

    with patch("backend.app.agents.competitive_intel.AsyncAnthropic") as mock_client_class:
        mock_client = AsyncMock()
        mock_client_class.return_value = mock_client
        mock_client.messages.create = AsyncMock(return_value=mock_message)

        with pytest.raises(ValueError) as exc_info:
            asyncio.run(
                identify_competitors_sync(sample_mandate, sample_client_profile)
            )

        assert "confidence must be integer 0-100" in str(exc_info.value)


def test_identify_competitors_sync_missing_name_field(sample_mandate, sample_client_profile):
    """Competitor identification should raise ValueError when competitor missing 'name' field."""
    import asyncio
    from backend.app.agents.competitive_intel import identify_competitors_sync

    # Mock response with missing name field
    mock_response = {
        "competitors": [
            {"confidence": 95},  # Missing 'name'
            {"name": "Adidas", "confidence": 92},
            {"name": "Puma", "confidence": 88},
            {"name": "New Balance", "confidence": 85},
            {"name": "Asics", "confidence": 82},
        ]
    }

    mock_message = AsyncMock()
    mock_message.content = [AsyncMock(text=json.dumps(mock_response))]

    with patch("backend.app.agents.competitive_intel.AsyncAnthropic") as mock_client_class:
        mock_client = AsyncMock()
        mock_client_class.return_value = mock_client
        mock_client.messages.create = AsyncMock(return_value=mock_message)

        with pytest.raises(ValueError) as exc_info:
            asyncio.run(
                identify_competitors_sync(sample_mandate, sample_client_profile)
            )

        assert "missing 'name' field" in str(exc_info.value)


def test_identify_competitors_sync_empty_api_response(sample_mandate, sample_client_profile):
    """Competitor identification should raise ValueError when LLM returns empty response."""
    import asyncio
    from backend.app.agents.competitive_intel import identify_competitors_sync

    # Mock empty response
    with patch("backend.app.agents.competitive_intel.AsyncAnthropic") as mock_client_class:
        mock_client = AsyncMock()
        mock_client_class.return_value = mock_client
        mock_client.messages.create.return_value = AsyncMock(content=[])

        with pytest.raises(ValueError) as exc_info:
            asyncio.run(
                identify_competitors_sync(sample_mandate, sample_client_profile)
            )

        assert "empty response" in str(exc_info.value)


@pytest.mark.asyncio
async def test_competitive_intel_agent_happy_path(sample_mandate, sample_client_profile):
    """Full agent orchestration should return CIReportInitial with valid structure."""
    from backend.app.agents.competitive_intel import competitive_intel_agent

    # Mock LLM response
    mock_response = {
        "competitors": [
            {"name": "Nike", "confidence": 95},
            {"name": "Adidas", "confidence": 92},
            {"name": "Puma", "confidence": 88},
            {"name": "New Balance", "confidence": 85},
            {"name": "Asics", "confidence": 82},
            {"name": "Saucony", "confidence": 78},
            {"name": "Brooks", "confidence": 75},
            {"name": "HOKA", "confidence": 72},
            {"name": "On Running", "confidence": 70},
            {"name": "Salomon", "confidence": 68},
        ]
    }

    mock_message = AsyncMock()
    mock_message.content = [AsyncMock(text=json.dumps(mock_response))]

    with patch("backend.app.agents.competitive_intel.AsyncAnthropic") as mock_client_class:
        mock_client = AsyncMock()
        mock_client_class.return_value = mock_client
        mock_client.messages.create = AsyncMock(return_value=mock_message)

        result = await competitive_intel_agent(
            mandate=sample_mandate,
            client_profile=sample_client_profile,
            mandate_id="mandate-001",
            tenant_id="tenant-001"
        )

    # Verify output structure
    assert hasattr(result, "job_id")
    assert hasattr(result, "mandate_id")
    assert hasattr(result, "competitors")
    assert hasattr(result, "status")
    assert hasattr(result, "created_at")

    # Verify types
    assert isinstance(result.job_id, str)
    assert isinstance(result.mandate_id, str)
    assert isinstance(result.competitors, list)
    assert isinstance(result.status, str)
    assert isinstance(result.created_at, datetime)

    # Verify values
    assert result.mandate_id == "mandate-001"
    assert result.status == "pending"
    assert len(result.competitors) == 10

    # Verify competitor items
    for competitor in result.competitors:
        assert hasattr(competitor, "name")
        assert hasattr(competitor, "confidence")
        assert isinstance(competitor.name, str)
        assert isinstance(competitor.confidence, int)


@pytest.mark.asyncio
async def test_competitive_intel_agent_with_validation_errors(sample_mandate, sample_client_profile):
    """Agent should propagate ValueError when competitor identification fails."""
    from backend.app.agents.competitive_intel import competitive_intel_agent

    # Mock response with too few competitors (should trigger validation error)
    mock_response = {
        "competitors": [
            {"name": "Nike", "confidence": 95},
            {"name": "Adidas", "confidence": 92},
        ]
    }

    mock_message = AsyncMock()
    mock_message.content = [AsyncMock(text=json.dumps(mock_response))]

    with patch("backend.app.agents.competitive_intel.AsyncAnthropic") as mock_client_class:
        mock_client = AsyncMock()
        mock_client_class.return_value = mock_client
        mock_client.messages.create = AsyncMock(return_value=mock_message)

        with pytest.raises(ValueError) as exc_info:
            await competitive_intel_agent(
                mandate=sample_mandate,
                client_profile=sample_client_profile,
                mandate_id="mandate-001",
                tenant_id="tenant-001"
            )

        assert "Competitor identification failed" in str(exc_info.value) or "Competitor count must be 5-15" in str(exc_info.value)


@pytest.mark.asyncio
async def test_competitive_intel_agent_boundary_5_competitors(sample_mandate, sample_client_profile):
    """Agent should accept exactly 5 competitors (minimum valid count)."""
    from backend.app.agents.competitive_intel import competitive_intel_agent

    # Mock response with exactly 5 competitors (boundary condition)
    mock_response = {
        "competitors": [
            {"name": "Nike", "confidence": 95},
            {"name": "Adidas", "confidence": 92},
            {"name": "Puma", "confidence": 88},
            {"name": "New Balance", "confidence": 85},
            {"name": "Asics", "confidence": 82},
        ]
    }

    mock_message = AsyncMock()
    mock_message.content = [AsyncMock(text=json.dumps(mock_response))]

    with patch("backend.app.agents.competitive_intel.AsyncAnthropic") as mock_client_class:
        mock_client = AsyncMock()
        mock_client_class.return_value = mock_client
        mock_client.messages.create = AsyncMock(return_value=mock_message)

        result = await competitive_intel_agent(
            mandate=sample_mandate,
            client_profile=sample_client_profile,
            mandate_id="mandate-001",
            tenant_id="tenant-001"
        )

    # Verify exactly 5 competitors returned
    assert len(result.competitors) == 5
    assert result.status == "pending"


@pytest.mark.asyncio
async def test_competitive_intel_agent_boundary_15_competitors(sample_mandate, sample_client_profile):
    """Agent should accept exactly 15 competitors (maximum valid count)."""
    from backend.app.agents.competitive_intel import competitive_intel_agent

    # Mock response with exactly 15 competitors (boundary condition)
    mock_response = {
        "competitors": [
            {"name": f"Competitor{i}", "confidence": 100 - i * 5}
            for i in range(1, 16)
        ]
    }

    mock_message = AsyncMock()
    mock_message.content = [AsyncMock(text=json.dumps(mock_response))]

    with patch("backend.app.agents.competitive_intel.AsyncAnthropic") as mock_client_class:
        mock_client = AsyncMock()
        mock_client_class.return_value = mock_client
        mock_client.messages.create = AsyncMock(return_value=mock_message)

        result = await competitive_intel_agent(
            mandate=sample_mandate,
            client_profile=sample_client_profile,
            mandate_id="mandate-001",
            tenant_id="tenant-001"
        )

    # Verify exactly 15 competitors returned
    assert len(result.competitors) == 15
    assert result.status == "pending"


@pytest.mark.asyncio
async def test_competitive_intel_agent_confidence_range_validation(sample_mandate, sample_client_profile):
    """Agent should correctly handle all valid confidence values (0-100)."""
    from backend.app.agents.competitive_intel import competitive_intel_agent

    # Mock response with boundary confidence values
    mock_response = {
        "competitors": [
            {"name": "Company0", "confidence": 0},      # Minimum
            {"name": "Company1", "confidence": 50},     # Mid
            {"name": "Company2", "confidence": 100},    # Maximum
            {"name": "Company3", "confidence": 75},
            {"name": "Company4", "confidence": 25},
        ]
    }

    mock_message = AsyncMock()
    mock_message.content = [AsyncMock(text=json.dumps(mock_response))]

    with patch("backend.app.agents.competitive_intel.AsyncAnthropic") as mock_client_class:
        mock_client = AsyncMock()
        mock_client_class.return_value = mock_client
        mock_client.messages.create = AsyncMock(return_value=mock_message)

        result = await competitive_intel_agent(
            mandate=sample_mandate,
            client_profile=sample_client_profile,
            mandate_id="mandate-001",
            tenant_id="tenant-001"
        )

    # Verify all confidence values are correctly parsed
    assert result.competitors[0].confidence == 0
    assert result.competitors[1].confidence == 50
    assert result.competitors[2].confidence == 100
    assert result.competitors[3].confidence == 75
    assert result.competitors[4].confidence == 25
