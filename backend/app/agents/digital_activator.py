"""DigitalActivatorAgent — routes approved activations to platform-specific Celery subtasks."""

import logging
from typing import Any, Dict, List, Optional
from uuid import UUID
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.services.platform_config import PlatformConfigService
from backend.app.services.activation_notifications import ActivationNotificationService
from backend.app.models.campaign import Campaign
from backend.app.tasks.activation_tasks import (
    platform_activate_google,
    platform_activate_meta,
    platform_activate_linkedin,
)

logger = logging.getLogger(__name__)


class DigitalActivatorAgent:
    """Agent for routing approved activations to digital ad platforms.

    Validates activation status, fetches campaign context, looks up platform
    configuration, and queues per-platform Celery subtasks without waiting
    for completion (eventual consistency model).
    """

    def __init__(self, db_session: AsyncSession):
        """Initialize agent with database session and services.

        Args:
            db_session: AsyncSession for database access
        """
        self.db = db_session
        self.platform_config_service = PlatformConfigService(db_session)
        self.notification_service = ActivationNotificationService()

    async def activate(
        self,
        activation: Any,
        creative_url: str
    ) -> Dict[str, Any]:
        """
        Route an approved activation to platform-specific Celery subtasks.

        Validates activation status is "approved", fetches parent campaign,
        looks up platform configuration, maps channel to platforms, and queues
        per-platform subtasks. Returns immediately without waiting for task
        completion (eventual consistency).

        Args:
            activation: Activation object (must be in 'approved' status)
            creative_url: URL to creative asset (image, video, etc.)

        Returns:
            Dict with keys:
                - status: "activation_queued"
                - activation_id: string UUID of activation
                - platforms: list of platform names queued
                - subtask_count: number of Celery subtasks created

        Raises:
            ValueError: If activation not approved, campaign not found,
                       or platform config not found
        """
        # Validate status
        if activation.status != "approved":
            raise ValueError(
                f"Activation must be in 'approved' status, got '{activation.status}'"
            )

        # Get parent campaign
        campaign = await self._get_campaign(activation.campaign_id)
        if not campaign:
            raise ValueError(f"Campaign {activation.campaign_id} not found")

        # Get platform config
        platform_config = await self.platform_config_service.get_platform_config(
            tenant_id=activation.tenant_id,
            channel_enum=activation.channel_enum,
            audience_segment=activation.audience_segment
        )

        if not platform_config:
            raise ValueError(
                f"No platform config found for {activation.channel_enum} / {activation.audience_segment}"
            )

        # Determine platforms to activate
        platforms = self._map_channel_to_platforms(activation.channel_enum)

        # Queue per-platform subtasks
        subtasks = []
        for platform in platforms:
            task = self._queue_platform_activation(
                activation=activation,
                platform=platform,
                platform_config=platform_config.platform_targeting_json,
                creative_url=creative_url
            )
            subtasks.append(task)

        logger.info(
            f"Activation {activation.id} queued for {len(platforms)} platforms",
            extra={
                "activation_id": str(activation.id),
                "tenant_id": activation.tenant_id,
                "platforms": platforms,
                "subtask_count": len(subtasks)
            }
        )

        return {
            "status": "activation_queued",
            "activation_id": str(activation.id),
            "platforms": platforms,
            "subtask_count": len(subtasks)
        }

    async def _get_campaign(self, campaign_id: UUID) -> Optional[Any]:
        """
        Fetch campaign record by ID.

        Queries the Campaign table and returns the record if found.

        Args:
            campaign_id: UUID of the campaign

        Returns:
            Campaign record if found, None otherwise
        """
        result = await self.db.execute(
            select(Campaign).where(Campaign.id == str(campaign_id))
        )
        return result.scalar_one_or_none()

    def _map_channel_to_platforms(self, channel_enum: str) -> List[str]:
        """
        Map Activation channel_enum to platform(s) for activation.

        Returns a list of platform identifiers that match the given channel.
        Each channel maps to one or more platforms that can activate it.

        Args:
            channel_enum: Channel type (e.g., "google_ads", "meta_ads")

        Returns:
            List of platform identifiers (e.g., ["google_ads"])
        """
        mapping = {
            "google_ads": ["google_ads"],
            "meta_ads": ["meta_ads"],
            "linkedin_ads": ["linkedin_ads"],
        }
        return mapping.get(channel_enum, [])

    def _queue_platform_activation(
        self,
        activation: Any,
        platform: str,
        platform_config: Dict[str, Any],
        creative_url: str
    ) -> Any:
        """
        Queue a platform-specific Celery subtask.

        Calls the appropriate Celery task for the given platform with
        activation details, configuration, and creative URL.

        Args:
            activation: Activation object
            platform: Platform identifier (e.g., "google_ads")
            platform_config: Platform-specific targeting configuration
            creative_url: URL to creative asset

        Returns:
            Celery AsyncResult or task object

        Note:
            This is a stub implementation. Task routing to platform-specific
            subtasks (activate_google, activate_meta, activate_linkedin) will
            be implemented in Task 9 when Celery tasks are registered.
        """
        activation_dict = (
            activation.to_dict()
            if hasattr(activation, "to_dict")
            else {k: v for k, v in vars(activation).items() if not k.startswith("_")}
        )
        if platform == "google_ads":
            return platform_activate_google.apply_async(
                args=[activation_dict, platform_config, creative_url]
            )
        elif platform == "meta_ads":
            return platform_activate_meta.apply_async(
                args=[activation_dict, platform_config, creative_url]
            )
        elif platform == "linkedin_ads":
            return platform_activate_linkedin.apply_async(
                args=[activation_dict, platform_config, creative_url]
            )
        logger.warning(f"[DigitalActivatorAgent] unknown platform: {platform}")
        return None
