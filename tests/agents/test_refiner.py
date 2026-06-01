"""Tests for Refinement Loop in Creative Director Agent (AGT-06)."""

from unittest.mock import AsyncMock, MagicMock

import pytest

from backend.app.agents.creative_director.models import CreativeValidation
from backend.app.agents.creative_director.refiner import Refiner


@pytest.fixture
def refiner():
    """Initialize Refiner with mock generator and validator."""
    ref = Refiner(max_attempts=2)
    ref.generator = AsyncMock()
    ref.validator = MagicMock()
    return ref


@pytest.fixture
def mock_creative():
    """Sample creative content for testing."""
    return {
        "type": "copy",
        "content": "Buy now!",
        "tone": "casual",
        "character_count": 9
    }


@pytest.fixture
def mock_validation_failed():
    """Mock validation result with violations."""
    return {
        "status": "failed",
        "violations": [
            {
                "rule": "character_limit",
                "severity": "error",
                "message": "Copy exceeds character limit"
            }
        ],
        "warnings": []
    }


@pytest.fixture
def mock_validation_passed():
    """Mock validation result with no violations."""
    return {
        "status": "passed",
        "violations": [],
        "warnings": []
    }


class TestRefinerInit:
    """Tests for Refiner initialization."""

    def test_refiner_init_with_defaults(self):
        """Should initialize with default max_attempts."""
        refiner = Refiner()
        assert refiner.max_attempts == 2
        assert refiner.generator is None
        assert refiner.validator is None

    def test_refiner_init_with_custom_max_attempts(self):
        """Should initialize with custom max_attempts."""
        refiner = Refiner(max_attempts=5)
        assert refiner.max_attempts == 5


class TestRefineMaxAttemptsExceeded:
    """Tests for max_attempts limit enforcement."""

    @pytest.mark.asyncio
    async def test_refine_respects_max_attempts(self, refiner, mock_creative, mock_validation_failed):
        """Should not exceed max_attempts even with persistent violations."""
        # Mock generator to always return failing creative
        refiner.generator.refine_creative = AsyncMock(
            return_value={
                "content": "Still bad content",
                "tone": "casual",
                "type": "copy"
            }
        )

        # Mock validator to always return failed
        refiner.validator.validate_copy = MagicMock(
            return_value=CreativeValidation(
                status="failed",
                violations=[{"message": "Still has issues", "severity": "error"}]
            )
        )

        result = await refiner.refine(
            creative=mock_creative,
            validation_result=mock_validation_failed,
            platform="instagram",
            brand_rules={"tone": "casual"}
        )

        # Should not exceed max_attempts
        assert result["attempts"] <= refiner.max_attempts
        assert result["attempts"] == refiner.max_attempts


class TestRefineUntilValid:
    """Tests for auto-refinement until valid or max attempts."""

    @pytest.mark.asyncio
    async def test_refine_until_valid(self, refiner, mock_creative, mock_validation_failed):
        """Should auto-refine until valid or max attempts."""
        # Mock generator: fail first, pass second
        call_count = [0]

        async def mock_refine(context):
            call_count[0] += 1
            if call_count[0] == 1:
                return {
                    "content": "Better content here",
                    "tone": "casual",
                    "type": "copy"
                }
            else:
                return {
                    "content": "Great content now!",
                    "tone": "casual",
                    "type": "copy"
                }

        refiner.generator.refine_creative = mock_refine

        # Mock validator: fail on first refine, pass on second
        call_count_val = [0]

        def mock_validate(copy_obj, platform, brand_rules):
            call_count_val[0] += 1
            if call_count_val[0] == 1:
                return CreativeValidation(
                    status="failed",
                    violations=[{"message": "Still needs work", "severity": "error"}]
                )
            else:
                return CreativeValidation(status="passed", violations=[])

        refiner.validator.validate_copy = mock_validate

        result = await refiner.refine(
            creative=mock_creative,
            validation_result=mock_validation_failed,
            platform="instagram",
            brand_rules={"tone": "casual"}
        )

        # Should refine up to 2 times (hit max_attempts)
        assert result["status"] in ["passed", "partial"]
        assert result["attempts"] > 0


class TestRefineEscalatesAfterMaxAttempts:
    """Tests for escalation after max_attempts exceeded."""

    @pytest.mark.asyncio
    async def test_refine_escalates_on_max_attempts(self, refiner, mock_creative, mock_validation_failed):
        """Should escalate with 'partial' status after max_attempts."""
        # Mock generator: always return bad content
        refiner.generator.refine_creative = AsyncMock(
            return_value={
                "content": "Still problematic",
                "tone": "casual",
                "type": "copy"
            }
        )

        # Mock validator: always fail
        refiner.validator.validate_copy = MagicMock(
            return_value=CreativeValidation(
                status="failed",
                violations=[{"message": "Persistent issue", "severity": "error"}]
            )
        )

        result = await refiner.refine(
            creative=mock_creative,
            validation_result=mock_validation_failed,
            platform="instagram",
            brand_rules={"tone": "casual"}
        )

        # Should escalate to partial after max_attempts
        assert result["status"] == "partial"
        assert result["escalated"] is True
        assert result["attempts"] == refiner.max_attempts
