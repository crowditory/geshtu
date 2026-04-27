"""Sessions: a thread of messages tied to a project + user."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from geshtu.auth import AuthedUser, current_user
from geshtu.db.models import Session_, SessionSummary
from geshtu.db.session import get_db
from geshtu.digest import summarize_session
from geshtu.routes.common import resolve_project

router = APIRouter(prefix="/sessions", tags=["sessions"])


class SessionIn(BaseModel):
    project: str = Field(..., description="project slug or UUID")
    title: str | None = None
    llm_model: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class SessionOut(BaseModel):
    id: uuid.UUID
    project_id: uuid.UUID
    user_id: uuid.UUID | None
    title: str | None
    llm_model: str | None
    started_at: datetime
    ended_at: datetime | None


class CloseSessionIn(BaseModel):
    summary_md: str | None = None
    open_questions: list[str] = Field(default_factory=list)
    next_actions: list[str] = Field(default_factory=list)
    auto_summarize: bool = False


class CloseSessionOut(BaseModel):
    id: uuid.UUID
    summary_id: uuid.UUID
    summary_md: str


def _to_out(s: Session_) -> SessionOut:
    return SessionOut(
        id=s.id,
        project_id=s.project_id,
        user_id=s.user_id,
        title=s.title,
        llm_model=s.llm_model,
        started_at=s.started_at,
        ended_at=s.ended_at,
    )


@router.post("", response_model=SessionOut, status_code=status.HTTP_201_CREATED)
def create_session(
    body: SessionIn,
    user: AuthedUser = Depends(current_user),
    db: Session = Depends(get_db),
) -> SessionOut:
    project = resolve_project(db, body.project)
    s = Session_(
        project_id=project.id,
        user_id=user.id,
        title=body.title,
        llm_model=body.llm_model,
        session_metadata=body.metadata,
    )
    db.add(s)
    db.commit()
    db.refresh(s)
    return _to_out(s)


@router.get("/{session_id}", response_model=SessionOut)
def get_session(
    session_id: uuid.UUID,
    _user: AuthedUser = Depends(current_user),
    db: Session = Depends(get_db),
) -> SessionOut:
    s = db.get(Session_, session_id)
    if s is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="session not found")
    return _to_out(s)


@router.post("/{session_id}/close", response_model=CloseSessionOut)
def close_session(
    session_id: uuid.UUID,
    body: CloseSessionIn,
    user: AuthedUser = Depends(current_user),
    db: Session = Depends(get_db),
) -> CloseSessionOut:
    s = db.get(Session_, session_id)
    if s is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="session not found")

    summary_md = body.summary_md
    if not summary_md and body.auto_summarize:
        # Synchronous Sonnet call: 5–30 seconds. The MCP `close_session`
        # tool is invoked at the END of a conversation, where a one-time
        # blocking wait is acceptable. If this becomes a UX problem in
        # practice, route to `summarize_session_task` and return a job id.
        summary_md = summarize_session(db, session_id)
    if not summary_md:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="summary_md is required (or set auto_summarize=true)",
        )

    existing = db.execute(
        select(SessionSummary).where(SessionSummary.session_id == session_id)
    ).scalar_one_or_none()

    if existing is None:
        ss = SessionSummary(
            session_id=session_id,
            summary_md=summary_md,
            open_questions=body.open_questions,
            next_actions=body.next_actions,
        )
        db.add(ss)
    else:
        existing.summary_md = summary_md
        existing.open_questions = body.open_questions
        existing.next_actions = body.next_actions
        ss = existing

    s.ended_at = datetime.now(tz=timezone.utc)
    db.commit()
    db.refresh(ss)
    _ = user  # logged via access_log below if needed
    return CloseSessionOut(id=session_id, summary_id=ss.id, summary_md=ss.summary_md)
