"""Helpers shared by route modules."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from geshtu.auth import AuthedUser
from geshtu.db.models import AccessLog, Project


def resolve_project(db: Session, project: str, user: AuthedUser | None = None) -> Project:
    """Resolve a slug or UUID to a Project, enforcing token scope.

    If ``user`` is provided and their token is project-scoped, the resolved
    project must match the token's scope — otherwise 403. This is the single
    chokepoint: every route that takes a `project` arg routes through here,
    so the scope check applies everywhere automatically.
    """
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

    if user is not None and user.token_project_id is not None and proj.id != user.token_project_id:
        # Project-scoped token used against a different project. Don't leak
        # which projects exist — same 403 either way.
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="this token is scoped to a different project",
        )

    return proj


def assert_project_in_scope(project_id: uuid.UUID, user: AuthedUser) -> None:
    """For routes that receive a session_id / message_id and look up the
    project indirectly: enforce token scope on the resolved project_id."""
    if user.token_project_id is not None and project_id != user.token_project_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="this token is scoped to a different project",
        )


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
