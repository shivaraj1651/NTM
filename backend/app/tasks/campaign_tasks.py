"""Celery tasks for campaign pipeline (stubs — full implementation in campaign phase)."""

import asyncio
import logging

from celery import shared_task

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=3)
def run_campaign_strategy(self, mandate_id: str, tenant_id: str) -> None:
    """Celery task: run AGT-02 campaign strategy for a confirmed mandate."""
    logger.info(f"[run_campaign_strategy] mandate_id={mandate_id} tenant_id={tenant_id}")
