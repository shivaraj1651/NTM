"""DigitalActivatorAgent — routes approved activations to platform-specific Celery subtasks."""

import logging
from typing import Any
from uuid import UUID

from celery import chord, group
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.external.stubs import stub_enabled
from backend.app.models.campaign import Campaign
from backend.app.services.activation_notifications import ActivationNotificationService
from backend.app.services.platform_config import PlatformConfigService
from backend.app.tasks.activation_tasks import (
    activation_completion_callback,
    platform_activate_google,
    platform_activate_linkedin,
    platform_activate_meta,
)

logger = logging.getLogger(__name__)


class DigitalActivatorAgent:
    """Agent for routing approved activations to digital ad platforms.

    Validates activation status, fetches campaign context, looks up platform
    configuration, and queues per-platform Celery subtasks via a chord so the
    completion callback fires once all platforms respond.
    """

    def __init__(self, db_session: AsyncSession):
        self.db = db_session
        self.platform_config_service = PlatformConfigService(db_session)
        self.notification_service = ActivationNotificationService()

    async def activate(
        self,
        activation: Any,
        creative_url: str,
        campaign_manager_email: str = "",
        campaign_manager_phone: str = "",
    ) -> dict[str, Any]:
        """Route an approved activation to platform-specific Celery subtasks via chord.

        Args:
            activation: Activation object (must be in 'approved' status).
            creative_url: URL to the creative asset (image, video, etc.).
            campaign_manager_email: Email for success/failure notification.
            campaign_manager_phone: Phone (E.164) for WhatsApp notification.

        Returns:
            Dict with status, activation_id, platforms list, and subtask_count.

        Raises:
            ValueError: If activation not approved, campaign not found, or
                        platform config not found.
        """
        if stub_enabled():
            platforms = self._map_channel_to_platforms(
                getattr(activation, "channel_enum", "")
            )
            logger.info(
                "DigitalActivatorAgent stubbed (NTM_STUB_EXTERNAL) activation_id=%s",
                activation.id,
            )
            return {
                "status": "activation_queued",
                "activation_id": str(activation.id),
                "platforms": platforms,
                "subtask_count": len(platforms),
                "stub": True,
            }

        if activation.status != "approved":
            raise ValueError(
                f"Activation must be in 'approved' status, got '{activation.status}'"
            )

        campaign = await self._get_campaign(activation.campaign_id)
        if not campaign:
            raise ValueError(f"Campaign {activation.campaign_id} not found")

        platform_config = await self.platform_config_service.get_platform_config(
            tenant_id=activation.tenant_id,
            channel_enum=activation.channel_enum,
            audience_segment=activation.audience_segment,
        )
        if not platform_config:
            raise ValueError(
                f"No platform config found for "
                f"{activation.channel_enum} / {activation.audience_segment}"
            )

        platforms = self._map_channel_to_platforms(activation.channel_enum)
        activation_dict = self._to_dict(activation)
        platform_config_json = platform_config.platform_targeting_json

        signatures = [
            sig
            for p in platforms
            if (sig := self._build_platform_signature(
                activation_dict=activation_dict,
                platform=p,
                platform_config=platform_config_json,
                creative_url=creative_url,
            )) is not None
        ]

        if not signatures:
            logger.warning(
                "No platform signatures built for channel_enum=%s", activation.channel_enum
            )
            return {
                "status": "activation_queued",
                "activation_id": str(activation.id),
                "platforms": [],
                "subtask_count": 0,
            }

        callback = activation_completion_callback.s(
            activation_id=str(activation.id),
            campaign_manager_email=campaign_manager_email,
            campaign_manager_phone=campaign_manager_phone,
        )
        chord(group(signatures))(callback)

        logger.info(
            "Activation %s queued for %d platforms via chord",
            activation.id,
            len(platforms),
            extra={"activation_id": str(activation.id), "platforms": platforms},
        )

        return {
            "status": "activation_queued",
            "activation_id": str(activation.id),
            "platforms": platforms,
            "subtask_count": len(signatures),
        }

    async def _get_campaign(self, campaign_id: UUID) -> Any | None:
        result = await self.db.execute(
            select(Campaign).where(Campaign.id == str(campaign_id))
        )
        return result.scalar_one_or_none()

    def _map_channel_to_platforms(self, channel_enum: str) -> list[str]:
        mapping = {
            "google_ads": ["google_ads"],
            "meta_ads": ["meta_ads"],
            "linkedin_ads": ["linkedin_ads"],
        }
        return mapping.get(channel_enum, [])

    def _build_platform_signature(
        self,
        activation_dict: dict[str, Any],
        platform: str,
        platform_config: dict[str, Any],
        creative_url: str,
    ) -> Any:
        """Return a Celery task signature for the given platform, or None if unknown."""
        if platform == "google_ads":
            return platform_activate_google.s(activation_dict, platform_config, creative_url)
        if platform == "meta_ads":
            return platform_activate_meta.s(activation_dict, platform_config, creative_url)
        if platform == "linkedin_ads":
            return platform_activate_linkedin.s(activation_dict, platform_config, creative_url)
        logger.warning("Unknown platform: %s", platform)
        return None

    @staticmethod
    def _to_dict(activation: Any) -> dict[str, Any]:
        if hasattr(activation, "to_dict"):
            return activation.to_dict()
        return {k: v for k, v in vars(activation).items() if not k.startswith("_")}
