"""AnalyticsAgent — daily scheduled analytics agent for KPI tracking and alerting.

Orchestrates the full daily analytics workflow:
  1. Fetch live activations for a mandate
  2. Fetch platform metrics via platform tools
  3. Store metrics in PerformanceMetric table
  4. Compute KPI achievement and flag status
  5. Build AnalyticsSummary JSON
  6. Send alerts for Red KPIs

TASK-020 — Analytics Agent implementation.
"""

import logging
from datetime import date
from typing import Dict, Any, List, Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.models.activation_platform_mapping import ActivationPlatformMapping
from backend.app.models.kpi import KPI
from backend.app.services.kpi_service import KPIService
from backend.app.services.performance_metric_service import PerformanceMetricService
from backend.app.services.analytics_summary_service import AnalyticsSummaryService

logger = logging.getLogger(__name__)


class AnalyticsAgent:
    """Daily scheduled analytics agent for KPI tracking and alerting."""

    def __init__(self, db_session: AsyncSession, platform_tools: Dict[str, Any]):
        """Initialize AnalyticsAgent.

        Args:
            db_session: AsyncSession for database operations.
            platform_tools: Dict mapping channel name → platform tool instance.
                            Each tool must implement async get_metrics(activation).
        """
        self.db = db_session
        self.platform_tools = platform_tools
        self.kpi_service = KPIService(db_session)
        self.metric_service = PerformanceMetricService(db_session)
        self.summary_service = AnalyticsSummaryService()

    # ------------------------------------------------------------------ #
    # Public entry point
    # ------------------------------------------------------------------ #

    async def run_daily_analysis(self, mandate_id: UUID) -> Dict[str, Any]:
        """Main entry point: analyze all live activations for a mandate.

        Fetches live activations, pulls metrics from platform tools, computes
        KPI achievement, builds summary JSON, and sends alerts for Red KPIs.

        Args:
            mandate_id: Mandate (campaign group) identifier to analyse.

        Returns:
            Summary dict with 'activations', 'red_alerts', 'summary_by_channel'.
        """
        activations = await self._get_live_activations(mandate_id)
        today = date.today()
        summary_entries: List[Dict[str, Any]] = []
        red_alerts: List[Dict[str, Any]] = []

        for activation in activations:
            try:
                entry, alerts = await self._analyze_activation(activation, today)
                if entry:
                    summary_entries.append(entry)
                red_alerts.extend(alerts)
            except Exception as exc:
                logger.warning(
                    "Skipping activation %s: %s", activation.get("id"), exc
                )
                continue

        summary = self._build_analytics_summary(
            mandate_id, today, summary_entries, red_alerts
        )

        if red_alerts:
            await self._send_notifications(red_alerts)

        return summary

    # ------------------------------------------------------------------ #
    # Internal helpers
    # ------------------------------------------------------------------ #

    async def _get_live_activations(self, mandate_id: UUID) -> List[Dict[str, Any]]:
        """Fetch all live ActivationPlatformMappings.

        NOTE: ActivationPlatformMapping does not carry mandate_id directly.
        The mandate_id parameter is reserved for future filtering once the
        activation model stores that relationship. Currently returns all live
        mappings so that downstream callers can filter further.

        Args:
            mandate_id: Mandate identifier (reserved for future filtering).

        Returns:
            List of activation dicts with id, campaign_id, channel, tenant_id.
        """
        result = await self.db.execute(
            select(ActivationPlatformMapping).where(
                ActivationPlatformMapping.status == "live"
            )
        )
        mappings = result.scalars().all()
        return [
            {
                "id": m.id,
                "campaign_id": m.activation_id,  # activation_id serves as campaign ref
                "channel": m.channel_enum,
                "sub_channel": "",
                "tenant_id": m.tenant_id,
                "audience_segment": "default",
            }
            for m in mappings
        ]

    async def _analyze_activation(
        self,
        activation: Dict[str, Any],
        analysis_date: date,
    ) -> tuple:
        """Analyze a single activation: fetch metrics, compute KPIs, flag status.

        Args:
            activation: Activation dict (id, campaign_id, channel, tenant_id, …).
            analysis_date: Date for which metrics should be fetched and stored.

        Returns:
            (summary_entry | None, list_of_red_alerts)
        """
        # 1. Fetch metrics from platform tool
        metrics = await self._fetch_metrics(activation)
        if not metrics:
            logger.warning("No metrics for activation %s", activation["id"])
            return None, []

        # 2. Store metrics in DB
        await self.metric_service.store_metric(
            activation_id=activation["id"],
            date=analysis_date,
            metrics_json=metrics,
            source=activation["channel"],
            tenant_id=activation["tenant_id"],
        )

        # 3. Fetch KPIs for this activation
        kpis = await self._get_activation_kpis(activation)
        if not kpis:
            logger.info("No KPIs defined for activation %s", activation["id"])
            return None, []

        # 4. Compute KPI results
        kpi_results: List[Dict[str, Any]] = []
        red_alerts: List[Dict[str, Any]] = []

        for kpi in kpis:
            actual = self._extract_metric(metrics, kpi.kpi_name)
            if actual is None:
                logger.warning(
                    "Missing metric '%s' for activation %s",
                    kpi.kpi_name,
                    activation["id"],
                )
                continue

            result = self.summary_service.build_kpi_result(
                kpi_name=kpi.kpi_name,
                target=kpi.target_value,
                actual=actual,
                threshold_unit=kpi.threshold_unit,
            )
            kpi_results.append(result)

            if result["status"] == "red":
                red_alerts.append(
                    {
                        "activation_id": str(activation["id"]),
                        "channel": activation["channel"],
                        "failed_kpi": kpi.kpi_name,
                        "severity": "red",
                    }
                )

        # 5. Build summary entry for this activation
        entry = self.summary_service.build_summary_entry(
            activation_id=activation["id"],
            campaign_id=activation["campaign_id"],
            channel=activation["channel"],
            sub_channel=activation.get("sub_channel", ""),
            kpi_results=kpi_results,
            metrics={
                k: v
                for k, v in metrics.items()
                if k in ("impressions", "clicks", "conversions", "spend")
            },
        )

        return entry, red_alerts

    async def _fetch_metrics(
        self, activation: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """Call the appropriate platform tool to fetch live metrics.

        Args:
            activation: Activation dict with 'channel' key.

        Returns:
            Metrics dict or None if the tool is unavailable or errors.
        """
        channel = activation["channel"]
        tool = self.platform_tools.get(channel)
        if not tool:
            logger.error("No platform tool registered for channel: %s", channel)
            return None

        try:
            return await tool.get_metrics(activation)
        except Exception as exc:
            logger.warning("Failed to fetch metrics for %s: %s", channel, exc)
            return None

    async def _get_activation_kpis(
        self, activation: Dict[str, Any]
    ) -> List[Any]:
        """Delegate KPI lookup to KPIService.

        Args:
            activation: Activation dict with campaign_id, channel, tenant_id.

        Returns:
            List of KPI ORM objects.
        """
        return await self.kpi_service.get_kpis_for_activation(
            campaign_id=activation["campaign_id"],
            channel=activation["channel"],
            audience_segment=activation.get("audience_segment", "default"),
            tenant_id=activation["tenant_id"],
        )

    def _extract_metric(
        self, metrics: Dict[str, Any], kpi_name: str
    ) -> Optional[float]:
        """Extract a single metric value from the platform metrics dict.

        Performs a direct key match. KPI names are expected to align with
        platform metric keys (e.g., 'conversion_rate', 'ctr', 'cpc').

        Args:
            metrics: Raw metrics dict from platform tool.
            kpi_name: KPI name to look up.

        Returns:
            Float value if found, None otherwise.
        """
        value = metrics.get(kpi_name)
        if value is None:
            return None
        try:
            return float(value)
        except (TypeError, ValueError):
            logger.warning("Non-numeric metric value for '%s': %s", kpi_name, value)
            return None

    def _build_analytics_summary(
        self,
        mandate_id: UUID,
        analysis_date: date,
        entries: List[Dict[str, Any]],
        red_alerts: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """Build the final AnalyticsSummary JSON for the mandate.

        Args:
            mandate_id: Mandate being analysed.
            analysis_date: Date of analysis.
            entries: Per-activation summary entries.
            red_alerts: List of red-alert dicts.

        Returns:
            Fully structured summary dict.
        """
        summary_by_channel: Dict[str, Dict[str, int]] = {}

        for entry in entries:
            channel = entry["channel"]
            status = entry["status"]
            if channel not in summary_by_channel:
                summary_by_channel[channel] = {
                    "total": 0,
                    "red": 0,
                    "amber": 0,
                    "green": 0,
                }
            summary_by_channel[channel]["total"] += 1
            if status in summary_by_channel[channel]:
                summary_by_channel[channel][status] += 1

        return {
            "mandate_id": str(mandate_id),
            "date": str(analysis_date),
            "summary_generated_at": analysis_date.isoformat() + "T00:00:00Z",
            "activations": entries,
            "red_alerts": red_alerts,
            "summary_by_channel": summary_by_channel,
        }

    async def _send_notifications(self, red_alerts: List[Dict[str, Any]]) -> None:
        """Send alert notifications for Red KPIs.

        Placeholder for email / WhatsApp / Slack notification integration.
        Called automatically by run_daily_analysis when red_alerts is non-empty.

        Args:
            red_alerts: List of red-alert dicts with activation_id, channel,
                        failed_kpi, severity.
        """
        logger.info(
            "Sending %d red alert notification(s): %s",
            len(red_alerts),
            [a["failed_kpi"] for a in red_alerts],
        )
        # Future: integrate with notification service (email, WhatsApp, Slack)
