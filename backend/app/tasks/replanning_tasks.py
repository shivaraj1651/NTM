"""Celery tasks for weekly replanning agent execution (AGT-14).

Wraps ReplanningAgent.run_weekly_replan() for Celery Beat scheduling.
Fetches a fresh AnalyticsSummary from AGT-13 before generating recommendations.
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
from backend.app.db import get_session_local
from backend.app.tasks.analytics_tasks import PlatformTool

logger = logging.getLogger(__name__)


class AsyncTask(Task):
    """Celery task base that runs async functions in a new event loop."""

    def __call__(self, *args: Any, **kwargs: Any) -> Any:
        loop = asyncio.get_event_loop_policy().new_event_loop()
        try:
            return loop.run_until_complete(self.run(*args, **kwargs))
        finally:
            loop.close()


@celery_app.task(
    name="replanning.run_weekly_replan",
    base=AsyncTask,
    bind=True,
)
async def run_weekly_replan_task(self, mandate_id: str) -> Dict[str, Any]:
    """Celery Beat weekly task for activation replanning.

    1. Fetches a fresh AnalyticsSummary via AnalyticsAgent (AGT-13)
    2. Passes it to ReplanningAgent (AGT-14) to generate recommendations
    3. Returns ReplanRecommendation list — all records pending AGT-6 approval

    Args:
        mandate_id: Mandate identifier to replan.

    Returns:
        Dict with 'recommendations' list and 'count'.

    Raises:
        RuntimeError: If SessionLocal factory not initialized.
    """
    try:
        logger.info("Starting weekly replan", extra={"mandate_id": mandate_id})

        SessionLocal = get_session_local()
        if SessionLocal is None:
            raise RuntimeError("SessionLocal factory not initialized")

        async with SessionLocal() as db_session:
            platform_tools = {
                "google_ads": PlatformTool(db_session, "google_ads"),
                "meta_ads": PlatformTool(db_session, "meta_ads"),
                "linkedin_ads": PlatformTool(db_session, "linkedin_ads"),
            }
            analytics_agent = AnalyticsAgent(db_session, platform_tools)
            analytics_summary = await analytics_agent.run_daily_analysis(
                mandate_id=UUID(mandate_id)
            )

        anthropic_client = anthropic.AsyncAnthropic(
            api_key=os.environ.get("ANTHROPIC_API_KEY", "")
        )
        replan_agent = ReplanningAgent(anthropic_client)
        recommendations = await replan_agent.run_weekly_replan(
            mandate_id=mandate_id,
            analytics_summary=analytics_summary,
            activation_plan={},
        )

        logger.info(
            "Weekly replan completed",
            extra={"mandate_id": mandate_id, "count": len(recommendations)},
        )
        return {"recommendations": recommendations, "count": len(recommendations)}

    except Exception as exc:
        logger.error(
            "Weekly replan failed: %s", exc,
            extra={"mandate_id": mandate_id},
            exc_info=True,
        )
        raise
