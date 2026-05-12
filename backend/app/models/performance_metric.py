"""SQLAlchemy model for PerformanceMetric.

Stores daily activation metrics from platform tools with flexible JSON structure.
One row per activation per day with aggregated platform metrics.
"""

from uuid import uuid4
from datetime import date, datetime
from sqlalchemy import Column, Date, DateTime, String, Index
from sqlalchemy.orm import declarative_base
from sqlalchemy.dialects.postgresql import UUID, JSON

Base = declarative_base()


class PerformanceMetric(Base):
    """
    PerformanceMetric (daily platform activation metrics).

    Stores daily aggregated metrics for an activation across a specific platform.
    Metrics are stored as flexible JSON to accommodate different platform fields.

    Each metric has:
    - Multi-tenant isolation via tenant_id
    - Activation tracking
    - Daily snapshots (one per activation per day)
    - Flexible JSON metrics (impressions, clicks, spend, conversions, etc.)
    - Platform source identification
    """
    __tablename__ = "performance_metric"

    # Primary key and identifiers
    id = Column(String, primary_key=True, default=lambda: str(uuid4()))
    activation_id = Column(String, nullable=False, index=True)
    tenant_id = Column(String, nullable=False, index=True)

    # Date and metrics
    date = Column(Date, nullable=False)
    metrics_json = Column(JSON, nullable=False)  # flexible: impressions, clicks, spend, ctr, cpc, roas, conversions, etc.
    source = Column(String(50), nullable=False)  # google_ads, meta_ads, linkedin_ads, etc.

    # Timestamps
    created_at = Column(
        DateTime,
        default=datetime.utcnow,
        nullable=False
    )

    # Indexes for query efficiency
    __table_args__ = (
        Index('ix_performance_metric_activation_date', 'activation_id', 'date'),
        Index('ix_performance_metric_date_tenant', 'date', 'tenant_id'),
    )

    def to_dict(self) -> dict:
        """Convert model to dictionary representation.

        Returns:
            Dictionary with all model fields
        """
        return {
            "id": str(self.id),
            "activation_id": self.activation_id,
            "tenant_id": self.tenant_id,
            "date": self.date.isoformat() if self.date else None,
            "metrics_json": self.metrics_json,
            "source": self.source,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
