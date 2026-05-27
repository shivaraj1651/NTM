"""SQLAlchemy model for AuditTrail — immutable log of entity actions per tenant."""

from datetime import datetime, timezone
import uuid

from sqlalchemy import Column, DateTime, Index, JSON, String
from backend.app.models.base import Base

class AuditTrail(Base):
    __tablename__ = "audit_trail"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    tenant_id = Column(String, nullable=False)
    entity_type = Column(String, nullable=False)   # e.g. "mandate", "campaign"
    entity_id = Column(String, nullable=False)
    action = Column(String, nullable=False)        # e.g. "create", "update", "delete"
    actor_id = Column(String, nullable=False)
    actor_role = Column(String, nullable=True)
    status = Column(String, nullable=False, default="success")
    payload_before = Column(JSON, nullable=True)
    payload_after = Column(JSON, nullable=True)
    created_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    __table_args__ = (
        Index("ix_audit_trail_tenant", "tenant_id"),
        Index("ix_audit_trail_actor", "actor_id"),
    )

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "tenant_id": self.tenant_id,
            "entity_type": self.entity_type,
            "entity_id": self.entity_id,
            "action": self.action,
            "actor_id": self.actor_id,
            "actor_role": self.actor_role,
            "status": self.status,
            "payload_before": self.payload_before,
            "payload_after": self.payload_after,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
