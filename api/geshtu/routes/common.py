"""Helpers shared by route modules."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from geshtu.db.models import AccessLog, Project


def resolve_project(db: Session, project: str) -> Project:
    """Accept either a slug or a UUID; return the Project row or 404."""
    proj: Project | None = None
    try:
        pid = uuid.UUID(project)
    except (ValueError, TypeError):
        pid = None

    if pid is not None:
        proj = db.execute(select(Project).where(Project.id == pid)).scalar_one_or_none()
    if proj is None:
        proj = db.execute(select(Project).where(Project.slug == project)).scalar_one_or_none()
    if proj is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"unknown project: {project}")
    return proj


def log_access(
    db: Session,
    user_id: uuid.UUID | None,
    operation: str,
    project_id: uuid.UUID | None,
    payload: dict[str, Any] | None = None,
) -> None:
    db.add(
        AccessLog(
            user_id=user_id,
            operation=operation,
            project_id=project_id,
            payload=payload,
        )
    )


def parse_since(since: str | None) -> datetime | None:
    if not since:
        return None
    try:
        # Accept "2026-04-01" or full ISO.
        if "T" in since:
            return datetime.fromisoformat(since.replace("Z", "+00:00"))
        return datetime.fromisoformat(since + "T00:00:00+00:00")
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"could not parse 'since': {exc}",
        ) from exc
