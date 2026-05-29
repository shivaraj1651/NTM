"""JSON session auth: POST /api/v1/auth/login and /register (frontend contract)."""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.core.auth import write_jwt
from backend.app.core.auth_helpers import hash_password, verify_password
from backend.app.core.models import User, Role
from backend.app.db import get_db

router = APIRouter(prefix="/api/v1/auth", tags=["auth-session"])


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


@router.post("/login")
async def login(body: LoginRequest, db: AsyncSession = Depends(get_db)) -> dict:
    result = await db.execute(
        select(User).where(User.email == body.email).options(selectinload(User.role))
    )
    user = result.scalar_one_or_none()
    if user is None or not user.is_active or not verify_password(body.password, user.hashed_password):
        raise HTTPException(status_code=401, detail={"error_code": "INVALID_CREDENTIALS", "message": "Invalid email or password"})
    token = await write_jwt(user)
    return _user_payload(user, token)


@router.post("/register", status_code=201)
async def register(body: RegisterRequest, db: AsyncSession = Depends(get_db)) -> dict:
    existing = await db.execute(select(User).where(User.email == body.email))
    if existing.scalar_one_or_none() is not None:
        raise HTTPException(status_code=409, detail={"error_code": "USER_EXISTS", "message": "User already exists"})

    role_name = body.role or "brand_manager"
    role_row = (await db.execute(select(Role).where(Role.name == role_name))).scalar_one_or_none()
    if role_row is None:
        raise HTTPException(status_code=400, detail={"error_code": "BAD_ROLE", "message": f"Unknown role {role_name}"})

    tenant_id = body.tenant_id or "tenant-acme"
    user = User(
        email=body.email, hashed_password=hash_password(body.password),
        tenant_id=tenant_id, role_id=role_row.id, is_active=True,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    user.role = role_row
    token = await write_jwt(user)
    return _user_payload(user, token)
