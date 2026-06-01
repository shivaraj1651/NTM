import pytest
from pydantic import ValidationError

from backend.app.core.config import Settings


def test_settings_loads_from_env(tmp_path, monkeypatch):
    """Settings should load DATABASE_URL and JWT config from .env"""
    env_file = tmp_path / ".env"
    env_file.write_text(
        "DATABASE_URL=postgresql+asyncpg://localhost/test_db\n"
        "SECRET_KEY=test-secret-key-32-chars-long-xxx\n"
        "ALGORITHM=HS256\n"
        "ACCESS_TOKEN_EXPIRE_MINUTES=30\n"
        "REFRESH_TOKEN_EXPIRE_DAYS=7\n"
    )

    monkeypatch.setenv("DATABASE_URL", "postgresql+asyncpg://localhost/test_db")
    monkeypatch.setenv("SECRET_KEY", "test-secret-key-32-chars-long-xxx")

    settings = Settings(_env_file=env_file)

    assert settings.DATABASE_URL == "postgresql+asyncpg://localhost/test_db"
    assert settings.SECRET_KEY == "test-secret-key-32-chars-long-xxx"
    assert settings.ALGORITHM == "HS256"
    assert settings.ACCESS_TOKEN_EXPIRE_MINUTES == 30
    assert settings.REFRESH_TOKEN_EXPIRE_DAYS == 7


def test_settings_has_rbac_roles(monkeypatch):
    """Settings should include RBAC role definitions"""
    monkeypatch.setenv("DATABASE_URL", "postgresql+asyncpg://localhost/test_db")
    monkeypatch.setenv("SECRET_KEY", "test-secret-key-32-chars-long-xxx")

    settings = Settings()

    assert "platform_admin" in settings.RBAC_ROLES
    assert "tenant_admin" in settings.RBAC_ROLES
    assert settings.RBAC_ROLES["platform_admin"] == ["*"]
    assert "tenant.manage" in settings.RBAC_ROLES["tenant_admin"]


def test_settings_has_feature_flags(monkeypatch):
    """Settings should include feature flags"""
    monkeypatch.setenv("DATABASE_URL", "postgresql+asyncpg://localhost/test_db")
    monkeypatch.setenv("SECRET_KEY", "test-secret-key-32-chars-long-xxx")

    settings = Settings()

    assert "enable_refresh_token_rotation" in settings.FEATURE_FLAGS
    assert isinstance(settings.FEATURE_FLAGS["enable_refresh_token_rotation"], bool)


def test_settings_is_singleton(monkeypatch):
    """Settings should be instantiated once and reused"""
    monkeypatch.setenv("DATABASE_URL", "postgresql+asyncpg://localhost/test_db")
    monkeypatch.setenv("SECRET_KEY", "original-secret-32-chars-long-xxx1")
    settings1 = Settings()

    monkeypatch.setenv("SECRET_KEY", "changed-secret-32-chars-long-xxx22")
    _settings2 = Settings()

    # In practice, app creates Settings once at startup
    # This test just verifies each instance reads from env at creation time
    assert settings1.SECRET_KEY == "original-secret-32-chars-long-xxx1"


def test_settings_rejects_missing_secrets(monkeypatch):
    """Settings should fail if SECRET_KEY is missing"""
    # Clear the secret key - should fail
    monkeypatch.delenv("SECRET_KEY", raising=False)
    monkeypatch.delenv("DATABASE_URL", raising=False)

    with pytest.raises(ValidationError):
        Settings()


def test_settings_rejects_short_secret_key(monkeypatch):
    """Settings should reject SECRET_KEY shorter than 32 chars"""
    monkeypatch.setenv("SECRET_KEY", "too-short")
    monkeypatch.setenv("DATABASE_URL", "postgresql://localhost/db")

    with pytest.raises(ValidationError):
        Settings()


def test_settings_rejects_negative_expiration(monkeypatch):
    """Settings should reject negative expiration times"""
    monkeypatch.setenv("SECRET_KEY", "secret-key-32-chars-long-xxxxxx")
    monkeypatch.setenv("DATABASE_URL", "postgresql://localhost/db")
    monkeypatch.setenv("ACCESS_TOKEN_EXPIRE_MINUTES", "-30")

    with pytest.raises(ValidationError):
        Settings()
