"""Celery tasks for daily and weekly report generation (AGT-15).

Schedules:
  generate_daily_report_task  — Daily 09:00 UTC (after AGT-13 at 08:00)
  generate_weekly_report_task — Monday 10:00 UTC (after AGT-14 at 09:00)
"""

import asyncio
import logging
import os
from typing import Any, Dict
from uuid import UUID

import anthropic
from celery import Task

from backend.app.celery_app import celery_app
from backend.app.agents.analytics_agent import AnalyticsAgent
from backend.app.agents.replanning_agent import ReplanningAgent
from backend.app.agents.report_generator import ReportAgent
from backend.app.db import get_session_local
from backend.app.tasks.analytics_tasks import PlatformTool

logger = logging.getLogger(__name__)

_CHANNELS = ["google_ads", "meta_ads", "linkedin_ads"]


class AsyncTask(Task):
    def __call__(self, *args: Any, **kwargs: Any) -> Any:
        loop = asyncio.get_event_loop_policy().new_event_loop()
        try:
            return loop.run_until_complete(self.run(*args, **kwargs))
        finally:
            loop.close()


@celery_app.task(
    name="reports.generate_daily_report",
    base=AsyncTask,
    bind=True,
)
async def generate_daily_report_task(self, mandate_id: str, tenant_id: str) -> Dict[str, Any]:
    """Daily 09:00 UTC — run AGT-13 then produce daily digest report.

    Args:
        mandate_id: Mandate identifier.
        tenant_id: Tenant identifier (multi-tenant isolation).

    Returns:
        Daily report dict.
    """
    logger.info("Starting daily report", extra={"mandate_id": mandate_id})
    try:
        SessionLocal = get_session_local()
        if SessionLocal is None:
            raise RuntimeError("SessionLocal factory not initialized")

        anthropic_client = anthropic.AsyncAnthropic(
            api_key=os.environ.get("ANTHROPIC_API_KEY", "")
        )

        async with SessionLocal() as db_session:
            platform_tools = {ch: PlatformTool(db_session, ch) for ch in _CHANNELS}
            analytics_agent = AnalyticsAgent(db_session, platform_tools)
            analytics_summary = await analytics_agent.run_daily_analysis(
                mandate_id=UUID(mandate_id)
            )
            report_agent = ReportAgent(db_session, anthropic_client)
            report = await report_agent.run_daily(mandate_id, tenant_id, analytics_summary)

        logger.info("Daily report complete", extra={"mandate_id": mandate_id})
        return report

    except Exception as exc:
        logger.error(
            "Daily report failed: %s", exc,
            extra={"mandate_id": mandate_id},
            exc_info=True,
        )
        raise


@celery_app.task(
    name="reports.generate_weekly_report",
    base=AsyncTask,
    bind=True,
)
async def generate_weekly_report_task(self, mandate_id: str, tenant_id: str) -> Dict[str, Any]:
    """Monday 10:00 UTC — run AGT-13 + AGT-14 then produce weekly full report.

    Args:
        mandate_id: Mandate identifier.
        tenant_id: Tenant identifier (multi-tenant isolation).

    Returns:
        Weekly report dict with trends and LLM narrative.
    """
    logger.info("Starting weekly report", extra={"mandate_id": mandate_id})
    try:
        SessionLocal = get_session_local()
        if SessionLocal is None:
            raise RuntimeError("SessionLocal factory not initialized")

        anthropic_client = anthropic.AsyncAnthropic(
            api_key=os.environ.get("ANTHROPIC_API_KEY", "")
        )

        async with SessionLocal() as db_session:
            platform_tools = {ch: PlatformTool(db_session, ch) for ch in _CHANNELS}
            analytics_agent = AnalyticsAgent(db_session, platform_tools)
            analytics_summary = await analytics_agent.run_daily_analysis(
                mandate_id=UUID(mandate_id)
            )

        replan_agent = ReplanningAgent(anthropic_client)
        replan_result = await replan_agent.run_weekly_replan(
            mandate_id=mandate_id,
            analytics_summary=analytics_summary,
            activation_plan={},
        )
        replan_recommendations = replan_result if isinstance(replan_result, list) else replan_result.get("recommendations", [])

        async with SessionLocal() as db_session:
            report_agent = ReportAgent(db_session, anthropic_client)
            report = await report_agent.run_weekly(
                mandate_id, tenant_id, analytics_summary, replan_recommendations
            )

        logger.info("Weekly report complete", extra={"mandate_id": mandate_id})
        return report

    except Exception as exc:
        logger.error(
            "Weekly report failed: %s", exc,
            extra={"mandate_id": mandate_id},
            exc_info=True,
        )
        raise
