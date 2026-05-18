"""SQLAlchemy model for PhysicalActivationLog — insert-only event log for channel activations."""

from datetime import datetime, timezone
import uuid

from sqlalchemy import Column, DateTime, String, Index, JSON
from sqlalchemy.orm import declarative_base

Base = declarative_base()


class PhysicalActivationLog(Base):
    __tablename__ = "physical_activation_logs"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    tenant_id = Column(String, nullable=False)
    campaign_id = Column(String, nullable=False)
    activation_id = Column(String, nullable=True)
    event_type = Column(String, nullable=False)
    channel = Column(String, nullable=False)
    payload = Column(JSON, nullable=False, default=lambda: {})
    logged_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    created_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    __table_args__ = (
        Index("ix_pal_tenant", "tenant_id"),
        Index("ix_pal_campaign", "campaign_id"),
        Index("ix_pal_activation", "activation_id"),
        Index("ix_pal_tenant_campaign", "tenant_id", "campaign_id"),
    )

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "tenant_id": self.tenant_id,
            "campaign_id": self.campaign_id,
            "activation_id": self.activation_id,
            "event_type": self.event_type,
            "channel": self.channel,
            "payload": self.payload,
            "logged_at": self.logged_at.isoformat() if self.logged_at else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
