"""PlatformConfigService — lookup platform configurations by channel and audience segment."""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.models.platform_config_template import PlatformConfigTemplate


class PlatformConfigService:
    """Service for retrieving platform-specific targeting configurations.

    Enables translation of generic Activation data into platform-specific targeting
    by looking up configurations stored in PlatformConfigTemplate.
    """

    def __init__(self, db_session: AsyncSession):
        """Initialize service with database session.

        Args:
            db_session: AsyncSession for database access
        """
        self.db_session = db_session

    async def get_platform_config(
        self,
        tenant_id: str,
        channel_enum: str,
        audience_segment: str
    ) -> PlatformConfigTemplate | None:
        """Retrieve platform configuration for a channel and audience segment.

        Queries the PlatformConfigTemplate table with tenant isolation.
        Returns None if no matching configuration is found.

        Args:
            tenant_id: The tenant identifier (UUID as string)
            channel_enum: Channel type (e.g., "google_ads", "meta_ads", "linkedin_ads")
            audience_segment: Audience segment (e.g., "brand_aware", "consideration")

        Returns:
            PlatformConfigTemplate if found, None otherwise
        """
        stmt = select(PlatformConfigTemplate).where(
            PlatformConfigTemplate.tenant_id == tenant_id,
            PlatformConfigTemplate.channel_enum == channel_enum,
            PlatformConfigTemplate.audience_segment == audience_segment,
        )
        result = await self.db_session.execute(stmt)
        return result.scalar_one_or_none()

    async def calculate_platform_budget(
        self,
        activation_cost: float,
        budget_multiplier: float
    ) -> float:
        """Calculate platform-specific budget using multiplier.

        Multiplies the activation cost by the platform-specific budget multiplier
        and rounds to 2 decimal places.

        Args:
            activation_cost: Base activation cost in dollars
            budget_multiplier: Platform-specific budget multiplier

        Returns:
            Calculated budget as float, rounded to 2 decimal places
        """
        return round(activation_cost * budget_multiplier, 2)
