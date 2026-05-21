"""Extended auth endpoints — password reset flow (M11).

POST /api/v1/auth/password-reset/request   — send OTP to email
POST /api/v1/auth/password-reset/confirm   — verify OTP + set new password
"""

import logging
import os
import secrets
import string
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, EmailStr
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.core.models import User
from backend.app.db import get_db

try:
    from passlib.context import CryptContext
    _pwd_ctx = CryptContext(schemes=["bcrypt"], deprecated="auto")
except ImportError:
    _pwd_ctx = None

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1/auth", tags=["auth-ext"])

# In-memory OTP store (replace with Redis in production)
_otp_store: dict[str, dict] = {}

_OTP_TTL_MINUTES = 10
_OTP_LENGTH = 6


def _generate_otp() -> str:
    return "".join(secrets.choice(string.digits) for _ in range(_OTP_LENGTH))


class PasswordResetRequest(BaseModel):
    email: EmailStr


class PasswordResetConfirm(BaseModel):
    email: EmailStr
    otp: str
    new_password: str


@router.post("/password-reset/request", status_code=200)
async def request_password_reset(
    body: PasswordResetRequest,
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Send a one-time password to the user's email for password reset."""
    stmt = select(User).where(User.email == body.email)
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()

    # Always return 200 — don't reveal whether email exists
    if user is None:
        logger.info("Password reset requested for unknown email: %s", body.email)
        return {"message": "If this email is registered, you will receive an OTP."}

    otp = _generate_otp()
    _otp_store[body.email] = {
        "otp": otp,
        "expires_at": datetime.now(timezone.utc) + timedelta(minutes=_OTP_TTL_MINUTES),
        "user_id": str(user.id),
    }

    # In production: send via AWS SES. Dev: log the OTP.
    ses_from = os.getenv("AWS_SES_FROM_EMAIL")
    if ses_from:
        logger.info("Would send OTP %s to %s via SES", otp, body.email)
    else:
        logger.warning("SES not configured — DEV OTP for %s: %s", body.email, otp)

    return {"message": "If this email is registered, you will receive an OTP."}


@router.post("/password-reset/confirm", status_code=200)
async def confirm_password_reset(
    body: PasswordResetConfirm,
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Verify OTP and set a new password."""
    record = _otp_store.get(body.email)

    if not record:
        raise HTTPException(status_code=400, detail="Invalid or expired OTP.")

    if datetime.now(timezone.utc) > record["expires_at"]:
        _otp_store.pop(body.email, None)
        raise HTTPException(status_code=400, detail="OTP has expired. Please request a new one.")

    if not secrets.compare_digest(record["otp"], body.otp):
        raise HTTPException(status_code=400, detail="Invalid OTP.")

    if _pwd_ctx is None:
        raise HTTPException(status_code=500, detail="Password hashing unavailable.")

    stmt = select(User).where(User.email == body.email)
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()
    if user is None:
        raise HTTPException(status_code=404, detail="User not found.")

    user.hashed_password = _pwd_ctx.hash(body.new_password)
    await db.commit()
    _otp_store.pop(body.email, None)

    logger.info("Password reset successful for: %s", body.email)
    return {"message": "Password updated successfully."}
