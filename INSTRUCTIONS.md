# INSTRUCTIONS.md
# Nexus Tensor Meridian (NTM) — Dev Team Setup & Run Guide
# Owner: Srinivas / SherpaVector
# Jai Jagannath

---

> **READ THIS ENTIRE DOCUMENT BEFORE TOUCHING ANY SCRIPT.**
> Follow every step in the exact sequence shown. Do not skip steps.
> Do not improvise. If something fails, stop and ask before continuing.

---

## TABLE OF CONTENTS

1. Prerequisites — What You Must Have Before Starting
2. One-Time Machine Setup
3. GitHub Repository Setup (Your Responsibility)
4. Adding katharguppe as Co-Author
5. Project Scaffold
6. Environment Configuration
7. Starting the Dev Stack
8. Running Your First Session in Claude Code
9. Per-Session Discipline (Read Every Day)
10. Claude Cowork + Marketing Plugin Setup
11. Git Workflow
12. Troubleshooting

---

## 1. PREREQUISITES — WHAT YOU MUST HAVE BEFORE STARTING

Install all of the following before running any script. Every single one is required.

| Tool | Required Version | Install Link |
|---|---|---|
| Node.js | v20 or higher | https://nodejs.org |
| Git | Any recent | https://git-scm.com |
| Docker Desktop | Latest stable | https://www.docker.com/products/docker-desktop |
| Python | 3.12 or higher | https://www.python.org/downloads |
| Claude Code CLI | Latest | `npm install -g @anthropic-ai/claude-code` |
| Warp Terminal | Latest | https://warp.dev |

**Verify each one after installing:**

```powershell
node --version       # Must show v20.x or higher
npm --version
git --version
docker --version
python --version     # Must show 3.12.x or higher
claude --version
```

If any command fails, fix it before proceeding. Do not continue with missing tools.

**Docker Desktop must be running** (not just installed) before any docker commands.
Start it from the Start Menu and wait for the whale icon to appear in the taskbar.

---

## 2. ONE-TIME MACHINE SETUP

This step is run **once per machine**. If you are on a new machine or doing a fresh install, run this. If you have already run it on this machine, skip to Step 3.

```powershell
# Open PowerShell as Administrator
# Navigate to where you saved the NTM scripts
cd <folder where you put the NTM ps1 files>

# Unblock all scripts first — required on Windows
Unblock-File .\setup-generic-ntm.ps1
Unblock-File .\setup-project-ntm.ps1
Unblock-File .\ntm-sessions.ps1

# Run the generic machine bootstrap
.\setup-generic-ntm.ps1
```

**What this does:**
- Checks all prerequisites
- Installs cc-status-line (context % display in Claude Code)
- Installs global MCP servers: filesystem, memory, sequential-thinking
- Writes `~/.claude/CLAUDE.md` — global rules for all Claude Code sessions
- Writes `~/.claude/settings.json` — sets Sonnet as default, dark theme

**After it completes:**

Open Claude Code and type `/plugin`. Install each of these at **USER scope** (not project scope):

| Plugin | Purpose |
|---|---|
| `superpowers` | Sub-agent orchestration — brainstorm / plan / execute |
| `code-simplifier` | Refactor assistant |
| `context7` | Live API docs — prevents hallucinated method calls |
| `context-mode` | 98% context savings on large outputs |

Do not proceed until all 4 plugins are installed.

---

## 3. GITHUB REPOSITORY SETUP — YOUR RESPONSIBILITY

You (the developer assigned to NTM) must create the GitHub repository yourself.

**Follow these steps exactly:**

### Step 3.1 — Create the repository

1. Go to https://github.com and log in with your account
2. Click the **+** button (top right) → **New repository**
3. Repository name: `ntm`
4. Description: `Nexus Tensor Meridian — AI Agentic Marketing Operations Suite`
5. Visibility: **Private**
6. Do **NOT** initialise with README, .gitignore, or license — leave all checkboxes unchecked
7. Click **Create repository**
8. Copy the HTTPS URL from the next screen — it will look like:
   `https://github.com/<your-github-handle>/ntm.git`

### Step 3.2 — Open setup-project-ntm.ps1 and fill in the URL

Open `setup-project-ntm.ps1` in a text editor (VS Code or Notepad++).

Find this line near the top:

```powershell
$GIT_REPO_URL  = ""   # FILL IN: your GitHub repo HTTPS URL before running
```

Replace the empty string with your repo URL:

```powershell
$GIT_REPO_URL  = "https://github.com/<your-github-handle>/ntm.git"
```

Save the file. Do not change any other variable.

---

## 4. ADDING katharguppe AS CO-AUTHOR — MANDATORY

This is not optional. Srinivas (katharguppe) must have access to the repository.

### Step 4.1 — Add as repository collaborator

After the repository is created:

1. Go to your GitHub repo → **Settings** tab
2. Click **Collaborators** (left sidebar, under Access)
3. Click **Add people**
4. Search for: `katharguppe`
5. Select the account and click **Add katharguppe to this repository**
6. Grant role: **Maintain** (not just Write)
7. Click **Confirm**

GitHub will send an invitation. Do not wait for acceptance before continuing — the invite goes out immediately.

### Step 4.2 — Co-author line in every commit

Every single Git commit you make on this project must include the co-author line.
This is already wired into the PS1 scripts and CLAUDE.md. When making manual commits:

```bash
git commit -m "[TASK-XXX] verb: what changed

Co-authored-by: katharguppe <katharguppe@users.noreply.github.com>"
```

The blank line between the commit message and the Co-authored-by line is mandatory.
Git requires it. Without the blank line, GitHub will not recognise the co-authorship.

---

## 5. PROJECT SCAFFOLD

Now run the project bootstrap. This creates the full NTM directory structure,
all config files, CLAUDE.md, TOOLS.md, SKILLS.md, and the initial Git commit.

```powershell
# From the folder where you have the ps1 files
.\setup-project-ntm.ps1
```

**What this does:**
- Creates `D:\staging\ntm\` with the complete folder tree (40+ directories)
- Writes project-scoped `CLAUDE.md` with the full NTM agent roster and rules
- Writes `TOOLS.md`, `SKILLS.md`, and 4 Claude Code skills
- Creates `TASK-000-repo-init.md` with your initial checklist
- Writes `.mcp.json` scoped to the project root
- Initialises Git, makes the first commit (with co-author line), adds remote, pushes

**After it completes:**

Verify the push worked by visiting your GitHub repo — you should see the files there.
If the push failed (wrong URL, auth issue), fix it manually:

```powershell
cd D:\staging\ntm
git remote set-url origin https://github.com/<your-handle>/ntm.git
git push -u origin main
```

---

## 6. ENVIRONMENT CONFIGURATION

The `.env` file holds all API keys and connection strings. It is **never committed to Git**.

```powershell
cd D:\staging\ntm
copy .env.example .env
```

Open `.env` in a text editor and fill in every value.

**Minimum required to start the dev stack (Phase 0):**

```
ANTHROPIC_API_KEY       — Get from https://console.anthropic.com
DATABASE_URL            — Leave as default (postgresql+asyncpg://ntm_user:ntm_pass@localhost:5432/ntm_db)
MONGODB_URL             — Leave as default (mongodb://localhost:27017/ntm)
REDIS_URL               — Leave as default (redis://localhost:6379/0)
JWT_SECRET_KEY          — Generate: python -c "import secrets; print(secrets.token_hex(32))"
```

**For Phase 1+ (agents need these):**

```
SERPAPI_KEY             — Get from https://serpapi.com (free tier available)
```

**For Phase 3+ (creative generation):**

```
ELEVENLABS_API_KEY      — Get from https://elevenlabs.io
STABILITY_AI_API_KEY    — Get from https://stability.ai
RUNWAY_API_KEY          — Get from https://runwayml.com
```

**For Phase 4+ (digital activation):**

```
GOOGLE_ADS_DEVELOPER_TOKEN
GOOGLE_ADS_CLIENT_ID / CLIENT_SECRET / REFRESH_TOKEN
META_APP_ID / APP_SECRET / META_SYSTEM_USER_TOKEN
LINKEDIN_CLIENT_ID / CLIENT_SECRET
```

**Rules for .env:**
- Never paste .env contents into Claude Code chat
- Never commit .env to Git (it is in .gitignore — verify this)
- Never share .env over Slack or email — use a secrets manager or encrypted channel
- If you accidentally commit .env, tell Srinivas immediately

---

## 7. STARTING THE DEV STACK

Once `.env` is filled in and Docker Desktop is running:

```powershell
cd D:\staging\ntm

# Start all 8 services (postgres, mongo, redis, minio, api, worker, beat, flower, frontend)
docker-compose up -d

# Wait 30 seconds for services to become healthy, then run migrations
docker-compose exec ntm-api alembic upgrade head

# Verify the API is running
curl http://localhost:8000/health
# Expected: {"status": "ok", "service": "ntm-api", "version": "1.0.0"}
```

**Service URLs:**

| Service | URL | Notes |
|---|---|---|
| API (Swagger docs) | http://localhost:8000/docs | Full API documentation, try endpoints |
| React Frontend | http://localhost:3000 | Main client UI |
| Celery Flower | http://localhost:5555 | Task queue monitor |
| MinIO Console | http://localhost:9001 | S3-compatible object storage (admin/admin) |
| PostgreSQL | localhost:5432 | Connect with any DB client (ntm_user / ntm_pass / ntm_db) |

**To watch logs:**

```powershell
docker-compose logs -f ntm-api            # API server logs
docker-compose logs -f ntm-agent-worker   # Agent task execution logs
docker-compose logs -f ntm-beat           # Scheduled task logs
```

**To stop:**

```powershell
docker-compose down          # Stop containers, keep data volumes
docker-compose down -v       # Stop + wipe all data (use only for clean reset)
```

---

## 8. RUNNING YOUR FIRST SESSION IN CLAUDE CODE

Every development session follows this exact sequence. Do not open Claude Code without doing this.

### Step 8.1 — Pick your session

```powershell
cd D:\staging\ntm
.\scripts\ntm-sessions.ps1 -Session list
```

This shows all available sessions with their model and label.
For Phase 0, start with `core`.

### Step 8.2 — Launch the session

```powershell
.\scripts\ntm-sessions.ps1 -Session core
```

This will:
1. Print the session context prompt
2. Copy it to your clipboard automatically
3. Open Claude Code in the project root with the correct model set

### Step 8.3 — Inside Claude Code

1. Paste the clipboard content (Ctrl+V) — this is your session context
2. Type: `superpowers brainstorm`
3. Work through the brainstorm output. Approve the plan before any code is written.
4. When plan is approved, type: `superpowers execute plan`

### Step 8.4 — Context limit discipline

Watch cc-status-line at the top of Claude Code at all times.

- Below 50%: continue working normally
- At 50%: finish the current unit of work (complete the function, not the file)
- After finishing the unit: `/clear` — start a fresh session for the next unit
- **NEVER use `/compact`** — it corrupts the context without clearing it

---

## 9. PER-SESSION DISCIPLINE — READ EVERY DAY

These rules apply to every session, every day, without exception.

**Before opening Claude Code:**
- [ ] Check the last checkpoint file in `.checkpoints/`
- [ ] Read the relevant TASK-XXX.md file to know where you left off
- [ ] Confirm Docker stack is running (`curl http://localhost:8000/health`)

**During the session:**
- [ ] One session = one module = one file scope (as defined in CLAUDE.md)
- [ ] Present plan to Claude before any file is touched — wait for your own approval
- [ ] Use `context7` for any library or API call — never trust Claude's memory of docs
- [ ] Use `filesystem MCP` to read full files — never paste entire files into chat
- [ ] Use `memory MCP` to store decisions: schema choices, open questions, gotchas

**Before closing Claude Code:**
- [ ] Run tests: `docker-compose exec ntm-api pytest tests/ -v`
- [ ] All tests passing: commit with co-author line
- [ ] Write or update the checkpoint file: `.checkpoints/ckXX-<phase>.md`
- [ ] Note the exact starting point for the next session in the checkpoint

**Model selection:**

| What you are building | Use |
|---|---|
| Config, env, CRUD routes, JSON schemas, Docker config | Haiku |
| Agent logic, API integrations, LLM calls, complex services | Sonnet |
| Architecture decisions that failed twice on Sonnet | Opus (last resort only) |

---

## 10. CLAUDE COWORK + MARKETING PLUGIN SETUP

The Marketing Plugin runs in **Claude Cowork** (the desktop app) — separate from Claude Code.
It is used to generate golden benchmark datasets and validate agent outputs.

### Step 10.1 — Install Claude Cowork

Download from: https://claude.com/product/cowork
Install and sign in with your Anthropic account.

### Step 10.2 — Install the Marketing Plugin

1. Open Claude Cowork
2. Go to Plugins (sidebar or settings)
3. Install: **Marketing** (Anthropic Verified) — https://claude.com/plugins/marketing
4. Load the SherpaVector brand guidelines into Cowork's local settings
   (this enables `/brand-review` to work against the correct brand standard)

### Step 10.3 — Generating Golden Datasets (Evals intern — do this in Phase 1)

For the 3 internal test clients:
1. Open Claude Cowork → Marketing Plugin
2. Type: `/campaign-plan` — follow the prompts, enter the test mandate details
3. Save the output to: `docs/golden/mandate_[n]_concept.json`
4. Repeat `/competitive-brief` for each test client
5. Save to: `docs/golden/mandate_[n]_ci_report.json`

These files become the benchmark for evaluating AGT-02 and AGT-03.

### Step 10.4 — Validating Agent Output

When an agent completes its build, the eval intern uses the Plugin to cross-check:
- Run the same mandate through `/campaign-plan` in Cowork
- Compare against AGT-03's output
- If Plugin output is noticeably stronger: identify the gap and refine AGT-03's system prompt
- Document the comparison in `docs/plans/agent-eval-agt03-<date>.md`

---

## 11. GIT WORKFLOW

### Branch strategy

```
main         — protected, production-ready only, never commit directly
dev          — integration branch, all features merge here first
feature/TASK-XXX  — your working branch per task
```

### Starting a new task

```powershell
cd D:\staging\ntm
git checkout dev
git pull origin dev
git checkout -b feature/TASK-XXX
```

### Committing

Every commit must have the co-author line. Two formats:

**Short commit (single line work):**
```bash
git commit -m "[TASK-XXX] add: mandate analyst agent base structure

Co-authored-by: katharguppe <katharguppe@users.noreply.github.com>"
```

**Multi-line commit:**
```bash
git commit -m "[TASK-XXX] feat: implement AGT-01 mandate analyst with completeness scoring

- Parse all mandate fields into MandateSummaryCard JSON
- Compute completeness_score 0-100
- Flag missing_fields list
- Tests: 3 passing (happy path, missing fields, contradiction detection)

Co-authored-by: katharguppe <katharguppe@users.noreply.github.com>"
```

### Always show diff before committing

```powershell
git diff --staged   # Review what is about to be committed
git commit ...      # Only after reviewing the diff
```

### Pull request

When your feature branch is complete and tests pass:
1. Push: `git push origin feature/TASK-XXX`
2. Open a Pull Request on GitHub: `feature/TASK-XXX` → `dev`
3. Title format: `[TASK-XXX] brief description`
4. Add Srinivas (katharguppe) as reviewer
5. Do not merge your own PR

---

## 12. TROUBLESHOOTING

**Docker containers not starting:**
```powershell
docker-compose down -v        # Wipe volumes
docker-compose up -d          # Fresh start
docker-compose logs ntm-postgres   # Check for DB errors
```

**`alembic upgrade head` fails:**
```powershell
# Check the migration file for syntax errors
# Common issue: pgvector extension not enabled
# Fix: add to first migration:
# op.execute("CREATE EXTENSION IF NOT EXISTS vector")
docker-compose exec ntm-api alembic downgrade base
docker-compose exec ntm-api alembic upgrade head
```

**Agent returns non-JSON output:**
- The agent's SYSTEM_PROMPT must contain: "Respond only with valid JSON. No markdown code fences. No preamble."
- Wrap `json.loads()` in try/except and retry with a clarification prompt

**404 on any API endpoint:**
- Almost always a missing `tenant_id` filter in the query
- Check the service function — add `.filter(Model.tenant_id == tenant_id)` to every query

**Claude Code context fills too fast:**
- You are pasting too much into the chat
- Use `filesystem MCP` to read files instead of pasting them
- Activate `context-mode` plugin for large outputs

**Push to GitHub fails (auth error):**
```powershell
# Configure credential helper
git config --global credential.helper wincred
# Then push again — Windows will prompt for GitHub credentials
git push origin main
```

**cc-status-line not showing:**
```powershell
npx cc-status-line@latest --install
# Restart Claude Code after installation
```

---

*Jai Jagannath*
*Document version: 1.0 | Project: NTM | Owner: Srinivas / SherpaVector*
*This document is the single source of truth for NTM setup. Do not deviate.*
