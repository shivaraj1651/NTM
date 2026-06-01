import jwt

from backend.app.core.auth_state import decode_user_id
from backend.app.core.config import settings


def _make_token(sub):
    return jwt.encode(
        {"sub": sub, "aud": ["fastapi-users:auth"]},
        settings.SECRET_KEY, algorithm=settings.ALGORITHM,
    )

def test_decode_user_id_ok():
    assert decode_user_id(_make_token("user-123")) == "user-123"

def test_decode_user_id_bad_token():
    assert decode_user_id("garbage") is None
