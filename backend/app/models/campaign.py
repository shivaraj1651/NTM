"""SQLAlchemy model for Campaign — core campaign entity."""

from datetime import datetime, timezone
import uuid

from sqlalchemy import Column, DateTime, String, Text, Index
from sqlalchemy.orm import declarative_base

Base = declarative_base()


class Campaign(Base):
    __tablename__ = "campaigns"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    tenant_id = Column(String, nullable=False)
    mandate_id = Column(String, nullable=True)
    client_id = Column(String, nullable=True)
    name = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    status = Column(String, nullable=False, default="pending")
    # status values: pending | concepts_ready | confirmed | planned |
    #                budget_proposed | approved | creative_generating |
    #                creative_ready | live
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
        Index("ix_campaigns_tenant", "tenant_id"),
        Index("ix_campaigns_mandate", "mandate_id"),
        Index("ix_campaigns_client", "client_id"),
    )

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "tenant_id": self.tenant_id,
            "mandate_id": self.mandate_id,
            "client_id": self.client_id,
            "name": self.name,
            "description": self.description,
            "status": self.status,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
