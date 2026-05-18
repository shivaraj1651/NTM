"""SQLAlchemy model for Budget — campaign budget with approval tracking."""

from datetime import datetime, timezone
import uuid

from sqlalchemy import Column, DateTime, Float, String, Index, JSON
from sqlalchemy.orm import declarative_base

Base = declarative_base()


class Budget(Base):
    __tablename__ = "budgets"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    tenant_id = Column(String, nullable=False)
    campaign_id = Column(String, nullable=False)
    total = Column(Float, nullable=False)
    currency = Column(String, nullable=False, default="USD")
    breakdown = Column(JSON, nullable=False, default=lambda: {})
    status = Column(String, nullable=False, default="draft")
    # status values: draft | approved
    approved_by = Column(String, nullable=True)
    approved_at = Column(DateTime(timezone=True), nullable=True)
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
        Index("ix_budgets_tenant", "tenant_id"),
        Index("ix_budgets_campaign", "campaign_id"),
    )

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "tenant_id": self.tenant_id,
            "campaign_id": self.campaign_id,
            "total": self.total,
            "currency": self.currency,
            "breakdown": self.breakdown,
            "status": self.status,
            "approved_by": self.approved_by,
            "approved_at": self.approved_at.isoformat() if self.approved_at else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
