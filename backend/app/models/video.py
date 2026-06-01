"""SQLAlchemy model for GeneratedVideo output from Video Generator Agent (AGT-11)."""

import uuid
from datetime import UTC, datetime

from sqlalchemy import Column, DateTime, Float, Index, String

from backend.app.models.base import Base


class GeneratedVideo(Base):
    """Generated video record. Multi-tenant isolated, one row per generation."""

    __tablename__ = "generated_video"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    campaign_id = Column(String, nullable=False, index=True)
    tenant_id = Column(String, nullable=False, index=True)
    generation_id = Column(String, nullable=False)
    asset_url = Column(String, nullable=False)
    job_id = Column(String, nullable=False)
    model_used = Column(String, nullable=False)
    script_format = Column(String, nullable=False)
    duration_seconds = Column(Float, nullable=False, default=0.0)
    status = Column(String, nullable=False)
    created_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        nullable=False,
    )

    __table_args__ = (
        Index("ix_generated_video_tenant_campaign", "tenant_id", "campaign_id"),
    )
