"""Celery tasks for digital campaign platform activation with retry logic.

Implements per-platform activation tasks (Google Ads, Meta, LinkedIn) with:
- 3x retry on API errors
- Platform mapping storage
- Completion callback for status aggregation
- Email/WhatsApp notifications on success or partial failure
"""

import asyncio
import logging
from datetime import UTC
from typing import Any
from uuid import UUID

from celery import Task

from backend.app.celery_app import celery_app
from backend.app.models.activation_platform_mapping import ActivationPlatformMapping
from backend.app.services.activation_notifications import ActivationNotificationService
from backend.app.tools.google_ads import activate_google
from backend.app.tools.linkedin_ads import activate_linkedin
from backend.app.tools.meta_ads import activate_meta

logger = logging.getLogger(__name__)


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
    name="activation_tasks.platform_activate_google",
    base=AsyncTask,
    bind=True,
    max_retries=3,
    default_retry_delay=60,
)
async def platform_activate_google(
    self,
    activation: dict[str, Any],
    platform_config: dict[str, Any],
    creative_url: str,
) -> dict[str, Any]:
    """Activate campaign on Google Ads with retry logic."""
    try:
        logger.info(
            "Starting Google Ads activation activation_id=%s tenant_id=%s",
            activation.get("id"), activation.get("tenant_id"),
        )

        result = await activate_google(activation, platform_config, creative_url)

        await _store_platform_mapping_async(
            activation_id=activation["id"],
            channel_enum="google_ads",
            campaign_id=result.get("campaign_id"),
            ad_id=result.get("ad_id"),
            status=result.get("status"),
            error=result.get("error"),
            tenant_id=activation.get("tenant_id"),
        )

        # Write live result back to MongoDB campaign doc for frontend polling
        await _push_activation_result_to_mongo(
            campaign_id=activation.get("campaign_id", ""),
            tenant_id=activation.get("tenant_id", ""),
            platform="google_ads",
            result=result,
        )

        logger.info(
            "Google Ads activation completed status=%s campaign_id=%s test_mode=%s",
            result.get("status"), result.get("campaign_id"), result.get("test_mode"),
        )
        return result

    except Exception as e:
        logger.warning(
            "Google Ads activation error (retry %d/%d): %s",
            self.request.retries, self.max_retries, e,
            exc_info=True,
        )
        try:
            countdown = 60 * (2 ** self.request.retries)
            raise self.retry(exc=e, countdown=countdown)
        except self.MaxRetriesExceededError:
            logger.error("Google Ads activation failed after %d retries: %s", self.max_retries, e)
            err_result = {
                "status": "failed", "error": str(e),
                "platform": "google_ads", "campaign_id": None, "ad_id": None,
            }
            await _store_platform_mapping_async(
                activation_id=activation["id"], channel_enum="google_ads",
                campaign_id=None, ad_id=None, status="failed", error=str(e),
                tenant_id=activation.get("tenant_id"),
            )
            await _push_activation_result_to_mongo(
                campaign_id=activation.get("campaign_id", ""),
                tenant_id=activation.get("tenant_id", ""),
                platform="google_ads", result=err_result,
            )
            return err_result


@celery_app.task(
    name="activation_tasks.platform_activate_meta",
    base=AsyncTask,
    bind=True,
    max_retries=3,
    default_retry_delay=60,
)
async def platform_activate_meta(
    self,
    activation: dict[str, Any],
    platform_config: dict[str, Any],
    creative_url: str,
) -> dict[str, Any]:
    """Activate campaign on Meta (Facebook/Instagram) with retry logic."""
    try:
        logger.info(
            "Starting Meta Ads activation activation_id=%s tenant_id=%s",
            activation.get("id"), activation.get("tenant_id"),
        )

        result = await activate_meta(activation, platform_config, creative_url)

        await _store_platform_mapping_async(
            activation_id=activation["id"],
            channel_enum="meta_ads",
            campaign_id=result.get("campaign_id"),
            ad_id=result.get("ad_id"),
            status=result.get("status"),
            error=result.get("error"),
            tenant_id=activation.get("tenant_id"),
        )

        await _push_activation_result_to_mongo(
            campaign_id=activation.get("campaign_id", ""),
            tenant_id=activation.get("tenant_id", ""),
            platform="meta_ads",
            result=result,
        )

        logger.info(
            "Meta Ads activation completed status=%s campaign_id=%s test_mode=%s",
            result.get("status"), result.get("campaign_id"), result.get("test_mode"),
        )
        return result

    except Exception as e:
        logger.warning(
            "Meta Ads activation error (retry %d/%d): %s",
            self.request.retries, self.max_retries, e,
            exc_info=True,
        )
        try:
            countdown = 60 * (2 ** self.request.retries)
            raise self.retry(exc=e, countdown=countdown)
        except self.MaxRetriesExceededError:
            logger.error("Meta Ads activation failed after %d retries: %s", self.max_retries, e)
            err_result = {
                "status": "failed", "error": str(e),
                "platform": "meta_ads", "campaign_id": None, "ad_id": None,
            }
            await _store_platform_mapping_async(
                activation_id=activation["id"], channel_enum="meta_ads",
                campaign_id=None, ad_id=None, status="failed", error=str(e),
                tenant_id=activation.get("tenant_id"),
            )
            await _push_activation_result_to_mongo(
                campaign_id=activation.get("campaign_id", ""),
                tenant_id=activation.get("tenant_id", ""),
                platform="meta_ads", result=err_result,
            )
            return err_result


@celery_app.task(
    name="activation_tasks.platform_activate_linkedin",
    base=AsyncTask,
    bind=True,
    max_retries=3,
    default_retry_delay=60,
)
async def platform_activate_linkedin(
    self,
    activation: dict[str, Any],
    platform_config: dict[str, Any],
    creative_url: str,
) -> dict[str, Any]:
    """Activate campaign on LinkedIn with retry logic.

    Args:
        activation: Activation record with id, tenant_id, name, cost_estimated
        platform_config: LinkedIn B2B targeting config (seniority, job_title, industries, locations)
        creative_url: URL to creative asset

    Returns:
        Dict with campaign_id, ad_id, status ('live'|'failed'), error message
    """
    try:
        logger.info(
            "Starting LinkedIn Ads activation",
            extra={"activation_id": activation.get("id"), "tenant_id": activation.get("tenant_id")},
        )

        # Call async activate_linkedin function
        result = await activate_linkedin(activation, platform_config, creative_url)

        # Store mapping in database
        await _store_platform_mapping_async(
            activation_id=activation["id"],
            channel_enum="linkedin_ads",
            campaign_id=result.get("campaign_id"),
            ad_id=result.get("ad_id"),
            status=result.get("status"),
            error=result.get("error"),
            tenant_id=activation.get("tenant_id"),
        )

        logger.info(
            "LinkedIn Ads activation completed",
            extra={
                "activation_id": activation.get("id"),
                "status": result.get("status"),
                "campaign_id": result.get("campaign_id"),
            },
        )

        return result

    except Exception as e:
        logger.warning(
            f"LinkedIn Ads activation error (retry {self.request.retries}/{self.max_retries})",
            extra={
                "activation_id": activation.get("id"),
                "error": str(e),
            },
            exc_info=True,
        )

        try:
            countdown = 60 * (2 ** self.request.retries)
            raise self.retry(exc=e, countdown=countdown)
        except self.MaxRetriesExceededError:
            logger.error(
                f"LinkedIn Ads activation failed after {self.max_retries} retries",
                extra={"activation_id": activation.get("id"), "error": str(e)},
            )

            await _store_platform_mapping_async(
                activation_id=activation["id"],
                channel_enum="linkedin_ads",
                campaign_id=None,
                ad_id=None,
                status="failed",
                error=str(e),
                tenant_id=activation.get("tenant_id"),
            )

            return {
                "status": "failed",
                "error": str(e),
                "platform": "linkedin_ads",
                "campaign_id": None,
                "ad_id": None,
            }


@celery_app.task(name="activation_tasks.activation_completion_callback")
def activation_completion_callback(
    results: list[dict[str, Any]],
    activation_id: str,
    campaign_manager_email: str,
    campaign_manager_phone: str,
) -> None:
    """Callback executed when all platform subtasks complete.

    Aggregates results from all platform tasks:
    - If all live: update status → "live", send success notification
    - If any failed: update status → "activation_partial_failure", send failure notification

    Args:
        results: List of dicts from platform tasks with status, campaign_id, ad_id, platform, error
        activation_id: UUID of the activation
        campaign_manager_email: Email for notification
        campaign_manager_phone: Phone for WhatsApp notification
    """
    try:
        # Filter out None results
        valid_results = [r for r in results if r is not None]

        logger.info(
            "Activation completion callback",
            extra={
                "activation_id": activation_id,
                "total_platforms": len(valid_results),
                "live_count": sum(1 for r in valid_results if r.get("status") == "live"),
                "failed_count": sum(1 for r in valid_results if r.get("status") == "failed"),
            },
        )

        # Determine success/failure
        all_live = all(r.get("status") == "live" for r in valid_results) if valid_results else False
        failed_platforms = {
            r.get("platform", "unknown"): r.get("error", "Unknown error")
            for r in valid_results
            if r.get("status") == "failed"
        }
        platforms_live = [r.get("platform", "") for r in valid_results if r.get("status") == "live"]
        budget_spent = sum(
            r.get("budget_spent", 0) for r in valid_results if r.get("budget_spent")
        )

        # Update activation status in database (synchronous)
        _update_activation_status(
            activation_id=activation_id,
            status="live" if all_live else "activation_partial_failure",
        )

        # Send notification
        notification_service = ActivationNotificationService()

        if all_live:
            # All platforms succeeded
            logger.info(
                f"Activation {activation_id} is now LIVE on all platforms",
                extra={"platforms": platforms_live},
            )

            # Queue notification task (async handled by Celery if needed)
            # For now, just log it - in production, queue this as separate Celery task
            try:
                # Try to run in event loop if available, otherwise skip
                loop = asyncio.get_event_loop()
                if not loop.is_running():
                    loop.run_until_complete(
                        notification_service.send_activation_success(
                            activation_id=UUID(activation_id),
                            activation_name="Campaign",
                            campaign_manager_email=campaign_manager_email,
                            campaign_manager_phone=campaign_manager_phone,
                            platforms_live=platforms_live,
                            budget_spent=budget_spent,
                        )
                    )
            except Exception as e:
                logger.warning(
                    f"Could not send success notification: {e}",
                    extra={"activation_id": activation_id},
                )
        else:
            # Partial or full failure
            logger.warning(
                f"Activation {activation_id} experienced failures",
                extra={
                    "failed_platforms": list(failed_platforms.keys()),
                    "live_platforms": platforms_live,
                },
            )

            partial_success = {p: "live" for p in platforms_live} if platforms_live else None

            # Queue notification task
            try:
                loop = asyncio.get_event_loop()
                if not loop.is_running():
                    loop.run_until_complete(
                        notification_service.send_activation_failure(
                            activation_id=UUID(activation_id),
                            activation_name="Campaign",
                            campaign_manager_email=campaign_manager_email,
                            campaign_manager_phone=campaign_manager_phone,
                            failed_platforms=failed_platforms,
                            partial_success=partial_success,
                        )
                    )
            except Exception as e:
                logger.warning(
                    f"Could not send failure notification: {e}",
                    extra={"activation_id": activation_id},
                )

    except Exception as e:
        logger.error(
            "Activation completion callback failed",
            extra={"activation_id": activation_id, "error": str(e)},
            exc_info=True,
        )

        # Mark activation as failed if callback fails
        try:
            _update_activation_status(
                activation_id=activation_id,
                status="activation_failed",
            )
        except Exception as inner_e:
            logger.error(
                "Failed to update activation status on callback error",
                extra={"activation_id": activation_id, "error": str(inner_e)},
            )


async def _push_activation_result_to_mongo(
    campaign_id: str,
    tenant_id: str,
    platform: str,
    result: dict[str, Any],
) -> None:
    """Push platform activation result into MongoDB campaign doc so frontend can poll."""
    if not campaign_id:
        return
    try:
        import os as _os
        from datetime import datetime

        from motor.motor_asyncio import AsyncIOMotorClient

        mongo_url = _os.getenv("MONGODB_URL", "mongodb://localhost:27017")
        mongo_db  = _os.getenv("MONGODB_DB", "ntm")
        client = AsyncIOMotorClient(mongo_url)
        try:
            db = client[mongo_db]
            payload = {
                "status":      result.get("status"),
                "campaign_id": result.get("campaign_id"),
                "ad_id":       result.get("ad_id"),
                "ad_set_id":   result.get("ad_set_id"),
                "test_mode":   result.get("test_mode", False),
                "error":       result.get("error"),
                "updated_at":  datetime.now(UTC).isoformat(),
            }
            await db["campaigns"].update_one(
                {"_id": campaign_id, "tenant_id": tenant_id},
                {"$set": {
                    f"activation_results.{platform}": payload,
                    "updated_at": payload["updated_at"],
                }},
            )
            logger.debug(
                "_push_activation_result_to_mongo: campaign=%s platform=%s status=%s",
                campaign_id, platform, payload["status"],
            )
        finally:
            client.close()
    except Exception as exc:
        logger.warning(
            "_push_activation_result_to_mongo failed for campaign=%s platform=%s: %s",
            campaign_id, platform, exc,
        )


async def _store_platform_mapping_async(
    activation_id: str,
    channel_enum: str,
    campaign_id: str | None,
    ad_id: str | None,
    status: str,
    error: str | None,
    tenant_id: str,
) -> None:
    """Store platform mapping in database (async wrapper).

    Args:
        activation_id: Activation UUID
        channel_enum: Platform name (google_ads, meta_ads, linkedin_ads)
        campaign_id: Platform campaign ID
        ad_id: Platform ad ID
        status: Mapping status (pending, live, failed)
        error: Error message if failed
        tenant_id: Tenant UUID for isolation
    """
    try:
        # Run sync operation in thread pool to avoid blocking event loop
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(
            None,
            _store_platform_mapping_sync,
            activation_id,
            channel_enum,
            campaign_id,
            ad_id,
            status,
            error,
            tenant_id,
        )
    except Exception as e:
        logger.error(
            "Failed to store platform mapping",
            extra={
                "activation_id": activation_id,
                "channel": channel_enum,
                "error": str(e),
            },
            exc_info=True,
        )


def _store_platform_mapping_sync(
    activation_id: str,
    channel_enum: str,
    campaign_id: str | None,
    ad_id: str | None,
    status: str,
    error: str | None,
    tenant_id: str,
) -> None:
    """Store platform mapping synchronously using SessionLocal.

    Args:
        activation_id: Activation UUID
        channel_enum: Platform name
        campaign_id: Platform campaign ID
        ad_id: Platform ad ID
        status: Mapping status
        error: Error message
        tenant_id: Tenant UUID
    """
    # Import here to avoid circular imports and initialization issues
    from backend.app.db import get_session_local

    session_local = get_session_local()
    if session_local is None:
        logger.warning(
            "SessionLocal not initialized, skipping platform mapping storage",
            extra={"activation_id": activation_id, "channel": channel_enum},
        )
        return

    db = session_local()
    try:
        mapping = ActivationPlatformMapping(
            activation_id=activation_id,
            tenant_id=tenant_id,
            channel_enum=channel_enum,
            platform_campaign_id=campaign_id,
            platform_ad_id=ad_id,
            status=status,
            error_message=error,
        )
        db.add(mapping)
        db.commit()

        logger.debug(
            "Stored platform mapping",
            extra={
                "activation_id": activation_id,
                "channel": channel_enum,
                "campaign_id": campaign_id,
            },
        )
    except Exception as e:
        db.rollback()
        logger.error(
            "Database error storing platform mapping",
            extra={"channel": channel_enum, "error": str(e)},
            exc_info=True,
        )
    finally:
        db.close()


def _update_activation_status(activation_id: str, status: str) -> None:
    """Update activation status in database.

    Args:
        activation_id: Activation UUID
        status: New status (live, activation_partial_failure, activation_failed)

    Note:
        This is a placeholder implementation. The actual Activation model
        needs to be created in backend/app/models/activation.py.
        Once created, this function will update the model directly.
    """
    # Import here to avoid circular imports
    from backend.app.db import get_session_local

    session_local = get_session_local()
    if session_local is None:
        logger.warning(
            "SessionLocal not initialized, skipping activation status update",
            extra={"activation_id": activation_id, "status": status},
        )
        return

    db = session_local()
    try:
        # TODO: Import Activation model once it exists
        # from backend.app.models.activation import Activation
        # from sqlalchemy import update
        #
        # stmt = update(Activation).where(Activation.id == activation_id).values(status=status)
        # db.execute(stmt)
        # db.commit()

        logger.info(
            "Would update activation status (Activation model not yet created)",
            extra={"activation_id": activation_id, "status": status},
        )
    except Exception as e:
        db.rollback()
        logger.error(
            "Failed to update activation status",
            extra={"activation_id": activation_id, "error": str(e)},
            exc_info=True,
        )
    finally:
        db.close()
