"""SQLAlchemy model for GeneratedImage output from Image Generator Agent (AGT-09)."""

import uuid
from datetime import UTC, datetime

from sqlalchemy import Column, DateTime, Index, String, Text
from sqlalchemy.dialects.postgresql import JSONB

from backend.app.models.base import Base


class GeneratedImage(Base):
    """Generated image record. Multi-tenant isolated, one row per generation."""

    __tablename__ = "generated_images"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    campaign_id = Column(String, nullable=False, index=True)
    tenant_id = Column(String, nullable=False, index=True)
    generation_id = Column(String, nullable=False)
    asset_url = Column(String, nullable=False)
    prompt_used = Column(Text, nullable=False)
    model_used = Column(String, nullable=False)
    generation_params = Column(JSONB, nullable=False, default=dict)
    image_format = Column(String, nullable=False)
    created_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        nullable=False,
    )

    __table_args__ = (
        Index("ix_generated_image_tenant_campaign", "tenant_id", "campaign_id"),
    )
