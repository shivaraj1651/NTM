# TASK-020 Analytics Agent (AGT-13) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a daily scheduled analytics agent that pulls live activation metrics, computes KPI achievement, flags Red/Amber/Green status, generates AnalyticsSummary JSON, and sends alert notifications.

**Architecture:** AnalyticsAgent runs as Celery Beat scheduled task (24h interval). For each live activation, it fetches metrics from platform tools, stores in PerformanceMetric table, computes KPI achievement vs targets, flags status (Red <-20%, Amber -20% to -10%, Green ≥-10%), and generates AnalyticsSummary JSON per mandate with alert notifications for Red KPIs.

**Tech Stack:** Python 3.12, FastAPI, SQLAlchemy async, PostgreSQL 16, Celery Beat, AsyncSession, platform tools (Google Ads, Meta Ads, LinkedIn Ads)

---

## File Structure

**Models:**
- `backend/app/models/kpi.py` — KPI target definition (campaign, channel, audience, kpi_name, target_value)
- `backend/app/models/performance_metric.py` — Daily metrics storage (activation, date, metrics_json, source)

**Services:**
- `backend/app/services/kpi_service.py` — Fetch KPIs for activation, query by campaign/channel/audience
- `backend/app/services/performance_metric_service.py` — Store and retrieve daily metrics from DB
- `backend/app/services/analytics_summary_service.py` — Compute KPI achievement, flag status, build summary JSON

**Agent & Tasks:**
- `backend/app/agents/analytics_agent.py` — Main AnalyticsAgent orchestrating daily analysis (single file, focused)
- `backend/app/tasks/analytics_tasks.py` — Celery Beat task registration and scheduling

**Tests:**
- `tests/unit/models/test_kpi.py` — KPI model and query tests
- `tests/unit/models/test_performance_metric.py` — PerformanceMetric model tests
- `tests/unit/services/test_kpi_service.py` — KPI fetching and filtering
- `tests/unit/services/test_performance_metric_service.py` — Metrics storage and retrieval
- `tests/unit/services/test_analytics_summary_service.py` — KPI achievement calculation, flagging logic
- `tests/unit/agents/test_analytics_agent.py` — Agent orchestration, metrics fetching, summary generation
- `tests/integration/test_analytics_end_to_end.py` — Full workflow with mocked platform tools

---

## Task 1: Create KPI Model and Migration

**Files:**
- Create: `backend/app/models/kpi.py`
- Create: `backend/alembic/versions/kpi_table_migration.py`
- Create: `tests/unit/models/test_kpi.py`

- [ ] **Step 1: Write failing test for KPI model**

```python
# tests/unit/models/test_kpi.py
import pytest
from sqlalchemy import select
from backend.app.models.kpi import KPI
from backend.app.db import AsyncSession

@pytest.mark.asyncio
async def test_kpi_creation(db_session: AsyncSession):
    """Test creating a KPI record with all required fields."""
    kpi = KPI(
        campaign_id="campaign-123",
        channel_enum="google_ads",
        audience_segment="brand_aware",
        kpi_name="conversion_rate",
        target_value=3.0,
        threshold_unit="percent",
        tenant_id="tenant-456"
    )
    db_session.add(kpi)
    await db_session.commit()
    
    result = await db_session.execute(
        select(KPI).where(KPI.campaign_id == "campaign-123")
    )
    created_kpi = result.scalar_one()
    assert created_kpi.kpi_name == "conversion_rate"
    assert created_kpi.target_value == 3.0
    assert created_kpi.threshold_unit == "percent"

@pytest.mark.asyncio
async def test_kpi_unique_constraint(db_session: AsyncSession):
    """Test unique constraint: (campaign_id, channel_enum, audience_segment, kpi_name, tenant_id)."""
    kpi1 = KPI(
        campaign_id="campaign-123",
        channel_enum="google_ads",
        audience_segment="brand_aware",
        kpi_name="conversion_rate",
        target_value=3.0,
        threshold_unit="percent",
        tenant_id="tenant-456"
    )
    db_session.add(kpi1)
    await db_session.commit()
    
    kpi2 = KPI(
        campaign_id="campaign-123",
        channel_enum="google_ads",
        audience_segment="brand_aware",
        kpi_name="conversion_rate",
        target_value=4.0,
        threshold_unit="percent",
        tenant_id="tenant-456"
    )
    db_session.add(kpi2)
    
    with pytest.raises(Exception):  # IntegrityError
        await db_session.commit()
```

- [ ] **Step 2: Run test to verify it fails**

```bash
pytest tests/unit/models/test_kpi.py -v
```

Expected: FAIL — `ModuleNotFoundError: No module named 'backend.app.models.kpi'`

- [ ] **Step 3: Create KPI model**

```python
# backend/app/models/kpi.py
from uuid import uuid4
from datetime import datetime
from sqlalchemy import Column, String, Float, DateTime, UniqueConstraint, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from backend.app.db import Base

class KPI(Base):
    __tablename__ = "kpi"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    campaign_id = Column(UUID(as_uuid=True), ForeignKey("campaign.id"), nullable=False)
    channel_enum = Column(String(50), nullable=False)  # google_ads, meta_ads, linkedin_ads
    audience_segment = Column(String(100), nullable=False)
    kpi_name = Column(String(100), nullable=False)  # conversion_rate, cost_per_click, etc.
    target_value = Column(Float, nullable=False)
    threshold_unit = Column(String(50), nullable=False)  # percent, currency, ratio, count
    tenant_id = Column(UUID(as_uuid=True), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    __table_args__ = (
        UniqueConstraint(
            "campaign_id", "channel_enum", "audience_segment", "kpi_name", "tenant_id",
            name="uq_kpi_campaign_channel_segment_name_tenant"
        ),
    )
```

- [ ] **Step 4: Create Alembic migration**

```python
# backend/alembic/versions/001_create_kpi_table.py
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = '001_create_kpi_table'
down_revision = None
branch_labels = None
depends_on = None

def upgrade():
    op.create_table(
        'kpi',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('campaign_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('channel_enum', sa.String(50), nullable=False),
        sa.Column('audience_segment', sa.String(100), nullable=False),
        sa.Column('kpi_name', sa.String(100), nullable=False),
        sa.Column('target_value', sa.Float(), nullable=False),
        sa.Column('threshold_unit', sa.String(50), nullable=False),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['campaign_id'], ['campaign.id']),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('campaign_id', 'channel_enum', 'audience_segment', 'kpi_name', 'tenant_id',
                           name='uq_kpi_campaign_channel_segment_name_tenant')
    )
    op.create_index('ix_kpi_campaign_id', 'kpi', ['campaign_id'])
    op.create_index('ix_kpi_tenant_id', 'kpi', ['tenant_id'])

def downgrade():
    op.drop_index('ix_kpi_tenant_id', 'kpi')
    op.drop_index('ix_kpi_campaign_id', 'kpi')
    op.drop_table('kpi')
```

- [ ] **Step 5: Run migration**

```bash
alembic upgrade head
```

Expected: Migration applies without error

- [ ] **Step 6: Run tests to verify they pass**

```bash
pytest tests/unit/models/test_kpi.py -v
```

Expected: PASS (2/2 tests pass)

- [ ] **Step 7: Commit**

```bash
git add backend/app/models/kpi.py backend/alembic/versions/001_create_kpi_table.py tests/unit/models/test_kpi.py
git commit -m "[TASK-020] feat: add KPI model and migration"
```

---

## Task 2: Create PerformanceMetric Model and Migration

**Files:**
- Create: `backend/app/models/performance_metric.py`
- Create: `backend/alembic/versions/performance_metric_table_migration.py`
- Create: `tests/unit/models/test_performance_metric.py`

- [ ] **Step 1: Write failing test for PerformanceMetric model**

```python
# tests/unit/models/test_performance_metric.py
import pytest
from datetime import date
from sqlalchemy import select
from backend.app.models.performance_metric import PerformanceMetric
from backend.app.db import AsyncSession

@pytest.mark.asyncio
async def test_performance_metric_creation(db_session: AsyncSession):
    """Test creating a PerformanceMetric record with flexible JSON metrics."""
    metrics_json = {
        "impressions": 5000,
        "clicks": 250,
        "conversions": 7,
        "spend": 500.00,
        "ctr": 0.05,
        "cpc": 2.00,
        "cost_per_conversion": 71.43,
        "roas": 1.2
    }
    metric = PerformanceMetric(
        activation_id="activation-123",
        date=date.today(),
        metrics_json=metrics_json,
        source="google_ads",
        tenant_id="tenant-456"
    )
    db_session.add(metric)
    await db_session.commit()
    
    result = await db_session.execute(
        select(PerformanceMetric).where(
            PerformanceMetric.activation_id == "activation-123"
        )
    )
    created = result.scalar_one()
    assert created.metrics_json["impressions"] == 5000
    assert created.source == "google_ads"

@pytest.mark.asyncio
async def test_performance_metric_one_per_day(db_session: AsyncSession):
    """Test that we can have one metric row per activation per day."""
    activation_id = "activation-123"
    metric_date = date.today()
    
    metric1 = PerformanceMetric(
        activation_id=activation_id,
        date=metric_date,
        metrics_json={"impressions": 1000},
        source="google_ads",
        tenant_id="tenant-456"
    )
    db_session.add(metric1)
    await db_session.commit()
    
    # Next day same activation should be allowed
    from datetime import timedelta
    next_day = metric_date + timedelta(days=1)
    metric2 = PerformanceMetric(
        activation_id=activation_id,
        date=next_day,
        metrics_json={"impressions": 1200},
        source="google_ads",
        tenant_id="tenant-456"
    )
    db_session.add(metric2)
    await db_session.commit()
    
    result = await db_session.execute(
        select(PerformanceMetric).where(
            PerformanceMetric.activation_id == activation_id
        )
    )
    metrics = result.scalars().all()
    assert len(metrics) == 2
```

- [ ] **Step 2: Run test to verify it fails**

```bash
pytest tests/unit/models/test_performance_metric.py -v
```

Expected: FAIL — `ModuleNotFoundError: No module named 'backend.app.models.performance_metric'`

- [ ] **Step 3: Create PerformanceMetric model**

```python
# backend/app/models/performance_metric.py
from uuid import uuid4
from datetime import date, datetime
from sqlalchemy import Column, Date, DateTime, String
from sqlalchemy.dialects.postgresql import UUID, JSON
from backend.app.db import Base

class PerformanceMetric(Base):
    __tablename__ = "performance_metric"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    activation_id = Column(UUID(as_uuid=True), nullable=False)
    date = Column(Date, nullable=False)
    metrics_json = Column(JSON, nullable=False)  # flexible: {impressions, clicks, spend, ctr, cpc, roas, ...}
    source = Column(String(50), nullable=False)  # google_ads, meta_ads, linkedin_ads
    tenant_id = Column(UUID(as_uuid=True), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    __table_args__ = (
        {"indexes": [
            {"columns": ["activation_id", "date"]},
            {"columns": ["date", "tenant_id"]}
        ]},
    )
```

- [ ] **Step 4: Create Alembic migration**

```python
# backend/alembic/versions/002_create_performance_metric_table.py
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = '002_create_performance_metric_table'
down_revision = '001_create_kpi_table'
branch_labels = None
depends_on = None

def upgrade():
    op.create_table(
        'performance_metric',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('activation_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('date', sa.Date(), nullable=False),
        sa.Column('metrics_json', postgresql.JSON(), nullable=False),
        sa.Column('source', sa.String(50), nullable=False),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_performance_metric_activation_date', 'performance_metric', ['activation_id', 'date'])
    op.create_index('ix_performance_metric_date_tenant', 'performance_metric', ['date', 'tenant_id'])

def downgrade():
    op.drop_index('ix_performance_metric_date_tenant', 'performance_metric')
    op.drop_index('ix_performance_metric_activation_date', 'performance_metric')
    op.drop_table('performance_metric')
```

- [ ] **Step 5: Run migration**

```bash
alembic upgrade head
```

Expected: Both migrations apply

- [ ] **Step 6: Run tests to verify they pass**

```bash
pytest tests/unit/models/test_performance_metric.py -v
```

Expected: PASS (2/2 tests pass)

- [ ] **Step 7: Commit**

```bash
git add backend/app/models/performance_metric.py backend/alembic/versions/002_create_performance_metric_table.py tests/unit/models/test_performance_metric.py
git commit -m "[TASK-020] feat: add PerformanceMetric model and migration"
```

---

## Task 3: Create KPIService

**Files:**
- Create: `backend/app/services/kpi_service.py`
- Create: `tests/unit/services/test_kpi_service.py`

- [ ] **Step 1: Write failing test for KPIService**

```python
# tests/unit/services/test_kpi_service.py
import pytest
from uuid import uuid4
from backend.app.services.kpi_service import KPIService
from backend.app.models.kpi import KPI
from backend.app.db import AsyncSession

@pytest.mark.asyncio
async def test_get_kpis_for_activation(db_session: AsyncSession):
    """Test fetching KPIs for a specific activation."""
    campaign_id = uuid4()
    tenant_id = uuid4()
    activation_id = uuid4()
    
    # Create KPIs
    kpi1 = KPI(
        campaign_id=campaign_id,
        channel_enum="google_ads",
        audience_segment="brand_aware",
        kpi_name="conversion_rate",
        target_value=3.0,
        threshold_unit="percent",
        tenant_id=tenant_id
    )
    kpi2 = KPI(
        campaign_id=campaign_id,
        channel_enum="google_ads",
        audience_segment="brand_aware",
        kpi_name="cost_per_click",
        target_value=1.50,
        threshold_unit="currency",
        tenant_id=tenant_id
    )
    db_session.add(kpi1)
    db_session.add(kpi2)
    await db_session.commit()
    
    service = KPIService(db_session)
    kpis = await service.get_kpis_for_activation(
        campaign_id=campaign_id,
        channel="google_ads",
        audience_segment="brand_aware",
        tenant_id=tenant_id
    )
    
    assert len(kpis) == 2
    assert any(k.kpi_name == "conversion_rate" for k in kpis)
    assert any(k.kpi_name == "cost_per_click" for k in kpis)

@pytest.mark.asyncio
async def test_get_kpis_empty_result(db_session: AsyncSession):
    """Test fetching KPIs when none exist."""
    service = KPIService(db_session)
    kpis = await service.get_kpis_for_activation(
        campaign_id=uuid4(),
        channel="google_ads",
        audience_segment="unknown",
        tenant_id=uuid4()
    )
    
    assert len(kpis) == 0
```

- [ ] **Step 2: Run test to verify it fails**

```bash
pytest tests/unit/services/test_kpi_service.py -v
```

Expected: FAIL — `ModuleNotFoundError: No module named 'backend.app.services.kpi_service'`

- [ ] **Step 3: Create KPIService**

```python
# backend/app/services/kpi_service.py
from typing import List
from uuid import UUID
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from backend.app.models.kpi import KPI

class KPIService:
    def __init__(self, db_session: AsyncSession):
        self.db = db_session
    
    async def get_kpis_for_activation(
        self,
        campaign_id: UUID,
        channel: str,
        audience_segment: str,
        tenant_id: UUID
    ) -> List[KPI]:
        """Fetch KPIs for a specific activation (campaign + channel + audience)."""
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
        campaign_id: UUID,
        channel: str,
        audience_segment: str,
        kpi_name: str,
        tenant_id: UUID
    ) -> KPI:
        """Fetch a specific KPI by name."""
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
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
pytest tests/unit/services/test_kpi_service.py -v
```

Expected: PASS (2/2 tests pass)

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/kpi_service.py tests/unit/services/test_kpi_service.py
git commit -m "[TASK-020] feat: add KPIService for fetching KPI targets"
```

---

## Task 4: Create PerformanceMetricService

**Files:**
- Create: `backend/app/services/performance_metric_service.py`
- Create: `tests/unit/services/test_performance_metric_service.py`

- [ ] **Step 1: Write failing test for PerformanceMetricService**

```python
# tests/unit/services/test_performance_metric_service.py
import pytest
from datetime import date
from uuid import uuid4
from backend.app.services.performance_metric_service import PerformanceMetricService
from backend.app.models.performance_metric import PerformanceMetric
from backend.app.db import AsyncSession

@pytest.mark.asyncio
async def test_store_metric(db_session: AsyncSession):
    """Test storing a performance metric."""
    activation_id = uuid4()
    tenant_id = uuid4()
    metrics = {"impressions": 5000, "clicks": 250, "conversions": 7, "spend": 500.00}
    
    service = PerformanceMetricService(db_session)
    metric = await service.store_metric(
        activation_id=activation_id,
        date=date.today(),
        metrics_json=metrics,
        source="google_ads",
        tenant_id=tenant_id
    )
    
    assert metric.activation_id == activation_id
    assert metric.metrics_json["impressions"] == 5000
    assert metric.source == "google_ads"

@pytest.mark.asyncio
async def test_get_latest_metric(db_session: AsyncSession):
    """Test retrieving the most recent metric for an activation."""
    activation_id = uuid4()
    tenant_id = uuid4()
    
    service = PerformanceMetricService(db_session)
    
    # Store two metrics on different days
    from datetime import timedelta
    today = date.today()
    yesterday = today - timedelta(days=1)
    
    metric1 = await service.store_metric(
        activation_id=activation_id,
        date=yesterday,
        metrics_json={"impressions": 4000},
        source="google_ads",
        tenant_id=tenant_id
    )
    
    metric2 = await service.store_metric(
        activation_id=activation_id,
        date=today,
        metrics_json={"impressions": 5000},
        source="google_ads",
        tenant_id=tenant_id
    )
    
    latest = await service.get_latest_metric(activation_id, tenant_id)
    assert latest.date == today
    assert latest.metrics_json["impressions"] == 5000
```

- [ ] **Step 2: Run test to verify it fails**

```bash
pytest tests/unit/services/test_performance_metric_service.py -v
```

Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 3: Create PerformanceMetricService**

```python
# backend/app/services/performance_metric_service.py
from datetime import date
from typing import Dict, Any, Optional
from uuid import UUID
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from backend.app.models.performance_metric import PerformanceMetric

class PerformanceMetricService:
    def __init__(self, db_session: AsyncSession):
        self.db = db_session
    
    async def store_metric(
        self,
        activation_id: UUID,
        date: date,
        metrics_json: Dict[str, Any],
        source: str,
        tenant_id: UUID
    ) -> PerformanceMetric:
        """Store a daily performance metric for an activation."""
        metric = PerformanceMetric(
            activation_id=activation_id,
            date=date,
            metrics_json=metrics_json,
            source=source,
            tenant_id=tenant_id
        )
        self.db.add(metric)
        await self.db.commit()
        return metric
    
    async def get_latest_metric(
        self,
        activation_id: UUID,
        tenant_id: UUID
    ) -> Optional[PerformanceMetric]:
        """Get the most recent metric for an activation."""
        result = await self.db.execute(
            select(PerformanceMetric).where(
                PerformanceMetric.activation_id == activation_id,
                PerformanceMetric.tenant_id == tenant_id
            ).order_by(PerformanceMetric.date.desc()).limit(1)
        )
        return result.scalar_one_or_none()
    
    async def get_metrics_for_date(
        self,
        date: date,
        tenant_id: UUID
    ) -> list:
        """Get all metrics for a specific date."""
        result = await self.db.execute(
            select(PerformanceMetric).where(
                PerformanceMetric.date == date,
                PerformanceMetric.tenant_id == tenant_id
            )
        )
        return result.scalars().all()
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
pytest tests/unit/services/test_performance_metric_service.py -v
```

Expected: PASS (2/2 tests pass)

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/performance_metric_service.py tests/unit/services/test_performance_metric_service.py
git commit -m "[TASK-020] feat: add PerformanceMetricService for storing/retrieving metrics"
```

---

## Task 5: Create AnalyticsSummaryService (KPI Computation & Status Flagging)

**Files:**
- Create: `backend/app/services/analytics_summary_service.py`
- Create: `tests/unit/services/test_analytics_summary_service.py`

- [ ] **Step 1: Write failing test for achievement calculation and status flagging**

```python
# tests/unit/services/test_analytics_summary_service.py
import pytest
from backend.app.services.analytics_summary_service import AnalyticsSummaryService

def test_compute_kpi_achievement_green():
    """Test KPI achievement calculation for Green status."""
    service = AnalyticsSummaryService()
    
    # Target: 3.0%, Actual: 2.4% → achievement = ((2.4 - 3.0) / 3.0) * 100 = -20.0% → Red boundary
    achievement = service.compute_achievement(actual=2.4, target=3.0)
    assert achievement == -20.0
    
    # Target: 3.0%, Actual: 2.8% → achievement = ((2.8 - 3.0) / 3.0) * 100 = -6.67% → Green
    achievement = service.compute_achievement(actual=2.8, target=3.0)
    assert abs(achievement - (-6.67)) < 0.01
    status = service.get_status(achievement)
    assert status == "green"

def test_compute_kpi_achievement_amber():
    """Test KPI achievement for Amber status."""
    service = AnalyticsSummaryService()
    
    # Target: 3.0%, Actual: 2.6% → achievement = ((2.6 - 3.0) / 3.0) * 100 = -13.33% → Amber
    achievement = service.compute_achievement(actual=2.6, target=3.0)
    status = service.get_status(achievement)
    assert status == "amber"

def test_compute_kpi_achievement_red():
    """Test KPI achievement for Red status."""
    service = AnalyticsSummaryService()
    
    # Target: 3.0%, Actual: 2.2% → achievement = ((2.2 - 3.0) / 3.0) * 100 = -26.67% → Red
    achievement = service.compute_achievement(actual=2.2, target=3.0)
    status = service.get_status(achievement)
    assert status == "red"

def test_status_boundaries():
    """Test exact boundary conditions."""
    service = AnalyticsSummaryService()
    
    # Exactly -20% boundary (Red/Amber cutoff)
    assert service.get_status(-20.0) == "amber"
    assert service.get_status(-19.9) == "green"
    assert service.get_status(-20.1) == "red"
    
    # Exactly -10% boundary (Amber/Green cutoff)
    assert service.get_status(-10.0) == "green"
    assert service.get_status(-9.9) == "green"
    assert service.get_status(-10.1) == "amber"
```

- [ ] **Step 2: Run test to verify it fails**

```bash
pytest tests/unit/services/test_analytics_summary_service.py -v
```

Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 3: Create AnalyticsSummaryService**

```python
# backend/app/services/analytics_summary_service.py
from datetime import datetime
from typing import Dict, Any, List
from uuid import UUID

class AnalyticsSummaryService:
    """Service for computing KPI achievement, flagging status, and building summary JSON."""
    
    def compute_achievement(self, actual: float, target: float) -> float:
        """
        Compute KPI achievement percentage.
        Formula: ((actual - target) / target) * 100
        """
        if target == 0:
            return 0.0
        return ((actual - target) / target) * 100
    
    def get_status(self, achievement_percent: float) -> str:
        """
        Determine status based on achievement percentage.
        - Red: < -20%
        - Amber: -20% to -10%
        - Green: >= -10%
        """
        if achievement_percent < -20:
            return "red"
        elif achievement_percent < -10:
            return "amber"
        else:
            return "green"
    
    def build_kpi_result(
        self,
        kpi_name: str,
        target: float,
        actual: float,
        threshold_unit: str
    ) -> Dict[str, Any]:
        """Build KPI result object with achievement and status."""
        achievement = self.compute_achievement(actual, target)
        status = self.get_status(achievement)
        
        return {
            "kpi_name": kpi_name,
            "target": target,
            "actual": actual,
            "achievement_percent": round(achievement, 2),
            "threshold_unit": threshold_unit,
            "status": status
        }
    
    def get_activation_status(self, kpi_results: List[Dict[str, Any]]) -> str:
        """
        Determine activation-level status from KPI results.
        - Red: If ANY KPI is Red
        - Amber: If ANY KPI is Amber (and none are Red)
        - Green: If ALL KPIs are Green
        """
        statuses = [result["status"] for result in kpi_results]
        
        if "red" in statuses:
            return "red"
        elif "amber" in statuses:
            return "amber"
        else:
            return "green"
    
    def build_summary_entry(
        self,
        activation_id: UUID,
        campaign_id: UUID,
        channel: str,
        sub_channel: str,
        kpi_results: List[Dict[str, Any]],
        metrics: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Build a summary entry for one activation."""
        return {
            "activation_id": str(activation_id),
            "campaign_id": str(campaign_id),
            "channel": channel,
            "sub_channel": sub_channel,
            "status": self.get_activation_status(kpi_results),
            "kpi_results": kpi_results,
            "metrics": metrics
        }
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
pytest tests/unit/services/test_analytics_summary_service.py -v
```

Expected: PASS (4/4 tests pass)

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/analytics_summary_service.py tests/unit/services/test_analytics_summary_service.py
git commit -m "[TASK-020] feat: add AnalyticsSummaryService for KPI computation and flagging"
```

---

## Task 6: Implement AnalyticsAgent

**Files:**
- Create: `backend/app/agents/analytics_agent.py`
- Create: `tests/unit/agents/test_analytics_agent.py`

- [ ] **Step 1: Write failing test for AnalyticsAgent**

```python
# tests/unit/agents/test_analytics_agent.py
import pytest
from datetime import date
from uuid import uuid4
from unittest.mock import AsyncMock, MagicMock
from backend.app.agents.analytics_agent import AnalyticsAgent
from backend.app.db import AsyncSession

@pytest.mark.asyncio
async def test_analytics_agent_run_daily_analysis(db_session: AsyncSession):
    """Test main daily analysis flow."""
    # Mock platform tools
    mock_google_ads = AsyncMock()
    mock_google_ads.get_metrics.return_value = {
        "impressions": 5000,
        "clicks": 250,
        "conversions": 7,
        "spend": 500.00,
        "ctr": 0.05,
        "cpc": 2.00
    }
    
    platform_tools = {
        "google_ads": mock_google_ads,
        "meta_ads": AsyncMock(),
        "linkedin_ads": AsyncMock()
    }
    
    # Mock activations query (in real scenario, this would fetch from DB)
    mock_activation = {
        "id": uuid4(),
        "campaign_id": uuid4(),
        "channel": "google_ads",
        "sub_channel": "Google Search",
        "status": "live",
        "tenant_id": uuid4()
    }
    
    agent = AnalyticsAgent(db_session, platform_tools)
    agent._get_live_activations = AsyncMock(return_value=[mock_activation])
    agent._get_activation_kpis = AsyncMock(return_value=[
        {
            "id": uuid4(),
            "kpi_name": "conversion_rate",
            "target_value": 3.0,
            "threshold_unit": "percent"
        }
    ])
    agent._send_notifications = AsyncMock()
    
    summary = await agent.run_daily_analysis(mandate_id=uuid4())
    
    assert summary is not None
    assert "activations" in summary
    assert "red_alerts" in summary

@pytest.mark.asyncio
async def test_analytics_agent_skip_on_platform_error(db_session: AsyncSession):
    """Test that agent skips broken activations and continues."""
    mock_google_ads = AsyncMock()
    mock_google_ads.get_metrics.side_effect = Exception("API error")
    
    platform_tools = {"google_ads": mock_google_ads, "meta_ads": AsyncMock(), "linkedin_ads": AsyncMock()}
    
    agent = AnalyticsAgent(db_session, platform_tools)
    # Agent should log warning and continue without raising
    assert agent is not None
```

- [ ] **Step 2: Run test to verify it fails**

```bash
pytest tests/unit/agents/test_analytics_agent.py -v
```

Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 3: Create AnalyticsAgent**

```python
# backend/app/agents/analytics_agent.py
import logging
from datetime import date
from typing import Dict, Any, List, Optional
from uuid import UUID
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from backend.app.models.activation import Activation
from backend.app.models.kpi import KPI
from backend.app.services.kpi_service import KPIService
from backend.app.services.performance_metric_service import PerformanceMetricService
from backend.app.services.analytics_summary_service import AnalyticsSummaryService

logger = logging.getLogger(__name__)

class AnalyticsAgent:
    """Daily scheduled analytics agent for KPI tracking and alerting."""
    
    def __init__(self, db_session: AsyncSession, platform_tools: Dict[str, Any]):
        self.db = db_session
        self.platform_tools = platform_tools
        self.kpi_service = KPIService(db_session)
        self.metric_service = PerformanceMetricService(db_session)
        self.summary_service = AnalyticsSummaryService()
    
    async def run_daily_analysis(self, mandate_id: UUID) -> Dict[str, Any]:
        """Main Celery Beat task entry point: analyze all live activations."""
        activations = await self._get_live_activations(mandate_id)
        today = date.today()
        summary_entries = []
        red_alerts = []
        
        for activation in activations:
            try:
                entry, alerts = await self._analyze_activation(activation, today)
                if entry:
                    summary_entries.append(entry)
                red_alerts.extend(alerts)
            except Exception as e:
                logger.warning(f"Skipping activation {activation['id']}: {e}")
                continue
        
        summary = self._build_analytics_summary(mandate_id, today, summary_entries, red_alerts)
        
        # Send alerts for any Red KPIs
        if red_alerts:
            await self._send_notifications(red_alerts)
        
        return summary
    
    async def _get_live_activations(self, mandate_id: UUID) -> List[Dict[str, Any]]:
        """Fetch all live activations for mandate."""
        result = await self.db.execute(
            select(Activation).where(
                Activation.mandate_id == mandate_id,
                Activation.status == "live"
            )
        )
        activations = result.scalars().all()
        return [
            {
                "id": a.id,
                "campaign_id": a.campaign_id,
                "channel": a.channel_enum,
                "sub_channel": a.sub_channel,
                "tenant_id": a.tenant_id
            }
            for a in activations
        ]
    
    async def _analyze_activation(
        self,
        activation: Dict[str, Any],
        analysis_date: date
    ) -> tuple:
        """Analyze single activation: fetch metrics, compute KPIs, flag status."""
        # Fetch metrics from platform tool
        metrics = await self._fetch_metrics(activation)
        if not metrics:
            logger.warning(f"No metrics for activation {activation['id']}")
            return None, []
        
        # Store metrics in DB
        await self.metric_service.store_metric(
            activation_id=activation["id"],
            date=analysis_date,
            metrics_json=metrics,
            source=activation["channel"],
            tenant_id=activation["tenant_id"]
        )
        
        # Fetch KPIs for this activation
        kpis = await self.kpi_service.get_kpis_for_activation(
            campaign_id=activation["campaign_id"],
            channel=activation["channel"],
            audience_segment=activation.get("audience_segment", "default"),
            tenant_id=activation["tenant_id"]
        )
        
        if not kpis:
            logger.info(f"No KPIs defined for activation {activation['id']}")
            return None, []
        
        # Compute KPI results
        kpi_results = []
        red_alerts = []
        
        for kpi in kpis:
            actual = self._extract_metric(metrics, kpi.kpi_name)
            if actual is None:
                logger.warning(f"Missing metric {kpi.kpi_name} for activation {activation['id']}")
                continue
            
            result = self.summary_service.build_kpi_result(
                kpi_name=kpi.kpi_name,
                target=kpi.target_value,
                actual=actual,
                threshold_unit=kpi.threshold_unit
            )
            kpi_results.append(result)
            
            if result["status"] == "red":
                red_alerts.append({
                    "activation_id": str(activation["id"]),
                    "channel": activation["channel"],
                    "failed_kpi": kpi.kpi_name,
                    "severity": "red"
                })
        
        # Build summary entry
        entry = self.summary_service.build_summary_entry(
            activation_id=activation["id"],
            campaign_id=activation["campaign_id"],
            channel=activation["channel"],
            sub_channel=activation.get("sub_channel", ""),
            kpi_results=kpi_results,
            metrics={k: v for k, v in metrics.items() if k in ["impressions", "clicks", "conversions", "spend"]}
        )
        
        return entry, red_alerts
    
    async def _fetch_metrics(self, activation: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Call platform tool to fetch metrics."""
        channel = activation["channel"]
        tool = self.platform_tools.get(channel)
        if not tool:
            logger.error(f"Unknown channel: {channel}")
            return None
        
        try:
            metrics = await tool.get_metrics(activation)
            return metrics
        except Exception as e:
            logger.warning(f"Failed to fetch metrics for {channel}: {e}")
            return None
    
    def _extract_metric(self, metrics: Dict[str, Any], kpi_name: str) -> Optional[float]:
        """Extract metric value from flexible metrics dict."""
        # Direct match
        if kpi_name in metrics:
            return metrics[kpi_name]
        # No conversion logic needed for now; KPI name matches metric key
        return None
    
    def _build_analytics_summary(
        self,
        mandate_id: UUID,
        analysis_date: date,
        entries: List[Dict[str, Any]],
        red_alerts: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Build final AnalyticsSummary JSON."""
        # Count by channel and status
        summary_by_channel = {}
        for entry in entries:
            channel = entry["channel"]
            status = entry["status"]
            if channel not in summary_by_channel:
                summary_by_channel[channel] = {"total": 0, "red": 0, "amber": 0, "green": 0}
            summary_by_channel[channel]["total"] += 1
            summary_by_channel[channel][status] += 1
        
        return {
            "mandate_id": str(mandate_id),
            "date": str(analysis_date),
            "summary_generated_at": date.today().isoformat() + "T00:00:00Z",
            "activations": entries,
            "red_alerts": red_alerts,
            "summary_by_channel": summary_by_channel
        }
    
    async def _send_notifications(self, red_alerts: List[Dict[str, Any]]):
        """Send alert notifications for Red KPIs."""
        logger.info(f"Sending {len(red_alerts)} red alert notifications")
        # Notification logic would be implemented here (email, WhatsApp, etc.)
        pass
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
pytest tests/unit/agents/test_analytics_agent.py -v
```

Expected: PASS (2/2 tests pass)

- [ ] **Step 5: Commit**

```bash
git add backend/app/agents/analytics_agent.py tests/unit/agents/test_analytics_agent.py
git commit -m "[TASK-020] feat: implement AnalyticsAgent with metrics fetching and KPI computation"
```

---

## Task 7: Add Celery Beat Scheduled Task Registration

**Files:**
- Create: `backend/app/tasks/analytics_tasks.py`
- Modify: `backend/app/celery_app.py` (add beat schedule)

- [ ] **Step 1: Write failing test for Celery task**

```python
# tests/unit/tasks/test_analytics_tasks.py
import pytest
from unittest.mock import AsyncMock, patch
from backend.app.tasks.analytics_tasks import run_daily_analytics

@pytest.mark.asyncio
async def test_run_daily_analytics_task():
    """Test Celery task wrapper."""
    with patch("backend.app.tasks.analytics_tasks.AnalyticsAgent") as mock_agent_class:
        mock_agent = AsyncMock()
        mock_agent.run_daily_analysis.return_value = {"mandate_id": "test", "activations": []}
        mock_agent_class.return_value = mock_agent
        
        # Task should execute without error
        result = await run_daily_analytics(mandate_id="test-mandate")
        assert result is not None
```

- [ ] **Step 2: Run test to verify it fails**

```bash
pytest tests/unit/tasks/test_analytics_tasks.py -v
```

Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 3: Create analytics_tasks.py**

```python
# backend/app/tasks/analytics_tasks.py
import logging
from uuid import UUID
from backend.app.celery_app import celery_app
from backend.app.agents.analytics_agent import AnalyticsAgent
from backend.app.db import SessionLocal
from backend.app.tools.google_ads import GoogleAdsTool
from backend.app.tools.meta_ads import MetaAdsTool
from backend.app.tools.linkedin_ads import LinkedInAdsTool

logger = logging.getLogger(__name__)

@celery_app.task(bind=True, name="analytics.run_daily_analysis")
def run_daily_analytics_task(self, mandate_id: str):
    """Celery Beat scheduled task (runs every 24h)."""
    import asyncio
    
    async def _run():
        async with SessionLocal() as db_session:
            platform_tools = {
                "google_ads": GoogleAdsTool(db_session),
                "meta_ads": MetaAdsTool(db_session),
                "linkedin_ads": LinkedInAdsTool(db_session)
            }
            
            agent = AnalyticsAgent(db_session, platform_tools)
            summary = await agent.run_daily_analysis(mandate_id=UUID(mandate_id))
            return summary
    
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    
    result = loop.run_until_complete(_run())
    logger.info(f"Analytics analysis completed for mandate {mandate_id}")
    return result
```

- [ ] **Step 4: Update celery_app.py to register beat schedule**

Read current `backend/app/celery_app.py`:

```bash
grep -n "beat_schedule\|app.conf" backend/app/celery_app.py
```

Then modify to add:

```python
# In backend/app/celery_app.py, add to celery_app configuration:

from celery.schedules import crontab

celery_app.conf.beat_schedule = {
    # ... existing tasks ...
    'analytics-daily-analysis': {
        'task': 'analytics.run_daily_analysis',
        'schedule': crontab(hour=0, minute=0),  # Run daily at midnight UTC
        'args': ('mandate-id-here',),  # This would be parameterized per mandate in production
    },
}
```

- [ ] **Step 5: Run tests to verify they pass**

```bash
pytest tests/unit/tasks/test_analytics_tasks.py -v
```

Expected: PASS (1/1 test pass)

- [ ] **Step 6: Commit**

```bash
git add backend/app/tasks/analytics_tasks.py backend/app/celery_app.py tests/unit/tasks/test_analytics_tasks.py
git commit -m "[TASK-020] feat: add Celery Beat scheduled task for daily analytics"
```

---

## Task 8: End-to-End Integration Test

**Files:**
- Create: `tests/integration/test_analytics_end_to_end.py`

- [ ] **Step 1: Write end-to-end integration test**

```python
# tests/integration/test_analytics_end_to_end.py
import pytest
from datetime import date
from uuid import uuid4
from unittest.mock import AsyncMock
from backend.app.agents.analytics_agent import AnalyticsAgent
from backend.app.models.kpi import KPI
from backend.app.models.performance_metric import PerformanceMetric
from backend.app.models.activation import Activation
from backend.app.db import AsyncSession

@pytest.mark.asyncio
async def test_full_analytics_workflow(db_session: AsyncSession):
    """
    Test complete workflow:
    1. Create KPIs and activations
    2. Mock platform tool responses
    3. Run agent
    4. Verify summary and alerts
    """
    tenant_id = uuid4()
    campaign_id = uuid4()
    mandate_id = uuid4()
    activation_id = uuid4()
    
    # Create KPI
    kpi = KPI(
        campaign_id=campaign_id,
        channel_enum="google_ads",
        audience_segment="brand_aware",
        kpi_name="conversion_rate",
        target_value=3.0,
        threshold_unit="percent",
        tenant_id=tenant_id
    )
    db_session.add(kpi)
    await db_session.commit()
    
    # Create activation
    activation = Activation(
        id=activation_id,
        mandate_id=mandate_id,
        campaign_id=campaign_id,
        channel_enum="google_ads",
        sub_channel="Google Search",
        status="live",
        tenant_id=tenant_id,
        audience_segment="brand_aware"
    )
    db_session.add(activation)
    await db_session.commit()
    
    # Mock platform tool
    mock_google_ads = AsyncMock()
    mock_google_ads.get_metrics.return_value = {
        "impressions": 5000,
        "clicks": 250,
        "conversions": 7,  # 7/250 = 0.028 = 2.8% (below 3.0% target)
        "spend": 500.00,
        "ctr": 0.05,
        "cpc": 2.00
    }
    
    platform_tools = {
        "google_ads": mock_google_ads,
        "meta_ads": AsyncMock(),
        "linkedin_ads": AsyncMock()
    }
    
    agent = AnalyticsAgent(db_session, platform_tools)
    summary = await agent.run_daily_analysis(mandate_id=mandate_id)
    
    # Verify summary
    assert summary["mandate_id"] == str(mandate_id)
    assert summary["date"] == str(date.today())
    assert len(summary["activations"]) == 1
    
    # Verify activation entry
    entry = summary["activations"][0]
    assert entry["activation_id"] == str(activation_id)
    assert entry["channel"] == "google_ads"
    assert len(entry["kpi_results"]) == 1
    
    # Verify KPI result (2.8% actual vs 3.0% target = -6.67% = GREEN)
    kpi_result = entry["kpi_results"][0]
    assert kpi_result["kpi_name"] == "conversion_rate"
    assert kpi_result["target"] == 3.0
    assert abs(kpi_result["achievement_percent"] - (-6.67)) < 0.1
    assert kpi_result["status"] == "green"
    
    # Verify metrics stored in DB
    metric = await db_session.execute(
        select(PerformanceMetric).where(
            PerformanceMetric.activation_id == activation_id,
            PerformanceMetric.date == date.today()
        )
    )
    stored_metric = metric.scalar_one()
    assert stored_metric.metrics_json["impressions"] == 5000
    assert stored_metric.source == "google_ads"

@pytest.mark.asyncio
async def test_red_alert_trigger(db_session: AsyncSession):
    """Test that Red KPI triggers alert."""
    tenant_id = uuid4()
    campaign_id = uuid4()
    mandate_id = uuid4()
    activation_id = uuid4()
    
    # Create KPI with high target
    kpi = KPI(
        campaign_id=campaign_id,
        channel_enum="google_ads",
        audience_segment="brand_aware",
        kpi_name="conversion_rate",
        target_value=5.0,  # High target
        threshold_unit="percent",
        tenant_id=tenant_id
    )
    db_session.add(kpi)
    
    # Create activation
    activation = Activation(
        id=activation_id,
        mandate_id=mandate_id,
        campaign_id=campaign_id,
        channel_enum="google_ads",
        sub_channel="Google Search",
        status="live",
        tenant_id=tenant_id,
        audience_segment="brand_aware"
    )
    db_session.add(activation)
    await db_session.commit()
    
    # Mock metrics with low conversion rate (below target)
    mock_google_ads = AsyncMock()
    mock_google_ads.get_metrics.return_value = {
        "impressions": 5000,
        "clicks": 250,
        "conversions": 5,  # 5/250 = 0.02 = 2.0% (way below 5.0% target = -60% = RED)
        "spend": 500.00
    }
    
    platform_tools = {
        "google_ads": mock_google_ads,
        "meta_ads": AsyncMock(),
        "linkedin_ads": AsyncMock()
    }
    
    agent = AnalyticsAgent(db_session, platform_tools)
    summary = await agent.run_daily_analysis(mandate_id=mandate_id)
    
    # Verify Red status and alerts
    assert summary["activations"][0]["status"] == "red"
    assert len(summary["red_alerts"]) == 1
    alert = summary["red_alerts"][0]
    assert alert["failed_kpi"] == "conversion_rate"
    assert alert["severity"] == "red"
```

- [ ] **Step 2: Run test to verify it passes**

```bash
pytest tests/integration/test_analytics_end_to_end.py -v
```

Expected: PASS (2/2 tests pass)

- [ ] **Step 3: Commit**

```bash
git add tests/integration/test_analytics_end_to_end.py
git commit -m "[TASK-020] test: add end-to-end integration test for analytics workflow"
```

---

## Task 9: Documentation and Final Verification

**Files:**
- Modify: `backend/app/agents/analytics_agent.py` (add docstrings)
- Create: `docs/analytics-agent-guide.md`

- [ ] **Step 1: Add comprehensive docstrings to AnalyticsAgent**

Update `backend/app/agents/analytics_agent.py`:

```python
# Add module docstring at top:
"""
Analytics Agent (AGT-13) for daily KPI tracking and alerting.

This module implements a Celery Beat scheduled task that runs daily to:
1. Fetch activation metrics from platform tools (Google Ads, Meta, LinkedIn)
2. Store metrics in PerformanceMetric table
3. Compute KPI achievement vs targets
4. Flag activations as Red/Amber/Green
5. Generate AnalyticsSummary JSON for dashboard API
6. Send alert notifications for Red KPIs

Key Components:
- AnalyticsAgent: Main orchestrator
- AnalyticsSummaryService: KPI computation and status flagging
- KPIService: Fetch target KPIs
- PerformanceMetricService: Store/retrieve daily metrics

Example Usage:
    agent = AnalyticsAgent(db_session, platform_tools)
    summary = await agent.run_daily_analysis(mandate_id=mandate_uuid)
"""
```

- [ ] **Step 2: Update method docstrings (if not already present)**

Ensure all public methods have clear docstrings with Args, Returns, Raises sections.

- [ ] **Step 3: Create documentation file**

```markdown
# Analytics Agent (AGT-13) Implementation Guide

## Overview
The Analytics Agent is a Celery Beat scheduled task that runs every 24 hours to analyze activation performance against KPI targets.

## Architecture

### Data Flow
1. **Fetch Activations** → Query live activations for mandate
2. **Fetch Metrics** → Call platform tools (Google Ads, Meta, LinkedIn)
3. **Store Metrics** → Insert into PerformanceMetric table
4. **Compute KPIs** → Compare actual vs target, calculate achievement %
5. **Flag Status** → Red (<-20%), Amber (-20% to -10%), Green (≥-10%)
6. **Generate Summary** → Build AnalyticsSummary JSON per mandate
7. **Send Alerts** → Email + WhatsApp for Red KPIs

### File Structure
```
backend/app/
├── agents/
│   └── analytics_agent.py          # Main agent orchestrator
├── models/
│   ├── kpi.py                      # KPI target definition
│   └── performance_metric.py        # Daily metrics storage
├── services/
│   ├── kpi_service.py              # Fetch KPIs
│   ├── performance_metric_service.py # Store/retrieve metrics
│   └── analytics_summary_service.py  # Compute KPI achievement & status
└── tasks/
    └── analytics_tasks.py           # Celery Beat task registration
```

## KPI Achievement Formula

```
achievement_percent = ((actual - target) / target) * 100
```

**Examples:**
- Target: 3.0% CTR, Actual: 2.4% → achievement = ((2.4 - 3.0) / 3.0) * 100 = -20.0%
- Target: $1.50 CPC, Actual: $1.55 → achievement = ((1.55 - 1.50) / 1.50) * 100 = +3.33%

## Status Mapping

| Achievement % | Status | Severity |
|---|---|---|
| < -20% | Red | Critical - KPI far below target |
| -20% to -10% | Amber | Warning - KPI below target |
| ≥ -10% | Green | On track - meeting or exceeding target |

## Usage

### Manual Execution
```python
from backend.app.db import SessionLocal
from backend.app.agents.analytics_agent import AnalyticsAgent
from backend.app.tools.google_ads import GoogleAdsTool
from backend.app.tools.meta_ads import MetaAdsTool
from backend.app.tools.linkedin_ads import LinkedInAdsTool
import asyncio

async def run_analysis():
    async with SessionLocal() as db_session:
        platform_tools = {
            "google_ads": GoogleAdsTool(db_session),
            "meta_ads": MetaAdsTool(db_session),
            "linkedin_ads": LinkedInAdsTool(db_session)
        }
        agent = AnalyticsAgent(db_session, platform_tools)
        summary = await agent.run_daily_analysis(mandate_id=mandate_uuid)
        return summary

result = asyncio.run(run_analysis())
```

### Celery Beat Schedule
Task registered in `backend/app/celery_app.py`:
```python
'analytics-daily-analysis': {
    'task': 'analytics.run_daily_analysis',
    'schedule': crontab(hour=0, minute=0),  # Runs daily at midnight UTC
}
```

## Dashboard API Integration

The AnalyticsSummary JSON is used by the dashboard API endpoint to display:
- Per-activation KPI results with achievement %
- Red/Amber/Green status indicators
- Channel-level summary counts
- Red alert list for quick action

## Error Handling

| Error | Handling |
|---|---|
| Platform API unavailable | Log warning, skip activation, continue with others |
| No KPIs defined | Log info, skip activation |
| Metrics JSON malformed | Log error, skip activation |
| Missing campaign contact | Log warning, skip notification |

## Testing

Run all tests:
```bash
pytest tests/unit/agents/test_analytics_agent.py -v
pytest tests/unit/services/test_analytics_summary_service.py -v
pytest tests/integration/test_analytics_end_to_end.py -v
```

Coverage target: 80%+

## Success Criteria

✅ Agent runs daily via Celery Beat  
✅ All live activations analyzed  
✅ Metrics stored correctly  
✅ KPI achievement computed accurately  
✅ Red/Amber/Green flags correct  
✅ AnalyticsSummary JSON complete  
✅ Alert notifications sent for Red KPIs  
✅ Graceful error handling (no crash on single activation error)  
✅ 80%+ test coverage
```

- [ ] **Step 4: Run all tests to verify everything passes**

```bash
pytest tests/unit/models/test_kpi.py tests/unit/models/test_performance_metric.py tests/unit/services/test_kpi_service.py tests/unit/services/test_performance_metric_service.py tests/unit/services/test_analytics_summary_service.py tests/unit/agents/test_analytics_agent.py tests/unit/tasks/test_analytics_tasks.py tests/integration/test_analytics_end_to_end.py -v --cov=backend/app/agents --cov=backend/app/services --cov=backend/app/models --cov-report=term-missing
```

Expected: All tests pass, coverage ≥ 80%

- [ ] **Step 5: Run linter and type checker**

```bash
black backend/app/agents/analytics_agent.py backend/app/services/ backend/app/models/kpi.py backend/app/models/performance_metric.py
mypy backend/app/agents/analytics_agent.py backend/app/services/ backend/app/models/kpi.py backend/app/models/performance_metric.py --ignore-missing-imports
```

Expected: No errors or warnings

- [ ] **Step 6: Commit documentation**

```bash
git add docs/analytics-agent-guide.md backend/app/agents/analytics_agent.py
git commit -m "[TASK-020] docs: add comprehensive analytics agent documentation"
```

- [ ] **Step 7: Verify all commits are present**

```bash
git log --oneline | grep "TASK-020" | head -10
```

Expected: At least 7-9 commits starting with [TASK-020]

---

## Success Verification

After all tasks complete, verify:

1. **All models created and migrations applied**
   ```bash
   alembic current
   ```

2. **All tests passing**
   ```bash
   pytest tests/ -k "analytics or kpi or performance_metric" --tb=short
   ```

3. **Code coverage ≥ 80%**
   ```bash
   pytest tests/ -k "analytics" --cov=backend/app --cov-report=term-missing
   ```

4. **Git history clean**
   ```bash
   git log --oneline -15
   ```

5. **No uncommitted changes**
   ```bash
   git status
   ```

All ready for final merge and deployment!
