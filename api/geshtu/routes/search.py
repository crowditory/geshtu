"""Hybrid search over facts + (optional) decisions."""

from __future__ import annotations

import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from geshtu.auth import AuthedUser, current_user
from geshtu.db.session import get_db
from geshtu.routes.common import log_access, resolve_project
from geshtu.search import search_decisions, search_facts

router = APIRouter(prefix="/search", tags=["search"])


class SearchedFactOut(BaseModel):
    id: uuid.UUID
    statement: str
    entity: str | None
    attribute: str | None
    score: float
    valid_from: datetime
    confidence: float


class SearchedDecisionOut(BaseModel):
    id: uuid.UUID
    decision: str
    rationale: str
    decided_at: datetime
    status: str
    score: float


class SearchOut(BaseModel):
    facts: list[SearchedFactOut]
    decisions: list[SearchedDecisionOut]


@router.get("", response_model=SearchOut)
def search(
    project: str = Query(...),
    q: str = Query(..., min_length=1),
    k: int = Query(10, ge=1, le=50),
    include_decisions: bool = Query(True),
    user: AuthedUser = Depends(current_user),
    db: Session = Depends(get_db),
) -> SearchOut:
    proj = resolve_project(db, project)
    facts = search_facts(db, proj.id, q, k=k)
    decisions = search_decisions(db, proj.id, q, k=k) if include_decisions else []
    log_access(
        db,
        user_id=user.id,
        operation="search",
        project_id=proj.id,
        payload={"q": q, "k": k},
    )
    db.commit()
    return SearchOut(
        facts=[
            SearchedFactOut(
                id=f.id,
                statement=f.statement,
                entity=f.entity,
                attribute=f.attribute,
                score=f.score,
                valid_from=f.valid_from,
                confidence=f.confidence,
            )
            for f in facts
        ],
        decisions=[
            SearchedDecisionOut(
                id=d.id,
                decision=d.decision,
                rationale=d.rationale,
                decided_at=d.decided_at,
                status=d.status,
                score=d.score,
            )
            for d in decisions
        ],
    )
