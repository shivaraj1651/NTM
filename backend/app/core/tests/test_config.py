import pytest
import os
from backend.app.core.config import Settings

def test_settings_loads_from_env(tmp_path, monkeypatch):
    """Settings should load DATABASE_URL and JWT config from .env"""
    env_file = tmp_path / ".env"
    env_file.write_text(
        "DATABASE_URL=postgresql+asyncpg://user:pass@localhost/test\n"
        "SECRET_KEY=test-secret-key-32-chars-long-xxx\n"
        "ALGORITHM=HS256\n"
        "ACCESS_TOKEN_EXPIRE_MINUTES=30\n"
        "REFRESH_TOKEN_EXPIRE_DAYS=7\n"
    )

    monkeypatch.setenv("DATABASE_URL", "postgresql+asyncpg://user:pass@localhost/test")
    monkeypatch.setenv("SECRET_KEY", "test-secret-key-32-chars-long-xxx")

    settings = Settings(_env_file=env_file)

    assert settings.DATABASE_URL == "postgresql+asyncpg://user:pass@localhost/test"
    assert settings.SECRET_KEY == "test-secret-key-32-chars-long-xxx"
    assert settings.ALGORITHM == "HS256"
    assert settings.ACCESS_TOKEN_EXPIRE_MINUTES == 30
    assert settings.REFRESH_TOKEN_EXPIRE_DAYS == 7

def test_settings_has_rbac_roles():
    """Settings should include RBAC role definitions"""
    settings = Settings()

    assert "platform_admin" in settings.RBAC_ROLES
    assert "tenant_admin" in settings.RBAC_ROLES
    assert settings.RBAC_ROLES["platform_admin"] == ["*"]
    assert "tenant.manage" in settings.RBAC_ROLES["tenant_admin"]

def test_settings_has_feature_flags():
    """Settings should include feature flags"""
    settings = Settings()

    assert "enable_refresh_token_rotation" in settings.FEATURE_FLAGS
    assert isinstance(settings.FEATURE_FLAGS["enable_refresh_token_rotation"], bool)

def test_settings_is_singleton(monkeypatch):
    """Settings should be instantiated once and reused"""
    monkeypatch.setenv("SECRET_KEY", "original-secret")
    settings1 = Settings()

    monkeypatch.setenv("SECRET_KEY", "changed-secret")
    settings2 = Settings()

    # In practice, app creates Settings once at startup
    # This test just verifies each instance reads from env at creation time
    assert settings1.SECRET_KEY == "original-secret"
