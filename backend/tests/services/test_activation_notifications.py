"""Unit tests for ActivationNotificationService."""

from uuid import UUID

import pytest

from backend.app.services.activation_notifications import ActivationNotificationService


ACT_ID = UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa")


@pytest.fixture
def svc():
    return ActivationNotificationService()


# ── send_email / send_whatsapp stubs ─────────────────────────────────────────

@pytest.mark.asyncio
async def test_send_email_returns_true(svc):
    result = await svc.send_email("test@example.com", "Subject", "Body text")
    assert result is True


@pytest.mark.asyncio
async def test_send_whatsapp_returns_true(svc):
    result = await svc.send_whatsapp("+1234567890", "Hello campaign manager")
    assert result is True


# ── send_activation_success ───────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_send_activation_success_returns_true(svc):
    result = await svc.send_activation_success(
        activation_id=ACT_ID,
        activation_name="Spring Launch",
        campaign_manager_email="cm@brand.com",
        campaign_manager_phone="+447000000000",
        platforms_live=["google_ads", "meta_ads"],
        budget_spent=15000.0,
    )
    assert result is True


@pytest.mark.asyncio
async def test_send_activation_success_multiple_platforms(svc):
    result = await svc.send_activation_success(
        activation_id=ACT_ID,
        activation_name="Multi-Platform Blast",
        campaign_manager_email="mgr@corp.com",
        campaign_manager_phone="+1555000000",
        platforms_live=["google_ads", "meta_ads", "linkedin_ads", "twitter"],
        budget_spent=99999.99,
    )
    assert result is True


@pytest.mark.asyncio
async def test_send_activation_success_zero_budget(svc):
    result = await svc.send_activation_success(
        activation_id=ACT_ID,
        activation_name="Test",
        campaign_manager_email="a@b.com",
        campaign_manager_phone="+10000000000",
        platforms_live=["google_ads"],
        budget_spent=0.0,
    )
    assert result is True


# ── send_activation_failure ───────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_send_activation_failure_returns_true(svc):
    result = await svc.send_activation_failure(
        activation_id=ACT_ID,
        activation_name="Failed Launch",
        campaign_manager_email="cm@brand.com",
        campaign_manager_phone="+447000000000",
        failed_platforms={"google_ads": "API key invalid", "meta_ads": "Account suspended"},
    )
    assert result is True


@pytest.mark.asyncio
async def test_send_activation_failure_with_partial_success(svc):
    result = await svc.send_activation_failure(
        activation_id=ACT_ID,
        activation_name="Partial Fail",
        campaign_manager_email="cm@brand.com",
        campaign_manager_phone="+447000000000",
        failed_platforms={"meta_ads": "Budget exceeded"},
        partial_success={"google_ads": "live", "linkedin_ads": "live"},
    )
    assert result is True


@pytest.mark.asyncio
async def test_send_activation_failure_single_platform(svc):
    result = await svc.send_activation_failure(
        activation_id=ACT_ID,
        activation_name="Single Fail",
        campaign_manager_email="x@y.com",
        campaign_manager_phone="+10000",
        failed_platforms={"twitter": "Rate limit hit"},
    )
    assert result is True
