"""SQLAlchemy model for CampaignConcept — AI-generated concept with optional brand embedding."""

import uuid
from datetime import UTC, datetime

from sqlalchemy import JSON, Column, DateTime, Index, String, Text

from backend.app.models.base import Base

try:
    from pgvector.sqlalchemy import Vector
    HAS_PGVECTOR = True
except ImportError:
    HAS_PGVECTOR = False
class CampaignConcept(Base):
    __tablename__ = "campaign_concepts"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    tenant_id = Column(String, nullable=False)
    campaign_id = Column(String, nullable=False)
    title = Column(String, nullable=False)
    description = Column(Text, nullable=False)
    strategy = Column(JSON, nullable=False, default=lambda: {})
    status = Column(String, nullable=False, default="pending")
    # status values: pending | selected | rejected
    selected_by = Column(String, nullable=True)
    created_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        nullable=False,
    )
    updated_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
        nullable=False,
    )

    if HAS_PGVECTOR:
        brand_embedding = Column(Vector(1536), nullable=True)

    __table_args__ = (
        Index("ix_campaign_concepts_tenant", "tenant_id"),
        Index("ix_campaign_concepts_campaign", "campaign_id"),
    )

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "tenant_id": self.tenant_id,
            "campaign_id": self.campaign_id,
            "title": self.title,
            "description": self.description,
            "strategy": self.strategy,
            "status": self.status,
            "selected_by": self.selected_by,
            "brand_embedding": getattr(self, "brand_embedding", None),
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
