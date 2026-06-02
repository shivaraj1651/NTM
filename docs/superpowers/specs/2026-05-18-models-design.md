# SQLAlchemy DB Models Design

## Goal

Add 8 missing SQLAlchemy ORM models to `backend/app/models/` to cover the Campaign lifecycle, Mandate management, and supporting audit/config entities. No existing files are touched.

## Architecture

Follow existing 1.x declarative style: each file owns its own `Base = declarative_base()`, uses `Column(Type, ...)` (not `Mapped[]`), and supplies a `to_dict()` method. `tenant_id` is a denormalized `String` — no FK constraint at ORM level. All IDs are UUIDs (string). Timestamps use `datetime.now(timezone.utc)`.

**Tech Stack:** Python 3.12, SQLAlchemy 1.x, PostgreSQL 16, pgvector (`Vector(1536)` via sqlalchemy-pgvector), pytest + SQLite in-memory.

---

## File Structure

| File | Model | Notes |
|------|-------|-------|
| `backend/app/models/campaign.py` | Campaign | Core campaign entity |
| `backend/app/models/mandate.py` | Mandate | Client mandate with geography + budget |
| `backend/app/models/campaign_concept.py` | CampaignConcept | AI-generated concept with brand embedding |
| `backend/app/models/activation.py` | Activation | Channel-level execution unit |
| `backend/app/models/budget.py` | Budget | Campaign budget with approval tracking |
| `backend/app/models/approval_log.py` | ApprovalLog | Insert-only audit log |
| `backend/app/models/client.py` | Client | Client org profile with brand embedding |
| `backend/app/models/physical_activation_log.py` | PhysicalActivationLog | Insert-only event log |

Tests: `backend/app/models/tests/test_<model>.py` for each.

---

## Field Specs

### Campaign

```python
id              String  PK  default=uuid4
tenant_id       String  NOT NULL  index
mandate_id      String  nullable
client_id       String  nullable
name            String  NOT NULL
description     Text    nullable
status          String  NOT NULL  default='pending'
                # values: pending | concepts_ready | confirmed | planned |
                #         budget_proposed | approved | creative_generating |
                #         creative_ready | live
created_at      DateTime  NOT NULL  default=utcnow
updated_at      DateTime  NOT NULL  default=utcnow  onupdate=utcnow
```

### Mandate

```python
id              String  PK  default=uuid4
tenant_id       String  NOT NULL  index
client_id       String  NOT NULL
name            String  NOT NULL
description     Text    nullable
objective       String  NOT NULL
                # values: awareness | consideration | conversion | loyalty | engagement
region          String  NOT NULL
countries       JSONB   NOT NULL  default=[]      # list[str]
competitors     JSONB   NOT NULL  default=[]      # list[str]
total_budget    Float   NOT NULL
currency        String  NOT NULL  default='USD'
start_date      Date    NOT NULL
end_date        Date    NOT NULL
status          String  NOT NULL  default='draft'
                # values: draft | pending_review | confirmed | rejected
created_at      DateTime  NOT NULL  default=utcnow
updated_at      DateTime  NOT NULL  default=utcnow  onupdate=utcnow
```

### CampaignConcept

```python
id              String  PK  default=uuid4
tenant_id       String  NOT NULL  index
campaign_id     String  NOT NULL  index
title           String  NOT NULL
description     Text    NOT NULL
strategy        JSONB   NOT NULL  default={}
brand_embedding Vector(1536)  nullable          # pgvector; skip in SQLite tests
status          String  NOT NULL  default='pending'
                # values: pending | selected | rejected
selected_by     String  nullable                # user id who selected
created_at      DateTime  NOT NULL  default=utcnow
updated_at      DateTime  NOT NULL  default=utcnow  onupdate=utcnow
```

### Activation

```python
id                String  PK  default=uuid4
tenant_id         String  NOT NULL  index
campaign_id       String  NOT NULL  index
channel           String  NOT NULL
sub_channel       String  nullable
audience_segment  String  NOT NULL
budget_allocated  Float   NOT NULL
currency          String  NOT NULL  default='USD'
platform_config   JSONB   NOT NULL  default={}
status            String  NOT NULL  default='planned'
                  # values: planned | active | paused | completed | failed
created_at        DateTime  NOT NULL  default=utcnow
updated_at        DateTime  NOT NULL  default=utcnow  onupdate=utcnow
```

### Budget

```python
id           String  PK  default=uuid4
tenant_id    String  NOT NULL  index
campaign_id  String  NOT NULL  index
total        Float   NOT NULL
currency     String  NOT NULL  default='USD'
breakdown    JSONB   NOT NULL  default={}
status       String  NOT NULL  default='draft'
             # values: draft | approved
approved_by  String  nullable              # user id
approved_at  DateTime  nullable
created_at   DateTime  NOT NULL  default=utcnow
updated_at   DateTime  NOT NULL  default=utcnow  onupdate=utcnow
```

### ApprovalLog

Insert-only. No `updated_at`.

```python
id             String  PK  default=uuid4
tenant_id      String  NOT NULL  index
entity_type    String  NOT NULL              # e.g. 'campaign', 'budget'
entity_id      String  NOT NULL  index
action         String  NOT NULL
               # values: submitted | approved | rejected
actor_id       String  NOT NULL
notes          Text    nullable
status_before  String  nullable
status_after   String  nullable
created_at     DateTime  NOT NULL  default=utcnow
```

### Client

```python
id                      String  PK  default=uuid4
tenant_id               String  NOT NULL  index
org_name                String  NOT NULL
industry                String  NOT NULL
logo_url                String  nullable
brand_guidelines_url    String  nullable
competitors             JSONB   NOT NULL  default=[]   # list[str]
brand_embedding         Vector(1536)  nullable         # pgvector; skip in SQLite tests
created_at              DateTime  NOT NULL  default=utcnow
updated_at              DateTime  NOT NULL  default=utcnow  onupdate=utcnow
```

### PhysicalActivationLog

Insert-only. `logged_at` is the event timestamp (can differ from `created_at`).

```python
id             String  PK  default=uuid4
tenant_id      String  NOT NULL  index
campaign_id    String  NOT NULL  index
activation_id  String  nullable  index
event_type     String  NOT NULL
channel        String  NOT NULL
payload        JSONB   NOT NULL  default={}
logged_at      DateTime  NOT NULL  default=utcnow
created_at     DateTime  NOT NULL  default=utcnow
```

---

## Testing Approach

**Pattern:** SQLite in-memory via existing `conftest.py` (`create_all` → yield session → `drop_all`).

**Each test file covers:**
1. Round-trip: insert with all required fields, query back, assert values
2. `to_dict()` returns correct keys
3. `created_at` auto-populates
4. `updated_at` auto-updates on change (non-log models only)
5. `tenant_id` stored and returned correctly

**pgvector exception (Client + CampaignConcept):**
`Vector(1536)` columns cannot be reflected in SQLite. Tests for these two models are decorated with:
```python
pytest.mark.skipif(
    not os.getenv("POSTGRES_TEST_URL"),
    reason="requires postgres with pgvector"
)
```
SQLite tests omit the embedding column; a separate pg-only test asserts embedding round-trip.

**ApprovalLog + PhysicalActivationLog:** Insert-only — no `updated_at` update test. Assert `created_at` auto-populates.

---

## Known Constraints

- Alembic metadata is fragmented (each file has its own `Base`). This is existing tech debt — not addressed here.
- No FK constraints at ORM level; referential integrity is enforced by application logic.
- `tenant_id` on every model is denormalized for query isolation per NTM rules.
