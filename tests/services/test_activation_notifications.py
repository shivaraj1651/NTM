"""Tests for ActivationNotificationService."""

import pytest
from uuid import uuid4
from unittest.mock import AsyncMock, patch

from backend.app.services.activation_notifications import ActivationNotificationService


@pytest.mark.asyncio
async def test_send_activation_success_notification():
    """Test sending success notification to campaign manager."""
    campaign_manager_email = "manager@example.com"
    campaign_manager_phone = "+1234567890"

    service = ActivationNotificationService()

    with patch.object(service, 'send_email', new_callable=AsyncMock, return_value=True) as mock_email, \
         patch.object(service, 'send_whatsapp', new_callable=AsyncMock, return_value=True) as mock_whatsapp:

        result = await service.send_activation_success(
            activation_id=uuid4(),
            activation_name="Summer Campaign - Web",
            campaign_manager_email=campaign_manager_email,
            campaign_manager_phone=campaign_manager_phone,
            platforms_live=["google_ads", "meta_ads"],
            budget_spent=5000.0
        )

        # Should return True on success
        assert result is True

        # Verify email was sent
        mock_email.assert_called_once()
        call_args = mock_email.call_args
        assert campaign_manager_email in str(call_args)

        # Verify WhatsApp was sent
        mock_whatsapp.assert_called_once()


@pytest.mark.asyncio
async def test_send_activation_failure_notification():
    """Test sending failure notification with details."""
    service = ActivationNotificationService()

    with patch.object(service, 'send_email', new_callable=AsyncMock, return_value=True) as mock_email, \
         patch.object(service, 'send_whatsapp', new_callable=AsyncMock, return_value=True) as mock_whatsapp:

        result = await service.send_activation_failure(
            activation_id=uuid4(),
            activation_name="Summer Campaign - Web",
            campaign_manager_email="manager@example.com",
            campaign_manager_phone="+1234567890",
            failed_platforms={"linkedin_ads": "API rate limit exceeded"},
            partial_success={"google_ads": "live", "meta_ads": "live"}
        )

        # Should return True on success
        assert result is True

        # Verify both notifications sent
        mock_email.assert_called_once()
        mock_whatsapp.assert_called_once()


@pytest.mark.asyncio
async def test_send_email_basic():
    """Test send_email method."""
    service = ActivationNotificationService()

    result = await service.send_email(
        to_email="test@example.com",
        subject="Test Subject",
        body="Test body"
    )

    assert result is True


@pytest.mark.asyncio
async def test_send_whatsapp_basic():
    """Test send_whatsapp method."""
    service = ActivationNotificationService()

    result = await service.send_whatsapp(
        to_phone="+1234567890",
        message="Test message"
    )

    assert result is True


@pytest.mark.asyncio
async def test_send_activation_success_failure_handling():
    """Test that notification service handles send failures gracefully."""
    service = ActivationNotificationService()

    with patch.object(service, 'send_email', new_callable=AsyncMock) as mock_email, \
         patch.object(service, 'send_whatsapp', new_callable=AsyncMock) as mock_whatsapp:

        # Simulate email send failure
        mock_email.side_effect = Exception("Email service down")

        result = await service.send_activation_success(
            activation_id=uuid4(),
            activation_name="Test Campaign",
            campaign_manager_email="manager@example.com",
            campaign_manager_phone="+1234567890",
            platforms_live=["google_ads"],
            budget_spent=1000.0
        )

        # Should return False on exception
        assert result is False


@pytest.mark.asyncio
async def test_send_activation_failure_notification_handles_exceptions():
    """Test that send_activation_failure handles exceptions gracefully."""
    service = ActivationNotificationService()

    with patch.object(service, 'send_email', new_callable=AsyncMock) as mock_email:
        # Simulate email send failure
        mock_email.side_effect = Exception("Email service down")

        result = await service.send_activation_failure(
            activation_id=uuid4(),
            activation_name="Test Campaign",
            campaign_manager_email="manager@example.com",
            campaign_manager_phone="+1234567890",
            failed_platforms={"linkedin_ads": "API error"}
        )

        # Should return False on exception
        assert result is False
