"""Lightweight wrapper for enqueueing extraction jobs from the API.

We deliberately use ``send_task("geshtu.extract_message", ...)`` by name
rather than importing the task function. Importing it would pull in
``geshtu.tasks`` → ``geshtu.embed`` → ``sentence_transformers`` → torch,
which adds ~600ms of import time and ~2GB of RSS to every API process for
no benefit (the API never embeds; the worker does).
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
