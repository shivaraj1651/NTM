"""Admin router — tenant, user, role, and audit-log management (platform_admin only)."""

import logging
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, EmailStr
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.core.auth import current_user
from backend.app.core.models import User, Tenant, Role
from backend.app.models.approval_log import ApprovalLog
from backend.app.db import get_db

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/admin", tags=["admin"])


# ── Dependency ────────────────────────────────────────────────────────────────

async def require_platform_admin(user: User = Depends(current_user)) -> User:
    if user.role.name != "platform_admin":
        raise HTTPException(status_code=403, detail="Platform admin access required")
    return user


# ── Schemas ───────────────────────────────────────────────────────────────────

class TenantCreate(BaseModel):
    name: str


class TenantResponse(BaseModel):
    id: str
    name: str
    is_active: bool
    created_at: str

    model_config = {"from_attributes": True}


class UserCreate(BaseModel):
    email: EmailStr
    password: str
    tenant_id: str
    role_name: str = "viewer"


class UserResponse(BaseModel):
    id: str
    email: str
    tenant_id: str
    is_active: bool
    created_at: str

    model_config = {"from_attributes": True}


class RoleUpdate(BaseModel):
    role_name: str


class AuditLogResponse(BaseModel):
    id: str
    tenant_id: str
    entity_type: str
    entity_id: str
    action: str
    actor_id: str
    notes: Optional[str]
    status_before: Optional[str]
    status_after: Optional[str]
    created_at: str

    model_config = {"from_attributes": True}


# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.post("/tenants", response_model=TenantResponse, status_code=201)
async def create_tenant(
    body: TenantCreate,
    _: User = Depends(require_platform_admin),
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
    _: User = Depends(require_platform_admin),
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
    _: User = Depends(require_platform_admin),
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
    _: User = Depends(require_platform_admin),
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
    tenant_id: Optional[str] = Query(None),
    limit: int = Query(50, le=200),
    offset: int = Query(0),
    _: User = Depends(require_platform_admin),
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
