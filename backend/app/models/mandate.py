"""SQLAlchemy model for Mandate — client campaign mandate with geography and budget."""

import uuid
from datetime import UTC, datetime

from sqlalchemy import JSON, Column, Date, DateTime, Float, Index, String, Text

from backend.app.models.base import Base


class Mandate(Base):
    __tablename__ = "mandates"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    tenant_id = Column(String, nullable=False)
    client_id = Column(String, nullable=False)
    name = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    objective = Column(String, nullable=False)
    region = Column(String, nullable=False)
    countries = Column(JSON, nullable=False, default=lambda: [])
    cities = Column(JSON, nullable=True, default=lambda: [])
    competitors = Column(JSON, nullable=False, default=lambda: [])
    total_budget = Column(Float, nullable=False)
    currency = Column(String, nullable=False, default="USD")
    start_date = Column(Date, nullable=False)
    end_date = Column(Date, nullable=False)
    status = Column(String, nullable=False, default="draft")
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

    __table_args__ = (
        Index("ix_mandates_tenant", "tenant_id"),
        Index("ix_mandates_client", "client_id"),
        Index("ix_mandates_tenant_client", "tenant_id", "client_id"),
    )

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "tenant_id": self.tenant_id,
            "client_id": self.client_id,
            "name": self.name,
            "description": self.description,
            "objective": self.objective,
            "region": self.region,
            "countries": self.countries,
            "cities": self.cities or [],
            "competitors": self.competitors,
            "total_budget": self.total_budget,
            "currency": self.currency,
            "start_date": self.start_date.isoformat() if self.start_date else None,
            "end_date": self.end_date.isoformat() if self.end_date else None,
            "status": self.status,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
