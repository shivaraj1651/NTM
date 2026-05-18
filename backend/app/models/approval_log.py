"""SQLAlchemy model for ApprovalLog — insert-only audit log for entity state transitions."""

from datetime import datetime, timezone
import uuid

from sqlalchemy import Column, DateTime, String, Text, Index
from sqlalchemy.orm import declarative_base

Base = declarative_base()


class ApprovalLog(Base):
    __tablename__ = "approval_logs"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    tenant_id = Column(String, nullable=False)
    entity_type = Column(String, nullable=False)
    entity_id = Column(String, nullable=False)
    action = Column(String, nullable=False)
    # action values: submitted | approved | rejected
    actor_id = Column(String, nullable=False)
    notes = Column(Text, nullable=True)
    status_before = Column(String, nullable=True)
    status_after = Column(String, nullable=True)
    created_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    __table_args__ = (
        Index("ix_approval_logs_tenant", "tenant_id"),
        Index("ix_approval_logs_entity", "entity_id"),
        Index("ix_approval_logs_tenant_entity", "tenant_id", "entity_id"),
    )

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "tenant_id": self.tenant_id,
            "entity_type": self.entity_type,
            "entity_id": self.entity_id,
            "action": self.action,
            "actor_id": self.actor_id,
            "notes": self.notes,
            "status_before": self.status_before,
            "status_after": self.status_after,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
