#!/bin/sh
set -e

# Run DB setup only for the API process (not celery worker / beat)
if [ "${1}" = "uvicorn" ]; then
    echo "Running Alembic migrations..."
    alembic upgrade head

    echo "Ensuring all tables exist (idempotent create_all)..."
    python -m backend.app.scripts.create_tables
fi

exec "$@"
