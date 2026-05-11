"""
FastAPI-Users configuration with JWT authentication.

Sets up user management, JWT strategy, and auth dependencies.
"""

from fastapi_users import FastAPIUsers
from fastapi_users.authentication import AuthenticationBackend, JWTStrategy, BearerTransport
from fastapi_users_db_sqlalchemy import SQLAlchemyUserDatabase
from backend.app.core.models import User
from backend.app.core.config import settings


# Database adapter for FastAPI-Users
async def get_user_db(session):
    """Provide SQLAlchemy user database adapter.

    Args:
        session: SQLAlchemy AsyncSession (type not annotated to avoid FastAPI validation)
    """
    yield SQLAlchemyUserDatabase(session, User)


# JWT strategy getter - lazily loads settings to avoid import-time validation
def get_jwt_strategy() -> JWTStrategy:
    """Get JWT strategy with settings from config."""
    return JWTStrategy(
        secret=settings.SECRET_KEY,
        lifetime_seconds=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        algorithm=settings.ALGORITHM
    )


# Bearer transport for JWT tokens
bearer_transport = BearerTransport(tokenUrl="auth/jwt/login")


# Authentication backend combining transport and strategy
auth_backend = AuthenticationBackend(
    name="jwt",
    transport=bearer_transport,
    get_strategy=get_jwt_strategy,
)


# FastAPI-Users instance
fastapi_users = FastAPIUsers[User, str](
    get_user_db,
    [auth_backend],
)


# Current user dependency for route guards
current_user = fastapi_users.current_user(active=True)
