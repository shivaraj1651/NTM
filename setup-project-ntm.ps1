# ==============================================================================
# setup-project-ntm.ps1
# NTM - Nexus Tensor Meridian project bootstrap.
# Safe Windows PowerShell compatible version.
# ==============================================================================

$ErrorActionPreference = "Stop"

# ------------------------------------------------------------------------------
# VARIABLES
# ------------------------------------------------------------------------------

$PROJECT_NAME  = "ntm"
$PROJECT_ROOT  = "D:\staging\ntm"

$STACK = "Python 3.12, FastAPI, PostgreSQL 16 (pgvector), MongoDB 7, Redis 7, React 18, TypeScript, Tailwind CSS, LangGraph, CrewAI, Celery, Docker, AWS ECS"

$PHASE_CURRENT = 0

$MODULES = @(
    "core",
    "models",
    "schemas",
    "routers",
    "services",
    "agents",
    "tools",
    "tasks"
)

$GIT_REPO_URL = "https://github.com/Lakshmikanth-27/ntm.git"

$COAUTHOR = "Co-authored-by: katharguppe <katharguppe@users.noreply.github.com>"

# ------------------------------------------------------------------------------
# HEADER
# ------------------------------------------------------------------------------

Write-Host ""
Write-Host "==============================================================" -ForegroundColor Cyan
Write-Host " NEXUS TENSOR MERIDIAN - PROJECT BOOTSTRAP " -ForegroundColor Cyan
Write-Host " Jai Jagannath " -ForegroundColor Yellow
Write-Host "==============================================================" -ForegroundColor Cyan
Write-Host ""

# ------------------------------------------------------------------------------
# VALIDATE REPO URL
# ------------------------------------------------------------------------------

if ($GIT_REPO_URL -eq "") {
    Write-Host "ERROR: GIT_REPO_URL is empty." -ForegroundColor Red
    exit 1
}

# ------------------------------------------------------------------------------
# CREATE PROJECT ROOT
# ------------------------------------------------------------------------------

Write-Host "[1/8] Creating project root..." -ForegroundColor Yellow

if (-not (Test-Path $PROJECT_ROOT)) {

    New-Item -ItemType Directory -Path $PROJECT_ROOT | Out-Null

    Write-Host "[OK] Created: $PROJECT_ROOT" -ForegroundColor Green
}
else {

    Write-Host "[OK] Exists: $PROJECT_ROOT" -ForegroundColor DarkGray
}

Set-Location $PROJECT_ROOT

# ------------------------------------------------------------------------------
# CREATE FOLDER STRUCTURE
# ------------------------------------------------------------------------------

Write-Host ""
Write-Host "[2/8] Creating folder structure..." -ForegroundColor Yellow

$folders = @(
    "tasks",
    "docs",
    "docs\plans",
    "docs\golden",
    ".checkpoints",
    ".claude",
    ".claude\skills",

    "backend",
    "backend\app",
    "backend\app\core",
    "backend\app\models",
    "backend\app\schemas",
    "backend\app\routers",
    "backend\app\services",
    "backend\app\agents",
    "backend\app\tools",
    "backend\app\tasks",
    "backend\app\utils",
    "backend\alembic",
    "backend\alembic\versions",

    "backend\tests",
    "backend\tests\agents",
    "backend\tests\routers",
    "backend\tests\services",
    "backend\tests\golden",

    "frontend",
    "frontend\src",
    "frontend\src\pages",
    "frontend\src\components",
    "frontend\src\api",
    "frontend\src\store",
    "frontend\src\types",
    "frontend\public",

    "infra",
    "infra\terraform",
    "infra\github-actions",

    "scripts"
)

foreach ($folder in $folders) {

    $path = Join-Path $PROJECT_ROOT $folder

    if (-not (Test-Path $path)) {

        New-Item -ItemType Directory -Path $path | Out-Null

        Write-Host "[OK] $folder" -ForegroundColor Green
    }
    else {

        Write-Host "[OK] Exists: $folder" -ForegroundColor DarkGray
    }
}

# ------------------------------------------------------------------------------
# CLAUDE.MD
# ------------------------------------------------------------------------------

Write-Host ""
Write-Host "[3/8] Writing CLAUDE.md..." -ForegroundColor Yellow

$moduleMap = ($MODULES | ForEach-Object {
    "Session -> $_ : backend/app/$_ ONLY"
}) -join "`n"

$claudeContent = @"
# CLAUDE.md

## Stack
$STACK

## Current Phase
$PHASE_CURRENT

## Module Boundaries
$moduleMap

Session -> frontend : frontend/src/pages ONLY
Session -> debug : one error and one file per session

## Agent Rules

- One session per module
- Use context7 for APIs
- Use filesystem MCP for reading files
- Use memory MCP for decisions
- Every DB query must include tenant_id

## Model Selection

Haiku:
- Boilerplate
- CRUD
- Config

Sonnet:
- APIs
- Agents
- Debugging

Opus:
- Hard architecture only

## Git

Branch format:
feature/TASK-XXX

Commit format:
[TASK-XXX] action: description

$COAUTHOR
"@

Set-Content "$PROJECT_ROOT\CLAUDE.md" $claudeContent -Encoding UTF8

Write-Host "[OK] CLAUDE.md written." -ForegroundColor Green

# ------------------------------------------------------------------------------
# TOOLS.MD
# ------------------------------------------------------------------------------

Write-Host ""
Write-Host "[4/8] Writing TOOLS.md..." -ForegroundColor Yellow

$toolsContent = @"
# TOOLS.md

## Claude Plugins

- superpowers
- context7
- code-simplifier
- context-mode

## MCP Servers

- filesystem
- memory
- sequential-thinking

## Docker

docker-compose up -d
docker-compose logs -f

## Tests

pytest
alembic upgrade head
"@

Set-Content "$PROJECT_ROOT\TOOLS.md" $toolsContent -Encoding UTF8

Write-Host "[OK] TOOLS.md written." -ForegroundColor Green

# ------------------------------------------------------------------------------
# SKILLS
# ------------------------------------------------------------------------------

Write-Host ""
Write-Host "[5/8] Writing skills..." -ForegroundColor Yellow

$skillsContent = @"
# SKILLS.md

- task-create
- agent-stub
- tool-stub
- audit-module
"@

Set-Content "$PROJECT_ROOT\SKILLS.md" $skillsContent -Encoding UTF8

Set-Content "$PROJECT_ROOT\.claude\skills\task-create.md" "Task create skill" -Encoding UTF8
Set-Content "$PROJECT_ROOT\.claude\skills\agent-stub.md" "Agent stub skill" -Encoding UTF8
Set-Content "$PROJECT_ROOT\.claude\skills\tool-stub.md" "Tool stub skill" -Encoding UTF8
Set-Content "$PROJECT_ROOT\.claude\skills\audit-module.md" "Audit module skill" -Encoding UTF8

Write-Host "[OK] Skills written." -ForegroundColor Green

# ------------------------------------------------------------------------------
# TASK FILE
# ------------------------------------------------------------------------------

Write-Host ""
Write-Host "[6/8] Creating TASK-000..." -ForegroundColor Yellow

$taskContent = @"
# TASK-000

## Objective

Initial project setup.

## Checklist

- Setup scripts completed
- Git repo connected
- Docker working
- Claude configured
"@

Set-Content "$PROJECT_ROOT\tasks\TASK-000-repo-init.md" $taskContent -Encoding UTF8

Write-Host "[OK] TASK-000 written." -ForegroundColor Green

# ------------------------------------------------------------------------------
# MCP CONFIG
# ------------------------------------------------------------------------------

Write-Host ""
Write-Host "[7/8] Writing .mcp.json..." -ForegroundColor Yellow

$npmGlobalRoot = (npm root -g).Trim()

$mcpContent = @"
{
  "mcpServers": {
    "filesystem": {
      "command": "node",
      "args": [
        "$npmGlobalRoot\\@modelcontextprotocol\\server-filesystem\\dist\\index.js",
        "$PROJECT_ROOT"
      ]
    },
    "memory": {
      "command": "node",
      "args": [
        "$npmGlobalRoot\\@modelcontextprotocol\\server-memory\\dist\\index.js"
      ]
    },
    "sequential-thinking": {
      "command": "node",
      "args": [
        "$npmGlobalRoot\\@modelcontextprotocol\\server-sequential-thinking\\dist\\index.js"
      ]
    }
  }
}
"@

Set-Content "$PROJECT_ROOT\.mcp.json" $mcpContent -Encoding UTF8

Write-Host "[OK] .mcp.json written." -ForegroundColor Green

# ------------------------------------------------------------------------------
# GIT
# ------------------------------------------------------------------------------

Write-Host ""
Write-Host "[8/8] Initialising Git..." -ForegroundColor Yellow

if (-not (Test-Path "$PROJECT_ROOT\.git")) {

    git init $PROJECT_ROOT

    Write-Host "[OK] git init" -ForegroundColor Green
}
else {

    Write-Host "[OK] Git already initialised." -ForegroundColor DarkGray
}

Set-Location $PROJECT_ROOT

$gitignore = @"
.env
node_modules/
__pycache__/
dist/
build/
.vscode/
.idea/
*.log
"@

Set-Content "$PROJECT_ROOT\.gitignore" $gitignore -Encoding UTF8

git add .

$commitMessage = @"
[TASK-000] init: NTM scaffold

$COAUTHOR
"@

git commit -m $commitMessage

$existingRemote = git remote

if ($existingRemote -notcontains "origin") {

    git remote add origin $GIT_REPO_URL

    Write-Host "[OK] Remote added." -ForegroundColor Green
}

Write-Host ""
Write-Host "Pushing to GitHub..." -ForegroundColor Yellow

git push -u origin main

if ($LASTEXITCODE -ne 0) {

    git push -u origin master
}

Write-Host ""
Write-Host "==============================================================" -ForegroundColor Green
Write-Host "[OK] NTM PROJECT BOOTSTRAP COMPLETE" -ForegroundColor Green
Write-Host "==============================================================" -ForegroundColor Green
Write-Host ""

Write-Host "Next Steps:" -ForegroundColor Cyan
Write-Host "1. Add katharguppe as collaborator"
Write-Host "2. Create .env"
Write-Host "3. docker-compose up -d"
Write-Host "4. Open Claude Code"
Write-Host ""