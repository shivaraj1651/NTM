"""Celery tasks for daily analytics agent execution.

Implements scheduled analytics tasks for KPI tracking and alerts:
- run_daily_analytics_task: Wraps AnalyticsAgent.run_daily_analysis for Celery Beat
- Fetches live activations per mandate
- Computes metrics and KPI achievement
- Sends alerts for Red KPIs
"""

import asyncio
import logging
from typing import Any
from uuid import UUID

from celery import Task
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.agents.analytics_agent import AnalyticsAgent
from backend.app.celery_app import celery_app
from backend.app.db import get_session_local

logger = logging.getLogger(__name__)


class PlatformTool:
    """Wrapper for platform-specific API tools used by AnalyticsAgent.

    Each tool fetches metrics for an activation on its platform.
    """

    def __init__(self, db_session: AsyncSession, channel: str):
        """Initialize platform tool.

        Args:
            db_session: Async database session.
            channel: Channel name (google_ads, meta_ads, linkedin_ads).
        """
        self.db = db_session
        self.channel = channel

    async def get_metrics(self, activation: dict[str, Any]) -> dict[str, Any] | None:
        """Fetch metrics for an activation from the platform API.

        Args:
            activation: Activation dict with campaign_id, channel, etc.

        Returns:
            Metrics dict with impressions, clicks, conversions, spend.
        """
        # Placeholder: in production, call the actual platform API tools
        # (google_ads.activate_google, meta_ads functions, etc.)
        return {
            "impressions": 0,
            "clicks": 0,
            "conversions": 0,
            "spend": 0.0,
        }


class AsyncTask(Task):
    """Celery task that can handle async functions.

    Wraps async function execution in a new event loop for synchronous
    Celery task execution.
    """

    def __call__(self, *args: Any, **kwargs: Any) -> Any:
        """Run async function in event loop."""
        loop = asyncio.get_event_loop_policy().new_event_loop()
        try:
            return loop.run_until_complete(self.run(*args, **kwargs))
        finally:
            loop.close()


@celery_app.task(
    name="analytics.run_daily_analysis",
    base=AsyncTask,
    bind=True,
)
async def run_daily_analytics_task(self, mandate_id: str) -> dict[str, Any]:
    """Celery Beat scheduled task for daily analytics (runs every 24h at midnight UTC).

    Fetches live activations for a mandate, pulls metrics from platform tools,
    computes KPI achievement, builds summary JSON, and sends alerts for Red KPIs.

    Args:
        mandate_id: Mandate (campaign group) identifier to analyse.

    Returns:
        Summary dict with 'activations', 'red_alerts', 'summary_by_channel'.

    Raises:
        RuntimeError: If SessionLocal factory not initialized.
    """
    try:
        logger.info(
            "Starting daily analytics analysis",
            extra={"mandate_id": mandate_id},
        )

        # Get SessionLocal factory and create async session
        SessionLocal = get_session_local()
        if SessionLocal is None:
            raise RuntimeError("SessionLocal factory not initialized")

        async with SessionLocal() as db_session:
            # Initialize platform tools
            platform_tools = {
                "google_ads": PlatformTool(db_session, "google_ads"),
                "meta_ads": PlatformTool(db_session, "meta_ads"),
                "linkedin_ads": PlatformTool(db_session, "linkedin_ads"),
            }

            # Create agent and run daily analysis
            agent = AnalyticsAgent(db_session, platform_tools)
            summary = await agent.run_daily_analysis(mandate_id=UUID(mandate_id))

        logger.info(
            "Daily analytics analysis completed",
            extra={
                "mandate_id": mandate_id,
                "num_activations": len(summary.get("activations", [])),
            },
        )

        return summary

    except Exception as e:
        logger.error(
            f"Daily analytics analysis failed: {e}",
            extra={"mandate_id": mandate_id},
            exc_info=True,
        )
        raise
