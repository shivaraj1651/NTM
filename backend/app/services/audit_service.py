"""AuditService — writes rows to the audit_trail table.

Uses a separate SQLAlchemy session so:
  - Audit writes succeed even if the caller's transaction rolls back.
  - Audit failures never surface to callers (swallowed with a warning log).
"""

import logging

from backend.app.core.audit_context import get_audit_context
from backend.app.db import get_session_local
from backend.app.models.audit_trail import AuditTrail

logger = logging.getLogger(__name__)


class AuditService:
    async def emit(
        self,
        entity_type: str,
        entity_id: str,
        action: str,
        status: str = "success",
        payload_before: dict | None = None,
        payload_after: dict | None = None,
    ) -> None:
        ctx = get_audit_context()
        if ctx is None:
            return
        try:
            factory = get_session_local()
            if factory is None:
                return
            async with factory() as session:
                row = AuditTrail(
                    tenant_id=ctx.tenant_id or "",
                    entity_type=entity_type,
                    entity_id=str(entity_id),
                    action=action,
                    actor_id=ctx.actor_id,
                    actor_role=ctx.actor_role,
                    status=status,
                    payload_before=payload_before,
                    payload_after=payload_after,
                )
                session.add(row)
                await session.commit()
        except Exception as exc:
            logger.warning(
                "Audit emit failed for %s/%s action=%s: %s",
                entity_type, entity_id, action, exc,
            )


def get_audit_service() -> AuditService:
    return AuditService()
