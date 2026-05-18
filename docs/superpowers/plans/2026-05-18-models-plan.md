# SQLAlchemy DB Models Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add 8 missing SQLAlchemy ORM models to `backend/app/models/` covering Client, Mandate, Campaign, CampaignConcept, Activation, Budget, ApprovalLog, and PhysicalActivationLog.

**Architecture:** Each model lives in its own file with its own `declarative_base()`, matching the 1.x style from `platform_config_template.py` (the canonical pattern). `tenant_id` is denormalized on every model — no FK constraint. Two models (Client, CampaignConcept) use optional pgvector `Vector(1536)` columns, guarded by `try/except ImportError`; SQLite tests skip the embedding column. Each task also updates the shared `conftest.py` to register the new Base so `db_session` creates that model's table.

**Tech Stack:** Python 3.12, SQLAlchemy 1.x declarative, PostgreSQL 16 + pgvector, pytest-asyncio, aiosqlite (SQLite in-memory for tests)

---

## File Structure

**Created:**
- `backend/app/models/client.py`
- `backend/app/models/mandate.py`
- `backend/app/models/campaign.py`
- `backend/app/models/campaign_concept.py`
- `backend/app/models/activation.py`
- `backend/app/models/budget.py`
- `backend/app/models/approval_log.py`
- `backend/app/models/physical_activation_log.py`
- `backend/app/models/tests/test_client.py`
- `backend/app/models/tests/test_mandate.py`
- `backend/app/models/tests/test_campaign.py`
- `backend/app/models/tests/test_campaign_concept.py`
- `backend/app/models/tests/test_activation.py`
- `backend/app/models/tests/test_budget.py`
- `backend/app/models/tests/test_approval_log.py`
- `backend/app/models/tests/test_physical_activation_log.py`

**Modified:**
- `backend/app/models/tests/conftest.py` — one new Base import + `create_all` call added per task

---

### Task 1: Client model

**Files:**
- Create: `backend/app/models/client.py`
- Modify: `backend/app/models/tests/conftest.py`
- Test: `backend/app/models/tests/test_client.py`

- [ ] **Step 1: Write the failing test**

```python
# backend/app/models/tests/test_client.py
import pytest
from uuid import uuid4
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.models.client import Client


@pytest.mark.asyncio
async def test_create_client(db_session: AsyncSession):
    tenant_id = str(uuid4())
    client = Client(
        tenant_id=tenant_id,
        org_name="Acme Corp",
        industry="Technology",
        logo_url="https://example.com/logo.png",
        brand_guidelines_url="https://example.com/brand.pdf",
        competitors=["CompetitorA", "CompetitorB"],
    )
    db_session.add(client)
    await db_session.commit()

    result = await db_session.execute(
        select(Client).where(Client.tenant_id == tenant_id)
    )
    fetched = result.scalar_one()

    assert fetched.org_name == "Acme Corp"
    assert fetched.industry == "Technology"
    assert fetched.competitors == ["CompetitorA", "CompetitorB"]
    assert fetched.created_at is not None
    assert fetched.updated_at is not None


@pytest.mark.asyncio
async def test_client_nullable_fields(db_session: AsyncSession):
    client = Client(
        tenant_id=str(uuid4()),
        org_name="Minimal Corp",
        industry="Finance",
    )
    db_session.add(client)
    await db_session.commit()

    result = await db_session.execute(
        select(Client).where(Client.org_name == "Minimal Corp")
    )
    fetched = result.scalar_one()

    assert fetched.logo_url is None
    assert fetched.brand_guidelines_url is None
    assert fetched.competitors == []


@pytest.mark.asyncio
async def test_client_to_dict(db_session: AsyncSession):
    tenant_id = str(uuid4())
    client = Client(
        tenant_id=tenant_id,
        org_name="Dict Corp",
        industry="Retail",
        competitors=["X", "Y"],
    )
    db_session.add(client)
    await db_session.commit()

    result = await db_session.execute(
        select(Client).where(Client.id == client.id)
    )
    fetched = result.scalar_one()
    d = fetched.to_dict()

    assert d["tenant_id"] == tenant_id
    assert d["org_name"] == "Dict Corp"
    assert d["industry"] == "Retail"
    assert d["competitors"] == ["X", "Y"]
    assert "created_at" in d
    assert "updated_at" in d


@pytest.mark.asyncio
async def test_client_tenant_isolation(db_session: AsyncSession):
    tenant_a = str(uuid4())
    tenant_b = str(uuid4())
    db_session.add(Client(tenant_id=tenant_a, org_name="Corp A", industry="Tech"))
    db_session.add(Client(tenant_id=tenant_b, org_name="Corp B", industry="Finance"))
    await db_session.commit()

    result = await db_session.execute(
        select(Client).where(Client.tenant_id == tenant_a)
    )
    clients = result.scalars().all()
    assert len(clients) == 1
    assert clients[0].org_name == "Corp A"
```

- [ ] **Step 2: Run test to verify it fails**

```
cd D:\staging\ntm
python -m pytest backend/app/models/tests/test_client.py -v
```

Expected: FAIL — `ModuleNotFoundError: No module named 'backend.app.models.client'`

- [ ] **Step 3: Create the model**

```python
# backend/app/models/client.py
"""SQLAlchemy model for Client — org profile with brand metadata and optional embedding."""

from datetime import datetime, timezone
import uuid

from sqlalchemy import Column, DateTime, String, Index
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import declarative_base

try:
    from pgvector.sqlalchemy import Vector
    HAS_PGVECTOR = True
except ImportError:
    HAS_PGVECTOR = False

Base = declarative_base()


class Client(Base):
    __tablename__ = "clients"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    tenant_id = Column(String, nullable=False, index=True)
    org_name = Column(String, nullable=False)
    industry = Column(String, nullable=False)
    logo_url = Column(String, nullable=True)
    brand_guidelines_url = Column(String, nullable=True)
    competitors = Column(JSONB, nullable=False, default=lambda: [])
    created_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    updated_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    if HAS_PGVECTOR:
        brand_embedding = Column(Vector(1536), nullable=True)

    __table_args__ = (
        Index("ix_clients_tenant", "tenant_id"),
    )

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "tenant_id": self.tenant_id,
            "org_name": self.org_name,
            "industry": self.industry,
            "logo_url": self.logo_url,
            "brand_guidelines_url": self.brand_guidelines_url,
            "competitors": self.competitors,
            "brand_embedding": getattr(self, "brand_embedding", None),
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
```

- [ ] **Step 4: Update conftest.py — add Client Base**

In `backend/app/models/tests/conftest.py`, add one import after the existing Base imports:
```python
from backend.app.models.client import Base as Base4
```

Inside the `db_session` fixture, inside `async with engine.begin() as conn:`, add:
```python
        await conn.run_sync(Base4.metadata.create_all)
```

- [ ] **Step 5: Run tests to verify they pass**

```
python -m pytest backend/app/models/tests/test_client.py -v
```

Expected: 4 passed

- [ ] **Step 6: Commit**

```
git add backend/app/models/client.py backend/app/models/tests/test_client.py backend/app/models/tests/conftest.py
git commit -m "[TASK-002] feat: add Client model with tests"
```

---

### Task 2: Mandate model

**Files:**
- Create: `backend/app/models/mandate.py`
- Modify: `backend/app/models/tests/conftest.py`
- Test: `backend/app/models/tests/test_mandate.py`

- [ ] **Step 1: Write the failing test**

```python
# backend/app/models/tests/test_mandate.py
import pytest
from datetime import date
from uuid import uuid4
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.models.mandate import Mandate


@pytest.mark.asyncio
async def test_create_mandate(db_session: AsyncSession):
    tenant_id = str(uuid4())
    mandate = Mandate(
        tenant_id=tenant_id,
        client_id=str(uuid4()),
        name="Q3 Brand Awareness",
        objective="awareness",
        region="APAC",
        countries=["India", "Singapore"],
        competitors=["BrandX", "BrandY"],
        total_budget=500000.0,
        currency="USD",
        start_date=date(2025, 7, 1),
        end_date=date(2025, 9, 30),
    )
    db_session.add(mandate)
    await db_session.commit()

    result = await db_session.execute(
        select(Mandate).where(Mandate.tenant_id == tenant_id)
    )
    fetched = result.scalar_one()

    assert fetched.name == "Q3 Brand Awareness"
    assert fetched.objective == "awareness"
    assert fetched.countries == ["India", "Singapore"]
    assert fetched.competitors == ["BrandX", "BrandY"]
    assert fetched.total_budget == 500000.0
    assert fetched.status == "draft"
    assert fetched.description is None
    assert fetched.created_at is not None
    assert fetched.updated_at is not None


@pytest.mark.asyncio
async def test_mandate_defaults(db_session: AsyncSession):
    mandate = Mandate(
        tenant_id=str(uuid4()),
        client_id=str(uuid4()),
        name="Minimal Mandate",
        objective="conversion",
        region="EMEA",
        countries=["UK"],
        total_budget=100000.0,
        start_date=date(2025, 1, 1),
        end_date=date(2025, 6, 30),
    )
    db_session.add(mandate)
    await db_session.commit()

    result = await db_session.execute(
        select(Mandate).where(Mandate.name == "Minimal Mandate")
    )
    fetched = result.scalar_one()

    assert fetched.status == "draft"
    assert fetched.currency == "USD"
    assert fetched.competitors == []
    assert fetched.description is None


@pytest.mark.asyncio
async def test_mandate_to_dict(db_session: AsyncSession):
    tenant_id = str(uuid4())
    mandate = Mandate(
        tenant_id=tenant_id,
        client_id=str(uuid4()),
        name="Dict Mandate",
        objective="loyalty",
        region="Americas",
        countries=["USA"],
        total_budget=250000.0,
        start_date=date(2025, 3, 1),
        end_date=date(2025, 8, 31),
    )
    db_session.add(mandate)
    await db_session.commit()

    result = await db_session.execute(
        select(Mandate).where(Mandate.id == mandate.id)
    )
    fetched = result.scalar_one()
    d = fetched.to_dict()

    assert d["tenant_id"] == tenant_id
    assert d["name"] == "Dict Mandate"
    assert d["status"] == "draft"
    assert d["start_date"] == "2025-03-01"
    assert d["end_date"] == "2025-08-31"
    assert "created_at" in d
    assert "updated_at" in d


@pytest.mark.asyncio
async def test_mandate_tenant_isolation(db_session: AsyncSession):
    tenant_a = str(uuid4())
    tenant_b = str(uuid4())
    db_session.add(Mandate(
        tenant_id=tenant_a, client_id=str(uuid4()), name="A Mandate",
        objective="awareness", region="APAC", countries=["Japan"],
        total_budget=100000.0, start_date=date(2025, 1, 1), end_date=date(2025, 12, 31),
    ))
    db_session.add(Mandate(
        tenant_id=tenant_b, client_id=str(uuid4()), name="B Mandate",
        objective="conversion", region="EMEA", countries=["France"],
        total_budget=200000.0, start_date=date(2025, 1, 1), end_date=date(2025, 12, 31),
    ))
    await db_session.commit()

    result = await db_session.execute(
        select(Mandate).where(Mandate.tenant_id == tenant_a)
    )
    mandates = result.scalars().all()
    assert len(mandates) == 1
    assert mandates[0].name == "A Mandate"
```

- [ ] **Step 2: Run test to verify it fails**

```
python -m pytest backend/app/models/tests/test_mandate.py -v
```

Expected: FAIL — `ModuleNotFoundError: No module named 'backend.app.models.mandate'`

- [ ] **Step 3: Create the model**

```python
# backend/app/models/mandate.py
"""SQLAlchemy model for Mandate — client campaign mandate with geography and budget."""

from datetime import datetime, timezone
import uuid

from sqlalchemy import Column, Date, DateTime, Float, String, Text, Index
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import declarative_base

Base = declarative_base()


class Mandate(Base):
    __tablename__ = "mandates"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    tenant_id = Column(String, nullable=False, index=True)
    client_id = Column(String, nullable=False, index=True)
    name = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    objective = Column(String, nullable=False)
    # objective values: awareness | consideration | conversion | loyalty | engagement
    region = Column(String, nullable=False)
    countries = Column(JSONB, nullable=False, default=lambda: [])
    competitors = Column(JSONB, nullable=False, default=lambda: [])
    total_budget = Column(Float, nullable=False)
    currency = Column(String, nullable=False, default="USD")
    start_date = Column(Date, nullable=False)
    end_date = Column(Date, nullable=False)
    status = Column(String, nullable=False, default="draft")
    # status values: draft | pending_review | confirmed | rejected
    created_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    updated_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    __table_args__ = (
        Index("ix_mandates_tenant", "tenant_id"),
        Index("ix_mandates_client", "client_id"),
        Index("ix_mandates_tenant_client", "tenant_id", "client_id"),
    )

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "tenant_id": self.tenant_id,
            "client_id": self.client_id,
            "name": self.name,
            "description": self.description,
            "objective": self.objective,
            "region": self.region,
            "countries": self.countries,
            "competitors": self.competitors,
            "total_budget": self.total_budget,
            "currency": self.currency,
            "start_date": self.start_date.isoformat() if self.start_date else None,
            "end_date": self.end_date.isoformat() if self.end_date else None,
            "status": self.status,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
```

- [ ] **Step 4: Update conftest.py — add Mandate Base**

In `backend/app/models/tests/conftest.py`, add one import after the existing Base imports:
```python
from backend.app.models.mandate import Base as Base5
```

Inside the `db_session` fixture, inside `async with engine.begin() as conn:`, add:
```python
        await conn.run_sync(Base5.metadata.create_all)
```

- [ ] **Step 5: Run tests to verify they pass**

```
python -m pytest backend/app/models/tests/test_mandate.py -v
```

Expected: 4 passed

- [ ] **Step 6: Commit**

```
git add backend/app/models/mandate.py backend/app/models/tests/test_mandate.py backend/app/models/tests/conftest.py
git commit -m "[TASK-002] feat: add Mandate model with tests"
```

---

### Task 3: Campaign model

**Files:**
- Create: `backend/app/models/campaign.py`
- Modify: `backend/app/models/tests/conftest.py`
- Test: `backend/app/models/tests/test_campaign.py`

- [ ] **Step 1: Write the failing test**

```python
# backend/app/models/tests/test_campaign.py
import pytest
from uuid import uuid4
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.models.campaign import Campaign


@pytest.mark.asyncio
async def test_create_campaign(db_session: AsyncSession):
    tenant_id = str(uuid4())
    campaign = Campaign(
        tenant_id=tenant_id,
        mandate_id=str(uuid4()),
        client_id=str(uuid4()),
        name="Q3 APAC Campaign",
        description="Full funnel push across APAC markets.",
    )
    db_session.add(campaign)
    await db_session.commit()

    result = await db_session.execute(
        select(Campaign).where(Campaign.tenant_id == tenant_id)
    )
    fetched = result.scalar_one()

    assert fetched.name == "Q3 APAC Campaign"
    assert fetched.description == "Full funnel push across APAC markets."
    assert fetched.status == "pending"
    assert fetched.created_at is not None
    assert fetched.updated_at is not None


@pytest.mark.asyncio
async def test_campaign_optional_fields(db_session: AsyncSession):
    campaign = Campaign(
        tenant_id=str(uuid4()),
        name="Bare Campaign",
    )
    db_session.add(campaign)
    await db_session.commit()

    result = await db_session.execute(
        select(Campaign).where(Campaign.name == "Bare Campaign")
    )
    fetched = result.scalar_one()

    assert fetched.status == "pending"
    assert fetched.mandate_id is None
    assert fetched.client_id is None
    assert fetched.description is None


@pytest.mark.asyncio
async def test_campaign_to_dict(db_session: AsyncSession):
    tenant_id = str(uuid4())
    campaign = Campaign(
        tenant_id=tenant_id,
        name="Dict Campaign",
        description="Testing to_dict.",
        status="planned",
    )
    db_session.add(campaign)
    await db_session.commit()

    result = await db_session.execute(
        select(Campaign).where(Campaign.id == campaign.id)
    )
    fetched = result.scalar_one()
    d = fetched.to_dict()

    assert d["tenant_id"] == tenant_id
    assert d["name"] == "Dict Campaign"
    assert d["description"] == "Testing to_dict."
    assert d["status"] == "planned"
    assert "created_at" in d
    assert "updated_at" in d


@pytest.mark.asyncio
async def test_campaign_tenant_isolation(db_session: AsyncSession):
    tenant_a = str(uuid4())
    tenant_b = str(uuid4())
    db_session.add(Campaign(tenant_id=tenant_a, name="Campaign A"))
    db_session.add(Campaign(tenant_id=tenant_b, name="Campaign B"))
    await db_session.commit()

    result = await db_session.execute(
        select(Campaign).where(Campaign.tenant_id == tenant_a)
    )
    campaigns = result.scalars().all()
    assert len(campaigns) == 1
    assert campaigns[0].name == "Campaign A"
```

- [ ] **Step 2: Run test to verify it fails**

```
python -m pytest backend/app/models/tests/test_campaign.py -v
```

Expected: FAIL — `ModuleNotFoundError: No module named 'backend.app.models.campaign'`

- [ ] **Step 3: Create the model**

```python
# backend/app/models/campaign.py
"""SQLAlchemy model for Campaign — core campaign entity."""

from datetime import datetime, timezone
import uuid

from sqlalchemy import Column, DateTime, String, Text, Index
from sqlalchemy.orm import declarative_base

Base = declarative_base()


class Campaign(Base):
    __tablename__ = "campaigns"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    tenant_id = Column(String, nullable=False, index=True)
    mandate_id = Column(String, nullable=True, index=True)
    client_id = Column(String, nullable=True, index=True)
    name = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    status = Column(String, nullable=False, default="pending")
    # status values: pending | concepts_ready | confirmed | planned |
    #                budget_proposed | approved | creative_generating |
    #                creative_ready | live
    created_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    updated_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    __table_args__ = (
        Index("ix_campaigns_tenant", "tenant_id"),
        Index("ix_campaigns_mandate", "mandate_id"),
        Index("ix_campaigns_client", "client_id"),
    )

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "tenant_id": self.tenant_id,
            "mandate_id": self.mandate_id,
            "client_id": self.client_id,
            "name": self.name,
            "description": self.description,
            "status": self.status,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
```

- [ ] **Step 4: Update conftest.py — add Campaign Base**

In `backend/app/models/tests/conftest.py`, add one import after the existing Base imports:
```python
from backend.app.models.campaign import Base as Base6
```

Inside the `db_session` fixture, inside `async with engine.begin() as conn:`, add:
```python
        await conn.run_sync(Base6.metadata.create_all)
```

- [ ] **Step 5: Run tests to verify they pass**

```
python -m pytest backend/app/models/tests/test_campaign.py -v
```

Expected: 4 passed

- [ ] **Step 6: Commit**

```
git add backend/app/models/campaign.py backend/app/models/tests/test_campaign.py backend/app/models/tests/conftest.py
git commit -m "[TASK-002] feat: add Campaign model with tests"
```

---

### Task 4: CampaignConcept model

**Files:**
- Create: `backend/app/models/campaign_concept.py`
- Modify: `backend/app/models/tests/conftest.py`
- Test: `backend/app/models/tests/test_campaign_concept.py`

- [ ] **Step 1: Write the failing test**

```python
# backend/app/models/tests/test_campaign_concept.py
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
        select(CampaignConcept).where(CampaignConcept.title == "Selected Concept")
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
```

- [ ] **Step 2: Run test to verify it fails**

```
python -m pytest backend/app/models/tests/test_campaign_concept.py -v
```

Expected: FAIL — `ModuleNotFoundError: No module named 'backend.app.models.campaign_concept'`

- [ ] **Step 3: Create the model**

```python
# backend/app/models/campaign_concept.py
"""SQLAlchemy model for CampaignConcept — AI-generated concept with optional brand embedding."""

from datetime import datetime, timezone
import uuid

from sqlalchemy import Column, DateTime, String, Text, Index
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import declarative_base

try:
    from pgvector.sqlalchemy import Vector
    HAS_PGVECTOR = True
except ImportError:
    HAS_PGVECTOR = False

Base = declarative_base()


class CampaignConcept(Base):
    __tablename__ = "campaign_concepts"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    tenant_id = Column(String, nullable=False, index=True)
    campaign_id = Column(String, nullable=False, index=True)
    title = Column(String, nullable=False)
    description = Column(Text, nullable=False)
    strategy = Column(JSONB, nullable=False, default=lambda: {})
    status = Column(String, nullable=False, default="pending")
    # status values: pending | selected | rejected
    selected_by = Column(String, nullable=True)
    created_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    updated_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    if HAS_PGVECTOR:
        brand_embedding = Column(Vector(1536), nullable=True)

    __table_args__ = (
        Index("ix_campaign_concepts_tenant", "tenant_id"),
        Index("ix_campaign_concepts_campaign", "campaign_id"),
    )

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "tenant_id": self.tenant_id,
            "campaign_id": self.campaign_id,
            "title": self.title,
            "description": self.description,
            "strategy": self.strategy,
            "status": self.status,
            "selected_by": self.selected_by,
            "brand_embedding": getattr(self, "brand_embedding", None),
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
```

- [ ] **Step 4: Update conftest.py — add CampaignConcept Base**

In `backend/app/models/tests/conftest.py`, add one import after the existing Base imports:
```python
from backend.app.models.campaign_concept import Base as Base7
```

Inside the `db_session` fixture, inside `async with engine.begin() as conn:`, add:
```python
        await conn.run_sync(Base7.metadata.create_all)
```

- [ ] **Step 5: Run tests to verify they pass**

```
python -m pytest backend/app/models/tests/test_campaign_concept.py -v
```

Expected: 4 passed

- [ ] **Step 6: Commit**

```
git add backend/app/models/campaign_concept.py backend/app/models/tests/test_campaign_concept.py backend/app/models/tests/conftest.py
git commit -m "[TASK-002] feat: add CampaignConcept model with tests"
```

---

### Task 5: Activation model

**Files:**
- Create: `backend/app/models/activation.py`
- Modify: `backend/app/models/tests/conftest.py`
- Test: `backend/app/models/tests/test_activation.py`

- [ ] **Step 1: Write the failing test**

```python
# backend/app/models/tests/test_activation.py
import pytest
from uuid import uuid4
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.models.activation import Activation


@pytest.mark.asyncio
async def test_create_activation(db_session: AsyncSession):
    tenant_id = str(uuid4())
    activation = Activation(
        tenant_id=tenant_id,
        campaign_id=str(uuid4()),
        channel="meta_ads",
        sub_channel="instagram_feed",
        audience_segment="brand_aware",
        budget_allocated=50000.0,
        currency="USD",
        platform_config={"age_min": 25, "age_max": 45, "interests": ["tech"]},
    )
    db_session.add(activation)
    await db_session.commit()

    result = await db_session.execute(
        select(Activation).where(Activation.tenant_id == tenant_id)
    )
    fetched = result.scalar_one()

    assert fetched.channel == "meta_ads"
    assert fetched.sub_channel == "instagram_feed"
    assert fetched.audience_segment == "brand_aware"
    assert fetched.budget_allocated == 50000.0
    assert fetched.status == "planned"
    assert fetched.platform_config["age_min"] == 25
    assert fetched.created_at is not None
    assert fetched.updated_at is not None


@pytest.mark.asyncio
async def test_activation_optional_sub_channel(db_session: AsyncSession):
    activation = Activation(
        tenant_id=str(uuid4()),
        campaign_id=str(uuid4()),
        channel="google_ads",
        audience_segment="consideration",
        budget_allocated=30000.0,
        platform_config={},
    )
    db_session.add(activation)
    await db_session.commit()

    result = await db_session.execute(
        select(Activation).where(Activation.channel == "google_ads")
    )
    fetched = result.scalar_one()
    assert fetched.sub_channel is None
    assert fetched.status == "planned"
    assert fetched.currency == "USD"


@pytest.mark.asyncio
async def test_activation_to_dict(db_session: AsyncSession):
    tenant_id = str(uuid4())
    activation = Activation(
        tenant_id=tenant_id,
        campaign_id=str(uuid4()),
        channel="linkedin_ads",
        audience_segment="decision_maker",
        budget_allocated=75000.0,
        status="active",
        platform_config={"job_titles": ["CTO", "VP Engineering"]},
    )
    db_session.add(activation)
    await db_session.commit()

    result = await db_session.execute(
        select(Activation).where(Activation.id == activation.id)
    )
    fetched = result.scalar_one()
    d = fetched.to_dict()

    assert d["tenant_id"] == tenant_id
    assert d["channel"] == "linkedin_ads"
    assert d["status"] == "active"
    assert d["platform_config"]["job_titles"] == ["CTO", "VP Engineering"]
    assert "created_at" in d
    assert "updated_at" in d


@pytest.mark.asyncio
async def test_activation_failed_status(db_session: AsyncSession):
    activation = Activation(
        tenant_id=str(uuid4()),
        campaign_id=str(uuid4()),
        channel="meta_ads",
        audience_segment="retargeting",
        budget_allocated=10000.0,
        status="failed",
        platform_config={},
    )
    db_session.add(activation)
    await db_session.commit()

    result = await db_session.execute(
        select(Activation).where(Activation.status == "failed")
    )
    fetched = result.scalar_one()
    assert fetched.status == "failed"


@pytest.mark.asyncio
async def test_activation_tenant_isolation(db_session: AsyncSession):
    tenant_a = str(uuid4())
    tenant_b = str(uuid4())
    db_session.add(Activation(
        tenant_id=tenant_a, campaign_id=str(uuid4()),
        channel="meta_ads", audience_segment="brand_aware",
        budget_allocated=10000.0, platform_config={},
    ))
    db_session.add(Activation(
        tenant_id=tenant_b, campaign_id=str(uuid4()),
        channel="google_ads", audience_segment="consideration",
        budget_allocated=20000.0, platform_config={},
    ))
    await db_session.commit()

    result = await db_session.execute(
        select(Activation).where(Activation.tenant_id == tenant_a)
    )
    activations = result.scalars().all()
    assert len(activations) == 1
    assert activations[0].channel == "meta_ads"
```

- [ ] **Step 2: Run test to verify it fails**

```
python -m pytest backend/app/models/tests/test_activation.py -v
```

Expected: FAIL — `ModuleNotFoundError: No module named 'backend.app.models.activation'`

- [ ] **Step 3: Create the model**

```python
# backend/app/models/activation.py
"""SQLAlchemy model for Activation — channel-level campaign execution unit."""

from datetime import datetime, timezone
import uuid

from sqlalchemy import Column, DateTime, Float, String, Index
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import declarative_base

Base = declarative_base()


class Activation(Base):
    __tablename__ = "activations"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    tenant_id = Column(String, nullable=False, index=True)
    campaign_id = Column(String, nullable=False, index=True)
    channel = Column(String, nullable=False)
    sub_channel = Column(String, nullable=True)
    audience_segment = Column(String, nullable=False)
    budget_allocated = Column(Float, nullable=False)
    currency = Column(String, nullable=False, default="USD")
    platform_config = Column(JSONB, nullable=False, default=lambda: {})
    status = Column(String, nullable=False, default="planned")
    # status values: planned | active | paused | completed | failed
    created_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    updated_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    __table_args__ = (
        Index("ix_activations_tenant", "tenant_id"),
        Index("ix_activations_campaign", "campaign_id"),
        Index("ix_activations_tenant_campaign", "tenant_id", "campaign_id"),
    )

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "tenant_id": self.tenant_id,
            "campaign_id": self.campaign_id,
            "channel": self.channel,
            "sub_channel": self.sub_channel,
            "audience_segment": self.audience_segment,
            "budget_allocated": self.budget_allocated,
            "currency": self.currency,
            "platform_config": self.platform_config,
            "status": self.status,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
```

- [ ] **Step 4: Update conftest.py — add Activation Base**

In `backend/app/models/tests/conftest.py`, add one import after the existing Base imports:
```python
from backend.app.models.activation import Base as Base8
```

Inside the `db_session` fixture, inside `async with engine.begin() as conn:`, add:
```python
        await conn.run_sync(Base8.metadata.create_all)
```

- [ ] **Step 5: Run tests to verify they pass**

```
python -m pytest backend/app/models/tests/test_activation.py -v
```

Expected: 5 passed

- [ ] **Step 6: Commit**

```
git add backend/app/models/activation.py backend/app/models/tests/test_activation.py backend/app/models/tests/conftest.py
git commit -m "[TASK-002] feat: add Activation model with tests"
```

---

### Task 6: Budget model

**Files:**
- Create: `backend/app/models/budget.py`
- Modify: `backend/app/models/tests/conftest.py`
- Test: `backend/app/models/tests/test_budget.py`

- [ ] **Step 1: Write the failing test**

```python
# backend/app/models/tests/test_budget.py
import pytest
from datetime import datetime, timezone
from uuid import uuid4
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.models.budget import Budget


@pytest.mark.asyncio
async def test_create_budget(db_session: AsyncSession):
    tenant_id = str(uuid4())
    budget = Budget(
        tenant_id=tenant_id,
        campaign_id=str(uuid4()),
        total=1000000.0,
        currency="USD",
        breakdown={"meta_ads": 400000, "google_ads": 400000, "linkedin_ads": 200000},
    )
    db_session.add(budget)
    await db_session.commit()

    result = await db_session.execute(
        select(Budget).where(Budget.tenant_id == tenant_id)
    )
    fetched = result.scalar_one()

    assert fetched.total == 1000000.0
    assert fetched.currency == "USD"
    assert fetched.breakdown["meta_ads"] == 400000
    assert fetched.status == "draft"
    assert fetched.approved_by is None
    assert fetched.approved_at is None
    assert fetched.created_at is not None
    assert fetched.updated_at is not None


@pytest.mark.asyncio
async def test_budget_approval_fields(db_session: AsyncSession):
    approver_id = str(uuid4())
    approved_time = datetime.now(timezone.utc)
    budget = Budget(
        tenant_id=str(uuid4()),
        campaign_id=str(uuid4()),
        total=500000.0,
        currency="EUR",
        breakdown={},
        status="approved",
        approved_by=approver_id,
        approved_at=approved_time,
    )
    db_session.add(budget)
    await db_session.commit()

    result = await db_session.execute(
        select(Budget).where(Budget.status == "approved")
    )
    fetched = result.scalar_one()

    assert fetched.status == "approved"
    assert fetched.approved_by == approver_id
    assert fetched.approved_at is not None


@pytest.mark.asyncio
async def test_budget_to_dict(db_session: AsyncSession):
    tenant_id = str(uuid4())
    budget = Budget(
        tenant_id=tenant_id,
        campaign_id=str(uuid4()),
        total=250000.0,
        currency="GBP",
        breakdown={"channel_a": 125000, "channel_b": 125000},
    )
    db_session.add(budget)
    await db_session.commit()

    result = await db_session.execute(
        select(Budget).where(Budget.id == budget.id)
    )
    fetched = result.scalar_one()
    d = fetched.to_dict()

    assert d["tenant_id"] == tenant_id
    assert d["total"] == 250000.0
    assert d["currency"] == "GBP"
    assert d["status"] == "draft"
    assert d["approved_by"] is None
    assert d["approved_at"] is None
    assert "created_at" in d
    assert "updated_at" in d


@pytest.mark.asyncio
async def test_budget_tenant_isolation(db_session: AsyncSession):
    tenant_a = str(uuid4())
    tenant_b = str(uuid4())
    db_session.add(Budget(
        tenant_id=tenant_a, campaign_id=str(uuid4()),
        total=100000.0, breakdown={},
    ))
    db_session.add(Budget(
        tenant_id=tenant_b, campaign_id=str(uuid4()),
        total=200000.0, breakdown={},
    ))
    await db_session.commit()

    result = await db_session.execute(
        select(Budget).where(Budget.tenant_id == tenant_a)
    )
    budgets = result.scalars().all()
    assert len(budgets) == 1
    assert budgets[0].total == 100000.0
```

- [ ] **Step 2: Run test to verify it fails**

```
python -m pytest backend/app/models/tests/test_budget.py -v
```

Expected: FAIL — `ModuleNotFoundError: No module named 'backend.app.models.budget'`

- [ ] **Step 3: Create the model**

```python
# backend/app/models/budget.py
"""SQLAlchemy model for Budget — campaign budget with approval tracking."""

from datetime import datetime, timezone
import uuid

from sqlalchemy import Column, DateTime, Float, String, Index
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import declarative_base

Base = declarative_base()


class Budget(Base):
    __tablename__ = "budgets"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    tenant_id = Column(String, nullable=False, index=True)
    campaign_id = Column(String, nullable=False, index=True)
    total = Column(Float, nullable=False)
    currency = Column(String, nullable=False, default="USD")
    breakdown = Column(JSONB, nullable=False, default=lambda: {})
    status = Column(String, nullable=False, default="draft")
    # status values: draft | approved
    approved_by = Column(String, nullable=True)
    approved_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    updated_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    __table_args__ = (
        Index("ix_budgets_tenant", "tenant_id"),
        Index("ix_budgets_campaign", "campaign_id"),
    )

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "tenant_id": self.tenant_id,
            "campaign_id": self.campaign_id,
            "total": self.total,
            "currency": self.currency,
            "breakdown": self.breakdown,
            "status": self.status,
            "approved_by": self.approved_by,
            "approved_at": self.approved_at.isoformat() if self.approved_at else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
```

- [ ] **Step 4: Update conftest.py — add Budget Base**

In `backend/app/models/tests/conftest.py`, add one import after the existing Base imports:
```python
from backend.app.models.budget import Base as Base9
```

Inside the `db_session` fixture, inside `async with engine.begin() as conn:`, add:
```python
        await conn.run_sync(Base9.metadata.create_all)
```

- [ ] **Step 5: Run tests to verify they pass**

```
python -m pytest backend/app/models/tests/test_budget.py -v
```

Expected: 4 passed

- [ ] **Step 6: Commit**

```
git add backend/app/models/budget.py backend/app/models/tests/test_budget.py backend/app/models/tests/conftest.py
git commit -m "[TASK-002] feat: add Budget model with tests"
```

---

### Task 7: ApprovalLog model

**Files:**
- Create: `backend/app/models/approval_log.py`
- Modify: `backend/app/models/tests/conftest.py`
- Test: `backend/app/models/tests/test_approval_log.py`

- [ ] **Step 1: Write the failing test**

```python
# backend/app/models/tests/test_approval_log.py
import pytest
from uuid import uuid4
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.models.approval_log import ApprovalLog


@pytest.mark.asyncio
async def test_create_approval_log(db_session: AsyncSession):
    tenant_id = str(uuid4())
    log = ApprovalLog(
        tenant_id=tenant_id,
        entity_type="campaign",
        entity_id=str(uuid4()),
        action="submitted",
        actor_id=str(uuid4()),
        status_before="planned",
        status_after="pending_review",
    )
    db_session.add(log)
    await db_session.commit()

    result = await db_session.execute(
        select(ApprovalLog).where(ApprovalLog.tenant_id == tenant_id)
    )
    fetched = result.scalar_one()

    assert fetched.entity_type == "campaign"
    assert fetched.action == "submitted"
    assert fetched.status_before == "planned"
    assert fetched.status_after == "pending_review"
    assert fetched.notes is None
    assert fetched.created_at is not None


@pytest.mark.asyncio
async def test_approval_log_with_notes(db_session: AsyncSession):
    log = ApprovalLog(
        tenant_id=str(uuid4()),
        entity_type="budget",
        entity_id=str(uuid4()),
        action="rejected",
        actor_id=str(uuid4()),
        notes="Budget exceeds Q3 cap by 15%.",
        status_before="pending_review",
        status_after="rejected",
    )
    db_session.add(log)
    await db_session.commit()

    result = await db_session.execute(
        select(ApprovalLog).where(ApprovalLog.action == "rejected")
    )
    fetched = result.scalar_one()
    assert fetched.notes == "Budget exceeds Q3 cap by 15%."


@pytest.mark.asyncio
async def test_approval_log_nullable_status_fields(db_session: AsyncSession):
    log = ApprovalLog(
        tenant_id=str(uuid4()),
        entity_type="mandate",
        entity_id=str(uuid4()),
        action="approved",
        actor_id=str(uuid4()),
    )
    db_session.add(log)
    await db_session.commit()

    result = await db_session.execute(
        select(ApprovalLog).where(ApprovalLog.entity_type == "mandate")
    )
    fetched = result.scalar_one()
    assert fetched.status_before is None
    assert fetched.status_after is None


@pytest.mark.asyncio
async def test_approval_log_to_dict(db_session: AsyncSession):
    tenant_id = str(uuid4())
    actor_id = str(uuid4())
    entity_id = str(uuid4())
    log = ApprovalLog(
        tenant_id=tenant_id,
        entity_type="campaign",
        entity_id=entity_id,
        action="approved",
        actor_id=actor_id,
        status_before="pending_review",
        status_after="approved",
    )
    db_session.add(log)
    await db_session.commit()

    result = await db_session.execute(
        select(ApprovalLog).where(ApprovalLog.id == log.id)
    )
    fetched = result.scalar_one()
    d = fetched.to_dict()

    assert d["tenant_id"] == tenant_id
    assert d["entity_type"] == "campaign"
    assert d["entity_id"] == entity_id
    assert d["action"] == "approved"
    assert d["actor_id"] == actor_id
    assert d["status_before"] == "pending_review"
    assert d["status_after"] == "approved"
    assert "created_at" in d
    assert "updated_at" not in d


@pytest.mark.asyncio
async def test_approval_log_tenant_isolation(db_session: AsyncSession):
    tenant_a = str(uuid4())
    tenant_b = str(uuid4())
    db_session.add(ApprovalLog(
        tenant_id=tenant_a, entity_type="campaign", entity_id=str(uuid4()),
        action="submitted", actor_id=str(uuid4()),
    ))
    db_session.add(ApprovalLog(
        tenant_id=tenant_b, entity_type="budget", entity_id=str(uuid4()),
        action="approved", actor_id=str(uuid4()),
    ))
    await db_session.commit()

    result = await db_session.execute(
        select(ApprovalLog).where(ApprovalLog.tenant_id == tenant_a)
    )
    logs = result.scalars().all()
    assert len(logs) == 1
    assert logs[0].entity_type == "campaign"
```

- [ ] **Step 2: Run test to verify it fails**

```
python -m pytest backend/app/models/tests/test_approval_log.py -v
```

Expected: FAIL — `ModuleNotFoundError: No module named 'backend.app.models.approval_log'`

- [ ] **Step 3: Create the model**

```python
# backend/app/models/approval_log.py
"""SQLAlchemy model for ApprovalLog — insert-only audit log for entity state transitions."""

from datetime import datetime, timezone
import uuid

from sqlalchemy import Column, DateTime, String, Text, Index
from sqlalchemy.orm import declarative_base

Base = declarative_base()


class ApprovalLog(Base):
    __tablename__ = "approval_logs"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    tenant_id = Column(String, nullable=False, index=True)
    entity_type = Column(String, nullable=False)
    entity_id = Column(String, nullable=False, index=True)
    action = Column(String, nullable=False)
    # action values: submitted | approved | rejected
    actor_id = Column(String, nullable=False)
    notes = Column(Text, nullable=True)
    status_before = Column(String, nullable=True)
    status_after = Column(String, nullable=True)
    created_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    __table_args__ = (
        Index("ix_approval_logs_tenant", "tenant_id"),
        Index("ix_approval_logs_entity", "entity_id"),
        Index("ix_approval_logs_tenant_entity", "tenant_id", "entity_id"),
    )

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "tenant_id": self.tenant_id,
            "entity_type": self.entity_type,
            "entity_id": self.entity_id,
            "action": self.action,
            "actor_id": self.actor_id,
            "notes": self.notes,
            "status_before": self.status_before,
            "status_after": self.status_after,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
```

- [ ] **Step 4: Update conftest.py — add ApprovalLog Base**

In `backend/app/models/tests/conftest.py`, add one import after the existing Base imports:
```python
from backend.app.models.approval_log import Base as Base10
```

Inside the `db_session` fixture, inside `async with engine.begin() as conn:`, add:
```python
        await conn.run_sync(Base10.metadata.create_all)
```

- [ ] **Step 5: Run tests to verify they pass**

```
python -m pytest backend/app/models/tests/test_approval_log.py -v
```

Expected: 5 passed

- [ ] **Step 6: Commit**

```
git add backend/app/models/approval_log.py backend/app/models/tests/test_approval_log.py backend/app/models/tests/conftest.py
git commit -m "[TASK-002] feat: add ApprovalLog model with tests"
```

---

### Task 8: PhysicalActivationLog model

**Files:**
- Create: `backend/app/models/physical_activation_log.py`
- Modify: `backend/app/models/tests/conftest.py`
- Test: `backend/app/models/tests/test_physical_activation_log.py`

- [ ] **Step 1: Write the failing test**

```python
# backend/app/models/tests/test_physical_activation_log.py
import pytest
from datetime import datetime, timezone, timedelta
from uuid import uuid4
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.models.physical_activation_log import PhysicalActivationLog


@pytest.mark.asyncio
async def test_create_physical_activation_log(db_session: AsyncSession):
    tenant_id = str(uuid4())
    event_time = datetime.now(timezone.utc) - timedelta(minutes=5)
    log = PhysicalActivationLog(
        tenant_id=tenant_id,
        campaign_id=str(uuid4()),
        activation_id=str(uuid4()),
        event_type="impression",
        channel="meta_ads",
        payload={"placement": "feed", "device": "mobile", "impressions": 1200},
        logged_at=event_time,
    )
    db_session.add(log)
    await db_session.commit()

    result = await db_session.execute(
        select(PhysicalActivationLog).where(PhysicalActivationLog.tenant_id == tenant_id)
    )
    fetched = result.scalar_one()

    assert fetched.event_type == "impression"
    assert fetched.channel == "meta_ads"
    assert fetched.payload["impressions"] == 1200
    assert fetched.activation_id is not None
    assert fetched.created_at is not None


@pytest.mark.asyncio
async def test_physical_activation_log_no_activation_id(db_session: AsyncSession):
    log = PhysicalActivationLog(
        tenant_id=str(uuid4()),
        campaign_id=str(uuid4()),
        event_type="campaign_start",
        channel="google_ads",
        payload={"start_time": "2025-07-01T00:00:00Z"},
        logged_at=datetime.now(timezone.utc),
    )
    db_session.add(log)
    await db_session.commit()

    result = await db_session.execute(
        select(PhysicalActivationLog).where(PhysicalActivationLog.event_type == "campaign_start")
    )
    fetched = result.scalar_one()
    assert fetched.activation_id is None


@pytest.mark.asyncio
async def test_physical_activation_log_to_dict(db_session: AsyncSession):
    tenant_id = str(uuid4())
    log = PhysicalActivationLog(
        tenant_id=tenant_id,
        campaign_id=str(uuid4()),
        event_type="click",
        channel="linkedin_ads",
        payload={"url": "/landing", "clicks": 42},
        logged_at=datetime.now(timezone.utc),
    )
    db_session.add(log)
    await db_session.commit()

    result = await db_session.execute(
        select(PhysicalActivationLog).where(PhysicalActivationLog.id == log.id)
    )
    fetched = result.scalar_one()
    d = fetched.to_dict()

    assert d["tenant_id"] == tenant_id
    assert d["event_type"] == "click"
    assert d["channel"] == "linkedin_ads"
    assert d["payload"]["clicks"] == 42
    assert "logged_at" in d
    assert "created_at" in d
    assert "updated_at" not in d


@pytest.mark.asyncio
async def test_physical_activation_log_tenant_isolation(db_session: AsyncSession):
    tenant_a = str(uuid4())
    tenant_b = str(uuid4())
    now = datetime.now(timezone.utc)
    db_session.add(PhysicalActivationLog(
        tenant_id=tenant_a, campaign_id=str(uuid4()),
        event_type="impression", channel="meta_ads",
        payload={}, logged_at=now,
    ))
    db_session.add(PhysicalActivationLog(
        tenant_id=tenant_b, campaign_id=str(uuid4()),
        event_type="click", channel="google_ads",
        payload={}, logged_at=now,
    ))
    await db_session.commit()

    result = await db_session.execute(
        select(PhysicalActivationLog).where(PhysicalActivationLog.tenant_id == tenant_a)
    )
    logs = result.scalars().all()
    assert len(logs) == 1
    assert logs[0].event_type == "impression"
```

- [ ] **Step 2: Run test to verify it fails**

```
python -m pytest backend/app/models/tests/test_physical_activation_log.py -v
```

Expected: FAIL — `ModuleNotFoundError: No module named 'backend.app.models.physical_activation_log'`

- [ ] **Step 3: Create the model**

```python
# backend/app/models/physical_activation_log.py
"""SQLAlchemy model for PhysicalActivationLog — insert-only event log for channel activations."""

from datetime import datetime, timezone
import uuid

from sqlalchemy import Column, DateTime, String, Index
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import declarative_base

Base = declarative_base()


class PhysicalActivationLog(Base):
    __tablename__ = "physical_activation_logs"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    tenant_id = Column(String, nullable=False, index=True)
    campaign_id = Column(String, nullable=False, index=True)
    activation_id = Column(String, nullable=True, index=True)
    event_type = Column(String, nullable=False)
    channel = Column(String, nullable=False)
    payload = Column(JSONB, nullable=False, default=lambda: {})
    logged_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    created_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    __table_args__ = (
        Index("ix_pal_tenant", "tenant_id"),
        Index("ix_pal_campaign", "campaign_id"),
        Index("ix_pal_activation", "activation_id"),
        Index("ix_pal_tenant_campaign", "tenant_id", "campaign_id"),
    )

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "tenant_id": self.tenant_id,
            "campaign_id": self.campaign_id,
            "activation_id": self.activation_id,
            "event_type": self.event_type,
            "channel": self.channel,
            "payload": self.payload,
            "logged_at": self.logged_at.isoformat() if self.logged_at else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
```

- [ ] **Step 4: Update conftest.py — add PhysicalActivationLog Base**

In `backend/app/models/tests/conftest.py`, add one import after the existing Base imports:
```python
from backend.app.models.physical_activation_log import Base as Base11
```

Inside the `db_session` fixture, inside `async with engine.begin() as conn:`, add:
```python
        await conn.run_sync(Base11.metadata.create_all)
```

- [ ] **Step 5: Run tests to verify they pass**

```
python -m pytest backend/app/models/tests/test_physical_activation_log.py -v
```

Expected: 4 passed

- [ ] **Step 6: Commit**

```
git add backend/app/models/physical_activation_log.py backend/app/models/tests/test_physical_activation_log.py backend/app/models/tests/conftest.py
git commit -m "[TASK-002] feat: add PhysicalActivationLog model with tests"
```

---

### Task 9: Full suite verification

**Files:**
- None (verification only)

At this point `conftest.py` should have all 11 Bases registered (Base1–Base11). Run the full models test suite to confirm no regressions.

- [ ] **Step 1: Run the full models test suite**

```
python -m pytest backend/app/models/tests/ -v
```

Expected output — all of the following passing:
```
backend/app/models/tests/test_activation_platform_mapping.py  PASSED (existing)
backend/app/models/tests/test_platform_config_template.py     PASSED (existing)
backend/app/models/tests/test_client.py                       4 passed
backend/app/models/tests/test_mandate.py                      4 passed
backend/app/models/tests/test_campaign.py                     4 passed
backend/app/models/tests/test_campaign_concept.py             4 passed
backend/app/models/tests/test_activation.py                   5 passed
backend/app/models/tests/test_budget.py                       4 passed
backend/app/models/tests/test_approval_log.py                 5 passed
backend/app/models/tests/test_physical_activation_log.py      4 passed
```

- [ ] **Step 2: If any test fails, read the error, fix the specific model or test file, re-run only that file**

Fix pattern — example for a JSONB default issue:
```python
# Wrong — mutable default shared across instances
competitors = Column(JSONB, nullable=False, default=[])

# Correct — callable default
competitors = Column(JSONB, nullable=False, default=lambda: [])
```

- [ ] **Step 3: Commit final state if any fixes were needed**

```
git add backend/app/models/ backend/app/models/tests/
git commit -m "[TASK-002] fix: resolve any issues found in full suite run"
```

- [ ] **Step 4: Push to origin**

```
git push origin main
```
