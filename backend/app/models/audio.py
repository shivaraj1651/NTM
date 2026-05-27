"""SQLAlchemy model for GeneratedAudio output from Audio Generator Agent (AGT-10)."""

import uuid
from datetime import datetime, timezone

from sqlalchemy import Column, DateTime, Float, Index, String
from backend.app.models.base import Base

class GeneratedAudio(Base):
    """Generated audio record. Multi-tenant isolated, one row per generation."""

    __tablename__ = "generated_audio"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    campaign_id = Column(String, nullable=False, index=True)
    tenant_id = Column(String, nullable=False, index=True)
    generation_id = Column(String, nullable=False)
    asset_url = Column(String, nullable=False)
    voice_id = Column(String, nullable=False)
    model_used = Column(String, nullable=False)
    script_format = Column(String, nullable=False)
    duration_seconds = Column(Float, nullable=False, default=0.0)
    created_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    __table_args__ = (
        Index("ix_generated_audio_tenant_campaign", "tenant_id", "campaign_id"),
    )
