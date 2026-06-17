@echo off
set DATABASE_URL=postgresql+asyncpg://ntm_user:ntm_pass@localhost:5432/ntm_db
set NTM_STUB_EXTERNAL=1
set SECRET_KEY=dev-secret-key-for-local-testing-only-32chars
set ALGORITHM=HS256
set ACCESS_TOKEN_EXPIRE_MINUTES=30
cd /d F:\laxmikant\NTM
python -m uvicorn backend.app.main:app --reload --port 8000
