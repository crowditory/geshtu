"""Celery app for the worker container.

The worker imports geshtu.tasks to register tasks. Run with:

    celery -A geshtu.celery_app worker --loglevel=info --concurrency=2
"""

from __future__ import annotations

from celery import Celery

from geshtu.config import get_settings
from geshtu.logging import configure_logging

_settings = get_settings()
configure_logging(_settings.log_level)

app = Celery(
    "geshtu",
    broker=_settings.redis_url,
    backend=_settings.redis_url,
    include=["geshtu.tasks"],
)

app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_acks_late=True,
    worker_prefetch_multiplier=1,
    task_default_queue="extraction",
    broker_connection_retry_on_startup=True,
    task_routes={
        "geshtu.extract_message": {"queue": "extraction"},
        "geshtu.summarize_session": {"queue": "extraction"},
        "geshtu.retention_sweep": {"queue": "maintenance"},
    },
    beat_schedule={
        "retention-sweep-daily": {
            "task": "geshtu.retention_sweep",
            "schedule": 24 * 60 * 60.0,  # once a day
        },
    },
)
