import pytest
from uuid import uuid4
from backend.app.services.analytics_summary_service import AnalyticsSummaryService


def test_compute_kpi_achievement_green():
    """Test KPI achievement calculation for Green status."""
    service = AnalyticsSummaryService()

    # Target: 3.0%, Actual: 2.4% → achievement = ((2.4 - 3.0) / 3.0) * 100 = -20.0% → Amber boundary
    achievement = service.compute_achievement(actual=2.4, target=3.0)
    assert abs(achievement - (-20.0)) < 0.001

    # Target: 3.0%, Actual: 2.8% → achievement = ((2.8 - 3.0) / 3.0) * 100 = -6.67% → Green
    achievement = service.compute_achievement(actual=2.8, target=3.0)
    assert abs(achievement - (-6.67)) < 0.01
    status = service.get_status(achievement)
    assert status == "green"


def test_compute_kpi_achievement_amber():
    """Test KPI achievement for Amber status."""
    service = AnalyticsSummaryService()

    # Target: 3.0%, Actual: 2.6% → achievement = ((2.6 - 3.0) / 3.0) * 100 = -13.33% → Amber
    achievement = service.compute_achievement(actual=2.6, target=3.0)
    status = service.get_status(achievement)
    assert status == "amber"


def test_compute_kpi_achievement_red():
    """Test KPI achievement for Red status."""
    service = AnalyticsSummaryService()

    # Target: 3.0%, Actual: 2.2% → achievement = ((2.2 - 3.0) / 3.0) * 100 = -26.67% → Red
    achievement = service.compute_achievement(actual=2.2, target=3.0)
    status = service.get_status(achievement)
    assert status == "red"


def test_status_boundaries():
    """Test exact boundary conditions."""
    service = AnalyticsSummaryService()

    # Exactly -20% boundary (Red/Amber cutoff)
    # Red: < -20%, Amber: >= -20% and < -10%, Green: >= -10%
    assert service.get_status(-20.1) == "red"
    assert service.get_status(-20.0) == "amber"
    assert service.get_status(-19.9) == "amber"

    # Exactly -10% boundary (Amber/Green cutoff)
    assert service.get_status(-10.1) == "amber"
    assert service.get_status(-10.0) == "green"
    assert service.get_status(-9.9) == "green"


def test_build_kpi_result():
    """Test building a KPI result object."""
    service = AnalyticsSummaryService()

    result = service.build_kpi_result(
        kpi_name="Click-Through Rate",
        target=3.0,
        actual=2.8,
        threshold_unit="%"
    )

    assert result["kpi_name"] == "Click-Through Rate"
    assert result["target"] == 3.0
    assert result["actual"] == 2.8
    assert result["threshold_unit"] == "%"
    assert result["status"] == "green"
    assert abs(result["achievement_percent"] - (-6.67)) < 0.01


def test_get_activation_status_all_green():
    """Test activation status when all KPIs are green."""
    service = AnalyticsSummaryService()

    kpi_results = [
        {"status": "green"},
        {"status": "green"},
        {"status": "green"}
    ]

    assert service.get_activation_status(kpi_results) == "green"


def test_get_activation_status_with_amber():
    """Test activation status when any KPI is amber."""
    service = AnalyticsSummaryService()

    kpi_results = [
        {"status": "green"},
        {"status": "amber"},
        {"status": "green"}
    ]

    assert service.get_activation_status(kpi_results) == "amber"


def test_get_activation_status_with_red():
    """Test activation status when any KPI is red."""
    service = AnalyticsSummaryService()

    kpi_results = [
        {"status": "green"},
        {"status": "amber"},
        {"status": "red"}
    ]

    assert service.get_activation_status(kpi_results) == "red"


def test_build_summary_entry():
    """Test building a summary entry for an activation."""
    service = AnalyticsSummaryService()

    activation_id = uuid4()
    campaign_id = uuid4()
    kpi_results = [
        {
            "kpi_name": "Click-Through Rate",
            "target": 3.0,
            "actual": 2.8,
            "achievement_percent": -6.67,
            "threshold_unit": "%",
            "status": "green"
        }
    ]
    metrics = {
        "impressions": 10000,
        "clicks": 280,
        "conversions": 42
    }

    summary = service.build_summary_entry(
        activation_id=activation_id,
        campaign_id=campaign_id,
        channel="linkedin",
        sub_channel="ads",
        kpi_results=kpi_results,
        metrics=metrics
    )

    assert summary["activation_id"] == str(activation_id)
    assert summary["campaign_id"] == str(campaign_id)
    assert summary["channel"] == "linkedin"
    assert summary["sub_channel"] == "ads"
    assert summary["status"] == "green"
    assert summary["kpi_results"] == kpi_results
    assert summary["metrics"] == metrics
