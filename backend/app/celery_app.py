"""Celery application instance and configuration for NTM.

Configures Celery for async task execution with proper worker pool,
serialization, and result backend handling.
"""

import os
from celery import Celery
from kombu import Exchange, Queue

# Initialize Celery app
celery_app = Celery(__name__)

# Configuration
CELERY_BROKER_URL = os.getenv("CELERY_BROKER_URL", "redis://localhost:6379/0")
CELERY_RESULT_BACKEND = os.getenv("CELERY_RESULT_BACKEND", "redis://localhost:6379/1")
CELERY_TASK_SERIALIZER = "json"
CELERY_RESULT_SERIALIZER = "json"
CELERY_ACCEPT_CONTENT = ["json"]
CELERY_TIMEZONE = "UTC"
CELERY_ENABLE_UTC = True
CELERY_TASK_TRACK_STARTED = True
CELERY_TASK_TIME_LIMIT = 30 * 60  # 30 minutes hard limit

# Configure Celery
celery_app.conf.update(
    broker_url=CELERY_BROKER_URL,
    result_backend=CELERY_RESULT_BACKEND,
    task_serializer=CELERY_TASK_SERIALIZER,
    result_serializer=CELERY_RESULT_SERIALIZER,
    accept_content=[CELERY_ACCEPT_CONTENT],
    timezone=CELERY_TIMEZONE,
    enable_utc=CELERY_ENABLE_UTC,
    task_track_started=CELERY_TASK_TRACK_STARTED,
    task_time_limit=CELERY_TASK_TIME_LIMIT,
    # Task routing and queues
    task_default_queue="default",
    task_default_exchange="tasks",
    task_default_routing_key="default",
    task_queues=(
        Queue("default", Exchange("tasks"), routing_key="default"),
        Queue("activation", Exchange("activation"), routing_key="activation.*"),
    ),
    task_routes={
        "activation_tasks.*": {"queue": "activation", "routing_key": "activation.tasks"},
    },
)


def configure_celery(app):
    """Configure Celery from FastAPI app instance.

    This allows Celery tasks to access the FastAPI app context if needed.

    Args:
        app: FastAPI application instance
    """
    class ContextTask(celery_app.Task):
        """Make celery tasks work with FastAPI app."""
        def __call__(self, *args, **kwargs):
            return self.run(*args, **kwargs)

    celery_app.Task = ContextTask
