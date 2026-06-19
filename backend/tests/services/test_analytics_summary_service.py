"""Unit tests for AnalyticsSummaryService — pure computation logic."""

from uuid import UUID

import pytest

from backend.app.services.analytics_summary_service import AnalyticsSummaryService


@pytest.fixture
def svc():
    return AnalyticsSummaryService()


# ── compute_achievement ────────────────────────────────────────────────────────

def test_compute_achievement_above_target(svc):
    result = svc.compute_achievement(actual=110.0, target=100.0)
    assert result == pytest.approx(10.0)


def test_compute_achievement_below_target(svc):
    result = svc.compute_achievement(actual=80.0, target=100.0)
    assert result == pytest.approx(-20.0)


def test_compute_achievement_zero_target(svc):
    assert svc.compute_achievement(actual=50.0, target=0.0) == 0.0


def test_compute_achievement_exact_target(svc):
    assert svc.compute_achievement(actual=100.0, target=100.0) == pytest.approx(0.0)


# ── get_status ────────────────────────────────────────────────────────────────

@pytest.mark.parametrize("pct, expected", [
    (-30.0, "red"),
    (-20.1, "red"),
    (-20.0, "amber"),
    (-15.0, "amber"),
    (-10.0, "green"),
    (0.0, "green"),
    (25.0, "green"),
])
def test_get_status(svc, pct, expected):
    assert svc.get_status(pct) == expected


# ── build_kpi_result ──────────────────────────────────────────────────────────

def test_build_kpi_result_green(svc):
    result = svc.build_kpi_result("conversion_rate", target=5.0, actual=6.0, threshold_unit="%")
    assert result["kpi_name"] == "conversion_rate"
    assert result["target"] == 5.0
    assert result["actual"] == 6.0
    assert result["status"] == "green"
    assert result["achievement_percent"] == pytest.approx(20.0)


def test_build_kpi_result_red(svc):
    result = svc.build_kpi_result("cpc", target=2.0, actual=1.4, threshold_unit="USD")
    assert result["status"] == "red"


def test_build_kpi_result_amber(svc):
    result = svc.build_kpi_result("ctr", target=10.0, actual=8.7, threshold_unit="%")
    assert result["status"] == "amber"


# ── get_activation_status ─────────────────────────────────────────────────────

def test_get_activation_status_all_green(svc):
    results = [{"status": "green"}, {"status": "green"}]
    assert svc.get_activation_status(results) == "green"


def test_get_activation_status_any_amber(svc):
    results = [{"status": "green"}, {"status": "amber"}]
    assert svc.get_activation_status(results) == "amber"


def test_get_activation_status_any_red(svc):
    results = [{"status": "green"}, {"status": "amber"}, {"status": "red"}]
    assert svc.get_activation_status(results) == "red"


def test_get_activation_status_red_beats_amber(svc):
    results = [{"status": "amber"}, {"status": "red"}]
    assert svc.get_activation_status(results) == "red"


# ── build_summary_entry ───────────────────────────────────────────────────────

def test_build_summary_entry(svc):
    act_id = UUID("12345678-1234-5678-1234-567812345678")
    camp_id = UUID("87654321-4321-8765-4321-876543218765")
    kpi_results = [{"status": "green"}, {"status": "amber"}]
    metrics = {"impressions": 10000, "clicks": 500}

    entry = svc.build_summary_entry(
        activation_id=act_id,
        campaign_id=camp_id,
        channel="google_ads",
        sub_channel="search",
        kpi_results=kpi_results,
        metrics=metrics,
    )

    assert entry["activation_id"] == str(act_id)
    assert entry["campaign_id"] == str(camp_id)
    assert entry["channel"] == "google_ads"
    assert entry["sub_channel"] == "search"
    assert entry["status"] == "amber"
    assert entry["kpi_results"] == kpi_results
    assert entry["metrics"] == metrics
