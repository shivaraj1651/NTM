from typing import Any
from uuid import UUID


class AnalyticsSummaryService:
    """Service for computing KPI achievement, flagging status, and building summary JSON."""

    def compute_achievement(self, actual: float, target: float) -> float:
        """
        Compute KPI achievement percentage.
        Formula: ((actual - target) / target) * 100
        """
        if target == 0:
            return 0.0
        return ((actual - target) / target) * 100

    def get_status(self, achievement_percent: float) -> str:
        """
        Determine status based on achievement percentage.
        - Red: < -20%
        - Amber: -20% to -10%
        - Green: >= -10%
        """
        if achievement_percent < -20:
            return "red"
        elif achievement_percent < -10:
            return "amber"
        else:
            return "green"

    def build_kpi_result(
        self,
        kpi_name: str,
        target: float,
        actual: float,
        threshold_unit: str
    ) -> dict[str, Any]:
        """Build KPI result object with achievement and status."""
        achievement = self.compute_achievement(actual, target)
        status = self.get_status(achievement)

        return {
            "kpi_name": kpi_name,
            "target": target,
            "actual": actual,
            "achievement_percent": round(achievement, 2),
            "threshold_unit": threshold_unit,
            "status": status
        }

    def get_activation_status(self, kpi_results: list[dict[str, Any]]) -> str:
        """
        Determine activation-level status from KPI results.
        - Red: If ANY KPI is Red
        - Amber: If ANY KPI is Amber (and none are Red)
        - Green: If ALL KPIs are Green
        """
        statuses = [result["status"] for result in kpi_results]

        if "red" in statuses:
            return "red"
        elif "amber" in statuses:
            return "amber"
        else:
            return "green"

    def build_summary_entry(
        self,
        activation_id: UUID,
        campaign_id: UUID,
        channel: str,
        sub_channel: str,
        kpi_results: list[dict[str, Any]],
        metrics: dict[str, Any]
    ) -> dict[str, Any]:
        """Build a summary entry for one activation."""
        return {
            "activation_id": str(activation_id),
            "campaign_id": str(campaign_id),
            "channel": channel,
            "sub_channel": sub_channel,
            "status": self.get_activation_status(kpi_results),
            "kpi_results": kpi_results,
            "metrics": metrics
        }
