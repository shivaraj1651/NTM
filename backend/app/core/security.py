"""
Password hashing and JWT token utilities.

Uses bcrypt for password hashing and python-jose for JWT encoding/decoding.
"""

import bcrypt
from jose import JWTError, jwt
from datetime import datetime, timedelta, timezone
from backend.app.core.config import settings
from typing import Dict, Any, Optional


def hash_password(password: str) -> str:
    """Hash a password using bcrypt."""
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(password.encode(), salt)
    return hashed.decode()


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against its hash."""
    return bcrypt.checkpw(plain_password.encode(), hashed_password.encode())


# JWT exceptions
class TokenExpiredError(Exception):
    """Raised when JWT token has expired."""
    pass


class InvalidTokenError(Exception):
    """Raised when JWT token is invalid or malformed."""
    pass


# JWT token management
def create_access_token(
    data: Dict[str, Any],
    expires_delta: Optional[timedelta] = None
) -> str:
    """
    Create a JWT access token.

    Args:
        data: Claims to encode in the token
        expires_delta: Custom expiration time (default: from settings)

    Returns:
        Encoded JWT token string
    """
    to_encode = data.copy()

    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(
            minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES
        )

    to_encode.update({"exp": expire, "iat": datetime.now(timezone.utc)})

    encoded_jwt = jwt.encode(
        to_encode,
        settings.SECRET_KEY,
        algorithm=settings.ALGORITHM
    )
    return encoded_jwt


def decode_token(token: str) -> Dict[str, Any]:
    """
    Decode a JWT token and return claims.

    Args:
        token: JWT token string to decode

    Returns:
        Dict of decoded claims

    Raises:
        TokenExpiredError: If token has expired
        InvalidTokenError: If token is invalid or malformed
    """
    try:
        payload = jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=[settings.ALGORITHM]
        )
        return payload
    except JWTError as e:
        error_str = str(e).lower()
        if "expired" in error_str:
            raise TokenExpiredError("Token has expired")
        raise InvalidTokenError("Invalid token")
