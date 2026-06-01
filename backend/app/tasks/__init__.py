"""
Celery tasks for NTM application.

Async background tasks for mandate analysis, campaign strategy, media planning,
competitive intelligence, activation, analytics, replanning, and reporting.
"""

from backend.app.celery_app import celery_app
from backend.app.tasks.activation_tasks import (
    activation_completion_callback,
    platform_activate_google,
    platform_activate_linkedin,
    platform_activate_meta,
)
from backend.app.tasks.analytics_tasks import run_daily_analytics_task
from backend.app.tasks.campaign_tasks import (
    run_budget_optimization,
    run_campaign_strategy,
    run_media_planning,
    run_video_generation,
)
from backend.app.tasks.competitive_intel_tasks import (
    fetch_competitor_metrics,
    run_competitive_intel_pipeline,
)
from backend.app.tasks.mandate_tasks import run_mandate_analysis
from backend.app.tasks.replanning_tasks import run_weekly_replan_task
from backend.app.tasks.report_tasks import generate_daily_report_task, generate_weekly_report_task

# Expose Celery app so `celery -A backend.app.tasks` can discover it.
celery = celery_app
app = celery_app

__all__ = [
    # Celery app
    "celery",
    "app",
    "celery_app",
    # Mandate pipeline
    "run_mandate_analysis",
    # Campaign pipeline
    "run_campaign_strategy",
    "run_media_planning",
    "run_video_generation",
    # Budget optimization
    "run_budget_optimization",
    # Competitive intelligence
    "fetch_competitor_metrics",
    "run_competitive_intel_pipeline",
    # Analytics (Celery Beat — daily)
    "run_daily_analytics_task",
    # Replanning (Celery Beat — weekly)
    "run_weekly_replan_task",
    # Reporting (Celery Beat — daily + weekly)
    "generate_daily_report_task",
    "generate_weekly_report_task",
    # Platform activation
    "platform_activate_google",
    "platform_activate_meta",
    "platform_activate_linkedin",
    "activation_completion_callback",
]
