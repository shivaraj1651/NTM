@echo off
set DATABASE_URL=postgresql+asyncpg://ntm_user:ntm_pass@localhost:5432/ntm_db
set NTM_STUB_EXTERNAL=1
set SECRET_KEY=dev-secret-key-for-local-testing-only-32chars
set REDIS_URL=redis://localhost:6379/0
set CELERY_BROKER_URL=redis://localhost:6379/0
set CELERY_RESULT_BACKEND=redis://localhost:6379/1
set MONGODB_URL=mongodb://localhost:27017/ntm
cd /d F:\laxmikant\NTM
echo Starting Celery worker (stub mode)...
python -m celery -A backend.app.celery_app worker --loglevel=info --pool=solo
