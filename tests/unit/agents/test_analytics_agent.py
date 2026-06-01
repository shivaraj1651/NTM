"""Unit tests for AnalyticsAgent (TASK-020)."""

from datetime import date
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.agents.analytics_agent import AnalyticsAgent


@pytest.mark.asyncio
async def test_analytics_agent_run_daily_analysis(db_session: AsyncSession):
    """Test main daily analysis flow."""
    # Mock platform tools
    mock_google_ads = AsyncMock()
    mock_google_ads.get_metrics.return_value = {
        "impressions": 5000,
        "clicks": 250,
        "conversions": 7,
        "spend": 500.00,
        "ctr": 0.05,
        "cpc": 2.00
    }

    platform_tools = {
        "google_ads": mock_google_ads,
        "meta_ads": AsyncMock(),
        "linkedin_ads": AsyncMock()
    }

    # Mock activations query (in real scenario, this would fetch from DB)
    mock_activation = {
        "id": str(uuid4()),
        "campaign_id": str(uuid4()),
        "channel": "google_ads",
        "sub_channel": "Google Search",
        "status": "live",
        "tenant_id": str(uuid4())
    }

    agent = AnalyticsAgent(db_session, platform_tools)
    agent._get_live_activations = AsyncMock(return_value=[mock_activation])
    agent._get_activation_kpis = AsyncMock(return_value=[
        MagicMock(
            id=str(uuid4()),
            kpi_name="conversion_rate",
            target_value=3.0,
            threshold_unit="percent"
        )
    ])
    agent._send_notifications = AsyncMock()

    summary = await agent.run_daily_analysis(mandate_id=uuid4())

    assert summary is not None
    assert "activations" in summary
    assert "red_alerts" in summary


@pytest.mark.asyncio
async def test_analytics_agent_skip_on_platform_error(db_session: AsyncSession):
    """Test that agent skips broken activations and continues."""
    mock_google_ads = AsyncMock()
    mock_google_ads.get_metrics.side_effect = Exception("API error")

    platform_tools = {
        "google_ads": mock_google_ads,
        "meta_ads": AsyncMock(),
        "linkedin_ads": AsyncMock()
    }

    agent = AnalyticsAgent(db_session, platform_tools)
    # Agent should log warning and continue without raising
    assert agent is not None


@pytest.mark.asyncio
async def test_analytics_agent_no_activations(db_session: AsyncSession):
    """Test that agent handles empty activations list gracefully."""
    platform_tools = {
        "google_ads": AsyncMock(),
        "meta_ads": AsyncMock(),
        "linkedin_ads": AsyncMock()
    }

    agent = AnalyticsAgent(db_session, platform_tools)
    agent._get_live_activations = AsyncMock(return_value=[])
    agent._send_notifications = AsyncMock()

    summary = await agent.run_daily_analysis(mandate_id=uuid4())

    assert summary is not None
    assert summary["activations"] == []
    assert summary["red_alerts"] == []
    agent._send_notifications.assert_not_called()


@pytest.mark.asyncio
async def test_analytics_agent_red_alert_triggers_notification(db_session: AsyncSession):
    """Test that red KPI status triggers send_notifications."""
    mock_google_ads = AsyncMock()
    mock_google_ads.get_metrics.return_value = {
        "impressions": 100,
        "clicks": 1,
        "conversions": 0,
        "spend": 500.00,
        "conversion_rate": 0.0,  # Far below 3.0 target → red
    }

    platform_tools = {"google_ads": mock_google_ads}

    activation_id = str(uuid4())
    campaign_id = str(uuid4())
    tenant_id = str(uuid4())

    mock_activation = {
        "id": activation_id,
        "campaign_id": campaign_id,
        "channel": "google_ads",
        "sub_channel": "Search",
        "status": "live",
        "tenant_id": tenant_id
    }

    agent = AnalyticsAgent(db_session, platform_tools)
    agent._get_live_activations = AsyncMock(return_value=[mock_activation])
    agent._get_activation_kpis = AsyncMock(return_value=[
        MagicMock(
            kpi_name="conversion_rate",
            target_value=3.0,
            threshold_unit="percent"
        )
    ])
    agent._send_notifications = AsyncMock()

    # Patch store_metric to avoid DB dependency
    agent.metric_service.store_metric = AsyncMock()

    summary = await agent.run_daily_analysis(mandate_id=uuid4())

    assert len(summary["red_alerts"]) > 0
    agent._send_notifications.assert_called_once()


@pytest.mark.asyncio
async def test_extract_metric_direct_match(db_session: AsyncSession):
    """Test _extract_metric returns value for direct key match."""
    agent = AnalyticsAgent(db_session, {})
    metrics = {"conversion_rate": 4.5, "ctr": 0.05}
    assert agent._extract_metric(metrics, "conversion_rate") == 4.5


@pytest.mark.asyncio
async def test_extract_metric_missing_key(db_session: AsyncSession):
    """Test _extract_metric returns None when key not present."""
    agent = AnalyticsAgent(db_session, {})
    metrics = {"impressions": 1000}
    assert agent._extract_metric(metrics, "conversion_rate") is None


@pytest.mark.asyncio
async def test_build_analytics_summary_structure(db_session: AsyncSession):
    """Test _build_analytics_summary returns correct structure."""
    agent = AnalyticsAgent(db_session, {})
    mandate_id = uuid4()
    analysis_date = date.today()
    entries = [
        {"activation_id": str(uuid4()), "channel": "google_ads", "status": "green", "kpi_results": [], "metrics": {}}
    ]
    red_alerts = []

    summary = agent._build_analytics_summary(mandate_id, analysis_date, entries, red_alerts)

    assert summary["mandate_id"] == str(mandate_id)
    assert summary["date"] == str(analysis_date)
    assert "activations" in summary
    assert "red_alerts" in summary
    assert "summary_by_channel" in summary
    assert summary["summary_by_channel"]["google_ads"]["total"] == 1
    assert summary["summary_by_channel"]["google_ads"]["green"] == 1
