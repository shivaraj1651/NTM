"""Service for storing and retrieving daily activation metrics.

Provides an interface to persist and query performance metrics captured from
platform tools, enabling the AnalyticsAgent to track activation performance
over time.
"""

from datetime import date
from typing import Dict, Any, Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.models.performance_metric import PerformanceMetric


class PerformanceMetricService:
    """Service for managing PerformanceMetric records.

    Handles storing daily activation metrics from platform tools and retrieving
    them for analysis. All queries include tenant_id for multi-tenant isolation.
    """

    def __init__(self, db_session: AsyncSession):
        """Initialize the service with a database session.

        Args:
            db_session: AsyncSession for database operations.
        """
        self.db = db_session

    async def store_metric(
        self,
        activation_id: str,
        date: date,
        metrics_json: Dict[str, Any],
        source: str,
        tenant_id: str
    ) -> PerformanceMetric:
        """Store a daily performance metric for an activation.

        Persists a single day's aggregated metrics for a specific activation
        and platform source. Each metric record represents one activation's
        performance on one date from one platform.

        Args:
            activation_id: The activation being tracked.
            date: The date of the metrics.
            metrics_json: Dictionary of metrics (impressions, clicks, spend, etc.).
            source: Platform source (e.g., 'google_ads', 'meta_ads', 'linkedin_ads').
            tenant_id: The tenant for multi-tenant isolation.

        Returns:
            The created PerformanceMetric record.
        """
        metric = PerformanceMetric(
            activation_id=activation_id,
            date=date,
            metrics_json=metrics_json,
            source=source,
            tenant_id=tenant_id
        )
        self.db.add(metric)
        await self.db.commit()
        return metric

    async def get_latest_metric(
        self,
        activation_id: str,
        tenant_id: str
    ) -> Optional[PerformanceMetric]:
        """Get the most recent metric for an activation.

        Retrieves the latest performance metric for a specific activation,
        useful for getting the most up-to-date performance data.

        Args:
            activation_id: The activation to query.
            tenant_id: The tenant for multi-tenant isolation.

        Returns:
            The most recent PerformanceMetric or None if not found.
        """
        result = await self.db.execute(
            select(PerformanceMetric).where(
                PerformanceMetric.activation_id == activation_id,
                PerformanceMetric.tenant_id == tenant_id
            ).order_by(PerformanceMetric.date.desc()).limit(1)
        )
        return result.scalar_one_or_none()

    async def get_metrics_for_date(
        self,
        date: date,
        tenant_id: str
    ) -> list:
        """Get all metrics for a specific date.

        Retrieves all performance metrics captured on a given date for a tenant,
        useful for daily aggregation and reporting across all activations.

        Args:
            date: The date to query.
            tenant_id: The tenant for multi-tenant isolation.

        Returns:
            List of PerformanceMetric records for that date.
        """
        result = await self.db.execute(
            select(PerformanceMetric).where(
                PerformanceMetric.date == date,
                PerformanceMetric.tenant_id == tenant_id
            )
        )
        return result.scalars().all()
