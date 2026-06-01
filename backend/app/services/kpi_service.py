"""KPIService — service layer for querying KPI records (TASK-020)."""


from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.models.kpi import KPI


class KPIService:
    """Service for fetching and querying KPI records."""

    def __init__(self, db_session: AsyncSession):
        """Initialize KPIService with a database session.

        Args:
            db_session: AsyncSession for database operations
        """
        self.db = db_session

    async def get_kpis_for_activation(
        self,
        campaign_id: str,
        channel: str,
        audience_segment: str,
        tenant_id: str
    ) -> list[KPI]:
        """Fetch KPIs for a specific activation (campaign + channel + audience).

        Args:
            campaign_id: Campaign identifier
            channel: Channel enum (e.g., google_ads, meta_ads, linkedin_ads)
            audience_segment: Audience segment (e.g., brand_aware, consideration)
            tenant_id: Tenant identifier for multi-tenant isolation

        Returns:
            List of KPI records matching the criteria
        """
        result = await self.db.execute(
            select(KPI).where(
                KPI.campaign_id == campaign_id,
                KPI.channel_enum == channel,
                KPI.audience_segment == audience_segment,
                KPI.tenant_id == tenant_id
            )
        )
        return result.scalars().all()

    async def get_kpi_by_name(
        self,
        campaign_id: str,
        channel: str,
        audience_segment: str,
        kpi_name: str,
        tenant_id: str
    ) -> KPI | None:
        """Fetch a specific KPI by name.

        Args:
            campaign_id: Campaign identifier
            channel: Channel enum (e.g., google_ads, meta_ads, linkedin_ads)
            audience_segment: Audience segment (e.g., brand_aware, consideration)
            kpi_name: KPI name (e.g., conversion_rate, cost_per_click)
            tenant_id: Tenant identifier for multi-tenant isolation

        Returns:
            KPI record if found, None otherwise
        """
        result = await self.db.execute(
            select(KPI).where(
                KPI.campaign_id == campaign_id,
                KPI.channel_enum == channel,
                KPI.audience_segment == audience_segment,
                KPI.kpi_name == kpi_name,
                KPI.tenant_id == tenant_id
            )
        )
        return result.scalar_one_or_none()
