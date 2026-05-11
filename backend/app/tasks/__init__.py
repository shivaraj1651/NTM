"""
Celery tasks for NTM application.

Async background tasks for competitive intelligence, metrics gathering, activation,
and long-running operations.
"""

from backend.app.tasks.competitive_intel_tasks import fetch_competitor_metrics
from backend.app.tasks.activation_tasks import (
    platform_activate_google,
    platform_activate_meta,
    platform_activate_linkedin,
    activation_completion_callback,
)

__all__ = [
    "fetch_competitor_metrics",
    "platform_activate_google",
    "platform_activate_meta",
    "platform_activate_linkedin",
    "activation_completion_callback",
]
