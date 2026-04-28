"""Append messages to a session and enqueue extraction."""

from __future__ import annotations

import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from geshtu.auth import AuthedUser, current_user
from geshtu.db.models import Message, Session_
from geshtu.db.session import get_db
from geshtu.queue import enqueue_extraction
from geshtu.routes.common import assert_project_in_scope, log_access

router = APIRouter(prefix="/messages", tags=["messages"])


class MessageIn(BaseModel):
    session_id: uuid.UUID
    role: str = Field(..., pattern="^(user|assistant|system|tool)$")
    content: str
    token_count: int | None = None
    extract: bool = True


class MessageOut(BaseModel):
    id: uuid.UUID
    session_id: uuid.UUID
    role: str
    content: str
    token_count: int | None
    created_at: datetime
    extraction_job_id: str | None = None


@router.post("", response_model=MessageOut, status_code=status.HTTP_201_CREATED)
def append_message(
    body: MessageIn,
    user: AuthedUser = Depends(current_user),
    db: Session = Depends(get_db),
) -> MessageOut:
    sess = db.get(Session_, body.session_id)
    if sess is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="session not found")
    assert_project_in_scope(sess.project_id, user)

    msg = Message(
        session_id=body.session_id,
        role=body.role,
        content=body.content,
        token_count=body.token_count,
    )
    db.add(msg)

    log_access(
        db,
        user_id=user.id,
        operation="message.append",
        project_id=sess.project_id,
        payload={"session_id": str(body.session_id), "role": body.role},
    )
    db.commit()
    db.refresh(msg)

    # Spec §5.1 invariant: the message is committed BEFORE we touch Redis.
    # Two consequences:
    #   1) The user gets a 200 even if extraction fails or is delayed.
    #   2) If Redis is down here, we still keep the raw log; the message can
    #      be re-enqueued later (it's already in `messages`).
    # We skip extraction on `system` / `tool` messages: they're framing or
    # tool output, not statements the team is making about the world.
    job_id: str | None = None
    if body.extract and body.role in ("user", "assistant"):
        try:
            job_id = enqueue_extraction(message_id=msg.id, project_id=sess.project_id)
        except Exception:  # noqa: BLE001
            job_id = None

    return MessageOut(
        id=msg.id,
        session_id=msg.session_id,
        role=msg.role,
        content=msg.content,
        token_count=msg.token_count,
        created_at=msg.created_at,
        extraction_job_id=job_id,
    )
