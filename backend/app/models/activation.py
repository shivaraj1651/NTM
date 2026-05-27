"""SQLAlchemy model for Activation — channel-level campaign execution unit."""

from datetime import datetime, timezone
import uuid

from sqlalchemy import Column, DateTime, Float, String, Index, JSON
from backend.app.models.base import Base

class Activation(Base):
    __tablename__ = "activations"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    tenant_id = Column(String, nullable=False)
    campaign_id = Column(String, nullable=False)
    channel = Column(String, nullable=False)
    sub_channel = Column(String, nullable=True)
    audience_segment = Column(String, nullable=False)
    budget_allocated = Column(Float, nullable=False)
    currency = Column(String, nullable=False, default="USD")
    platform_config = Column(JSON, nullable=False, default=lambda: {})
    status = Column(String, nullable=False, default="planned")
    # status values: planned | active | paused | completed | failed
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

    __table_args__ = (
        Index("ix_activations_tenant", "tenant_id"),
        Index("ix_activations_campaign", "campaign_id"),
        Index("ix_activations_tenant_campaign", "tenant_id", "campaign_id"),
    )

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "tenant_id": self.tenant_id,
            "campaign_id": self.campaign_id,
            "channel": self.channel,
            "sub_channel": self.sub_channel,
            "audience_segment": self.audience_segment,
            "budget_allocated": self.budget_allocated,
            "currency": self.currency,
            "platform_config": self.platform_config,
            "status": self.status,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
