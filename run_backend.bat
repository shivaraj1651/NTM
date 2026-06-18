@echo off
echo Starting MongoDB...
docker start ntm-mongo 2>nul || docker run -d --name ntm-mongo -p 27017:27017 mongo:7
echo Waiting for MongoDB...
timeout /t 3 /nobreak >nul

set DATABASE_URL=postgresql+asyncpg://ntm_user:ntm_pass@localhost:5432/ntm_db
set NTM_STUB_EXTERNAL=1
set SECRET_KEY=dev-secret-key-for-local-testing-only-32chars
set ALGORITHM=HS256
set ACCESS_TOKEN_EXPIRE_MINUTES=30
cd /d F:\laxmikant\NTM
echo Starting backend...
python -m uvicorn backend.app.main:app --reload --port 8000
