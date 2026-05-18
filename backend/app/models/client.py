"""SQLAlchemy model for Client — org profile with brand metadata and optional embedding."""

from datetime import datetime, timezone
import uuid

from sqlalchemy import Column, DateTime, String, Index, JSON
from sqlalchemy.orm import declarative_base

try:
    from pgvector.sqlalchemy import Vector
    HAS_PGVECTOR = True
except ImportError:
    HAS_PGVECTOR = False

Base = declarative_base()


class Client(Base):
    __tablename__ = "clients"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    tenant_id = Column(String, nullable=False, index=True)
    org_name = Column(String, nullable=False)
    industry = Column(String, nullable=False)
    logo_url = Column(String, nullable=True)
    brand_guidelines_url = Column(String, nullable=True)
    competitors = Column(JSON, nullable=False, default=lambda: [])
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

    if HAS_PGVECTOR:
        brand_embedding = Column(Vector(1536), nullable=True)

    __table_args__ = (
        Index("ix_clients_tenant", "tenant_id"),
    )

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "tenant_id": self.tenant_id,
            "org_name": self.org_name,
            "industry": self.industry,
            "logo_url": self.logo_url,
            "brand_guidelines_url": self.brand_guidelines_url,
            "competitors": self.competitors,
            "brand_embedding": getattr(self, "brand_embedding", None),
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
