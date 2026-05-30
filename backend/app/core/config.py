"""
Configuration management for NTM application.

Loads settings from environment variables (.env file) with validation.
Ensures required secrets are present and properly formatted.
"""

from pydantic_settings import BaseSettings
from pydantic import ConfigDict, Field
from typing import Dict, List

# Define role definitions as constants to avoid mutable default issues
DEFAULT_RBAC_ROLES = {
    "platform_admin": ["*"],
    "tenant_admin": ["tenant.manage", "user.manage", "brand.manage"],
    "brand_manager": ["brand.manage", "campaign.manage"],
    "cmo": ["campaign.manage", "analytics.read"],
    "creative_lead": ["campaign.manage", "asset.manage"],
    "campaign_manager": ["campaign.manage"],
    "viewer": ["analytics.read"]
}

DEFAULT_FEATURE_FLAGS = {
    "enable_refresh_token_rotation": True,
    "require_2fa": False,
    "log_auth_events": True
}


class Settings(BaseSettings):
    """
    Application settings loaded from environment variables.

    Enforces validation on security-critical fields (SECRET_KEY, DATABASE_URL)
    and reasonable bounds on token expiration times.
    """

    model_config = ConfigDict(case_sensitive=True, extra="ignore")

    # Database
    DATABASE_URL: str = Field(..., description="PostgreSQL connection URL with asyncpg driver")

    # JWT Configuration
    SECRET_KEY: str = Field(..., min_length=32, description="JWT signing key (minimum 32 characters for security)")
    ALGORITHM: str = Field(default="HS256", description="JWT algorithm")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = Field(default=30, gt=0, le=1440, description="Access token TTL in minutes (1-24 hours)")
    REFRESH_TOKEN_EXPIRE_DAYS: int = Field(default=7, gt=0, le=365, description="Refresh token TTL in days (1-365 days)")

    # RBAC Role Definitions
    RBAC_ROLES: Dict[str, List[str]] = Field(default_factory=lambda: DEFAULT_RBAC_ROLES.copy())

    # Feature Flags
    FEATURE_FLAGS: Dict[str, bool] = Field(default_factory=lambda: DEFAULT_FEATURE_FLAGS.copy())

# Singleton instance - created lazily to avoid requiring env vars at import time
_settings_instance = None


def get_settings() -> Settings:
    """Get or create the settings singleton instance."""
    global _settings_instance
    if _settings_instance is None:
        _settings_instance = Settings(_env_file=".env")
    return _settings_instance


# For backward compatibility, create a lazy proxy
class _SettingsProxy:
    """Lazy proxy for settings singleton to avoid loading at import time."""

    def __getattr__(self, name: str):
        return getattr(get_settings(), name)


settings = _SettingsProxy()
