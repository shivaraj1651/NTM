"""Admin router — tenant, user, role, and audit-log management (platform_admin only)."""

import logging

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from backend.app.core.dependencies import require_role
from backend.app.core.models import Role, Tenant, User, UserRole
from backend.app.db import get_db
from backend.app.models.approval_log import ApprovalLog
from backend.app.schemas.admin import (  # noqa: F401 — re-exported for router use
    AuditLogResponse,
    RoleResponse,
    RoleUpdate,
    TenantCreate,
    TenantResponse,
    TenantUpdate,
    UserCreate,
    UserResponse,
    UserUpdate,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/admin", tags=["admin"])


# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.post("/tenants", response_model=TenantResponse, status_code=201)
async def create_tenant(
    body: TenantCreate,
    _: User = Depends(require_role([UserRole.PLATFORM_ADMIN])),
    db: AsyncSession = Depends(get_db),
) -> TenantResponse:
    tenant = Tenant(name=body.name)
    db.add(tenant)
    await db.commit()
    await db.refresh(tenant)
    return TenantResponse(
        id=tenant.id,
        name=tenant.name,
        is_active=tenant.is_active,
        created_at=tenant.created_at.isoformat(),
    )


@router.get("/tenants", response_model=list[TenantResponse])
async def list_tenants(
    _: User = Depends(require_role([UserRole.PLATFORM_ADMIN])),
    db: AsyncSession = Depends(get_db),
) -> list[TenantResponse]:
    result = await db.execute(select(Tenant).order_by(Tenant.created_at.desc()))
    tenants = result.scalars().all()
    return [
        TenantResponse(
            id=t.id,
            name=t.name,
            is_active=t.is_active,
            created_at=t.created_at.isoformat(),
        )
        for t in tenants
    ]


@router.post("/users", response_model=UserResponse, status_code=201)
async def create_user(
    body: UserCreate,
    _: User = Depends(require_role([UserRole.PLATFORM_ADMIN])),
    db: AsyncSession = Depends(get_db),
) -> UserResponse:
    from passlib.context import CryptContext
    pwd_ctx = CryptContext(schemes=["bcrypt"], deprecated="auto")

    role_result = await db.execute(select(Role).where(Role.name == body.role_name))
    role = role_result.scalar_one_or_none()
    if not role:
        raise HTTPException(status_code=400, detail=f"Role '{body.role_name}' not found")

    tenant_result = await db.execute(select(Tenant).where(Tenant.id == body.tenant_id))
    if not tenant_result.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Tenant not found")

    user = User(
        email=body.email,
        hashed_password=pwd_ctx.hash(body.password),
        tenant_id=body.tenant_id,
        role_id=role.id,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return UserResponse(
        id=user.id,
        email=user.email,
        tenant_id=user.tenant_id,
        is_active=user.is_active,
        created_at=user.created_at.isoformat(),
    )


@router.put("/users/{user_id}/role", response_model=UserResponse)
async def update_user_role(
    user_id: str,
    body: RoleUpdate,
    _: User = Depends(require_role([UserRole.PLATFORM_ADMIN])),
    db: AsyncSession = Depends(get_db),
) -> UserResponse:
    role_result = await db.execute(select(Role).where(Role.name == body.role_name))
    role = role_result.scalar_one_or_none()
    if not role:
        raise HTTPException(status_code=400, detail=f"Role '{body.role_name}' not found")

    user_result = await db.execute(select(User).where(User.id == user_id))
    target = user_result.scalar_one_or_none()
    if not target:
        raise HTTPException(status_code=404, detail="User not found")

    await db.execute(update(User).where(User.id == user_id).values(role_id=role.id))
    await db.commit()
    await db.refresh(target)
    return UserResponse(
        id=target.id,
        email=target.email,
        tenant_id=target.tenant_id,
        is_active=target.is_active,
        created_at=target.created_at.isoformat(),
    )


@router.get("/audit-log", response_model=list[AuditLogResponse])
async def get_audit_log(
    tenant_id: str | None = Query(None),
    limit: int = Query(50, le=200),
    offset: int = Query(0),
    _: User = Depends(require_role([UserRole.PLATFORM_ADMIN])),
    db: AsyncSession = Depends(get_db),
) -> list[AuditLogResponse]:
    stmt = select(ApprovalLog).order_by(ApprovalLog.created_at.desc()).limit(limit).offset(offset)
    if tenant_id:
        stmt = stmt.where(ApprovalLog.tenant_id == tenant_id)
    result = await db.execute(stmt)
    logs = result.scalars().all()
    return [
        AuditLogResponse(
            id=log.id,
            tenant_id=log.tenant_id,
            entity_type=log.entity_type,
            entity_id=log.entity_id,
            action=log.action,
            actor_id=log.actor_id,
            notes=log.notes,
            status_before=log.status_before,
            status_after=log.status_after,
            created_at=log.created_at.isoformat(),
        )
        for log in logs
    ]


# ── TASK 1: PATCH /tenants/{tenant_id} ───────────────────────────────────────

@router.patch("/tenants/{tenant_id}", response_model=TenantResponse)
async def update_tenant(
    tenant_id: str,
    body: TenantUpdate,
    _: User = Depends(require_role([UserRole.PLATFORM_ADMIN])),
    db: AsyncSession = Depends(get_db),
) -> TenantResponse:
    result = await db.execute(select(Tenant).where(Tenant.id == tenant_id))
    tenant = result.scalar_one_or_none()
    if tenant is None:
        raise HTTPException(status_code=404, detail="Tenant not found")
    tenant.is_active = body.is_active
    await db.commit()
    await db.refresh(tenant)
    return TenantResponse(
        id=tenant.id,
        name=tenant.name,
        is_active=tenant.is_active,
        created_at=tenant.created_at.isoformat(),
    )


# ── TASK 2: GET /tenants/{tenant_id}/users ────────────────────────────────────

@router.get("/tenants/{tenant_id}/users", response_model=list[UserResponse])
async def list_tenant_users(
    tenant_id: str,
    _: User = Depends(require_role([UserRole.PLATFORM_ADMIN])),
    db: AsyncSession = Depends(get_db),
) -> list[UserResponse]:
    result = await db.execute(
        select(User).options(selectinload(User.role)).where(User.tenant_id == tenant_id)
    )
    users = result.scalars().all()
    return [
        UserResponse(
            id=u.id,
            email=u.email,
            tenant_id=u.tenant_id,
            is_active=u.is_active,
            role=(u.role.name if u.role else None),
            created_at=u.created_at.isoformat(),
        )
        for u in users
    ]


# ── TASK 3: PATCH /users/{user_id} ───────────────────────────────────────────

@router.patch("/users/{user_id}", response_model=UserResponse)
async def update_user(
    user_id: str,
    body: UserUpdate,
    _: User = Depends(require_role([UserRole.PLATFORM_ADMIN])),
    db: AsyncSession = Depends(get_db),
) -> UserResponse:
    result = await db.execute(
        select(User).options(selectinload(User.role)).where(User.id == user_id)
    )
    target = result.scalar_one_or_none()
    if target is None:
        raise HTTPException(status_code=404, detail="User not found")
    target.is_active = body.is_active
    await db.commit()
    await db.refresh(target)
    return UserResponse(
        id=target.id,
        email=target.email,
        tenant_id=target.tenant_id,
        is_active=target.is_active,
        role=(target.role.name if target.role else None),
        created_at=target.created_at.isoformat(),
    )


# ── TASK 4: GET /roles ────────────────────────────────────────────────────────

@router.get("/roles", response_model=list[RoleResponse])
async def list_roles(
    _: User = Depends(require_role([UserRole.PLATFORM_ADMIN])),
    db: AsyncSession = Depends(get_db),
) -> list[RoleResponse]:
    result = await db.execute(select(Role).order_by(Role.name))
    roles = result.scalars().all()
    out: list[RoleResponse] = []
    for role in roles:
        count_result = await db.execute(
            select(func.count()).select_from(User).where(User.role_id == role.id)
        )
        out.append(
            RoleResponse(
                id=role.id,
                name=role.name,
                permissions=list(role.permissions or []),
                user_count=count_result.scalar() or 0,
            )
        )
    return out
