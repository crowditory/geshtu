"""List + log decisions."""

from __future__ import annotations

import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from geshtu.auth import AuthedUser, current_user
from geshtu.db.models import Decision
from geshtu.db.session import get_db
from geshtu.embed import embed
from geshtu.logging import get_logger
from geshtu.routes.common import log_access, parse_since, resolve_project

router = APIRouter(prefix="/decisions", tags=["decisions"])
_log = get_logger(__name__)


class DecisionOut(BaseModel):
    id: uuid.UUID
    project_id: uuid.UUID
    decision: str
    rationale: str
    decided_at: datetime
    decided_by: uuid.UUID | None
    status: str


class LogDecisionIn(BaseModel):
    project: str
    decision: str = Field(..., min_length=3)
    rationale: str = Field(..., min_length=3)
    source_session_id: uuid.UUID | None = None
    source_message_id: uuid.UUID | None = None


@router.get("", response_model=list[DecisionOut])
def list_decisions(
    project: str = Query(...),
    limit: int = Query(10, ge=1, le=200),
    since: str | None = Query(None),
    user: AuthedUser = Depends(current_user),
    db: Session = Depends(get_db),
) -> list[DecisionOut]:
    proj = resolve_project(db, project)
    stmt = select(Decision).where(Decision.project_id == proj.id)
    s = parse_since(since)
    if s is not None:
        stmt = stmt.where(Decision.decided_at >= s)
    stmt = stmt.order_by(Decision.decided_at.desc()).limit(limit)
    rows = db.execute(stmt).scalars().all()

    log_access(
        db,
        user_id=user.id,
        operation="decisions.list",
        project_id=proj.id,
        payload={"limit": limit, "since": since},
    )
    db.commit()
    return [
        DecisionOut(
            id=d.id,
            project_id=d.project_id,
            decision=d.decision,
            rationale=d.rationale,
            decided_at=d.decided_at,
            decided_by=d.decided_by,
            status=d.status,
        )
        for d in rows
    ]


@router.post("", response_model=DecisionOut, status_code=status.HTTP_201_CREATED)
def log_decision(
    body: LogDecisionIn,
    user: AuthedUser = Depends(current_user),
    db: Session = Depends(get_db),
) -> DecisionOut:
    proj = resolve_project(db, body.project)
    if not body.rationale.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="rationale is required"
        )

    # Embed best-effort; if model not available, leave NULL.
    vec: list[float] | None = None
    try:
        vec = embed(f"{body.decision}\n\n{body.rationale}")
    except Exception as exc:  # noqa: BLE001
        _log.warning("decision_embed_skipped", error=str(exc))

    d = Decision(
        project_id=proj.id,
        decision=body.decision.strip(),
        rationale=body.rationale.strip(),
        embedding=vec,
        decided_by=user.id,
        source_session_id=body.source_session_id,
        source_message_id=body.source_message_id,
    )
    db.add(d)

    log_access(
        db,
        user_id=user.id,
        operation="decision.log",
        project_id=proj.id,
        payload={"decision": body.decision[:200]},
    )
    db.commit()
    db.refresh(d)
    return DecisionOut(
        id=d.id,
        project_id=d.project_id,
        decision=d.decision,
        rationale=d.rationale,
        decided_at=d.decided_at,
        decided_by=d.decided_by,
        status=d.status,
    )
