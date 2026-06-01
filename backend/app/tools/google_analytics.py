"""Google Analytics 4 tool — fetches website traffic attribution metrics via GA4 Data API."""

import logging
import os
from datetime import date, timedelta
from typing import Any

logger = logging.getLogger(__name__)

_GA4_AVAILABLE = False
try:
    from google.analytics.data_v1beta import BetaAnalyticsDataClient
    from google.analytics.data_v1beta.types import (
        DateRange,
        Dimension,
        Metric,
        RunReportRequest,
    )
    from google.oauth2 import service_account
    _GA4_AVAILABLE = True
except ImportError:
    logger.warning("google-analytics-data not installed — GA4 tool disabled")


class GoogleAnalyticsTool:
    """Wraps GA4 Data API for website attribution metrics.

    Requires environment variables:
      GA4_PROPERTY_ID          — numeric GA4 property ID (e.g. "123456789")
      GA4_SERVICE_ACCOUNT_JSON_PATH — path to service account JSON key file

    Falls back to mock data if credentials are not configured (dev/test mode).
    """

    def __init__(self) -> None:
        self.property_id = os.getenv("GA4_PROPERTY_ID", "")
        self.sa_json_path = os.getenv("GA4_SERVICE_ACCOUNT_JSON_PATH", "")
        self._client: Any | None = None

    def _get_client(self) -> Any:
        if self._client is not None:
            return self._client
        if not _GA4_AVAILABLE:
            raise RuntimeError("google-analytics-data package not installed")
        if not self.property_id or not self.sa_json_path:
            raise RuntimeError("GA4_PROPERTY_ID and GA4_SERVICE_ACCOUNT_JSON_PATH must be set")
        creds = service_account.Credentials.from_service_account_file(
            self.sa_json_path,
            scopes=["https://www.googleapis.com/auth/analytics.readonly"],
        )
        self._client = BetaAnalyticsDataClient(credentials=creds)
        return self._client

    def get_metrics(
        self,
        activation: dict,
        start_date: date | None = None,
        end_date: date | None = None,
    ) -> dict:
        """Fetch GA4 metrics for an activation's date window.

        Args:
            activation: Activation dict with at least 'id', 'channel', optional 'start_date'/'end_date'.
            start_date: Override start date. Defaults to activation start or 30 days ago.
            end_date:   Override end date. Defaults to today.

        Returns:
            Dict with sessions, users, goal_completions, bounce_rate, source_medium.
        """
        if not self.property_id or not self.sa_json_path or not _GA4_AVAILABLE:
            return self._mock_metrics(activation)

        try:
            return self._fetch_from_api(activation, start_date, end_date)
        except Exception as exc:
            logger.warning("GA4 API error for activation %s: %s", activation.get("id"), exc)
            return self._mock_metrics(activation)

    def _fetch_from_api(
        self,
        activation: dict,
        start_date: date | None,
        end_date: date | None,
    ) -> dict:
        client = self._get_client()
        today = date.today()
        end = end_date or today
        start = start_date or (today - timedelta(days=30))

        request = RunReportRequest(
            property=f"properties/{self.property_id}",
            dimensions=[Dimension(name="sessionSourceMedium")],
            metrics=[
                Metric(name="sessions"),
                Metric(name="totalUsers"),
                Metric(name="conversions"),
                Metric(name="bounceRate"),
            ],
            date_ranges=[DateRange(
                start_date=start.strftime("%Y-%m-%d"),
                end_date=end.strftime("%Y-%m-%d"),
            )],
        )
        response = client.run_report(request)

        sessions = 0
        users = 0
        conversions = 0
        bounce_rate = 0.0
        rows = getattr(response, "rows", [])
        for row in rows:
            vals = [mv.value for mv in row.metric_values]
            sessions += int(vals[0]) if vals[0].isdigit() else 0
            users += int(vals[1]) if vals[1].isdigit() else 0
            conversions += int(vals[2]) if vals[2].isdigit() else 0
            try:
                bounce_rate = float(vals[3])
            except (ValueError, IndexError):
                pass

        return {
            "activation_id": activation.get("id"),
            "sessions": sessions,
            "users": users,
            "goal_completions": conversions,
            "bounce_rate": round(bounce_rate, 4),
            "source": "ga4",
        }

    def _mock_metrics(self, activation: dict) -> dict:
        return {
            "activation_id": activation.get("id"),
            "sessions": 0,
            "users": 0,
            "goal_completions": 0,
            "bounce_rate": 0.0,
            "source": "mock",
        }
