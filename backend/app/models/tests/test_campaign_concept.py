import pytest
from uuid import uuid4
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.models.campaign_concept import CampaignConcept


@pytest.mark.asyncio
async def test_create_campaign_concept(db_session: AsyncSession):
    tenant_id = str(uuid4())
    campaign_id = str(uuid4())
    concept = CampaignConcept(
        tenant_id=tenant_id,
        campaign_id=campaign_id,
        title="Bright Future",
        description="A campaign about sustainable growth.",
        strategy={"theme": "sustainability", "channels": ["meta_ads", "google_ads"]},
    )
    db_session.add(concept)
    await db_session.commit()

    result = await db_session.execute(
        select(CampaignConcept).where(CampaignConcept.campaign_id == campaign_id)
    )
    fetched = result.scalar_one()

    assert fetched.title == "Bright Future"
    assert fetched.strategy["theme"] == "sustainability"
    assert fetched.status == "pending"
    assert fetched.selected_by is None
    assert fetched.created_at is not None
    assert fetched.updated_at is not None


@pytest.mark.asyncio
async def test_campaign_concept_selected_by(db_session: AsyncSession):
    actor_id = str(uuid4())
    concept = CampaignConcept(
        tenant_id=str(uuid4()),
        campaign_id=str(uuid4()),
        title="Selected Concept",
        description="This one was chosen.",
        strategy={},
        status="selected",
        selected_by=actor_id,
    )
    db_session.add(concept)
    await db_session.commit()

    result = await db_session.execute(
        select(CampaignConcept).where(CampaignConcept.id == concept.id)
    )
    fetched = result.scalar_one()
    assert fetched.status == "selected"
    assert fetched.selected_by == actor_id


@pytest.mark.asyncio
async def test_campaign_concept_to_dict(db_session: AsyncSession):
    tenant_id = str(uuid4())
    concept = CampaignConcept(
        tenant_id=tenant_id,
        campaign_id=str(uuid4()),
        title="Dict Concept",
        description="For to_dict test.",
        strategy={"angle": "premium"},
    )
    db_session.add(concept)
    await db_session.commit()

    result = await db_session.execute(
        select(CampaignConcept).where(CampaignConcept.id == concept.id)
    )
    fetched = result.scalar_one()
    d = fetched.to_dict()

    assert d["tenant_id"] == tenant_id
    assert d["title"] == "Dict Concept"
    assert d["status"] == "pending"
    assert d["strategy"]["angle"] == "premium"
    assert d["selected_by"] is None
    assert "created_at" in d
    assert "updated_at" in d


@pytest.mark.asyncio
async def test_campaign_concept_tenant_isolation(db_session: AsyncSession):
    tenant_a = str(uuid4())
    tenant_b = str(uuid4())
    db_session.add(CampaignConcept(
        tenant_id=tenant_a, campaign_id=str(uuid4()),
        title="A Concept", description="desc a", strategy={},
    ))
    db_session.add(CampaignConcept(
        tenant_id=tenant_b, campaign_id=str(uuid4()),
        title="B Concept", description="desc b", strategy={},
    ))
    await db_session.commit()

    result = await db_session.execute(
        select(CampaignConcept).where(CampaignConcept.tenant_id == tenant_a)
    )
    concepts = result.scalars().all()
    assert len(concepts) == 1
    assert concepts[0].title == "A Concept"
