"""Database session management for SQLAlchemy async sessions.

Provides SessionLocal factory for creating async database sessions.
Used for dependency injection in FastAPI endpoints and Celery tasks.

Note: This is a placeholder. In actual deployment, the FastAPI app
will initialize the database engine and provide SessionLocal.
For Celery tasks, we create new connections as needed.
"""

import os
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
import logging

logger = logging.getLogger(__name__)


def create_session_local():
    """Create and return a SessionLocal factory.

    Returns:
        async_sessionmaker: Factory for creating AsyncSession instances
    """
    database_url = os.getenv(
        "DATABASE_URL",
        "sqlite+aiosqlite:///:memory:"
    )

    engine = create_async_engine(
        database_url,
        echo=False,
        pool_size=20,
        max_overflow=0,
        pool_pre_ping=True,
        future=True,
    )

    SessionLocal = async_sessionmaker(
        engine,
        class_=AsyncSession,
        expire_on_commit=False,
        future=True,
    )

    return SessionLocal


# Create default SessionLocal instance (lazy)
_session_local = None


def get_session_local():
    """Get or create the default SessionLocal factory."""
    global _session_local
    if _session_local is None:
        try:
            _session_local = create_session_local()
        except Exception as e:
            logger.warning(f"Failed to create SessionLocal: {e}")
            # Return a dummy that will fail at runtime
            return None
    return _session_local


# For backward compatibility with imports
class _SessionLocalProxy:
    """Proxy that creates SessionLocal on first call."""

    def __call__(self):
        """Create a new async session."""
        factory = get_session_local()
        if factory is None:
            raise RuntimeError("SessionLocal factory not initialized")
        return factory()

    def __getattr__(self, name):
        """Delegate to actual factory."""
        factory = get_session_local()
        if factory is None:
            raise RuntimeError("SessionLocal factory not initialized")
        return getattr(factory, name)


# Create singleton proxy
SessionLocal = _SessionLocalProxy()


async def get_db() -> AsyncSession:
    """Provide async database session for dependency injection.

    Yields:
        AsyncSession: Async database session

    Example:
        async def endpoint(db: AsyncSession = Depends(get_db)):
            result = await db.execute(select(User))
    """
    factory = get_session_local()
    if factory is None:
        raise RuntimeError("SessionLocal factory not initialized")

    async with factory() as session:
        try:
            yield session
        finally:
            await session.close()
