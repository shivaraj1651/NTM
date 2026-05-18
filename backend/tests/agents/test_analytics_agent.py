"""Unit tests for AnalyticsAgent (TASK-020)."""

import pytest
import json
from datetime import date
from uuid import uuid4
from unittest.mock import AsyncMock, MagicMock, patch


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_db_session(mappings=None):
    """Return a minimal AsyncSession mock that yields ActivationPlatformMapping rows."""
    if mappings is None:
        mappings = []

    scalars_mock = MagicMock()
    scalars_mock.all.return_value = mappings

    result_mock = MagicMock()
    result_mock.scalars.return_value = scalars_mock

    db = AsyncMock()
    db.execute = AsyncMock(return_value=result_mock)
    return db


def _make_mapping(channel="TikTok", tenant_id=None):
    """Return a fake ActivationPlatformMapping ORM object."""
    m = MagicMock()
    m.id = uuid4()
    m.activation_id = uuid4()
    m.channel_enum = channel
    m.tenant_id = tenant_id or uuid4()
    m.status = "live"
    return m


def _make_kpi_service_mock(kpis=None):
    """Return a KPIService mock."""
    svc = AsyncMock()
    svc.get_kpis_for_activation = AsyncMock(return_value=kpis or [])
    return svc


def _make_metric_service_mock():
    """Return a PerformanceMetricService mock."""
    svc = AsyncMock()
    svc.store_metric = AsyncMock(return_value=None)
    return svc


# ---------------------------------------------------------------------------
# Basic importability
# ---------------------------------------------------------------------------

def test_analytics_agent_importable():
    """Module must import cleanly."""
    from backend.app.agents.analytics_agent import AnalyticsAgent
    assert AnalyticsAgent is not None


def test_analytics_agent_class_exists():
    """AnalyticsAgent must be a class with run_daily_analysis method."""
    from backend.app.agents.analytics_agent import AnalyticsAgent
    assert hasattr(AnalyticsAgent, "run_daily_analysis")
    assert callable(AnalyticsAgent.run_daily_analysis)


def test_analytics_agent_instantiation():
    """AnalyticsAgent must instantiate with db_session and platform_tools."""
    from backend.app.agents.analytics_agent import AnalyticsAgent

    db = _make_db_session()
    platform_tools = {}
    agent = AnalyticsAgent(db_session=db, platform_tools=platform_tools)

    assert agent.db is db
    assert agent.platform_tools is platform_tools


# ---------------------------------------------------------------------------
# run_daily_analysis — no live activations
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_run_daily_analysis_no_activations():
    """Should return a valid summary dict when no live activations exist."""
    from backend.app.agents.analytics_agent import AnalyticsAgent

    db = _make_db_session(mappings=[])
    agent = AnalyticsAgent(db_session=db, platform_tools={})

    mandate_id = uuid4()
    result = await agent.run_daily_analysis(mandate_id)

    assert isinstance(result, dict)
    assert "mandate_id" in result
    assert result["mandate_id"] == str(mandate_id)
    assert "activations" in result
    assert result["activations"] == []
    assert "red_alerts" in result
    assert result["red_alerts"] == []
    assert "summary_by_channel" in result


# ---------------------------------------------------------------------------
# run_daily_analysis — activation with no platform tool
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_run_daily_analysis_missing_platform_tool():
    """Activation with no registered platform tool must be skipped gracefully."""
    from backend.app.agents.analytics_agent import AnalyticsAgent

    mapping = _make_mapping(channel="TikTok")
    db = _make_db_session(mappings=[mapping])
    # No platform tool for TikTok → _fetch_metrics returns None
    agent = AnalyticsAgent(db_session=db, platform_tools={})

    result = await agent.run_daily_analysis(uuid4())

    assert isinstance(result, dict)
    # Activation skipped because no metrics → activations list empty
    assert result["activations"] == []
    assert result["red_alerts"] == []


# ---------------------------------------------------------------------------
# run_daily_analysis — happy path (metrics + KPIs)
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_run_daily_analysis_happy_path():
    """Should process activation metrics and return summary entry."""
    from backend.app.agents.analytics_agent import AnalyticsAgent

    mapping = _make_mapping(channel="Email")
    db = _make_db_session(mappings=[mapping])

    # Platform tool returns valid metrics
    mock_tool = AsyncMock()
    mock_tool.get_metrics = AsyncMock(
        return_value={
            "impressions": 10000,
            "clicks": 500,
            "conversions": 50,
            "spend": 1000.0,
            "ctr": 0.05,
            "conversion_rate": 0.01,
        }
    )
    platform_tools = {"Email": mock_tool}

    # Mock KPI with a green result
    mock_kpi = MagicMock()
    mock_kpi.kpi_name = "ctr"
    mock_kpi.target_value = 0.03
    mock_kpi.threshold_unit = "rate"

    with (
        patch("backend.app.agents.analytics_agent.KPIService") as MockKPIService,
        patch("backend.app.agents.analytics_agent.PerformanceMetricService") as MockMetricService,
        patch("backend.app.agents.analytics_agent.AnalyticsSummaryService") as MockSummaryService,
    ):
        kpi_svc_instance = AsyncMock()
        kpi_svc_instance.get_kpis_for_activation = AsyncMock(return_value=[mock_kpi])
        MockKPIService.return_value = kpi_svc_instance

        metric_svc_instance = AsyncMock()
        metric_svc_instance.store_metric = AsyncMock(return_value=None)
        MockMetricService.return_value = metric_svc_instance

        summary_svc_instance = MagicMock()
        summary_svc_instance.build_kpi_result = MagicMock(
            return_value={"kpi_name": "ctr", "target": 0.03, "actual": 0.05, "status": "green"}
        )
        summary_svc_instance.build_summary_entry = MagicMock(
            return_value={
                "activation_id": str(mapping.id),
                "campaign_id": str(mapping.activation_id),
                "channel": "Email",
                "sub_channel": "",
                "kpi_results": [],
                "status": "green",
            }
        )
        MockSummaryService.return_value = summary_svc_instance

        agent = AnalyticsAgent(db_session=db, platform_tools=platform_tools)
        result = await agent.run_daily_analysis(uuid4())

    assert isinstance(result, dict)
    assert "activations" in result
    assert len(result["activations"]) == 1
    assert result["activations"][0]["channel"] == "Email"
    assert result["red_alerts"] == []


# ---------------------------------------------------------------------------
# run_daily_analysis — red KPI triggers alert
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_run_daily_analysis_red_kpi_generates_alert():
    """Red KPI status must populate red_alerts list."""
    from backend.app.agents.analytics_agent import AnalyticsAgent

    mapping = _make_mapping(channel="TikTok")
    db = _make_db_session(mappings=[mapping])

    mock_tool = AsyncMock()
    mock_tool.get_metrics = AsyncMock(
        return_value={"impressions": 5000, "clicks": 10, "conversions": 0,
                      "spend": 500.0, "ctr": 0.002, "conversion_rate": 0.0}
    )
    platform_tools = {"TikTok": mock_tool}

    mock_kpi = MagicMock()
    mock_kpi.kpi_name = "ctr"
    mock_kpi.target_value = 0.05
    mock_kpi.threshold_unit = "rate"

    with (
        patch("backend.app.agents.analytics_agent.KPIService") as MockKPIService,
        patch("backend.app.agents.analytics_agent.PerformanceMetricService") as MockMetricService,
        patch("backend.app.agents.analytics_agent.AnalyticsSummaryService") as MockSummaryService,
    ):
        kpi_svc_instance = AsyncMock()
        kpi_svc_instance.get_kpis_for_activation = AsyncMock(return_value=[mock_kpi])
        MockKPIService.return_value = kpi_svc_instance

        metric_svc_instance = AsyncMock()
        metric_svc_instance.store_metric = AsyncMock(return_value=None)
        MockMetricService.return_value = metric_svc_instance

        summary_svc_instance = MagicMock()
        summary_svc_instance.build_kpi_result = MagicMock(
            return_value={"kpi_name": "ctr", "target": 0.05, "actual": 0.002, "status": "red"}
        )
        summary_svc_instance.build_summary_entry = MagicMock(
            return_value={
                "activation_id": str(mapping.id),
                "campaign_id": str(mapping.activation_id),
                "channel": "TikTok",
                "sub_channel": "",
                "kpi_results": [],
                "status": "red",
            }
        )
        MockSummaryService.return_value = summary_svc_instance

        agent = AnalyticsAgent(db_session=db, platform_tools=platform_tools)
        result = await agent.run_daily_analysis(uuid4())

    assert isinstance(result, dict)
    assert len(result["red_alerts"]) == 1
    assert result["red_alerts"][0]["failed_kpi"] == "ctr"
    assert result["red_alerts"][0]["severity"] == "red"


# ---------------------------------------------------------------------------
# _extract_metric unit tests
# ---------------------------------------------------------------------------

def test_extract_metric_found():
    """Should return float for a present numeric key."""
    from backend.app.agents.analytics_agent import AnalyticsAgent

    db = _make_db_session()
    agent = AnalyticsAgent(db_session=db, platform_tools={})

    result = agent._extract_metric({"ctr": 0.05, "impressions": 1000}, "ctr")
    assert result == pytest.approx(0.05)


def test_extract_metric_missing_key():
    """Should return None for a missing key."""
    from backend.app.agents.analytics_agent import AnalyticsAgent

    db = _make_db_session()
    agent = AnalyticsAgent(db_session=db, platform_tools={})

    result = agent._extract_metric({"ctr": 0.05}, "conversion_rate")
    assert result is None


def test_extract_metric_non_numeric_value():
    """Should return None for a non-numeric value."""
    from backend.app.agents.analytics_agent import AnalyticsAgent

    db = _make_db_session()
    agent = AnalyticsAgent(db_session=db, platform_tools={})

    result = agent._extract_metric({"ctr": "not-a-number"}, "ctr")
    assert result is None


# ---------------------------------------------------------------------------
# _build_analytics_summary unit tests
# ---------------------------------------------------------------------------

def test_build_analytics_summary_structure():
    """Should build a correctly structured summary dict."""
    from backend.app.agents.analytics_agent import AnalyticsAgent

    db = _make_db_session()
    agent = AnalyticsAgent(db_session=db, platform_tools={})

    mandate_id = uuid4()
    today = date.today()
    entries = [
        {"channel": "Email", "status": "green", "activation_id": str(uuid4())},
        {"channel": "Email", "status": "red", "activation_id": str(uuid4())},
        {"channel": "TikTok", "status": "amber", "activation_id": str(uuid4())},
    ]
    red_alerts = [{"activation_id": "x", "channel": "Email", "failed_kpi": "ctr", "severity": "red"}]

    summary = agent._build_analytics_summary(mandate_id, today, entries, red_alerts)

    assert summary["mandate_id"] == str(mandate_id)
    assert summary["date"] == str(today)
    assert summary["activations"] == entries
    assert summary["red_alerts"] == red_alerts
    assert "Email" in summary["summary_by_channel"]
    assert summary["summary_by_channel"]["Email"]["total"] == 2
    assert summary["summary_by_channel"]["Email"]["green"] == 1
    assert summary["summary_by_channel"]["Email"]["red"] == 1
    assert "TikTok" in summary["summary_by_channel"]
    assert summary["summary_by_channel"]["TikTok"]["amber"] == 1


def test_build_analytics_summary_empty_entries():
    """Should handle empty entries list."""
    from backend.app.agents.analytics_agent import AnalyticsAgent

    db = _make_db_session()
    agent = AnalyticsAgent(db_session=db, platform_tools={})

    summary = agent._build_analytics_summary(uuid4(), date.today(), [], [])

    assert summary["activations"] == []
    assert summary["red_alerts"] == []
    assert summary["summary_by_channel"] == {}


# ---------------------------------------------------------------------------
# platform tool error resilience
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_run_daily_analysis_platform_tool_raises():
    """Platform tool that raises must not propagate — activation skipped."""
    from backend.app.agents.analytics_agent import AnalyticsAgent

    mapping = _make_mapping(channel="TikTok")
    db = _make_db_session(mappings=[mapping])

    mock_tool = AsyncMock()
    mock_tool.get_metrics = AsyncMock(side_effect=RuntimeError("API timeout"))
    platform_tools = {"TikTok": mock_tool}

    with (
        patch("backend.app.agents.analytics_agent.KPIService"),
        patch("backend.app.agents.analytics_agent.PerformanceMetricService"),
        patch("backend.app.agents.analytics_agent.AnalyticsSummaryService"),
    ):
        agent = AnalyticsAgent(db_session=db, platform_tools=platform_tools)
        result = await agent.run_daily_analysis(uuid4())

    assert isinstance(result, dict)
    # Activation skipped because metrics fetch raised → no entries
    assert result["activations"] == []
