"""Per-request audit context stored in a ContextVar.

Set by AuditMiddleware after TenantValidationMiddleware populates request.state.
Read by AuditService.emit() to stamp every audit row with actor/tenant/IP.
"""

from contextvars import ContextVar
from dataclasses import dataclass


@dataclass
class AuditContext:
    actor_id: str
    actor_role: str | None
    tenant_id: str | None
    ip_address: str | None


_audit_ctx: ContextVar[AuditContext | None] = ContextVar("audit_ctx", default=None)


def set_audit_context(ctx: AuditContext | None) -> None:
    _audit_ctx.set(ctx)


def get_audit_context() -> AuditContext | None:
    return _audit_ctx.get()
