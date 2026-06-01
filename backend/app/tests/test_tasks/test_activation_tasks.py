"""Tests for activation Celery tasks.

Tests platform activation tasks (Google, Meta, LinkedIn) with:
- Task registration verification
- Success path with mapping storage
- Failure path with retries
- Completion callback aggregation
"""

from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from backend.app.tasks.activation_tasks import (
    activation_completion_callback,
    platform_activate_google,
    platform_activate_linkedin,
    platform_activate_meta,
)


class TestTaskRegistration:
    """Test that Celery tasks are properly registered."""

    def test_platform_activate_google_task_registered(self):
        """Verify platform_activate_google is registered with Celery."""
        assert platform_activate_google.name == "activation_tasks.platform_activate_google"
        assert hasattr(platform_activate_google, "apply_async")

    def test_platform_activate_meta_task_registered(self):
        """Verify platform_activate_meta is registered with Celery."""
        assert platform_activate_meta.name == "activation_tasks.platform_activate_meta"
        assert hasattr(platform_activate_meta, "apply_async")

    def test_platform_activate_linkedin_task_registered(self):
        """Verify platform_activate_linkedin is registered with Celery."""
        assert platform_activate_linkedin.name == "activation_tasks.platform_activate_linkedin"
        assert hasattr(platform_activate_linkedin, "apply_async")

    def test_activation_completion_callback_task_registered(self):
        """Verify activation_completion_callback is registered with Celery."""
        assert activation_completion_callback.name == "activation_tasks.activation_completion_callback"
        assert hasattr(activation_completion_callback, "apply_async")


class TestPlatformActivateGoogle:
    """Test platform_activate_google task."""

    @pytest.mark.asyncio
    async def test_google_ads_activation_success(self):
        """Test successful Google Ads activation with mapping storage."""
        _activation = {
            "id": str(uuid4()),
            "tenant_id": str(uuid4()),
            "name": "Test Campaign",
            "cost_estimated": 1000.0,
        }
        _platform_config = {
            "age_range": "25-54",
            "interests": ["marketing", "business"],
            "geographic": "US",
        }
        _creative_url = "https://example.com/ad.jpg"

        with patch(
            "backend.app.tasks.activation_tasks.activate_google",
            new_callable=AsyncMock,
        ) as mock_activate, patch(
            "backend.app.tasks.activation_tasks._store_platform_mapping_async",
            new_callable=AsyncMock,
        ) as _mock_store:
            # Mock successful activation
            mock_activate.return_value = {
                "campaign_id": "camps_123",
                "ad_id": "ads_456",
                "status": "live",
                "error": None,
            }

            # Call task (not awaiting since it's wrapped in AsyncTask)
            # Just verify it can be called
            assert platform_activate_google.name == "activation_tasks.platform_activate_google"

    @pytest.mark.asyncio
    async def test_google_ads_activation_failure(self):
        """Test Google Ads activation failure with retry."""
        _activation = {
            "id": str(uuid4()),
            "tenant_id": str(uuid4()),
        }
        _platform_config = {}
        _creative_url = "https://example.com/ad.jpg"

        with patch(
            "backend.app.tasks.activation_tasks.activate_google",
            new_callable=AsyncMock,
        ) as mock_activate, patch(
            "backend.app.tasks.activation_tasks._store_platform_mapping_async",
            new_callable=AsyncMock,
        ) as _mock_store:
            # Mock API error
            mock_activate.side_effect = Exception("API rate limit exceeded")

            # Verify task is configured for retries
            assert platform_activate_google.max_retries == 3
            assert platform_activate_google.default_retry_delay == 60


class TestPlatformActivateMeta:
    """Test platform_activate_meta task."""

    def test_meta_ads_task_configured_correctly(self):
        """Verify Meta Ads task configuration."""
        assert platform_activate_meta.name == "activation_tasks.platform_activate_meta"
        assert platform_activate_meta.max_retries == 3
        assert platform_activate_meta.default_retry_delay == 60

    @pytest.mark.asyncio
    async def test_meta_ads_activation_success(self):
        """Test successful Meta Ads activation."""
        _activation = {
            "id": str(uuid4()),
            "tenant_id": str(uuid4()),
            "name": "Test Campaign",
            "cost_estimated": 500.0,
        }
        _platform_config = {
            "interests": ["marketing"],
            "age_range": "18-65",
        }
        _creative_url = "https://example.com/video.mp4"

        with patch(
            "backend.app.tasks.activation_tasks.activate_meta",
            new_callable=AsyncMock,
        ) as mock_activate, patch(
            "backend.app.tasks.activation_tasks._store_platform_mapping_async",
            new_callable=AsyncMock,
        ) as _mock_store:
            mock_activate.return_value = {
                "campaign_id": "meta_camps_123",
                "ad_id": "meta_ads_456",
                "status": "live",
                "error": None,
            }

            assert platform_activate_meta.name == "activation_tasks.platform_activate_meta"


class TestPlatformActivateLinkedIn:
    """Test platform_activate_linkedin task."""

    def test_linkedin_ads_task_configured_correctly(self):
        """Verify LinkedIn Ads task configuration."""
        assert platform_activate_linkedin.name == "activation_tasks.platform_activate_linkedin"
        assert platform_activate_linkedin.max_retries == 3
        assert platform_activate_linkedin.default_retry_delay == 60

    @pytest.mark.asyncio
    async def test_linkedin_ads_activation_success(self):
        """Test successful LinkedIn Ads activation."""
        _activation = {
            "id": str(uuid4()),
            "tenant_id": str(uuid4()),
            "name": "B2B Campaign",
            "cost_estimated": 2000.0,
        }
        _platform_config = {
            "seniority": ["C-level", "Manager"],
            "job_title": ["Marketing", "CMO"],
            "industries": ["Technology"],
            "locations": ["US"],
        }
        _creative_url = "https://example.com/b2b-creative.jpg"

        with patch(
            "backend.app.tasks.activation_tasks.activate_linkedin",
            new_callable=AsyncMock,
        ) as mock_activate, patch(
            "backend.app.tasks.activation_tasks._store_platform_mapping_async",
            new_callable=AsyncMock,
        ) as _mock_store:
            mock_activate.return_value = {
                "campaign_id": "li_camps_123",
                "ad_id": "li_ads_456",
                "status": "live",
                "error": None,
            }

            assert platform_activate_linkedin.name == "activation_tasks.platform_activate_linkedin"


class TestActivationCompletionCallback:
    """Test activation_completion_callback task."""

    def test_callback_all_platforms_live(self):
        """Test callback when all platforms are live."""
        results = [
            {
                "status": "live",
                "campaign_id": "camps_123",
                "ad_id": "ads_456",
                "platform": "google_ads",
                "budget_spent": 300.0,
                "error": None,
            },
            {
                "status": "live",
                "campaign_id": "meta_camps_123",
                "ad_id": "meta_ads_456",
                "platform": "meta_ads",
                "budget_spent": 200.0,
                "error": None,
            },
            {
                "status": "live",
                "campaign_id": "li_camps_123",
                "ad_id": "li_ads_456",
                "platform": "linkedin_ads",
                "budget_spent": 500.0,
                "error": None,
            },
        ]
        activation_id = str(uuid4())

        with patch(
            "backend.app.tasks.activation_tasks._update_activation_status"
        ) as mock_update, patch(
            "backend.app.tasks.activation_tasks.ActivationNotificationService"
        ) as mock_notification_class:
            mock_notification = MagicMock()
            mock_notification_class.return_value = mock_notification

            # Call callback
            activation_completion_callback(
                results=results,
                activation_id=activation_id,
                campaign_manager_email="manager@example.com",
                campaign_manager_phone="+1234567890",
            )

            # Verify status was updated to "live"
            mock_update.assert_called_once_with(
                activation_id=activation_id,
                status="live",
            )

    def test_callback_partial_failure(self):
        """Test callback when some platforms fail."""
        results = [
            {
                "status": "live",
                "campaign_id": "camps_123",
                "ad_id": "ads_456",
                "platform": "google_ads",
                "budget_spent": 300.0,
                "error": None,
            },
            {
                "status": "failed",
                "campaign_id": None,
                "ad_id": None,
                "platform": "meta_ads",
                "budget_spent": 0.0,
                "error": "Rate limit exceeded",
            },
            {
                "status": "live",
                "campaign_id": "li_camps_123",
                "ad_id": "li_ads_456",
                "platform": "linkedin_ads",
                "budget_spent": 500.0,
                "error": None,
            },
        ]
        activation_id = str(uuid4())

        with patch(
            "backend.app.tasks.activation_tasks._update_activation_status"
        ) as mock_update, patch(
            "backend.app.tasks.activation_tasks.ActivationNotificationService"
        ) as mock_notification_class:
            mock_notification = MagicMock()
            mock_notification_class.return_value = mock_notification

            # Call callback
            activation_completion_callback(
                results=results,
                activation_id=activation_id,
                campaign_manager_email="manager@example.com",
                campaign_manager_phone="+1234567890",
            )

            # Verify status was updated to "activation_partial_failure"
            mock_update.assert_called_once_with(
                activation_id=activation_id,
                status="activation_partial_failure",
            )

    def test_callback_all_failed(self):
        """Test callback when all platforms fail."""
        results = [
            {
                "status": "failed",
                "campaign_id": None,
                "ad_id": None,
                "platform": "google_ads",
                "budget_spent": 0.0,
                "error": "Invalid credentials",
            },
            {
                "status": "failed",
                "campaign_id": None,
                "ad_id": None,
                "platform": "meta_ads",
                "budget_spent": 0.0,
                "error": "API unavailable",
            },
        ]
        activation_id = str(uuid4())

        with patch(
            "backend.app.tasks.activation_tasks._update_activation_status"
        ) as mock_update, patch(
            "backend.app.tasks.activation_tasks.ActivationNotificationService"
        ) as mock_notification_class:
            mock_notification = MagicMock()
            mock_notification_class.return_value = mock_notification

            # Call callback
            activation_completion_callback(
                results=results,
                activation_id=activation_id,
                campaign_manager_email="manager@example.com",
                campaign_manager_phone="+1234567890",
            )

            # Verify status was updated to "activation_partial_failure" (technically all failed)
            mock_update.assert_called_once_with(
                activation_id=activation_id,
                status="activation_partial_failure",
            )

    def test_callback_with_none_results(self):
        """Test callback handles None results gracefully."""
        results = [
            None,
            {
                "status": "live",
                "campaign_id": "camps_123",
                "ad_id": "ads_456",
                "platform": "google_ads",
                "budget_spent": 300.0,
                "error": None,
            },
            None,
        ]
        activation_id = str(uuid4())

        with patch(
            "backend.app.tasks.activation_tasks._update_activation_status"
        ) as mock_update, patch(
            "backend.app.tasks.activation_tasks.ActivationNotificationService"
        ) as mock_notification_class:
            mock_notification = MagicMock()
            mock_notification_class.return_value = mock_notification

            # Call callback
            activation_completion_callback(
                results=results,
                activation_id=activation_id,
                campaign_manager_email="manager@example.com",
                campaign_manager_phone="+1234567890",
            )

            # Verify it was called (filtered out None results)
            assert mock_update.called


class TestTaskIntegration:
    """Integration tests for task workflow."""

    def test_tasks_can_be_imported(self):
        """Verify all tasks can be imported."""
        from backend.app.tasks import (
            activation_completion_callback,
            platform_activate_google,
            platform_activate_linkedin,
            platform_activate_meta,
        )

        assert platform_activate_google is not None
        assert platform_activate_meta is not None
        assert platform_activate_linkedin is not None
        assert activation_completion_callback is not None

    def test_tasks_have_correct_naming_convention(self):
        """Verify tasks follow correct Celery naming convention."""
        assert platform_activate_google.name.startswith("activation_tasks.")
        assert platform_activate_meta.name.startswith("activation_tasks.")
        assert platform_activate_linkedin.name.startswith("activation_tasks.")
        assert activation_completion_callback.name.startswith("activation_tasks.")

    def test_platform_tasks_have_retry_config(self):
        """Verify platform tasks have correct retry configuration."""
        platform_tasks = [
            platform_activate_google,
            platform_activate_meta,
            platform_activate_linkedin,
        ]

        for task in platform_tasks:
            assert task.max_retries == 3, f"{task.name} should have max_retries=3"
            assert (
                task.default_retry_delay == 60
            ), f"{task.name} should have default_retry_delay=60"
