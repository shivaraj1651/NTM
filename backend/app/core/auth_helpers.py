"""Shared password hashing/verification (bcrypt).

Wraps the bcrypt library directly (passlib 1.7.4 is incompatible with bcrypt>=4).
Exposes a pwd_context shim so callers can use either the context or the helpers.
"""
import bcrypt as _bcrypt


class _PwdContext:
    """Minimal passlib-style context backed by the bcrypt package."""

    def hash(self, raw: str) -> str:
        salt = _bcrypt.gensalt()
        return _bcrypt.hashpw(raw.encode(), salt).decode()

    def verify(self, raw: str, hashed: str) -> bool:
        try:
            return _bcrypt.checkpw(raw.encode(), hashed.encode())
        except Exception:
            return False


pwd_context = _PwdContext()


def hash_password(raw: str) -> str:
    return pwd_context.hash(raw)


def verify_password(raw: str, hashed: str) -> bool:
    try:
        return pwd_context.verify(raw, hashed)
    except Exception:
        return False
