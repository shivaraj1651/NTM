"""SQLAlchemy model for ActivationPlatformMapping tracking platform-specific IDs.

Tracks platform campaign and ad IDs across Google Ads, Meta Ads, and LinkedIn
for activated campaigns, including activation status and error tracking.
"""

from datetime import datetime, timezone
import uuid

from sqlalchemy import Column, DateTime, String, UniqueConstraint, Index
from backend.app.models.base import Base

class ActivationPlatformMapping(Base):
    """
    Platform-specific mapping for campaign activations.

    Tracks the mapping between internal activation_id and platform-specific
    campaign_id and ad_id for each channel (Google Ads, Meta Ads, LinkedIn).
    Enables activation status monitoring and error tracking per platform.

    Multi-tenant isolated via tenant_id.
    One row per (activation, channel) combination.
    """

    __tablename__ = "activation_platform_mapping"

    # Primary key and identifiers
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    activation_id = Column(String, nullable=False, index=True)
    tenant_id = Column(String, nullable=False, index=True)

    # Platform and channel
    channel_enum = Column(String, nullable=False)  # google_ads, meta_ads, linkedin_ads

    # Platform-specific IDs
    platform_campaign_id = Column(String, nullable=True)  # Nullable until assigned
    platform_ad_id = Column(String, nullable=True)  # Nullable until assigned

    # Status tracking
    status = Column(String, nullable=False, default="pending")  # pending, live, failed
    error_message = Column(String, nullable=True)  # Error details if activation failed

    # Timestamps
    created_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    updated_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    # Indexes and constraints
    __table_args__ = (
        UniqueConstraint(
            "activation_id", "channel_enum", "tenant_id",
            name="uq_activation_platform_mapping_unique_channel",
        ),
        Index("ix_activation_platform_mapping_tenant_activation", "tenant_id", "activation_id"),
        Index("ix_activation_platform_mapping_status", "status"),
        Index("ix_activation_platform_mapping_channel", "channel_enum"),
    )

    def to_dict(self) -> dict:
        """Convert model to dictionary representation.

        Returns:
            Dictionary with all model fields
        """
        return {
            "id": self.id,
            "activation_id": self.activation_id,
            "tenant_id": self.tenant_id,
            "channel_enum": self.channel_enum,
            "platform_campaign_id": self.platform_campaign_id,
            "platform_ad_id": self.platform_ad_id,
            "status": self.status,
            "error_message": self.error_message,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
