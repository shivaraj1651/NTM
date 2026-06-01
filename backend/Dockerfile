FROM python:3.12-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends curl \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip
RUN pip install --no-cache-dir --timeout 120 "celery[redis]==5.6.3" "kombu==5.6.2"
RUN pip install --no-cache-dir --timeout 120 -r requirements.txt

COPY backend/ backend/
COPY alembic/ alembic/
COPY alembic.ini .
COPY pyproject.toml .

ENV PYTHONPATH=/app

COPY docker-entrypoint.sh /docker-entrypoint.sh
RUN chmod +x /docker-entrypoint.sh

EXPOSE 8000

ENTRYPOINT ["/docker-entrypoint.sh"]
CMD ["uvicorn", "backend.app.main:app", "--host", "0.0.0.0", "--port", "8000"]
