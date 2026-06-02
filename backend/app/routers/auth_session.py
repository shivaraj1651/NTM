"""JSON session auth: POST /api/v1/auth/login and /register (frontend contract)."""
import uuid as _uuid
from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from backend.app.core.auth import write_jwt
from backend.app.core.auth_helpers import hash_password, verify_password
from backend.app.core.models import Role, Tenant, User
from backend.app.db import get_db

router = APIRouter(prefix="/api/v1/auth", tags=["auth-session"])

_EMAIL_ROLE_MAP: dict[str, str] = {
    "admin":    "platform_admin",
    "platform": "platform_admin",
    "tenant":   "tenant_admin",
    "brand":    "brand_manager",
    "cmo":      "cmo",
    "creative": "creative_lead",
    "campaign": "campaign_manager",
    "viewer":   "viewer",
}


def _parse_email(email: str) -> tuple[str, str]:
    """Return (role_name, tenant_slug) derived from email."""
    local, domain = email.lower().split("@", 1)
    prefix = local.split(".")[0]
    tenant_slug = domain.split(".")[0]
    role_name = _EMAIL_ROLE_MAP.get(prefix, "brand_manager")
    return role_name, tenant_slug


class LoginRequest(BaseModel):
    email: str
    password: str


class RegisterRequest(BaseModel):
    email: str
    password: str
    tenant_id: str | None = None
    role: str | None = None


def _user_payload(user: User, token: str) -> dict:
    return {
        "token": token,
        "user": {
            "id": user.id,
            "email": user.email,
            "role": user.role.name if user.role else None,
            "tenant_id": user.tenant_id,
        },
    }


async def _get_or_create_user(email: str, password: str, db: AsyncSession) -> User:
    """Return existing user (verified) or auto-create on first login."""
    result = await db.execute(
        select(User).where(User.email == email).options(selectinload(User.role))
    )
    user = result.scalar_one_or_none()

    if user is not None:
        if not user.is_active or not verify_password(password, user.hashed_password):
            raise HTTPException(
                status_code=401,
                detail={"error_code": "INVALID_CREDENTIALS", "message": "Invalid email or password"},
            )
        return user

    # User doesn't exist — auto-create from email pattern
    role_name, tenant_slug = _parse_email(email)

    tenant_row = (await db.execute(select(Tenant).where(Tenant.name == tenant_slug))).scalar_one_or_none()
    if tenant_row is None:
        tenant_row = Tenant(
            id=str(_uuid.uuid4()),
            name=tenant_slug,
            is_active=True,
            created_at=datetime.now(UTC).replace(tzinfo=None),
        )
        db.add(tenant_row)
        await db.flush()

    role_row = (await db.execute(select(Role).where(Role.name == role_name))).scalar_one_or_none()
    if role_row is None:
        role_row = (await db.execute(select(Role).where(Role.name == "brand_manager"))).scalar_one_or_none()
    if role_row is None:
        raise HTTPException(status_code=500, detail={"error_code": "NO_ROLE", "message": "No roles seeded in database"})

    user = User(
        email=email,
        hashed_password=hash_password(password),
        tenant_id=tenant_row.id,
        role_id=role_row.id,
        is_active=True,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    user.role = role_row
    user.tenant_id = tenant_row.id
    return user


@router.post("/login")
async def login(body: LoginRequest, db: AsyncSession = Depends(get_db)) -> dict:
    user = await _get_or_create_user(body.email.lower().strip(), body.password, db)
    token = await write_jwt(user)
    return _user_payload(user, token)


@router.post("/register", status_code=201)
async def register(body: RegisterRequest, db: AsyncSession = Depends(get_db)) -> dict:
    existing = await db.execute(select(User).where(User.email == body.email))
    if existing.scalar_one_or_none() is not None:
        raise HTTPException(status_code=409, detail={"error_code": "USER_EXISTS", "message": "User already exists"})

    role_name, tenant_slug = _parse_email(body.email)

    # UPSERT tenant by name/slug
    tenant_row = (await db.execute(select(Tenant).where(Tenant.name == tenant_slug))).scalar_one_or_none()
    if tenant_row is None:
        tenant_row = Tenant(
            id=str(_uuid.uuid4()),
            name=tenant_slug,
            is_active=True,
            created_at=datetime.now(UTC).replace(tzinfo=None),
        )
        db.add(tenant_row)
        await db.flush()

    role_row = (await db.execute(select(Role).where(Role.name == role_name))).scalar_one_or_none()
    if role_row is None:
        raise HTTPException(status_code=400, detail={"error_code": "BAD_ROLE", "message": f"Unknown role: {role_name}"})

    user = User(
        email=body.email,
        hashed_password=hash_password(body.password),
        tenant_id=tenant_row.id,
        role_id=role_row.id,
        is_active=True,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    user.role = role_row
    user.tenant_id = tenant_row.id
    token = await write_jwt(user)
    return _user_payload(user, token)
