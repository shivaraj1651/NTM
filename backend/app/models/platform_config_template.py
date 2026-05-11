"""SQLAlchemy model for PlatformConfigTemplate storing platform-specific targeting configurations.

Stores the lookup table that translates generic Activation segments to platform-native targeting
configurations (age ranges, interests, job titles, device types, etc.) for Google Ads, Meta Ads,
and LinkedIn Ads.
"""

from datetime import datetime, timezone
import uuid

from sqlalchemy import Column, DateTime, String, UniqueConstraint, Index, Float, JSON
from sqlalchemy.orm import declarative_base

Base = declarative_base()


class PlatformConfigTemplate(Base):
    """
    Platform-specific targeting configuration template.

    Stores the mapping between generic audience segments (brand_aware, consideration, etc.)
    and platform-native targeting configurations for each channel.

    Enables flexible, platform-specific targeting while maintaining consistent audience
    segmentation across channels.

    Multi-tenant isolated via tenant_id.
    One row per (channel, audience_segment) combination per tenant.
    """

    __tablename__ = "platform_config_template"

    # Primary key and identifiers
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    tenant_id = Column(String, nullable=False, index=True)

    # Platform and targeting
    channel_enum = Column(String, nullable=False, index=True)  # google_ads, meta_ads, linkedin_ads
    audience_segment = Column(String, nullable=False, index=True)  # brand_aware, consideration, etc.

    # Platform-specific targeting configuration (flexible JSON)
    platform_targeting_json = Column(JSON, nullable=False)  # {age_min, age_max, interests, device, etc.}

    # Budget allocation multiplier
    budget_multiplier = Column(Float, nullable=False, default=1.0)  # Multiplier for activation budget

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
            "tenant_id", "channel_enum", "audience_segment",
            name="uq_platform_config_template_unique",
        ),
        Index("ix_platform_config_template_tenant", "tenant_id"),
        Index("ix_platform_config_template_channel", "channel_enum"),
        Index("ix_platform_config_template_segment", "audience_segment"),
    )

    def to_dict(self) -> dict:
        """Convert model to dictionary representation.

        Returns:
            Dictionary with all model fields
        """
        return {
            "id": self.id,
            "tenant_id": self.tenant_id,
            "channel_enum": self.channel_enum,
            "audience_segment": self.audience_segment,
            "platform_targeting_json": self.platform_targeting_json,
            "budget_multiplier": self.budget_multiplier,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
