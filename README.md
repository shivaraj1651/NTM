# NTM — AI-Native Campaign Management Platform

NTM is a full-stack, multi-tenant advertising campaign management platform powered by AI agents. It takes a brand from a raw marketing brief all the way to live digital ad campaigns — generating strategy, media plans, budgets, copy, images, audio, and video using large language models and third-party creative APIs, then activating across Google Ads, Meta, and LinkedIn.

---

## Table of Contents

1. [What It Does](#1-what-it-does)
2. [Tech Stack](#2-tech-stack)
3. [Architecture Overview](#3-architecture-overview)
4. [AI Agents](#4-ai-agents)
5. [Campaign Workflow](#5-campaign-workflow)
6. [User Roles](#6-user-roles)
7. [Project Structure](#7-project-structure)
8. [Prerequisites](#8-prerequisites)
9. [Getting API Keys](#9-getting-api-keys)
10. [Local Setup](#10-local-setup)
11. [Environment Variables](#11-environment-variables)
12. [Running the Project](#12-running-the-project)
13. [Seed Data and Test Accounts](#13-seed-data-and-test-accounts)
14. [Running Tests](#14-running-tests)
15. [API Reference](#15-api-reference)
16. [Frontend Pages](#16-frontend-pages)
17. [Deploying to Render](#17-deploying-to-render)
18. [Stub Mode (No API Keys)](#18-stub-mode-no-api-keys)
19. [Troubleshooting](#19-troubleshooting)

---

## 1. What It Does

NTM automates the entire campaign lifecycle for advertising agencies and brands:

- **Onboarding** — a brand sets up their organisation, logo, brand guidelines, and competitors
- **Mandate creation** — define a campaign brief: objective, budget, target audience, geography, channels, and timeline
- **AI strategy** — the platform generates 3 campaign concepts via the Campaign Strategist agent
- **Media planning** — an Activation Master Plan is created with channel/market/phase breakdowns and cost estimates
- **Budget optimisation** — AI redistributes budget across channels for maximum ROI
- **Creative generation** — copy, scripts, images (Stability AI), audio (ElevenLabs), and video (Kling AI) are generated per activation
- **Creative Studio** — review, regenerate, and download every creative asset
- **Campaign activation** — push live to Google Ads, Meta, and LinkedIn with a single click
- **KPI & Analytics** — real-time performance tracking with RAG (Red/Amber/Green) status, spend trends, and replanning alerts

---

## 2. Tech Stack

| Layer | Technology |
|---|---|
| **Backend** | Python 3.12, FastAPI, Uvicorn |
| **Task queue** | Celery 5.6, Redis 7 (broker + result backend) |
| **Primary database** | PostgreSQL 16 with pgvector extension |
| **Document store** | MongoDB 7 (campaigns, creatives, analytics) |
| **Cache / broker** | Redis 7 |
| **Object storage** | MinIO (local) / Cloudflare R2 or AWS S3 (production) |
| **ORM / migrations** | SQLAlchemy 2 (async), Alembic |
| **Frontend** | React 18, TypeScript, Vite, Tailwind CSS, shadcn/ui |
| **State management** | Zustand (auth), TanStack Query (server state) |
| **LLMs** | Anthropic Claude (Haiku, Sonnet), OpenAI GPT-4o |
| **Creative APIs** | Stability AI (images), ElevenLabs (audio), Kling AI (video), OpenAI DALL·E |
| **Ad platforms** | Google Ads API v17, Meta Marketing API, LinkedIn Ads API |
| **Analytics** | Google Analytics 4, SerpAPI (competitive intel) |
| **Containerisation** | Docker, Docker Compose |
| **Deployment** | Render (API, workers, static site) |

---

## 3. Architecture Overview

```
Browser (React SPA)
        │  HTTP /api/v1/*
        ▼
  ┌─────────────┐
  │  FastAPI    │  ← handles auth, CRUD, dispatches Celery tasks
  │  (ntm-api)  │
  └──────┬──────┘
         │ Redis broker
  ┌──────▼──────────────────────────────────┐
  │           Celery Workers                │
  │  ntm-agent-worker  │  ntm-beat          │
  │  (AI tasks)        │  (scheduled jobs)  │
  └──────┬─────────────┴────────────────────┘
         │
  ┌──────▼───────────────────────────────────────────┐
  │  AI Agents (15 agents)                           │
  │  Mandate Analyst → Campaign Strategist →         │
  │  Media Planner → Budget Optimizer →              │
  │  Copywriter / Scriptwriter / Image / Audio /     │
  │  Video Generator → Digital Activator →           │
  │  Analytics Agent → Replanning Agent →            │
  │  Report Generator                                │
  └──────┬───────────────────────────────────────────┘
         │
  ┌──────▼──────────────────────────────────┐
  │  External APIs                          │
  │  Anthropic · OpenAI · Stability AI      │
  │  ElevenLabs · Kling AI · Google Ads     │
  │  Meta · LinkedIn · SerpAPI · GA4        │
  └─────────────────────────────────────────┘

Databases
  PostgreSQL  ← users, tenants, roles, mandates (structured data)
  MongoDB     ← campaigns, creatives, media plans, analytics (documents)
  Redis       ← Celery broker, task results, cache
  S3 / R2     ← generated images, audio files, video files
```

---

## 4. AI Agents

Each agent is a single Python module under `backend/app/agents/`. All LLM calls are async and use Claude Haiku by default for speed.

| ID | Agent | What it does |
|---|---|---|
| AGT-01 | **Mandate Analyst** | Analyses a new mandate, scores it for risk/opportunity, produces a structured brief |
| AGT-02 | **Competitive Intel** | Uses SerpAPI to research competitors and identify whitespace gaps |
| AGT-03 | **Campaign Strategist** | Generates 3 campaign concepts with channel mix, tone, message architecture |
| AGT-04 | **Media Planner** | Creates an Activation Master Plan: phases × channels × geographies with CPM/reach estimates |
| AGT-05 | **Budget Optimizer** | Redistributes budget across channels to maximise ROI given the activation plan |
| AGT-06 | **Creative Director** | Orchestrates all creative agents, manages approval cycles |
| AGT-07 | **Copywriter** | Writes ad copy variants per platform and audience segment |
| AGT-08 | **Scriptwriter** | Writes video/radio scripts with scene-by-scene breakdowns |
| AGT-09 | **Image Generator** | Generates images via Stability AI or OpenAI DALL·E |
| AGT-10 | **Audio Generator** | Generates voiceovers and audio ads via ElevenLabs |
| AGT-11 | **Video Generator** | Generates video via Kling AI |
| AGT-12 | **Digital Activator** | Pushes campaigns live to Google Ads, Meta, LinkedIn |
| AGT-13 | **Analytics Agent** | Pulls performance data, computes KPI achievement, flags red alerts |
| AGT-14 | **Replanning Agent** | Triggered when KPIs go red — re-runs media planning for failing channels |
| AGT-15 | **Report Generator** | Produces weekly/monthly campaign performance reports |

---

## 5. Campaign Workflow

A campaign moves through these statuses in order:

```
pending
  │  AGT-03 generates 3 concepts (background)
  ▼
concepts_ready
  │  User selects a concept
  ▼
confirmed
  │  AGT-04 creates activation plan (background, ~instant)
  ▼
planned
  │  User clicks "Approve Budget" → AGT-05 runs (background)
  ▼
budget_pending → budget_proposed
  │  User confirms budget
  ▼
approved
  │  User clicks "Generate Creatives" → AGT-06/07/08/09/10/11 run
  ▼
creative_generating → creative_ready
  │  User reviews creatives in Creative Studio
  │  User clicks "Go Live" → AGT-12 activates on ad platforms
  ▼
live
  │  AGT-13 polls platform APIs for performance data
  │  KPIs tracked in real time — red alerts trigger AGT-14
  ▼
(ongoing analytics + replanning)
```

---

## 6. User Roles

| Role | Email (seed) | Permissions |
|---|---|---|
| `platform_admin` | admin@acme.test | Everything — all tenants, all settings |
| `tenant_admin` | tenant@acme.test | Manage users, brand, campaigns for their tenant |
| `brand_manager` | brand@acme.test | Manage brand settings and campaigns |
| `cmo` | cmo@acme.test | View all campaigns and analytics |
| `creative_lead` | creative@acme.test | Manage creative assets |
| `campaign_manager` | campaign@acme.test | Run campaigns end-to-end |
| `viewer` | viewer@acme.test | Read-only access |

All seed accounts use password: `devpass123`

---

## 7. Project Structure

```
ntm/
├── backend/
│   ├── app/
│   │   ├── agents/          # 15 AI agents (AGT-01 to AGT-15)
│   │   ├── core/            # Auth, config, RBAC, DB session
│   │   ├── models/          # SQLAlchemy models (PostgreSQL)
│   │   ├── routers/         # FastAPI route handlers
│   │   ├── schemas/         # Pydantic schemas
│   │   ├── services/        # Business logic layer
│   │   ├── tasks/           # Celery tasks (campaign, mandate, reports)
│   │   ├── tools/           # External API wrappers (Google, Meta, LinkedIn, etc.)
│   │   ├── external/        # Stub helpers for dev without real API keys
│   │   └── scripts/         # seed.py, create_tables.py
│   ├── tests/               # pytest test suites (480+ tests)
│   └── Dockerfile
├── frontend/
│   ├── src/
│   │   ├── api/             # Axios client + typed API functions
│   │   ├── components/      # Shared UI components (shadcn/ui)
│   │   ├── hooks/           # TanStack Query hooks
│   │   ├── pages/           # Route-level page components
│   │   ├── store/           # Zustand stores (auth)
│   │   ├── types/           # TypeScript type definitions
│   │   └── mocks/           # MSW mock handlers for tests
│   ├── Dockerfile
│   └── package.json
├── alembic/                 # Database migration scripts
├── docker-compose.yml       # Full local dev stack
├── render.yaml              # Render deployment blueprint
└── .env.example             # Template for environment variables
```

---

## 8. Prerequisites

Install these before starting:

| Tool | Version | Download |
|---|---|---|
| Docker Desktop | Latest | [docker.com/products/docker-desktop](https://www.docker.com/products/docker-desktop/) |
| Git | Any | [git-scm.com](https://git-scm.com) |
| Node.js | 20+ | [nodejs.org](https://nodejs.org) (only needed for local frontend dev) |
| Python | 3.12+ | [python.org](https://www.python.org) (only needed for local backend dev) |

For full functionality you will also need accounts (free tiers available) at the services listed in the next section.

---

## 9. Getting API Keys

This section explains where to get every key the platform needs. If you just want to run it locally without real AI, see [Stub Mode](#18-stub-mode-no-api-keys) first.

### Anthropic (Claude — required for AI features)
1. Go to [console.anthropic.com](https://console.anthropic.com)
2. Sign up or log in → click **API Keys** in the left sidebar
3. Click **Create Key** → name it `ntm-dev` → copy the key
4. It starts with `sk-ant-api03-...`
5. Set `ANTHROPIC_API_KEY=sk-ant-api03-YOUR_KEY_HERE`

### OpenAI (image generation + fallback LLM)
1. Go to [platform.openai.com](https://platform.openai.com)
2. Sign up → click your avatar (top right) → **API Keys**
3. Click **Create new secret key** → copy it
4. It starts with `sk-proj-...`
5. Set `OPENAI_API_KEY=sk-proj-YOUR_KEY_HERE`

### Google Ads API
1. Apply for a developer token at [ads.google.com/home/tools/manager-accounts](https://ads.google.com/home/tools/manager-accounts) → **API Center**
2. Create a Google Cloud project at [console.cloud.google.com](https://console.cloud.google.com)
3. Enable the **Google Ads API** in the library
4. Create an **OAuth 2.0 Client ID** (Desktop App) → download the JSON
5. Use the downloaded credentials to run the OAuth flow and get a refresh token
6. Set these variables:
   ```
   GOOGLE_ADS_DEVELOPER_TOKEN=your_developer_token
   GOOGLE_ADS_CLIENT_ID=your_client_id.apps.googleusercontent.com
   GOOGLE_ADS_CLIENT_SECRET=your_client_secret
   GOOGLE_ADS_REFRESH_TOKEN=your_refresh_token
   GOOGLE_ADS_CUSTOMER_ID=your_10_digit_customer_id
   ```
> Tip: `NTM_ADS_TEST_MODE=1` lets you test without actually spending money on ads.

### Meta (Facebook / Instagram Ads)
1. Go to [developers.facebook.com](https://developers.facebook.com) → **My Apps** → **Create App**
2. Choose **Business** type → set up the app
3. Add the **Marketing API** product
4. Go to **Business Settings** → create a System User with admin access
5. Generate a System User token with `ads_management` and `ads_read` permissions
6. Set these variables:
   ```
   META_APP_ID=your_app_id
   META_APP_SECRET=your_app_secret
   META_SYSTEM_USER_TOKEN=your_system_user_token
   META_AD_ACCOUNT_ID=act_your_ad_account_id
   ```

### LinkedIn Ads (optional)
1. Go to [linkedin.com/developers/apps](https://www.linkedin.com/developers/apps) → **Create App**
2. Under **Products**, request access to **Marketing Developer Platform**
3. Get your Client ID and Client Secret from the app settings
4. Set these variables:
   ```
   LINKEDIN_CLIENT_ID=your_client_id
   LINKEDIN_CLIENT_SECRET=your_client_secret
   ```

### Stability AI (image generation)
1. Go to [platform.stability.ai](https://platform.stability.ai) → sign up
2. Click your avatar → **API Keys** → **Create API Key**
3. Set `STABILITY_AI_API_KEY=sk-YOUR_KEY_HERE`

### ElevenLabs (audio / voiceover generation)
1. Go to [elevenlabs.io](https://elevenlabs.io) → sign up (free tier: 10,000 chars/month)
2. Click your avatar → **Profile** → copy your **API Key**
3. Set `ELEVENLABS_API_KEY=your_key_here`

### Kling AI (video generation)
1. Go to [klingai.com](https://klingai.com) → sign up for API access
2. From the developer portal, get your Access Key and Secret Key
3. Set:
   ```
   KLING_AI_ACCESS_KEY=your_access_key
   KLING_AI_SECRET_KEY=your_secret_key
   ```

### SerpAPI (competitive intelligence)
1. Go to [serpapi.com](https://serpapi.com) → sign up (free tier: 100 searches/month)
2. From the dashboard, copy your **API Key**
3. Set `SERPAPI_API_KEY=your_key_here`

### Google Analytics 4 (performance analytics — optional)
1. In Google Cloud Console, enable the **Google Analytics Data API**
2. Create a Service Account → download the JSON key file
3. Share your GA4 property with the service account email
4. Set:
   ```
   GA4_PROPERTY_ID=your_property_id
   GA4_SERVICE_ACCOUNT_JSON_PATH=/path/to/service_account.json
   ```

---

## 10. Local Setup

### Step 1 — Clone the repository
```bash
git clone https://github.com/Lakshmikanth-27/ntm.git
cd ntm
```

### Step 2 — Create your environment file
```bash
cp .env.example .env
```
Open `.env` and fill in your API keys as described in the previous section. For a quick start without real keys, set `NTM_STUB_EXTERNAL=1` (see [Stub Mode](#18-stub-mode-no-api-keys)).

### Step 3 — Start the full stack
```bash
docker compose up --build
```

This starts 9 containers:
- `ntm-postgres` — PostgreSQL 16 with pgvector
- `ntm-mongo` — MongoDB 7
- `ntm-redis` — Redis 7
- `ntm-minio` — MinIO object storage
- `ntm-api` — FastAPI backend (port 8000)
- `ntm-agent-worker` — Celery AI task worker
- `ntm-beat` — Celery Beat scheduler
- `ntm-flower` — Celery task monitor (port 5555)
- `ntm-frontend` — React app served via nginx (port 3000)

The first build takes 3–5 minutes to download and install all dependencies. Subsequent starts take under 30 seconds.

### Step 4 — Check everything is running
```
http://localhost:3000       ← React frontend
http://localhost:8000/docs  ← FastAPI interactive API docs (Swagger UI)
http://localhost:5555       ← Celery Flower task monitor
http://localhost:9001       ← MinIO console (storage browser)
```

> **Note:** The API runs database migrations automatically on first start via the Docker entrypoint. You do not need to run `alembic upgrade head` manually when using Docker.

---

## 11. Environment Variables

Copy `.env.example` to `.env`. Never commit your `.env` file — it is in `.gitignore`.

```bash
# ── Databases ─────────────────────────────────────────────────────────────────
DATABASE_URL=postgresql+asyncpg://ntm:ntm_dev@localhost:5432/ntm
POSTGRES_USER=ntm
POSTGRES_PASSWORD=ntm_dev
POSTGRES_DB=ntm

MONGODB_URL=mongodb://ntm:ntm_dev@localhost:27017
MONGO_USER=ntm
MONGO_PASSWORD=ntm_dev

REDIS_URL=redis://localhost:6379/0

# ── Object Storage ────────────────────────────────────────────────────────────
S3_ENDPOINT_URL=http://localhost:9000          # MinIO locally, R2/S3 in production
S3_PUBLIC_URL=http://localhost:9000
S3_BUCKET=ntm-assets
AWS_REGION=ap-south-1
AWS_ACCESS_KEY=your_access_key
AWS_SECRET_KEY=your_secret_key

# ── Auth ──────────────────────────────────────────────────────────────────────
SECRET_KEY=generate_a_64_char_hex_string_here   # openssl rand -hex 32
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=60
REFRESH_TOKEN_EXPIRE_DAYS=7

# ── LLM ───────────────────────────────────────────────────────────────────────
ANTHROPIC_API_KEY=sk-ant-api03-YOUR_KEY_HERE
OPENAI_API_KEY=sk-proj-YOUR_KEY_HERE

# ── Ad Platform Mode ──────────────────────────────────────────────────────────
NTM_ADS_TEST_MODE=1          # 1 = test mode (no real spend), 0 = live mode

# ── Google Ads ────────────────────────────────────────────────────────────────
GOOGLE_ADS_DEVELOPER_TOKEN=your_developer_token
GOOGLE_ADS_CLIENT_ID=your_client_id.apps.googleusercontent.com
GOOGLE_ADS_CLIENT_SECRET=your_client_secret
GOOGLE_ADS_REFRESH_TOKEN=your_refresh_token
GOOGLE_ADS_CUSTOMER_ID=your_customer_id

# ── Meta Ads ──────────────────────────────────────────────────────────────────
META_APP_ID=your_app_id
META_APP_SECRET=your_app_secret
META_SYSTEM_USER_TOKEN=your_system_user_token
META_AD_ACCOUNT_ID=your_ad_account_id

# ── LinkedIn Ads ──────────────────────────────────────────────────────────────
LINKEDIN_CLIENT_ID=your_client_id
LINKEDIN_CLIENT_SECRET=your_client_secret

# ── Creative APIs ─────────────────────────────────────────────────────────────
STABILITY_AI_API_KEY=sk-YOUR_KEY_HERE
ELEVENLABS_API_KEY=your_key_here
KLING_AI_ACCESS_KEY=your_access_key
KLING_AI_SECRET_KEY=your_secret_key

# ── Research ──────────────────────────────────────────────────────────────────
SERPAPI_API_KEY=your_key_here

# ── Analytics ─────────────────────────────────────────────────────────────────
GA4_PROPERTY_ID=your_property_id
GA4_SERVICE_ACCOUNT_JSON_PATH=/path/to/service_account.json

# ── Dev Controls ─────────────────────────────────────────────────────────────
NTM_STUB_EXTERNAL=0           # set to 1 to skip all real API calls
FRONTEND_URL=http://localhost:3000
```

Generate a secure `SECRET_KEY` with:
```bash
openssl rand -hex 32
```

---

## 12. Running the Project

### Using Docker (recommended)

```bash
# Start everything
docker compose up --build

# Start in background
docker compose up -d --build

# Stop everything
docker compose down

# Stop and wipe all data (databases, storage)
docker compose down -v

# Rebuild one service after a code change
docker compose build ntm-api && docker compose up -d ntm-api

# Rebuild all backend services
docker compose build ntm-api ntm-agent-worker ntm-beat ntm-frontend
docker compose up -d ntm-api ntm-agent-worker ntm-beat ntm-frontend

# View logs
docker compose logs -f ntm-api
docker compose logs -f ntm-agent-worker

# Run a shell inside the API container
docker compose exec ntm-api bash
```

### Local development (without Docker)

If you want to run the backend or frontend outside Docker for faster iteration:

**Backend:**
```bash
# Install Python dependencies
pip install -r backend/requirements.txt

# Set PYTHONPATH
export PYTHONPATH=$(pwd)

# Run migrations
alembic upgrade head

# Start API server
uvicorn backend.app.main:app --host 0.0.0.0 --port 8000 --reload

# Start Celery worker (in a separate terminal)
celery -A backend.app.tasks worker --loglevel=info --concurrency=2

# Start Celery Beat scheduler (in a separate terminal)
celery -A backend.app.tasks beat --loglevel=info
```

**Frontend:**
```bash
cd frontend

# Install Node dependencies
npm install

# Start dev server (hot reload on port 5173)
npm run dev

# Build for production
npm run build
```

---

## 13. Seed Data and Test Accounts

The seed script creates one tenant (`Acme`) and 7 user accounts. Run it after the containers are up:

```bash
docker compose exec ntm-api python -m backend.app.scripts.seed
```

Or inside the API container shell:
```bash
python -m backend.app.scripts.seed
```

### Test accounts

All accounts use the password: **`devpass123`**

| Role | Email | What you can do |
|---|---|---|
| `platform_admin` | admin@acme.test | Full access to all tenants and platform settings |
| `tenant_admin` | tenant@acme.test | Manage your tenant's users, brand, and campaigns |
| `brand_manager` | brand@acme.test | Create and manage campaigns |
| `cmo` | cmo@acme.test | View all campaigns and analytics |
| `creative_lead` | creative@acme.test | Review and approve creative assets |
| `campaign_manager` | campaign@acme.test | Run the full campaign lifecycle |
| `viewer` | viewer@acme.test | Read-only access |

### Running a complete campaign (step by step)

1. Log in as `tenant@acme.test` at `http://localhost:3000`
2. Go to **Onboarding** and fill in your organisation details
3. Go to **Mandates** → **New Mandate** and fill in the campaign brief
4. Once the mandate is analysed, go to **Campaigns** → **New Campaign** from that mandate
5. Wait for AI concepts to generate (spinner on the Concepts page, ~10 seconds)
6. Select your preferred concept → click **Confirm**
7. The Activation Plan generates instantly → click **Approve Budget**
8. Budget optimisation runs → review the budget proposal → click **Confirm Budget**
9. Click **Generate Creatives** → wait for copy/images/audio/video to generate
10. Open **Creative Studio** to review, regenerate, or download assets
11. When satisfied, go to **Go Live** → click **Activate Campaign**
12. Monitor performance on the **KPI Dashboard** and **Analytics** pages

---

## 14. Running Tests

### Backend tests

```bash
# Run all backend tests
docker compose exec ntm-api pytest

# Run with coverage report
docker compose exec ntm-api pytest --cov=backend/app --cov-report=term-missing

# Run a specific test file
docker compose exec ntm-api pytest backend/tests/agents/test_media_planner.py

# Run a specific test by name
docker compose exec ntm-api pytest -k "test_budget_allocation"

# Run without Docker (from project root)
pytest backend/tests/ -q
```

### Frontend tests

```bash
cd frontend

# Run all tests once
npm test

# Run in watch mode
npm run test:watch

# Run with coverage
npm run test -- --coverage
```

### Test accounts in tests

Backend tests use SQLite in-memory for isolation — no real database needed. Integration tests that hit MongoDB use a test database prefix.

Frontend tests use MSW (Mock Service Worker) to intercept API calls — no running backend needed.

---

## 15. API Reference

The full interactive API documentation is available at:
- **Swagger UI:** `http://localhost:8000/docs`
- **ReDoc:** `http://localhost:8000/redoc`

### Key endpoints

#### Auth
```
POST   /api/v1/auth/login          Log in, returns access + refresh tokens
POST   /api/v1/auth/refresh        Refresh access token
POST   /api/v1/auth/logout         Invalidate session
GET    /api/v1/auth/me             Get current user profile
```

#### Mandates
```
GET    /api/v1/mandates            List mandates for current tenant
POST   /api/v1/mandates            Create a new mandate (triggers AGT-01)
GET    /api/v1/mandates/{id}       Get mandate details + analysis
PATCH  /api/v1/mandates/{id}       Update mandate fields
```

#### Campaigns
```
POST   /api/v1/campaigns                              Create campaign from mandate (triggers AGT-03)
GET    /api/v1/campaigns/{id}                         Get campaign with all data
POST   /api/v1/campaigns/{id}/confirm                 Select a concept (triggers AGT-04)
GET    /api/v1/campaigns/{id}/activation-plan         Get the activation plan
POST   /api/v1/campaigns/{id}/propose-budget          Trigger budget optimisation (AGT-05)
POST   /api/v1/campaigns/{id}/confirm-budget          Accept the budget proposal
POST   /api/v1/campaigns/{id}/generate-creatives      Trigger all creative agents
POST   /api/v1/campaigns/{id}/go-live                 Activate on ad platforms (AGT-12)
```

#### Creatives
```
GET    /api/v1/creatives                              List all creative assets
GET    /api/v1/creatives?campaign_id={id}             Filter by campaign
GET    /api/v1/creatives/{id}                         Get a single asset
PATCH  /api/v1/creatives/{id}/status                  Approve / request revision
GET    /api/v1/creatives/{id}/download                Get download URL
POST   /api/v1/campaigns/{id}/creatives/{kind}/{assetId}/regenerate   Regenerate one asset
```

#### Analytics
```
GET    /api/v1/analytics/dashboard?mandate_id={id}&as_of_date={date}   KPI summary
GET    /api/v1/analytics/trends?tenant_id={id}&days={n}                Spend trends
POST   /api/v1/analytics/replan/{campaign_id}                          Trigger replanning
```

#### Admin
```
GET    /api/v1/admin/tenants       List all tenants (platform_admin only)
GET    /api/v1/admin/users         List all users
POST   /api/v1/admin/users         Create a user
GET    /api/v1/admin/roles         List RBAC roles
GET    /api/v1/admin/audit-log     View audit log
```

---

## 16. Frontend Pages

| URL | Page | Role required |
|---|---|---|
| `/login` | Login | Public |
| `/onboarding` | Brand setup wizard | tenant_admin |
| `/mandates` | Mandate list | brand_manager+ |
| `/mandates/new` | Create mandate | brand_manager+ |
| `/mandates/:id` | Mandate summary + AI analysis | brand_manager+ |
| `/campaigns` | Campaign list | campaign_manager+ |
| `/campaigns/:id` | Campaign detail | campaign_manager+ |
| `/campaigns/:id/concepts` | AI concept selection | campaign_manager+ |
| `/campaigns/:id/plan` | Activation plan | campaign_manager+ |
| `/campaigns/:id/budget` | Budget proposal | campaign_manager+ |
| `/campaigns/:id/creatives` | Creative assets list | creative_lead+ |
| `/campaigns/:id/go-live` | Go live / platform results | campaign_manager+ |
| `/campaigns/:id/kpis` | KPI config | campaign_manager+ |
| `/creative-studio` | All creatives browser | creative_lead+ |
| `/kpi-dashboard` | KPI / KRA dashboard | cmo+ |
| `/admin/analytics` | Analytics with trends | tenant_admin+ |
| `/admin/tenants` | Tenant management | platform_admin |
| `/admin/users` | User management | tenant_admin+ |
| `/admin/roles` | RBAC roles | platform_admin |
| `/admin/audit-log` | Audit trail | tenant_admin+ |
| `/health` | System health monitor | Any |

---

## 17. Deploying to Render

### What runs where

| Service | Render type | Plan |
|---|---|---|
| FastAPI API | Web Service | Free (or Starter $7/mo) |
| Celery Worker | Background Worker | Free |
| Celery Beat | Background Worker | Free |
| React Frontend | Static Site | Free |
| PostgreSQL | Managed Database | Free (90 days) |
| Redis | Managed Redis | Free |
| MongoDB | **MongoDB Atlas** (external) | Free M0 |
| File storage | **Cloudflare R2** (external) | Free 10GB |

### Step 1 — Set up MongoDB Atlas (external, free)
1. Go to [cloud.mongodb.com](https://cloud.mongodb.com) → sign up
2. Create a free **M0 cluster** in the region closest to your users
3. Create a database user: **Database Access** → **Add New User**
   - Username: `ntm_prod`, Password: generate a strong one
4. Allow connections from anywhere: **Network Access** → **Add IP** → **0.0.0.0/0**
5. Click **Connect** → **Drivers** → copy the connection string:
   ```
   mongodb+srv://ntm_prod:YOUR_PASSWORD@cluster0.xxxxx.mongodb.net/ntm?retryWrites=true&w=majority
   ```

### Step 2 — Set up Cloudflare R2 (replaces MinIO, free 10GB)
1. Go to [dash.cloudflare.com](https://dash.cloudflare.com) → sign up free
2. Left sidebar → **R2 Object Storage** → **Create bucket** → name it `ntm-assets`
3. **Manage R2 API Tokens** → **Create API Token**
   - Permissions: Object Read & Write on the `ntm-assets` bucket
   - Save the **Access Key ID** and **Secret Access Key**
4. From the bucket **Settings**, copy the S3 API endpoint:
   ```
   https://YOUR_ACCOUNT_ID.r2.cloudflarestorage.com
   ```
5. Enable public access for the bucket to get a public URL for served assets

### Step 3 — Deploy from GitHub to Render
1. Go to [render.com](https://render.com) → sign up with GitHub
2. Click **New +** → **Blueprint**
3. Select your `ntm` repository → Render reads `render.yaml` and lists all services
4. Click **Apply** — Render creates all services simultaneously

### Step 4 — Set secret environment variables
The `render.yaml` marks all secrets as `sync: false`, meaning you must paste them manually. For each of `ntm-api`, `ntm-worker`, and `ntm-beat`:

Go to the service → **Environment** tab → add:

```
MONGODB_URL          = mongodb+srv://ntm_prod:PASSWORD@cluster0.xxxxx.mongodb.net/ntm?...
S3_ENDPOINT_URL      = https://YOUR_ACCOUNT_ID.r2.cloudflarestorage.com
S3_PUBLIC_URL        = https://pub-XXXX.r2.dev
AWS_ACCESS_KEY       = your_r2_access_key_id
AWS_SECRET_KEY       = your_r2_secret_access_key
ANTHROPIC_API_KEY    = sk-ant-api03-...
OPENAI_API_KEY       = sk-proj-...
GOOGLE_ADS_*         = (your Google Ads credentials)
META_*               = (your Meta credentials)
SERPAPI_API_KEY      = your_key
KLING_AI_ACCESS_KEY  = your_key
KLING_AI_SECRET_KEY  = your_key
ELEVENLABS_API_KEY   = your_key
```

For `ntm-api` also add:
```
FRONTEND_URL = https://ntm-frontend.onrender.com
```

For `ntm-frontend` (Static Site) add:
```
VITE_API_BASE_URL = https://ntm-api.onrender.com/api/v1
```

### Step 5 — Run database migrations
Once `ntm-api` shows as **Live**, open its **Shell** tab and run:
```bash
alembic upgrade head
python -m backend.app.scripts.seed
```

### Step 6 — Verify
- Open `https://ntm-frontend.onrender.com`
- Log in with `tenant@acme.test` / `devpass123`

### Important notes on free tier
- **Web Services on the free tier sleep after 15 minutes of inactivity.** The first request after sleep takes ~30 seconds to wake up. Upgrade to the $7/month Starter plan for always-on hosting.
- **PostgreSQL free tier expires after 90 days.** Upgrade to Starter ($7/month) before the deadline to avoid data loss.
- **Every `git push origin main` triggers an automatic redeploy** of all services.

---

## 18. Stub Mode (No API Keys)

If you want to run the platform without any real API keys — to explore the UI and workflow — set:

```bash
NTM_STUB_EXTERNAL=1
```

in your `.env` file, then restart the stack:

```bash
docker compose down && docker compose up -d
```

In stub mode:
- All LLM calls (Claude, OpenAI) return hardcoded sample data instantly
- All creative generation (images, audio, video) returns placeholder URLs
- All ad platform API calls (Google, Meta, LinkedIn) return mock success responses
- The entire campaign workflow completes in seconds instead of minutes

This is useful for UI development, demos, and onboarding without any cost.

To re-enable real API calls:
```bash
NTM_STUB_EXTERNAL=0
```

---

## 19. Troubleshooting

### Containers not starting
```bash
docker compose logs ntm-api        # check for Python import errors
docker compose logs ntm-postgres   # check database startup
docker compose ps                  # check which containers are unhealthy
```

### Frontend shows blank page
```bash
docker compose logs ntm-frontend   # check nginx errors
```
Usually caused by a failed API build. Check `ntm-api` logs first.

### Database migration errors
```bash
docker compose exec ntm-api alembic history        # see migration history
docker compose exec ntm-api alembic current        # see current head
docker compose exec ntm-api alembic upgrade head   # run missing migrations
```

### Celery tasks not running
```bash
docker compose logs ntm-agent-worker   # check for import errors
# Open Flower at http://localhost:5555 to see queued/failed tasks
```
The most common cause is a missing environment variable (e.g., `ANTHROPIC_API_KEY` not set). Set `NTM_STUB_EXTERNAL=1` to bypass real API calls.

### "Could not connect to Redis" error
Redis must be healthy before Celery starts. Check:
```bash
docker compose exec ntm-redis redis-cli ping   # should return PONG
```

### MinIO / S3 connection errors
For local dev, MinIO must be running. Check:
```bash
docker compose ps ntm-minio
# Access MinIO console at http://localhost:9001
# Default credentials: ntm_minio / ntm_minio_dev
```

### Reset everything (clean slate)
```bash
docker compose down -v          # stops all containers and deletes all volumes
docker compose up --build -d    # rebuilds and restarts
docker compose exec ntm-api python -m backend.app.scripts.seed   # re-seed
```

### Port conflicts
If ports 3000, 5432, 8000, 27017, or 6379 are already in use on your machine, edit `docker-compose.yml` and change the host port (left side of `:`):
```yaml
ports:
  - "8001:8000"   # change 8000 to 8001 if 8000 is taken
```

---

## Security

- **Never commit `.env`** — it is in `.gitignore`. Use environment variables in CI/CD and hosting platforms.
- **Rotate keys immediately** if they are ever accidentally committed or exposed in logs.
- **`NTM_ADS_TEST_MODE=1`** prevents real budget spend on ad platforms — always use this unless you intend to run live campaigns.
- **`SECRET_KEY`** must be a random 64-character hex string. Generate one with `openssl rand -hex 32`. Never reuse the dev default in production.
- All API endpoints are protected by JWT auth. The CORS policy only allows requests from `FRONTEND_URL`.

---

## License

Proprietary — NTM Engineering. All rights reserved.
