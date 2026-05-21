import os
import pytest
from datetime import date, timedelta
from unittest.mock import patch, MagicMock

from backend.app.tools.google_analytics import GoogleAnalyticsTool

REQUIRED_KEYS = {"activation_id", "sessions", "users", "goal_completions", "bounce_rate", "source"}


def test_mock_fallback_no_credentials():
    with patch.dict(os.environ, {"GA4_PROPERTY_ID": "", "GA4_SERVICE_ACCOUNT_JSON_PATH": ""}):
        tool = GoogleAnalyticsTool()
        result = tool.get_metrics({"id": "act-1", "channel": "youtube"})
    assert isinstance(result, dict)
    assert result["source"] == "mock"


def test_mock_fallback_has_required_keys():
    with patch.dict(os.environ, {"GA4_PROPERTY_ID": "", "GA4_SERVICE_ACCOUNT_JSON_PATH": ""}):
        tool = GoogleAnalyticsTool()
        result = tool.get_metrics({"id": "act-1"})
    assert REQUIRED_KEYS.issubset(result.keys())


def test_mock_fallback_sdk_unavailable():
    with patch("backend.app.tools.google_analytics._GA4_AVAILABLE", False), \
         patch.dict(os.environ, {"GA4_PROPERTY_ID": "123", "GA4_SERVICE_ACCOUNT_JSON_PATH": "/p.json"}):
        tool = GoogleAnalyticsTool()
        result = tool.get_metrics({"id": "act-1"})
    assert result["source"] == "mock"
    assert REQUIRED_KEYS.issubset(result.keys())


def test_get_metrics_success():
    mock_row = MagicMock()
    mock_row.metric_values = [
        MagicMock(value="1500"),
        MagicMock(value="1200"),
        MagicMock(value="300"),
        MagicMock(value="0.35"),
    ]
    mock_response = MagicMock()
    mock_response.rows = [mock_row]
    mock_client = MagicMock()
    mock_client.run_report.return_value = mock_response

    with patch("backend.app.tools.google_analytics._GA4_AVAILABLE", True), \
         patch("backend.app.tools.google_analytics.BetaAnalyticsDataClient", return_value=mock_client, create=True), \
         patch("backend.app.tools.google_analytics.RunReportRequest", create=True), \
         patch("backend.app.tools.google_analytics.DateRange", create=True), \
         patch("backend.app.tools.google_analytics.Dimension", create=True), \
         patch("backend.app.tools.google_analytics.Metric", create=True), \
         patch("backend.app.tools.google_analytics.service_account", create=True) as mock_sa, \
         patch.dict(os.environ, {"GA4_PROPERTY_ID": "123", "GA4_SERVICE_ACCOUNT_JSON_PATH": "/p.json"}):

        mock_sa.Credentials.from_service_account_file.return_value = MagicMock()
        tool = GoogleAnalyticsTool()
        result = tool.get_metrics({"id": "act-1", "channel": "youtube"})

    assert result["sessions"] == 1500
    assert result["users"] == 1200
    assert result["goal_completions"] == 300
    assert result["source"] == "ga4"
    assert mock_client.run_report.called


def test_get_metrics_date_range_defaults():
    mock_response = MagicMock()
    mock_response.rows = []
    mock_client = MagicMock()
    mock_client.run_report.return_value = mock_response

    captured_request = {}

    def capture_request(req):
        captured_request['req'] = req
        return mock_response

    mock_client.run_report.side_effect = capture_request

    mock_date_range = MagicMock()

    def create_date_range(start_date, end_date):
        mock_date_range.start_date = start_date
        mock_date_range.end_date = end_date
        return mock_date_range

    with patch("backend.app.tools.google_analytics._GA4_AVAILABLE", True), \
         patch("backend.app.tools.google_analytics.BetaAnalyticsDataClient", return_value=mock_client, create=True), \
         patch("backend.app.tools.google_analytics.RunReportRequest", create=True) as mock_rr, \
         patch("backend.app.tools.google_analytics.DateRange", side_effect=create_date_range, create=True), \
         patch("backend.app.tools.google_analytics.Dimension", create=True), \
         patch("backend.app.tools.google_analytics.Metric", create=True), \
         patch("backend.app.tools.google_analytics.service_account", create=True) as mock_sa, \
         patch.dict(os.environ, {"GA4_PROPERTY_ID": "123", "GA4_SERVICE_ACCOUNT_JSON_PATH": "/p.json"}):

        mock_sa.Credentials.from_service_account_file.return_value = MagicMock()

        def create_request(**kwargs):
            req = MagicMock()
            req.date_ranges = kwargs.get('date_ranges', [])
            return req

        mock_rr.side_effect = create_request

        tool = GoogleAnalyticsTool()
        tool.get_metrics({"id": "act-1"})

    request = mock_client.run_report.call_args[0][0]
    today = date.today()
    expected_start = (today - timedelta(days=30)).strftime("%Y-%m-%d")
    expected_end = today.strftime("%Y-%m-%d")
    assert request.date_ranges[0].start_date == expected_start
    assert request.date_ranges[0].end_date == expected_end


def test_get_metrics_custom_date_range():
    mock_response = MagicMock()
    mock_response.rows = []
    mock_client = MagicMock()
    mock_client.run_report.return_value = mock_response

    custom_start = date(2026, 1, 1)
    custom_end = date(2026, 1, 31)

    captured_request = {}

    def capture_request(req):
        captured_request['req'] = req
        return mock_response

    mock_client.run_report.side_effect = capture_request

    mock_date_range = MagicMock()

    def create_date_range(start_date, end_date):
        mock_date_range.start_date = start_date
        mock_date_range.end_date = end_date
        return mock_date_range

    with patch("backend.app.tools.google_analytics._GA4_AVAILABLE", True), \
         patch("backend.app.tools.google_analytics.BetaAnalyticsDataClient", return_value=mock_client, create=True), \
         patch("backend.app.tools.google_analytics.RunReportRequest", create=True) as mock_rr, \
         patch("backend.app.tools.google_analytics.DateRange", side_effect=create_date_range, create=True), \
         patch("backend.app.tools.google_analytics.Dimension", create=True), \
         patch("backend.app.tools.google_analytics.Metric", create=True), \
         patch("backend.app.tools.google_analytics.service_account", create=True) as mock_sa, \
         patch.dict(os.environ, {"GA4_PROPERTY_ID": "123", "GA4_SERVICE_ACCOUNT_JSON_PATH": "/p.json"}):

        mock_sa.Credentials.from_service_account_file.return_value = MagicMock()

        def create_request(**kwargs):
            req = MagicMock()
            req.date_ranges = kwargs.get('date_ranges', [])
            return req

        mock_rr.side_effect = create_request

        tool = GoogleAnalyticsTool()
        tool.get_metrics({"id": "act-1"}, start_date=custom_start, end_date=custom_end)

    request = mock_client.run_report.call_args[0][0]
    assert request.date_ranges[0].start_date == "2026-01-01"
    assert request.date_ranges[0].end_date == "2026-01-31"


def test_get_metrics_api_error_returns_mock():
    mock_client = MagicMock()
    mock_client.run_report.side_effect = Exception("GA4 API unavailable")

    with patch("backend.app.tools.google_analytics._GA4_AVAILABLE", True), \
         patch("backend.app.tools.google_analytics.BetaAnalyticsDataClient", return_value=mock_client, create=True), \
         patch("backend.app.tools.google_analytics.service_account", create=True) as mock_sa, \
         patch.dict(os.environ, {"GA4_PROPERTY_ID": "123", "GA4_SERVICE_ACCOUNT_JSON_PATH": "/p.json"}):

        mock_sa.Credentials.from_service_account_file.return_value = MagicMock()
        tool = GoogleAnalyticsTool()
        result = tool.get_metrics({"id": "act-1"})

    assert isinstance(result, dict)
    assert result["source"] == "mock"
    assert REQUIRED_KEYS.issubset(result.keys())


def test_get_metrics_activation_channel_does_not_raise():
    with patch.dict(os.environ, {"GA4_PROPERTY_ID": "", "GA4_SERVICE_ACCOUNT_JSON_PATH": ""}):
        tool = GoogleAnalyticsTool()
        result = tool.get_metrics({"id": "act-1", "channel": "youtube"})
    assert isinstance(result, dict)


def test_client_cached():
    mock_client_instance = MagicMock()

    with patch("backend.app.tools.google_analytics._GA4_AVAILABLE", True), \
         patch("backend.app.tools.google_analytics.BetaAnalyticsDataClient", return_value=mock_client_instance, create=True) as mock_ctor, \
         patch("backend.app.tools.google_analytics.service_account", create=True) as mock_sa, \
         patch.dict(os.environ, {"GA4_PROPERTY_ID": "123", "GA4_SERVICE_ACCOUNT_JSON_PATH": "/p.json"}):

        mock_sa.Credentials.from_service_account_file.return_value = MagicMock()
        tool = GoogleAnalyticsTool()
        c1 = tool._get_client()
        c2 = tool._get_client()

    assert c1 is c2
    assert mock_ctor.call_count == 1
