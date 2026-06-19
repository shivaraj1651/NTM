"""AuditMiddleware — stamps per-request audit context after tenant resolution.

Must be added BEFORE TenantValidationMiddleware in main.py so it runs as the
inner layer (after tenant validation has set request.state.user and tenant_id).
"""

import logging

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware

from backend.app.core.audit_context import AuditContext, set_audit_context

logger = logging.getLogger(__name__)


class AuditMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        user = getattr(request.state, "user", None)
        if user is not None:
            tenant_id = getattr(request.state, "tenant_id", None)
            role = user.role.name if getattr(user, "role", None) else None
            ip = request.client.host if request.client else None
            set_audit_context(AuditContext(
                actor_id=str(user.id),
                actor_role=role,
                tenant_id=tenant_id,
                ip_address=ip,
            ))
        return await call_next(request)
