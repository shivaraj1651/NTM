"""SQLAlchemy model for KPI definitions.

Stores KPI targets for campaigns across different channels and audience segments.
Used for tracking performance metrics against defined targets.
"""

from uuid import uuid4
from datetime import datetime
from sqlalchemy import Column, String, Float, DateTime, UniqueConstraint, Index
from sqlalchemy.orm import declarative_base

Base = declarative_base()


class KPI(Base):
    """
    KPI (Key Performance Indicator) target definition.

    Stores target KPI values for a campaign/channel/segment combination.
    Each KPI has:
    - Multi-tenant isolation via tenant_id
    - Campaign and channel tracking
    - Audience segment targeting
    - Target value with unit specification
    """
    __tablename__ = "kpi"

    # Primary key and identifiers
    id = Column(String, primary_key=True, default=lambda: str(uuid4()))
    campaign_id = Column(String, nullable=False, index=True)
    tenant_id = Column(String, nullable=False, index=True)

    # Channel and targeting
    channel_enum = Column(String(50), nullable=False)  # google_ads, meta_ads, linkedin_ads, etc.
    audience_segment = Column(String(100), nullable=False)  # brand_aware, consideration, etc.

    # KPI definition
    kpi_name = Column(String(100), nullable=False)  # conversion_rate, cost_per_click, etc.
    target_value = Column(Float, nullable=False)  # The target value
    threshold_unit = Column(String(50), nullable=False)  # percent, currency, ratio, count

    # Timestamps
    created_at = Column(
        DateTime,
        default=datetime.utcnow,
        nullable=False
    )
    updated_at = Column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False
    )

    # Unique constraint on KPI combination
    __table_args__ = (
        UniqueConstraint(
            'campaign_id', 'channel_enum', 'audience_segment', 'kpi_name', 'tenant_id',
            name='uq_kpi_campaign_channel_segment_name_tenant'
        ),
    )

    def to_dict(self) -> dict:
        """Convert model to dictionary representation.

        Returns:
            Dictionary with all model fields
        """
        return {
            "id": str(self.id),
            "campaign_id": self.campaign_id,
            "tenant_id": self.tenant_id,
            "channel_enum": self.channel_enum,
            "audience_segment": self.audience_segment,
            "kpi_name": self.kpi_name,
            "target_value": self.target_value,
            "threshold_unit": self.threshold_unit,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
