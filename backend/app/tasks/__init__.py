"""
Celery tasks for NTM application.

Async background tasks for competitive intelligence, metrics gathering, and long-running operations.
"""

from backend.app.tasks.competitive_intel_tasks import fetch_competitor_metrics

__all__ = ["fetch_competitor_metrics"]
