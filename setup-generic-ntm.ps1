# ==============================================================================
# setup-generic-ntm.ps1
# One-time Claude Code machine bootstrap for NTM development.
# Safe PowerShell-compatible version.
# ==============================================================================

$ErrorActionPreference = "Stop"

Write-Host ""
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host " NEXUS TENSOR MERIDIAN - MACHINE BOOTSTRAP " -ForegroundColor Cyan
Write-Host " Run once per machine. Safe to re-run. " -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host ""

# ------------------------------------------------------------------------------
# 1. Prerequisites
# ------------------------------------------------------------------------------

Write-Host "[ 1/8 ] Checking prerequisites..." -ForegroundColor Yellow

$missing = @()

if (-not (Get-Command node -ErrorAction SilentlyContinue)) {
    $missing += "Node.js -> https://nodejs.org"
}

if (-not (Get-Command npm -ErrorAction SilentlyContinue)) {
    $missing += "npm -> comes with Node.js"
}

if (-not (Get-Command git -ErrorAction SilentlyContinue)) {
    $missing += "Git -> https://git-scm.com"
}

if (-not (Get-Command docker -ErrorAction SilentlyContinue)) {
    $missing += "Docker Desktop -> https://www.docker.com/products/docker-desktop"
}

if (-not (Get-Command python -ErrorAction SilentlyContinue)) {
    $missing += "Python -> https://www.python.org/downloads"
}

if ($missing.Count -gt 0) {
    Write-Host ""
    Write-Host "Missing prerequisites:" -ForegroundColor Red

    foreach ($m in $missing) {
        Write-Host " - $m" -ForegroundColor Red
    }

    exit 1
}

$nodeVer = (node --version)
$pythonVer = (python --version)

Write-Host "Node: $nodeVer" -ForegroundColor Green
Write-Host "Python: $pythonVer" -ForegroundColor Green

# ------------------------------------------------------------------------------
# 2. Install cc-status-line
# ------------------------------------------------------------------------------

Write-Host ""
Write-Host "[ 2/8 ] Installing cc-status-line..." -ForegroundColor Yellow

npx cc-status-line@latest --install

# ------------------------------------------------------------------------------
# 3. MCP Servers
# ------------------------------------------------------------------------------

Write-Host ""
Write-Host "[ 3/8 ] Installing MCP servers..." -ForegroundColor Yellow

$mcpPackages = @(
    "@modelcontextprotocol/server-filesystem",
    "@modelcontextprotocol/server-memory",
    "@modelcontextprotocol/server-sequential-thinking"
)

foreach ($pkg in $mcpPackages) {

    Write-Host "Installing $pkg"

    npm install -g $pkg
}

$claudeDir = "$env:USERPROFILE\.claude"

if (-not (Test-Path $claudeDir)) {
    New-Item -ItemType Directory -Path $claudeDir | Out-Null
}

$npmGlobalRoot = (npm root -g).Trim()

$mcpJson = @"
{
  "mcpServers": {
    "filesystem": {
      "command": "node",
      "args": [
        "$npmGlobalRoot\\@modelcontextprotocol\\server-filesystem\\dist\\index.js",
        "C:\\"
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

Set-Content "$claudeDir\.mcp.json" $mcpJson -Encoding UTF8

Write-Host "MCP config written." -ForegroundColor Green

# ------------------------------------------------------------------------------
# 4. CLAUDE.md
# ------------------------------------------------------------------------------

Write-Host ""
Write-Host "[ 4/8 ] Writing CLAUDE.md..." -ForegroundColor Yellow

$claudeMd = @"
# Global Rules

## Model Selection

- Haiku:
  - Boilerplate
  - CRUD
  - JSON
  - Config

- Sonnet:
  - APIs
  - Agents
  - LLM integrations
  - Debugging
  - Real implementation work

- Opus:
  - Hard architecture
  - Complex reasoning
  - Last resort only

Default model: Sonnet

## Context Rules

- Watch context percentage at all times
- Clear session around 50 percent
- Never compact context
- One session per module

## Workflow

1. Brainstorm
2. Write Plan
3. Execute Plan

## Tool Rules

- context7 -> API docs
- sequential-thinking -> architecture/debugging
- filesystem MCP -> file access
- memory MCP -> persistent decisions

## Git Rules

- Never commit to main
- Use feature branches
- Show diff before commit

## NTM Rules

- One agent per file
- One tool per integration
- Every agent needs tests
- All DB queries must include tenant_id
"@

Set-Content "$claudeDir\CLAUDE.md" $claudeMd -Encoding UTF8

Write-Host "CLAUDE.md written." -ForegroundColor Green

# ------------------------------------------------------------------------------
# 5. settings.json
# ------------------------------------------------------------------------------

Write-Host ""
Write-Host "[ 5/8 ] Writing settings.json..." -ForegroundColor Yellow

$settingsJson = @"
{
  "defaultModel": "claude-sonnet-4-6",
  "autoApprove": false,
  "theme": "dark",
  "statusLine": {
    "line1": "model|context_pct|session_cost|session_clock",
    "line2": "git_branch|git_worktree"
  }
}
"@

Set-Content "$claudeDir\settings.json" $settingsJson -Encoding UTF8

Write-Host "settings.json written." -ForegroundColor Green

# ------------------------------------------------------------------------------
# 6. Docker
# ------------------------------------------------------------------------------

Write-Host ""
Write-Host "[ 6/8 ] Checking Docker..." -ForegroundColor Yellow

docker info | Out-Null

if ($LASTEXITCODE -eq 0) {
    Write-Host "Docker is running." -ForegroundColor Green
}
else {
    Write-Host "Docker Desktop is not running." -ForegroundColor Yellow
}

# ------------------------------------------------------------------------------
# 7. Python
# ------------------------------------------------------------------------------

Write-Host ""
Write-Host "[ 7/8 ] Checking pip..." -ForegroundColor Yellow

pip --version

# ------------------------------------------------------------------------------
# 8. Manual Plugins
# ------------------------------------------------------------------------------

Write-Host ""
Write-Host "[ 8/8 ] Manual Claude plugins:" -ForegroundColor Yellow
Write-Host ""

Write-Host "Install these plugins inside Claude Code:" -ForegroundColor Cyan
Write-Host " - superpowers"
Write-Host " - code-simplifier"
Write-Host " - context7"
Write-Host " - context-mode"

Write-Host ""
Write-Host "Bootstrap complete." -ForegroundColor Green
Write-Host ""