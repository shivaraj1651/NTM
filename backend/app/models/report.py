"""SQLAlchemy model for Report — persisted output of AGT-15 ReportAgent."""

from uuid import uuid4
from datetime import datetime, date
from sqlalchemy import Column, Date, DateTime, String, Index
from sqlalchemy.orm import declarative_base
from sqlalchemy.dialects.postgresql import UUID, JSON

Base = declarative_base()


class Report(Base):
    """
    Report (output from AGT-15 ReportAgent).

    Stores generated reports (daily and weekly) for campaigns.
    Each report contains structured JSON output from the report generation process.

    Each report has:
    - Multi-tenant isolation via tenant_id
    - Mandate (campaign) tracking
    - Report type (daily or weekly)
    - Period start and end dates
    - Flexible JSON report content
    - Creation timestamp
    """
    __tablename__ = "report"

    # Primary key and identifiers
    id = Column(String, primary_key=True, default=lambda: str(uuid4()))
    mandate_id = Column(String, nullable=False, index=True)
    tenant_id = Column(String, nullable=False, index=True)

    # Report metadata
    report_type = Column(String(10), nullable=False)   # "daily" | "weekly"
    period_start = Column(Date, nullable=False)
    period_end = Column(Date, nullable=False)

    # Report content
    report_json = Column(JSON, nullable=False)

    # Timestamps
    created_at = Column(
        DateTime,
        default=datetime.utcnow,
        nullable=False
    )

    # Indexes for query efficiency
    __table_args__ = (
        Index('ix_report_mandate_type_start', 'mandate_id', 'report_type', 'period_start'),
        Index('ix_report_tenant_type', 'tenant_id', 'report_type'),
    )

    def to_dict(self) -> dict:
        """Convert model to dictionary representation.

        Returns:
            Dictionary with all model fields
        """
        return {
            "id": self.id,
            "mandate_id": self.mandate_id,
            "tenant_id": self.tenant_id,
            "report_type": self.report_type,
            "period_start": self.period_start.isoformat() if self.period_start else None,
            "period_end": self.period_end.isoformat() if self.period_end else None,
            "report_json": self.report_json,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
