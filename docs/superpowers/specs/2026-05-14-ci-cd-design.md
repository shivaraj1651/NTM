---
title: CI/CD Pipeline Design
date: 2026-05-14
status: approved
---

# CI/CD Pipeline — GitHub Actions

## Goal

Run the full NTM test suite on every PR and push to `main`. Block merges if tests fail or coverage drops below 80%. Track coverage trends via Codecov.

## Triggers

- `push` to `main`
- `pull_request` targeting `main`

## Workflow File

**Location:** `.github/workflows/ci.yml`

Single job: `test`, runner: `ubuntu-latest`

## Service Containers

Spun up alongside the job via GitHub Actions native service containers:

| Service | Image | Port | Credentials |
|---|---|---|---|
| PostgreSQL | `postgres:16` | 5432 | `ntm_user / ntm_pass / ntm_db` |
| MongoDB | `mongo:7` | 27017 | none |
| Redis | `redis:7` | 6379 | none |

Health checks configured so steps don't start until services are ready.

## Job Steps

1. `actions/checkout@v4`
2. `actions/setup-python@v5` — Python 3.12
3. `actions/cache@v4` — pip cache keyed on `requirements.txt` hash
4. `pip install -r requirements.txt`
5. Run Alembic migrations — `alembic upgrade head`
6. Run pytest with coverage — `pytest --cov=backend/app --cov=tests --cov-report=xml --cov-fail-under=80`
7. Upload `coverage.xml` to Codecov — `codecov/codecov-action@v4`

## Environment Variables

Injected directly in the workflow (not secrets, test-only credentials):

```
DATABASE_URL=postgresql+asyncpg://ntm_user:ntm_pass@localhost:5432/ntm_db
MONGODB_URL=mongodb://localhost:27017/ntm
REDIS_URL=redis://localhost:6379/0
JWT_SECRET_KEY=ci-test-secret-key-not-for-production
```

Injected as GitHub secrets:

```
ANTHROPIC_API_KEY  — required for agent tests that call the real API
CODECOV_TOKEN      — from Codecov dashboard after repo connection
```

## Coverage Policy

- Threshold: **80%** (`--cov-fail-under=80`)
- Job fails (and PR is blocked) if total coverage drops below threshold
- Codecov posts a diff coverage comment on every PR showing which new lines are uncovered

## Dependencies File

A `requirements.txt` at project root is required. It must include at minimum:

- `fastapi`, `uvicorn`
- `sqlalchemy[asyncio]`, `aiosqlite`, `asyncpg`
- `alembic`
- `pytest`, `pytest-asyncio`, `pytest-cov`
- `motor` (MongoDB async driver)
- `redis`
- `celery`
- `anthropic`
- All agent/tool dependencies (langchain, crewai, etc.)

Generated via `pip freeze > requirements.txt` from the active venv, then pruned to direct dependencies.

## pytest.ini Changes

Add `addopts` to centralise coverage flags:

```ini
[pytest]
asyncio_mode = auto
testpaths = backend/app tests
python_files = test_*.py
python_classes = Test*
python_functions = test_*
addopts = --cov=backend/app --cov=tests --cov-report=xml --cov-fail-under=80
```

Note: `testpaths` expanded from `backend/app` to include the top-level `tests/` directory.

## Branch Protection (Manual Step)

After pushing the workflow, configure in GitHub → Settings → Branches → Add rule for `main`:

- [x] Require status checks to pass before merging
  - Required check: `test`
- [x] Require branches to be up to date before merging
- [x] Do not allow bypassing the above settings

## Files Created / Modified

| File | Action |
|---|---|
| `.github/workflows/ci.yml` | Create |
| `requirements.txt` | Create |
| `pytest.ini` | Modify (add `addopts` and expand `testpaths`) |

## Out of Scope

- Frontend (React) test CI — separate workflow, future task
- Deployment pipeline — separate workflow in `infra/github-actions/`
- Nightly scheduled runs
- Docker image build/push
