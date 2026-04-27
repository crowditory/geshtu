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
    # acks_late + prefetch=1 makes one extraction = one task on the wire,
    # so a worker crash mid-extraction redelivers the job rather than losing it.
    task_acks_late=True,
    worker_prefetch_multiplier=1,
    task_default_queue="extraction",
    broker_connection_retry_on_startup=True,
    task_routes={
        "geshtu.extract_message": {"queue": "extraction"},
        "geshtu.summarize_session": {"queue": "extraction"},
        "geshtu.retention_sweep": {"queue": "maintenance"},
    },
)

# Retention is a maintenance task you trigger from cron or manually:
#
#     docker compose exec api python -c \
#       "from geshtu.tasks import retention_sweep_task; print(retention_sweep_task())"
#
# We intentionally do NOT start `celery beat` in compose: a beat process
# adds another moving part for a once-a-day job that's easier to manage with
# host cron or a scheduled GitHub Actions workflow.
