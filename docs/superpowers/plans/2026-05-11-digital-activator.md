# TASK-019: AGT-12 Digital Activator Agent - Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement a two-tier Celery-based agent that activates approved campaigns across Google Ads, Meta, and LinkedIn, storing platform IDs and sending confirmation notifications once all channels are live.

**Architecture:** Main agent receives an `Activation` object, spawns independent per-platform Celery subtasks (each retrying 3x on failure), waits for all to complete via Celery chord, stores platform IDs in `ActivationPlatformMapping`, then sends a single confirmation notification to the campaign manager from the parent `Campaign` record.

**Tech Stack:** FastAPI, SQLAlchemy async, Celery, Pydantic, PostgreSQL, httpx

---

## File Structure

**New Files to Create:**
- `backend/app/models/activation_platform_mapping.py` - ORM model for platform IDs
- `backend/app/models/platform_config_template.py` - ORM model for platform targeting config
- `backend/app/services/platform_config.py` - Service for translating Activation → platform config
- `backend/app/services/activation_notifications.py` - Service for campaign manager notifications
- `backend/app/tools/google_ads.py` - Google Ads platform tool (stub with activate_google subtask)
- `backend/app/tools/linkedin_ads.py` - LinkedIn Ads platform tool (stub with activate_linkedin subtask)
- `backend/app/agents/digital_activator.py` - Main agent with chord pattern
- `backend/app/tasks/activation_tasks.py` - Celery task definitions
- `backend/app/tests/test_models/test_activation_platform_mapping.py` - Model tests
- `backend/app/tests/test_services/test_platform_config.py` - Service tests
- `backend/app/tests/test_agents/test_digital_activator.py` - Agent integration tests

**Modify:**
- `backend/app/tools/meta_ads.py` - Add `activate_meta` subtask
- `backend/app/tools/__init__.py` - Export new tools
- `backend/app/models/__init__.py` - Export new models
- `backend/app/tasks/__init__.py` - Export Celery tasks
- Database migration file (created during Task 1)

---

## Tasks

### Task 1: Create ActivationPlatformMapping Model

**Files:**
- Create: `backend/app/models/activation_platform_mapping.py`
- Create: `backend/app/tests/test_models/test_activation_platform_mapping.py`
- Create: Migration file `backend/app/db/migrations/001_create_activation_platform_mapping.py`

- [ ] **Step 1: Write failing test for model creation and query**

```python
# backend/app/tests/test_models/test_activation_platform_mapping.py
import pytest
from uuid import uuid4
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from backend.app.models.activation_platform_mapping import ActivationPlatformMapping


@pytest.mark.asyncio
async def test_create_activation_platform_mapping(db_session: AsyncSession):
    """Test creating and querying ActivationPlatformMapping record."""
    activation_id = uuid4()
    
    mapping = ActivationPlatformMapping(
        activation_id=activation_id,
        channel_enum="google_ads",
        platform_campaign_id="camps_12345",
        platform_ad_id="ads_67890",
        status="live",
        error_message=None,
        tenant_id=uuid4()
    )
    
    db_session.add(mapping)
    await db_session.commit()
    
    # Query back
    result = await db_session.execute(
        select(ActivationPlatformMapping).where(
            ActivationPlatformMapping.activation_id == activation_id
        )
    )
    fetched = result.scalar_one()
    
    assert fetched.platform_campaign_id == "camps_12345"
    assert fetched.platform_ad_id == "ads_67890"
    assert fetched.status == "live"
    assert fetched.error_message is None


@pytest.mark.asyncio
async def test_update_platform_mapping_on_failure(db_session: AsyncSession):
    """Test updating mapping with error on failure."""
    activation_id = uuid4()
    tenant_id = uuid4()
    
    mapping = ActivationPlatformMapping(
        activation_id=activation_id,
        channel_enum="meta_ads",
        platform_campaign_id=None,
        platform_ad_id=None,
        status="pending",
        error_message=None,
        tenant_id=tenant_id
    )
    db_session.add(mapping)
    await db_session.commit()
    
    # Update on failure
    mapping.status = "failed"
    mapping.error_message = "API rate limit exceeded"
    await db_session.commit()
    
    result = await db_session.execute(
        select(ActivationPlatformMapping).where(
            ActivationPlatformMapping.id == mapping.id
        )
    )
    fetched = result.scalar_one()
    
    assert fetched.status == "failed"
    assert fetched.error_message == "API rate limit exceeded"
```

- [ ] **Step 2: Create the SQLAlchemy ORM model**

```python
# backend/app/models/activation_platform_mapping.py
import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, DateTime, ForeignKey, Enum as SQLEnum
from sqlalchemy.dialects.postgresql import UUID
from backend.app.db import Base
from enum import Enum as PyEnum


class ChannelEnum(str, PyEnum):
    """Supported ad platforms."""
    GOOGLE_ADS = "google_ads"
    META_ADS = "meta_ads"
    LINKEDIN_ADS = "linkedin_ads"


class ActivationPlatformMapping(Base):
    """Track platform-specific campaign and ad IDs for each activation."""
    __tablename__ = "activation_platform_mapping"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    activation_id = Column(UUID(as_uuid=True), ForeignKey("activation.id"), nullable=False, index=True)
    tenant_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    channel_enum = Column(SQLEnum(ChannelEnum), nullable=False, index=True)
    
    platform_campaign_id = Column(String, nullable=True)  # Platform-specific campaign ID
    platform_ad_id = Column(String, nullable=True)  # Platform-specific ad/creative ID
    
    status = Column(String, default="pending", nullable=False, index=True)  # pending, live, failed
    error_message = Column(String, nullable=True)
    
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=False)
```

- [ ] **Step 3: Create migration file**

```python
# backend/app/db/migrations/001_create_activation_platform_mapping.py
"""Create activation_platform_mapping table."""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


def upgrade():
    op.create_table(
        'activation_platform_mapping',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('activation_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('channel_enum', sa.String(), nullable=False),
        sa.Column('platform_campaign_id', sa.String(), nullable=True),
        sa.Column('platform_ad_id', sa.String(), nullable=True),
        sa.Column('status', sa.String(), nullable=False, server_default='pending'),
        sa.Column('error_message', sa.String(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(['activation_id'], ['activation.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_activation_platform_mapping_activation_id', 'activation_platform_mapping', ['activation_id'])
    op.create_index('ix_activation_platform_mapping_tenant_id', 'activation_platform_mapping', ['tenant_id'])
    op.create_index('ix_activation_platform_mapping_channel_enum', 'activation_platform_mapping', ['channel_enum'])
    op.create_index('ix_activation_platform_mapping_status', 'activation_platform_mapping', ['status'])


def downgrade():
    op.drop_table('activation_platform_mapping')
```

- [ ] **Step 4: Run test to verify it fails**

Run: `pytest backend/app/tests/test_models/test_activation_platform_mapping.py -v`
Expected: FAIL - "No such table: activation_platform_mapping"

- [ ] **Step 5: Run migration to create table**

Run: `alembic upgrade head`

- [ ] **Step 6: Run test to verify it passes**

Run: `pytest backend/app/tests/test_models/test_activation_platform_mapping.py -v`
Expected: PASS

- [ ] **Step 7: Commit**

```bash
git add backend/app/models/activation_platform_mapping.py \
        backend/app/tests/test_models/test_activation_platform_mapping.py \
        backend/app/db/migrations/001_create_activation_platform_mapping.py
git commit -m "[TASK-019] feat: create ActivationPlatformMapping model and migration"
```

---

### Task 2: Create PlatformConfigTemplate Model

**Files:**
- Create: `backend/app/models/platform_config_template.py`
- Create: `backend/app/tests/test_models/test_platform_config_template.py`
- Create: Migration file

- [ ] **Step 1: Write failing test for model**

```python
# backend/app/tests/test_models/test_platform_config_template.py
import pytest
from uuid import uuid4
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from backend.app.models.platform_config_template import PlatformConfigTemplate


@pytest.mark.asyncio
async def test_create_platform_config_template(db_session: AsyncSession):
    """Test creating platform config template."""
    config = PlatformConfigTemplate(
        channel_enum="google_ads",
        audience_segment="brand_aware",
        platform_targeting_json={
            "age_min": 18,
            "age_max": 65,
            "interests": ["technology", "business"],
            "device": "mobile"
        },
        budget_multiplier=1.0,
        tenant_id=uuid4()
    )
    
    db_session.add(config)
    await db_session.commit()
    
    result = await db_session.execute(
        select(PlatformConfigTemplate).where(
            PlatformConfigTemplate.channel_enum == "google_ads"
        )
    )
    fetched = result.scalar_one()
    
    assert fetched.audience_segment == "brand_aware"
    assert fetched.platform_targeting_json["age_min"] == 18
    assert fetched.budget_multiplier == 1.0
```

- [ ] **Step 2: Create the model**

```python
# backend/app/models/platform_config_template.py
import uuid
from sqlalchemy import Column, String, Float, JSON
from sqlalchemy.dialects.postgresql import UUID
from backend.app.db import Base


class PlatformConfigTemplate(Base):
    """Platform-specific targeting and budget configuration templates."""
    __tablename__ = "platform_config_template"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    
    channel_enum = Column(String, nullable=False, index=True)  # google_ads, meta_ads, linkedin_ads
    audience_segment = Column(String, nullable=False, index=True)  # brand_aware, consideration, etc.
    
    platform_targeting_json = Column(JSON, nullable=False)  # age, interests, device, etc.
    budget_multiplier = Column(Float, default=1.0, nullable=False)  # cost_estimated × multiplier = platform budget
    
    __table_args__ = (
        # Unique constraint: one template per tenant/channel/audience combo
        # (added in migration)
    )
```

- [ ] **Step 3: Create migration**

```python
# backend/app/db/migrations/002_create_platform_config_template.py
"""Create platform_config_template table."""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


def upgrade():
    op.create_table(
        'platform_config_template',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('channel_enum', sa.String(), nullable=False),
        sa.Column('audience_segment', sa.String(), nullable=False),
        sa.Column('platform_targeting_json', sa.JSON(), nullable=False),
        sa.Column('budget_multiplier', sa.Float(), nullable=False, server_default='1.0'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('tenant_id', 'channel_enum', 'audience_segment', 
                           name='uq_platform_config_tenant_channel_audience')
    )
    op.create_index('ix_platform_config_template_tenant_id', 'platform_config_template', ['tenant_id'])
    op.create_index('ix_platform_config_template_channel_enum', 'platform_config_template', ['channel_enum'])
    op.create_index('ix_platform_config_template_audience_segment', 'platform_config_template', ['audience_segment'])


def downgrade():
    op.drop_table('platform_config_template')
```

- [ ] **Step 4: Run migration and test**

Run: `alembic upgrade head && pytest backend/app/tests/test_models/test_platform_config_template.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add backend/app/models/platform_config_template.py \
        backend/app/tests/test_models/test_platform_config_template.py \
        backend/app/db/migrations/002_create_platform_config_template.py
git commit -m "[TASK-019] feat: create PlatformConfigTemplate model and migration"
```

---

### Task 3: Create PlatformConfigService

**Files:**
- Create: `backend/app/services/platform_config.py`
- Create: `backend/app/tests/test_services/test_platform_config.py`

- [ ] **Step 1: Write failing test**

```python
# backend/app/tests/test_services/test_platform_config.py
import pytest
from uuid import uuid4
from sqlalchemy.ext.asyncio import AsyncSession
from backend.app.services.platform_config import PlatformConfigService
from backend.app.models.platform_config_template import PlatformConfigTemplate


@pytest.mark.asyncio
async def test_get_platform_config_success(db_session: AsyncSession):
    """Test retrieving platform config for a channel and audience."""
    tenant_id = uuid4()
    
    # Create a template
    template = PlatformConfigTemplate(
        tenant_id=tenant_id,
        channel_enum="google_ads",
        audience_segment="brand_aware",
        platform_targeting_json={
            "age_min": 18,
            "age_max": 55,
            "interests": ["tech", "startup"]
        },
        budget_multiplier=1.2
    )
    db_session.add(template)
    await db_session.commit()
    
    # Retrieve via service
    service = PlatformConfigService(db_session)
    config = await service.get_platform_config(
        tenant_id=tenant_id,
        channel_enum="google_ads",
        audience_segment="brand_aware"
    )
    
    assert config is not None
    assert config.platform_targeting_json["age_min"] == 18
    assert config.budget_multiplier == 1.2


@pytest.mark.asyncio
async def test_get_platform_config_not_found(db_session: AsyncSession):
    """Test retrieving non-existent config returns None."""
    service = PlatformConfigService(db_session)
    
    config = await service.get_platform_config(
        tenant_id=uuid4(),
        channel_enum="linkedin_ads",
        audience_segment="non_existent"
    )
    
    assert config is None
```

- [ ] **Step 2: Implement the service**

```python
# backend/app/services/platform_config.py
from uuid import UUID
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from backend.app.models.platform_config_template import PlatformConfigTemplate


class PlatformConfigService:
    """Service for translating Activation data to platform-specific targeting."""
    
    def __init__(self, db_session: AsyncSession):
        self.db = db_session
    
    async def get_platform_config(
        self,
        tenant_id: UUID,
        channel_enum: str,
        audience_segment: str
    ) -> PlatformConfigTemplate | None:
        """
        Retrieve platform config template for a given channel and audience.
        
        Args:
            tenant_id: Tenant identifier
            channel_enum: Platform channel (google_ads, meta_ads, linkedin_ads)
            audience_segment: Audience segment name
        
        Returns:
            PlatformConfigTemplate or None if not found
        """
        result = await self.db.execute(
            select(PlatformConfigTemplate).where(
                PlatformConfigTemplate.tenant_id == tenant_id,
                PlatformConfigTemplate.channel_enum == channel_enum,
                PlatformConfigTemplate.audience_segment == audience_segment
            )
        )
        return result.scalar_one_or_none()
    
    async def calculate_platform_budget(
        self,
        activation_cost: float,
        budget_multiplier: float
    ) -> float:
        """Calculate platform-specific budget based on Activation cost and multiplier."""
        return round(activation_cost * budget_multiplier, 2)
```

- [ ] **Step 3: Run test**

Run: `pytest backend/app/tests/test_services/test_platform_config.py -v`
Expected: PASS

- [ ] **Step 4: Commit**

```bash
git add backend/app/services/platform_config.py \
        backend/app/tests/test_services/test_platform_config.py
git commit -m "[TASK-019] feat: create PlatformConfigService for platform targeting lookup"
```

---

### Task 4: Create ActivationNotificationService

**Files:**
- Create: `backend/app/services/activation_notifications.py`
- Create: `backend/app/tests/test_services/test_activation_notifications.py`

- [ ] **Step 1: Write failing test**

```python
# backend/app/tests/test_services/test_activation_notifications.py
import pytest
from uuid import uuid4
from unittest.mock import AsyncMock, patch
from backend.app.services.activation_notifications import ActivationNotificationService


@pytest.mark.asyncio
async def test_send_activation_success_notification():
    """Test sending success notification to campaign manager."""
    campaign_manager_email = "manager@example.com"
    campaign_manager_phone = "+1234567890"
    
    service = ActivationNotificationService()
    
    with patch.object(service, 'send_email', new_callable=AsyncMock) as mock_email, \
         patch.object(service, 'send_whatsapp', new_callable=AsyncMock) as mock_whatsapp:
        
        await service.send_activation_success(
            activation_id=uuid4(),
            activation_name="Summer Campaign - Web",
            campaign_manager_email=campaign_manager_email,
            campaign_manager_phone=campaign_manager_phone,
            platforms_live=["google_ads", "meta_ads"],
            budget_spent=5000.0
        )
        
        # Verify email was sent
        mock_email.assert_called_once()
        call_args = mock_email.call_args
        assert campaign_manager_email in str(call_args)
        
        # Verify WhatsApp was sent
        mock_whatsapp.assert_called_once()


@pytest.mark.asyncio
async def test_send_activation_failure_notification():
    """Test sending failure notification with details."""
    service = ActivationNotificationService()
    
    with patch.object(service, 'send_email', new_callable=AsyncMock) as mock_email, \
         patch.object(service, 'send_whatsapp', new_callable=AsyncMock) as mock_whatsapp:
        
        await service.send_activation_failure(
            activation_id=uuid4(),
            activation_name="Summer Campaign - Web",
            campaign_manager_email="manager@example.com",
            campaign_manager_phone="+1234567890",
            failed_platforms={"linkedin_ads": "API rate limit exceeded"},
            partial_success={"google_ads": "live", "meta_ads": "live"}
        )
        
        # Verify both notifications sent
        mock_email.assert_called_once()
        mock_whatsapp.assert_called_once()
```

- [ ] **Step 2: Implement the service**

```python
# backend/app/services/activation_notifications.py
from uuid import UUID
from typing import Dict, List, Optional
import logging

logger = logging.getLogger(__name__)


class ActivationNotificationService:
    """Send activation success/failure notifications to campaign manager."""
    
    async def send_email(
        self,
        to_email: str,
        subject: str,
        body: str
    ) -> bool:
        """Send email notification (stub - implement with email provider)."""
        logger.info(f"Email sent to {to_email}: {subject}")
        return True
    
    async def send_whatsapp(
        self,
        to_phone: str,
        message: str
    ) -> bool:
        """Send WhatsApp notification (stub - implement with WhatsApp provider)."""
        logger.info(f"WhatsApp sent to {to_phone}: {message}")
        return True
    
    async def send_activation_success(
        self,
        activation_id: UUID,
        activation_name: str,
        campaign_manager_email: str,
        campaign_manager_phone: str,
        platforms_live: List[str],
        budget_spent: float
    ) -> bool:
        """Send success notification when activation goes live across all platforms."""
        platforms_str = ", ".join(platforms_live)
        
        email_subject = f"✅ Campaign Activated: {activation_name}"
        email_body = f"""
        Your campaign has gone live!
        
        Activation: {activation_name}
        Activation ID: {activation_id}
        Platforms: {platforms_str}
        Budget Allocated: ${budget_spent:,.2f}
        
        Monitor performance in your dashboard.
        """
        
        whatsapp_message = f"✅ {activation_name} is now live on {platforms_str}. Budget: ${budget_spent:,.2f}"
        
        try:
            await self.send_email(campaign_manager_email, email_subject, email_body)
            await self.send_whatsapp(campaign_manager_phone, whatsapp_message)
            logger.info(f"Success notification sent for activation {activation_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to send success notification: {e}")
            return False
    
    async def send_activation_failure(
        self,
        activation_id: UUID,
        activation_name: str,
        campaign_manager_email: str,
        campaign_manager_phone: str,
        failed_platforms: Dict[str, str],
        partial_success: Optional[Dict[str, str]] = None
    ) -> bool:
        """Send notification when activation fails on one or more platforms."""
        failed_str = ", ".join(failed_platforms.keys())
        
        email_subject = f"⚠️ Activation Issue: {activation_name}"
        email_body = f"""
        Your campaign activation encountered issues.
        
        Activation: {activation_name}
        Activation ID: {activation_id}
        Failed Platforms: {failed_str}
        
        Details:
        """
        for platform, error in failed_platforms.items():
            email_body += f"\n- {platform}: {error}"
        
        if partial_success:
            email_body += f"\n\nSuccessful: {', '.join(partial_success.keys())}"
        
        whatsapp_message = f"⚠️ {activation_name} failed on {failed_str}. Check email for details."
        
        try:
            await self.send_email(campaign_manager_email, email_subject, email_body)
            await self.send_whatsapp(campaign_manager_phone, whatsapp_message)
            logger.info(f"Failure notification sent for activation {activation_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to send failure notification: {e}")
            return False
```

- [ ] **Step 3: Run test**

Run: `pytest backend/app/tests/test_services/test_activation_notifications.py -v`
Expected: PASS

- [ ] **Step 4: Commit**

```bash
git add backend/app/services/activation_notifications.py \
        backend/app/tests/test_services/test_activation_notifications.py
git commit -m "[TASK-019] feat: create ActivationNotificationService for email and WhatsApp"
```

---

### Task 5: Implement Google Ads activate_google Subtask

**Files:**
- Create: `backend/app/tools/google_ads.py`
- Create: `backend/app/tests/test_tools/test_google_ads.py`

- [ ] **Step 1: Write failing test**

```python
# backend/app/tests/test_tools/test_google_ads.py
import pytest
from uuid import uuid4
from unittest.mock import patch, AsyncMock
from backend.app.tools.google_ads import activate_google


@pytest.mark.asyncio
async def test_activate_google_success():
    """Test successful Google Ads campaign activation."""
    activation = {
        "id": str(uuid4()),
        "cost_estimated": 5000.0,
        "estimated_reach": 50000,
        "audience_segment": "brand_aware",
        "geography": "US",
        "format": "Video 15s"
    }
    
    platform_config = {
        "age_min": 18,
        "age_max": 65,
        "interests": ["technology"]
    }
    
    creative_url = "https://example.com/creative.mp4"
    
    with patch('backend.app.tools.google_ads.httpx.AsyncClient') as mock_client:
        mock_response = AsyncMock()
        mock_response.json.return_value = {
            "id": "camps_123456",
            "resourceName": "customers/1234567890/campaigns/1234567890"
        }
        mock_client.return_value.__aenter__.return_value.post.return_value = mock_response
        
        result = await activate_google(
            activation=activation,
            platform_config=platform_config,
            creative_url=creative_url
        )
        
        assert result["campaign_id"] == "camps_123456"
        assert result["status"] == "live"


@pytest.mark.asyncio
async def test_activate_google_api_failure():
    """Test handling API failure gracefully."""
    activation = {"id": str(uuid4())}
    platform_config = {}
    creative_url = "https://example.com/creative.mp4"
    
    with patch('backend.app.tools.google_ads.httpx.AsyncClient') as mock_client:
        mock_client.return_value.__aenter__.return_value.post.side_effect = Exception("API Error")
        
        result = await activate_google(
            activation=activation,
            platform_config=platform_config,
            creative_url=creative_url
        )
        
        assert result["status"] == "failed"
        assert "API Error" in result["error"]
```

- [ ] **Step 2: Implement Google Ads tool**

```python
# backend/app/tools/google_ads.py
"""Google Ads platform tool for campaign activation."""
import logging
from typing import Dict, Any, Optional
import httpx

logger = logging.getLogger(__name__)

GOOGLE_ADS_API_ENDPOINT = "https://googleads.googleapis.com/v17/customers/{customer_id}/campaigns"


async def activate_google(
    activation: Dict[str, Any],
    platform_config: Dict[str, Any],
    creative_url: str,
    customer_id: Optional[str] = None
) -> Dict[str, Any]:
    """
    Activate a campaign on Google Ads.
    
    Args:
        activation: Activation record with budget and targeting
        platform_config: Google Ads-specific targeting from PlatformConfigTemplate
        creative_url: URL to creative asset
        customer_id: Google Ads customer ID (from environment or config)
    
    Returns:
        Dict with campaign_id, ad_id, status, error
    """
    if not customer_id:
        customer_id = "1234567890"
    
    try:
        payload = {
            "campaign": {
                "name": activation.get("name", "Campaign"),
                "status": "ENABLED",
                "budget_allocation_strategy": "OPTIMIZE_FOR_REACH",
                "bidding_strategy": {
                    "type_": "MAXIMIZE_CONVERSIONS",
                    "maximize_conversions": {
                        "target_cpa_micros": int(activation.get("cost_estimated", 0) * 1_000_000)
                    }
                }
            },
            "targeting": {
                "age_range": platform_config.get("age_range"),
                "interests": platform_config.get("interests", []),
                "geographic": platform_config.get("geographic")
            },
            "creatives": [
                {
                    "url": creative_url,
                    "type": "VIDEO"
                }
            ]
        }
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"{GOOGLE_ADS_API_ENDPOINT}",
                json=payload,
                headers={
                    "Authorization": f"Bearer <token>",
                    "Content-Type": "application/json"
                }
            )
            response.raise_for_status()
            
            data = response.json()
            campaign_id = data.get("id")
            
            ad_payload = {"creative_url": creative_url}
            ad_response = await client.post(
                f"{GOOGLE_ADS_API_ENDPOINT}/{campaign_id}/ads",
                json=ad_payload,
                headers={"Authorization": f"Bearer <token>"}
            )
            ad_response.raise_for_status()
            ad_data = ad_response.json()
            ad_id = ad_data.get("id")
            
            logger.info(f"Google Ads campaign {campaign_id} activated successfully")
            
            return {
                "campaign_id": campaign_id,
                "ad_id": ad_id,
                "status": "live",
                "error": None
            }
    
    except Exception as e:
        logger.error(f"Google Ads activation failed: {e}")
        return {
            "campaign_id": None,
            "ad_id": None,
            "status": "failed",
            "error": str(e)
        }
```

- [ ] **Step 3: Run test**

Run: `pytest backend/app/tests/test_tools/test_google_ads.py -v`
Expected: PASS

- [ ] **Step 4: Commit**

```bash
git add backend/app/tools/google_ads.py \
        backend/app/tests/test_tools/test_google_ads.py
git commit -m "[TASK-019] feat: implement Google Ads activation tool"
```

---

### Task 6: Implement Meta Ads activate_meta Subtask

**Files:**
- Modify: `backend/app/tools/meta_ads.py` (add activate_meta function)
- Modify: `backend/app/tests/test_tools/test_meta_ads.py` (add activate_meta tests)

- [ ] **Step 1: Write failing test**

```python
# Add to backend/app/tests/test_tools/test_meta_ads.py
import pytest
from uuid import uuid4
from unittest.mock import patch, AsyncMock
from backend.app.tools.meta_ads import activate_meta


@pytest.mark.asyncio
async def test_activate_meta_success():
    """Test successful Meta campaign activation."""
    activation = {
        "id": str(uuid4()),
        "cost_estimated": 5000.0,
        "estimated_reach": 100000,
        "audience_segment": "consideration",
        "geography": "US",
        "format": "Static Image"
    }
    
    platform_config = {
        "age_min": 25,
        "age_max": 55,
        "interests": ["business"],
        "device": "mobile"
    }
    
    creative_url = "https://example.com/image.jpg"
    
    with patch('backend.app.tools.meta_ads.httpx.AsyncClient') as mock_client:
        mock_response = AsyncMock()
        mock_response.json.return_value = {
            "campaign_id": "123456789",
            "adset_id": "987654321",
            "ad_id": "111222333"
        }
        mock_client.return_value.__aenter__.return_value.post.return_value = mock_response
        
        result = await activate_meta(
            activation=activation,
            platform_config=platform_config,
            creative_url=creative_url
        )
        
        assert result["campaign_id"] == "123456789"
        assert result["ad_id"] == "111222333"
        assert result["status"] == "live"
```

- [ ] **Step 2: Add activate_meta function to meta_ads.py**

```python
# Add this function to backend/app/tools/meta_ads.py

async def activate_meta(
    activation: Dict[str, Any],
    platform_config: Dict[str, Any],
    creative_url: str,
    access_token: Optional[str] = None
) -> Dict[str, Any]:
    """
    Activate a campaign on Meta (Facebook/Instagram).
    
    Args:
        activation: Activation record with budget and targeting
        platform_config: Meta-specific targeting from PlatformConfigTemplate
        creative_url: URL to creative asset (image or video)
        access_token: Meta API access token
    
    Returns:
        Dict with campaign_id, ad_id, status, error
    """
    if not access_token:
        access_token = "<meta-token>"
    
    try:
        campaign_payload = {
            "name": activation.get("name", "Campaign"),
            "objective": "LINK_CLICKS",
            "status": "ACTIVE",
            "daily_budget": int(activation.get("cost_estimated", 0) * 100)
        }
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            campaign_response = await client.post(
                "https://graph.instagram.com/v19.0/act_1234/campaigns",
                params={"access_token": access_token},
                json=campaign_payload
            )
            campaign_response.raise_for_status()
            campaign_data = campaign_response.json()
            campaign_id = campaign_data.get("id")
            
            adset_payload = {
                "name": f"{activation.get('name')} - Adset",
                "campaign_id": campaign_id,
                "status": "ACTIVE",
                "daily_budget": int(activation.get("cost_estimated", 0) * 100),
                "targeting": {
                    "age_min": platform_config.get("age_min", 18),
                    "age_max": platform_config.get("age_max", 65),
                    "geo_locations": {"regions": [{"key": "US"}]},
                    "device_platforms": ["mobile", "desktop"]
                }
            }
            
            adset_response = await client.post(
                "https://graph.instagram.com/v19.0/act_1234/adsets",
                params={"access_token": access_token},
                json=adset_payload
            )
            adset_response.raise_for_status()
            adset_data = adset_response.json()
            adset_id = adset_data.get("id")
            
            ad_payload = {
                "name": f"{activation.get('name')} - Ad",
                "adset_id": adset_id,
                "status": "ACTIVE",
                "creative": {
                    "object_story_spec": {
                        "page_id": "1234567890",
                        "link_data": {
                            "image_hash": "image_hash_from_url",
                            "link": creative_url,
                            "message": "Check this out!"
                        }
                    }
                }
            }
            
            ad_response = await client.post(
                "https://graph.instagram.com/v19.0/act_1234/ads",
                params={"access_token": access_token},
                json=ad_payload
            )
            ad_response.raise_for_status()
            ad_data = ad_response.json()
            ad_id = ad_data.get("id")
            
            logger.info(f"Meta campaign {campaign_id} activated successfully")
            
            return {
                "campaign_id": campaign_id,
                "ad_id": ad_id,
                "status": "live",
                "error": None
            }
    
    except Exception as e:
        logger.error(f"Meta activation failed: {e}")
        return {
            "campaign_id": None,
            "ad_id": None,
            "status": "failed",
            "error": str(e)
        }
```

- [ ] **Step 3: Run test**

Run: `pytest backend/app/tests/test_tools/test_meta_ads.py::test_activate_meta_success -v`
Expected: PASS

- [ ] **Step 4: Commit**

```bash
git add backend/app/tools/meta_ads.py \
        backend/app/tests/test_tools/test_meta_ads.py
git commit -m "[TASK-019] feat: add activate_meta Celery subtask to Meta Ads tool"
```

---

### Task 7: Implement LinkedIn Ads activate_linkedin Subtask

**Files:**
- Create: `backend/app/tools/linkedin_ads.py`
- Create: `backend/app/tests/test_tools/test_linkedin_ads.py`

- [ ] **Step 1: Write failing test**

```python
# backend/app/tests/test_tools/test_linkedin_ads.py
import pytest
from uuid import uuid4
from unittest.mock import patch, AsyncMock
from backend.app.tools.linkedin_ads import activate_linkedin


@pytest.mark.asyncio
async def test_activate_linkedin_success():
    """Test successful LinkedIn campaign activation."""
    activation = {
        "id": str(uuid4()),
        "cost_estimated": 3000.0,
        "estimated_reach": 30000,
        "audience_segment": "brand_aware",
        "geography": "US",
        "format": "Static Image"
    }
    
    platform_config = {
        "seniority": ["director", "c_level"],
        "job_title": ["marketing", "business"],
        "industries": ["technology"]
    }
    
    creative_url = "https://example.com/linkedin-image.jpg"
    
    with patch('backend.app.tools.linkedin_ads.httpx.AsyncClient') as mock_client:
        mock_response = AsyncMock()
        mock_response.json.return_value = {
            "id": "urn:li:sponsoredCampaign:123456",
            "adId": "urn:li:sponsoredCreative:789012"
        }
        mock_client.return_value.__aenter__.return_value.post.return_value = mock_response
        
        result = await activate_linkedin(
            activation=activation,
            platform_config=platform_config,
            creative_url=creative_url
        )
        
        assert "123456" in result["campaign_id"]
        assert result["status"] == "live"
```

- [ ] **Step 2: Implement LinkedIn Ads tool**

```python
# backend/app/tools/linkedin_ads.py
"""LinkedIn Ads platform tool for B2B campaign activation."""
import logging
from typing import Dict, Any, Optional
import httpx

logger = logging.getLogger(__name__)

LINKEDIN_ADS_API_ENDPOINT = "https://api.linkedin.com/v2/sponsoredCampaigns"


async def activate_linkedin(
    activation: Dict[str, Any],
    platform_config: Dict[str, Any],
    creative_url: str,
    access_token: Optional[str] = None
) -> Dict[str, Any]:
    """
    Activate a campaign on LinkedIn.
    
    Args:
        activation: Activation record with budget and targeting
        platform_config: LinkedIn-specific targeting from PlatformConfigTemplate
        creative_url: URL to creative asset
        access_token: LinkedIn API access token
    
    Returns:
        Dict with campaign_id, ad_id, status, error
    """
    if not access_token:
        access_token = "<linkedin-token>"
    
    try:
        campaign_payload = {
            "name": activation.get("name", "Campaign"),
            "status": "ACTIVE",
            "costType": "CPM",
            "unitCost": {"currencyCode": "USD", "amount": 5},
            "dailyBudget": {"currencyCode": "USD", "amount": int(activation.get("cost_estimated", 0))}
        }
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            campaign_response = await client.post(
                LINKEDIN_ADS_API_ENDPOINT,
                headers={
                    "Authorization": f"Bearer {access_token}",
                    "Content-Type": "application/json",
                    "LinkedIn-Version": "202401"
                },
                json=campaign_payload
            )
            campaign_response.raise_for_status()
            campaign_data = campaign_response.json()
            campaign_id = campaign_data.get("id")
            
            creative_payload = {
                "campaignId": campaign_id,
                "status": "ACTIVE",
                "creativeContent": {
                    "contentReference": creative_url,
                    "contentTitle": activation.get("name", "Campaign"),
                    "contentDescription": "Check out our latest campaign"
                },
                "targetingCriteria": {
                    "seniorities": platform_config.get("seniority", []),
                    "jobTitles": platform_config.get("job_title", []),
                    "industries": platform_config.get("industries", []),
                    "locations": [{"country": "US"}]
                }
            }
            
            creative_response = await client.post(
                "https://api.linkedin.com/v2/sponsoredCreatives",
                headers={
                    "Authorization": f"Bearer {access_token}",
                    "Content-Type": "application/json",
                    "LinkedIn-Version": "202401"
                },
                json=creative_payload
            )
            creative_response.raise_for_status()
            creative_data = creative_response.json()
            ad_id = creative_data.get("id")
            
            logger.info(f"LinkedIn campaign {campaign_id} activated successfully")
            
            return {
                "campaign_id": campaign_id,
                "ad_id": ad_id,
                "status": "live",
                "error": None
            }
    
    except Exception as e:
        logger.error(f"LinkedIn activation failed: {e}")
        return {
            "campaign_id": None,
            "ad_id": None,
            "status": "failed",
            "error": str(e)
        }
```

- [ ] **Step 3: Run test**

Run: `pytest backend/app/tests/test_tools/test_linkedin_ads.py -v`
Expected: PASS

- [ ] **Step 4: Commit**

```bash
git add backend/app/tools/linkedin_ads.py \
        backend/app/tests/test_tools/test_linkedin_ads.py
git commit -m "[TASK-019] feat: implement LinkedIn Ads activation tool"
```

---

### Task 8: Implement Main Digital Activator Agent

**Files:**
- Create: `backend/app/agents/digital_activator.py`
- Create: `backend/app/tests/test_agents/test_digital_activator.py`

**Remaining task details in plan file. Dispatcher will provide remaining tasks incrementally.**
