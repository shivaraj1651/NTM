from pydantic_settings import BaseSettings
from pydantic import ConfigDict
from typing import Dict, List, Optional

class Settings(BaseSettings):
    model_config = ConfigDict(env_file=".env", case_sensitive=True)

    # Database
    DATABASE_URL: Optional[str] = None

    # JWT Configuration
    SECRET_KEY: Optional[str] = None
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # RBAC Role Definitions
    RBAC_ROLES: Dict[str, List[str]] = {
        "platform_admin": ["*"],
        "tenant_admin": ["tenant.manage", "user.manage", "brand.manage"],
        "brand_manager": ["brand.manage", "campaign.manage"],
        "cmo": ["campaign.manage", "analytics.read"],
        "creative_lead": ["campaign.manage", "asset.manage"],
        "campaign_manager": ["campaign.manage"],
        "viewer": ["analytics.read"]
    }

    # Feature Flags
    FEATURE_FLAGS: Dict[str, bool] = {
        "enable_refresh_token_rotation": True,
        "require_2fa": False,
        "log_auth_events": True
    }

# Singleton instance
settings = Settings()
