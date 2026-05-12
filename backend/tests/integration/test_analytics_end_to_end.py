"""End-to-end integration test for Analytics Agent.

Tests complete workflow:
1. Create KPIs and activations
2. Mock platform tool responses
3. Run agent
4. Verify summary and alerts
"""

import pytest
from datetime import date
from uuid import uuid4
from unittest.mock import AsyncMock
from sqlalchemy import select

from backend.app.agents.analytics_agent import AnalyticsAgent
from backend.app.models.kpi import KPI
from backend.app.models.performance_metric import PerformanceMetric
from backend.app.db import AsyncSession


@pytest.mark.asyncio
async def test_full_analytics_workflow(db_session: AsyncSession):
    """
    Test complete workflow:
    1. Create KPIs and activations
    2. Mock platform tool responses
    3. Run agent
    4. Verify summary and alerts
    """
    tenant_id = str(uuid4())
    campaign_id = str(uuid4())
    mandate_id = uuid4()
    activation_id = str(uuid4())

    # Create KPI
    kpi = KPI(
        campaign_id=campaign_id,
        channel_enum="google_ads",
        audience_segment="brand_aware",
        kpi_name="conversion_rate",
        target_value=3.0,
        threshold_unit="percent",
        tenant_id=tenant_id
    )
    db_session.add(kpi)
    await db_session.commit()

    # Mock platform tool
    mock_google_ads = AsyncMock()
    mock_google_ads.get_metrics.return_value = {
        "impressions": 5000,
        "clicks": 250,
        "conversions": 7,  # 7/250 = 0.028 = 2.8% (below 3.0% target)
        "conversion_rate": 2.8,
        "spend": 500.00,
        "ctr": 0.05,
        "cpc": 2.00
    }

    platform_tools = {
        "google_ads": mock_google_ads,
        "meta_ads": AsyncMock(),
        "linkedin_ads": AsyncMock()
    }

    agent = AnalyticsAgent(db_session, platform_tools)

    # Mock activations (since real Activation model may not exist)
    mock_activation = {
        "id": activation_id,
        "campaign_id": campaign_id,
        "channel": "google_ads",
        "sub_channel": "Google Search",
        "tenant_id": tenant_id,
        "audience_segment": "brand_aware"
    }
    agent._get_live_activations = AsyncMock(return_value=[mock_activation])

    summary = await agent.run_daily_analysis(mandate_id=mandate_id)

    # Verify summary
    assert summary["mandate_id"] == str(mandate_id)
    assert summary["date"] == str(date.today())
    assert len(summary["activations"]) == 1

    # Verify activation entry
    entry = summary["activations"][0]
    assert entry["activation_id"] == activation_id
    assert entry["channel"] == "google_ads"
    assert len(entry["kpi_results"]) == 1

    # Verify KPI result (2.8% actual vs 3.0% target = -6.67% = GREEN)
    kpi_result = entry["kpi_results"][0]
    assert kpi_result["kpi_name"] == "conversion_rate"
    assert kpi_result["target"] == 3.0
    assert abs(kpi_result["achievement_percent"] - (-6.67)) < 0.1
    assert kpi_result["status"] == "green"

    # Verify metrics stored in DB
    metric = await db_session.execute(
        select(PerformanceMetric).where(
            PerformanceMetric.activation_id == activation_id,
            PerformanceMetric.date == date.today()
        )
    )
    stored_metric = metric.scalar_one()
    assert stored_metric.metrics_json["impressions"] == 5000
    assert stored_metric.source == "google_ads"


@pytest.mark.asyncio
async def test_red_alert_trigger(db_session: AsyncSession):
    """Test that Red KPI triggers alert."""
    tenant_id = str(uuid4())
    campaign_id = str(uuid4())
    mandate_id = uuid4()
    activation_id = str(uuid4())

    # Create KPI with high target
    kpi = KPI(
        campaign_id=campaign_id,
        channel_enum="google_ads",
        audience_segment="brand_aware",
        kpi_name="conversion_rate",
        target_value=5.0,  # High target
        threshold_unit="percent",
        tenant_id=tenant_id
    )
    db_session.add(kpi)
    await db_session.commit()

    # Mock metrics with low conversion rate (below target)
    mock_google_ads = AsyncMock()
    mock_google_ads.get_metrics.return_value = {
        "impressions": 5000,
        "clicks": 250,
        "conversions": 5,  # 5/250 = 0.02 = 2.0% (way below 5.0% target = -60% = RED)
        "conversion_rate": 2.0,
        "spend": 500.00
    }

    platform_tools = {
        "google_ads": mock_google_ads,
        "meta_ads": AsyncMock(),
        "linkedin_ads": AsyncMock()
    }

    agent = AnalyticsAgent(db_session, platform_tools)

    # Mock activation
    mock_activation = {
        "id": activation_id,
        "campaign_id": campaign_id,
        "channel": "google_ads",
        "sub_channel": "Google Search",
        "tenant_id": tenant_id,
        "audience_segment": "brand_aware"
    }
    agent._get_live_activations = AsyncMock(return_value=[mock_activation])

    summary = await agent.run_daily_analysis(mandate_id=mandate_id)

    # Verify Red status and alerts
    assert summary["activations"][0]["status"] == "red"
    assert len(summary["red_alerts"]) == 1
    alert = summary["red_alerts"][0]
    assert alert["failed_kpi"] == "conversion_rate"
    assert alert["severity"] == "red"
