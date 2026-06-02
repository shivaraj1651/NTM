# CI/CD GitHub Actions Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a GitHub Actions CI pipeline that runs the full test suite (unit + integration) on every PR and push to `main`, blocks merges on test failure or coverage below 80%, and reports diff coverage via Codecov.

**Architecture:** Single `test` job on `ubuntu-latest` using GitHub Actions native service containers for PostgreSQL 16, MongoDB 7, and Redis 7. pytest runs with `--cov-fail-under=80` so the job fails (and the PR is blocked) if coverage drops. Codecov receives `coverage.xml` and posts a diff comment on every PR.

**Tech Stack:** GitHub Actions, pytest, pytest-cov, Codecov, Python 3.12, PostgreSQL 16, MongoDB 7, Redis 7, Alembic

---

## File Map

| File | Action | Purpose |
|---|---|---|
| `requirements.txt` | Create | Pinned dependencies for CI install |
| `pytest.ini` | Modify | Expand testpaths, add coverage addopts |
| `.github/workflows/ci.yml` | Create | Full CI workflow |

---

### Task 1: Generate requirements.txt

**Files:**
- Create: `requirements.txt` (project root)

- [ ] **Step 1: List all currently installed packages**

Run in the project venv (PowerShell):
```powershell
pip freeze
```

Expected: long list of packages with pinned versions.

- [ ] **Step 2: Create requirements.txt**

Create `requirements.txt` at project root with the following content (replace version pins with actual output from `pip freeze` for packages that exist in your environment — add any missing ones):

```text
# Web framework
fastapi>=0.115.0
uvicorn[standard]>=0.30.0
python-multipart>=0.0.9

# Auth
fastapi-users[sqlalchemy]>=13.0.0
fastapi-users-db-sqlalchemy>=4.0.0

# Settings
pydantic>=2.7.0
pydantic-settings>=2.3.0

# Database — PostgreSQL
sqlalchemy[asyncio]>=2.0.30
asyncpg>=0.29.0
alembic>=1.13.0

# Database — MongoDB
motor>=3.4.0

# Cache / queue
redis>=5.0.4
celery[redis]>=5.4.0
kombu>=5.3.0

# AI / agents
anthropic>=0.28.0
langchain>=0.2.0
langchain-anthropic>=0.1.0

# Testing
pytest>=8.2.0
pytest-asyncio>=0.23.0
pytest-cov>=5.0.0
aiosqlite>=0.20.0
httpx>=0.27.0

# Utilities
python-dotenv>=1.0.0
```

- [ ] **Step 3: Validate the file installs cleanly**

```powershell
pip install -r requirements.txt --dry-run
```

Expected: no errors. If a package is missing or has a wrong name, fix `requirements.txt` before continuing.

- [ ] **Step 4: Commit**

```powershell
git add requirements.txt
git commit -m "chore: add requirements.txt for CI

Co-authored-by: katharguppe <katharguppe@users.noreply.github.com>"
```

---

### Task 2: Update pytest.ini

**Files:**
- Modify: `pytest.ini`

Current content:
```ini
[pytest]
asyncio_mode = auto
testpaths = backend/app
python_files = test_*.py
python_classes = Test*
python_functions = test_*
```

- [ ] **Step 1: Update pytest.ini**

Replace the full file content with:

```ini
[pytest]
asyncio_mode = auto
testpaths = backend tests
python_files = test_*.py
python_classes = Test*
python_functions = test_*
addopts = --cov=backend/app --cov=tests --cov-report=xml --cov-fail-under=80
```

Changes made:
- `testpaths` expanded from `backend/app` to `backend tests` — now discovers `backend/tests/` (integration, routers, services) and top-level `tests/` (agents, unit)
- `addopts` added — coverage runs automatically on every `pytest` invocation

- [ ] **Step 2: Verify test discovery**

```powershell
pytest --collect-only -q 2>&1 | Select-Object -First 30
```

Expected: list of test files from both `backend/` and `tests/`. No import errors.

If you see `ModuleNotFoundError`, check that `PYTHONPATH` includes the project root:
```powershell
$env:PYTHONPATH = "."
pytest --collect-only -q 2>&1 | Select-Object -First 30
```

- [ ] **Step 3: Run tests locally to confirm coverage threshold passes**

```powershell
$env:PYTHONPATH = "."
pytest -x -q
```

Expected: all tests pass, coverage report printed, no `FAIL Required test coverage of 80%` message.

If coverage is below 80%, do NOT lower the threshold — investigate which modules have no tests and note them. The threshold is a gate, not a target to game.

- [ ] **Step 4: Commit**

```powershell
git add pytest.ini
git commit -m "chore: expand testpaths and add coverage addopts to pytest.ini

Co-authored-by: katharguppe <katharguppe@users.noreply.github.com>"
```

---

### Task 3: Create .github/workflows/ci.yml

**Files:**
- Create: `.github/workflows/ci.yml`

- [ ] **Step 1: Create the .github/workflows directory**

```powershell
New-Item -ItemType Directory -Force .github\workflows
```

- [ ] **Step 2: Create .github/workflows/ci.yml**

Create the file with this exact content:

```yaml
name: CI

on:
  push:
    branches: [main]
  pull_request:
    branches: [main]

jobs:
  test:
    runs-on: ubuntu-latest

    services:
      postgres:
        image: postgres:16
        env:
          POSTGRES_USER: ntm_user
          POSTGRES_PASSWORD: ntm_pass
          POSTGRES_DB: ntm_db
        ports:
          - 5432:5432
        options: >-
          --health-cmd pg_isready
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5

      mongo:
        image: mongo:7
        ports:
          - 27017:27017
        options: >-
          --health-cmd "mongosh --eval 'db.runCommand({ ping: 1 })'"
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5

      redis:
        image: redis:7
        ports:
          - 6379:6379
        options: >-
          --health-cmd "redis-cli ping"
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5

    env:
      DATABASE_URL: postgresql+asyncpg://ntm_user:ntm_pass@localhost:5432/ntm_db
      MONGODB_URL: mongodb://localhost:27017/ntm
      REDIS_URL: redis://localhost:6379/0
      JWT_SECRET_KEY: ci-test-secret-key-not-for-production
      ANTHROPIC_API_KEY: ${{ secrets.ANTHROPIC_API_KEY }}
      PYTHONPATH: .

    steps:
      - name: Checkout
        uses: actions/checkout@v4

      - name: Set up Python 3.12
        uses: actions/setup-python@v5
        with:
          python-version: "3.12"

      - name: Cache pip
        uses: actions/cache@v4
        with:
          path: ~/.cache/pip
          key: ${{ runner.os }}-pip-${{ hashFiles('requirements.txt') }}
          restore-keys: |
            ${{ runner.os }}-pip-

      - name: Install dependencies
        run: pip install -r requirements.txt

      - name: Run Alembic migrations
        run: alembic upgrade head

      - name: Run tests with coverage
        run: pytest -x -q

      - name: Upload coverage to Codecov
        uses: codecov/codecov-action@v4
        with:
          token: ${{ secrets.CODECOV_TOKEN }}
          files: ./coverage.xml
          fail_ci_if_error: false
```

- [ ] **Step 3: Commit**

```powershell
git add .github/workflows/ci.yml
git commit -m "ci: add GitHub Actions workflow with service containers and coverage

Co-authored-by: katharguppe <katharguppe@users.noreply.github.com>"
```

---

### Task 4: Connect Codecov

**Files:** None (external service configuration)

- [ ] **Step 1: Sign in to Codecov**

Go to https://codecov.io and sign in with your GitHub account.

- [ ] **Step 2: Connect the ntm repository**

After signing in:
1. Click **Add new repository**
2. Find `ntm` in the list
3. Click **Setup repo**
4. Copy the `CODECOV_TOKEN` value shown on screen

- [ ] **Step 3: Add CODECOV_TOKEN to GitHub secrets**

In your GitHub repo:
1. Go to **Settings** → **Secrets and variables** → **Actions**
2. Click **New repository secret**
3. Name: `CODECOV_TOKEN`
4. Value: paste the token from Codecov
5. Click **Add secret**

- [ ] **Step 4: Add ANTHROPIC_API_KEY to GitHub secrets**

In the same secrets page:
1. Click **New repository secret**
2. Name: `ANTHROPIC_API_KEY`
3. Value: your Anthropic API key (from `.env` locally)
4. Click **Add secret**

---

### Task 5: Push Branch and Verify CI

- [ ] **Step 1: Push the feature branch**

```powershell
git push origin feature/TASK-020
```

- [ ] **Step 2: Open a pull request**

```powershell
gh pr create --title "ci: add GitHub Actions CI pipeline" --body "$(cat <<'EOF'
## Summary
- Adds `.github/workflows/ci.yml` with PostgreSQL 16, MongoDB 7, Redis 7 service containers
- Runs full test suite (unit + integration) with 80% coverage gate
- Uploads coverage to Codecov for PR diff comments

## Test plan
- [ ] CI workflow runs on this PR
- [ ] All tests pass
- [ ] Coverage report appears in PR via Codecov

Co-Authored-By: katharguppe <katharguppe@users.noreply.github.com>
EOF
)"
```

- [ ] **Step 3: Monitor the workflow run**

```powershell
gh run list --branch feature/TASK-020 --limit 3
```

Then watch live logs:
```powershell
gh run watch
```

Expected: `test` job goes green. If it fails, check:
- **Install step fails** → missing package in `requirements.txt`
- **Alembic step fails** → `DATABASE_URL` env var not reaching alembic; check `alembic.ini` uses `os.environ.get("DATABASE_URL")`
- **pytest fails** → test failure or import error; check `PYTHONPATH=.` is set
- **Coverage below 80%** → check which modules are uncovered with `pytest --cov-report=term-missing`

- [ ] **Step 4: Verify Codecov comment appears on the PR**

After the workflow completes, check the PR on GitHub. Codecov should have posted a comment showing coverage diff. If not, verify `CODECOV_TOKEN` secret was set correctly.

---

### Task 6: Enable Branch Protection

**This is a manual step in GitHub settings.**

- [ ] **Step 1: Open branch protection settings**

Go to your GitHub repo → **Settings** → **Branches** → **Add branch protection rule**

- [ ] **Step 2: Configure the rule**

Branch name pattern: `main`

Check these boxes:
- [x] Require a pull request before merging
- [x] Require status checks to pass before merging
  - In the search box, type `test` and select the `test` check (it appears after the first CI run)
- [x] Require branches to be up to date before merging
- [x] Do not allow bypassing the above settings

Click **Create** (or **Save changes**).

After this, any PR that fails the `test` job will show a red ✗ and the **Merge** button will be greyed out.

---

## Troubleshooting Reference

| Symptom | Likely cause | Fix |
|---|---|---|
| `ModuleNotFoundError: No module named 'backend'` | `PYTHONPATH` not set | Add `PYTHONPATH: .` to workflow `env` block |
| `alembic: command not found` | alembic not in requirements.txt | Add `alembic>=1.13.0` to requirements.txt |
| `connection refused` to postgres/mongo/redis | Service container not healthy yet | GHA waits for health checks automatically; if it still fails, increase `--health-retries` |
| Coverage always 0% | `--cov` paths wrong | Verify `backend/app` and `tests` directories exist in CI runner with `ls -la` step |
| Codecov comment not appearing | Wrong token or `fail_ci_if_error: false` silently failing | Check workflow logs for the Codecov upload step |
