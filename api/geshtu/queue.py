"""Lightweight wrapper for enqueueing extraction jobs from the API.

The API doesn't import Celery tasks directly (avoids loading torch/HF
on the API container at import time). Instead it uses send_task with
the well-known task name. The worker registers the actual task body.
"""

from __future__ import annotations

import uuid
from typing import Any

from celery import Celery

from geshtu.config import get_settings

_app: Celery | None = None


def get_celery() -> Celery:
    global _app
    if _app is not None:
        return _app
    s = get_settings()
    _app = Celery("geshtu", broker=s.redis_url, backend=s.redis_url)
    _app.conf.update(
        task_serializer="json",
        accept_content=["json"],
        result_serializer="json",
        timezone="UTC",
        enable_utc=True,
        task_acks_late=True,
        worker_prefetch_multiplier=1,
        broker_connection_retry_on_startup=True,
    )
    return _app


def enqueue_extraction(message_id: uuid.UUID, project_id: uuid.UUID) -> str:
    app = get_celery()
    res = app.send_task(
        "geshtu.extract_message",
        kwargs={"message_id": str(message_id), "project_id": str(project_id)},
        queue="extraction",
    )
    return res.id


def enqueue(name: str, **kwargs: Any) -> str:
    app = get_celery()
    return app.send_task(name, kwargs=kwargs).id
