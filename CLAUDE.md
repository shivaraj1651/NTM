# CLAUDE.md

## Stack
Python 3.12, FastAPI, PostgreSQL 16 (pgvector), MongoDB 7, Redis 7, React 18, TypeScript, Tailwind CSS, LangGraph, CrewAI, Celery, Docker, AWS ECS

## Current Phase
0

## Module Boundaries
Session -> core : backend/app/core ONLY
Session -> models : backend/app/models ONLY
Session -> schemas : backend/app/schemas ONLY
Session -> routers : backend/app/routers ONLY
Session -> services : backend/app/services ONLY
Session -> agents : backend/app/agents ONLY
Session -> tools : backend/app/tools ONLY
Session -> tasks : backend/app/tasks ONLY

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

Co-authored-by: katharguppe <katharguppe@users.noreply.github.com>
