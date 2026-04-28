"""Async digest endpoint + manual fact-logging endpoint.

Exposes:
- GET  /digest    → on-demand summary at three depths
- POST /facts     → user-driven `geshtu_log_fact`
"""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from geshtu.auth import AuthedUser, current_user
from geshtu.db.session import get_db
from geshtu.dedup import upsert_fact
from geshtu.digest import DEPTHS, DigestGenerationError, generate_digest
from geshtu.embed import embed
from geshtu.logging import get_logger
from geshtu.routes.common import log_access, parse_since, resolve_project

router = APIRouter(tags=["memory"])
_log = get_logger(__name__)


class DigestOut(BaseModel):
    id: uuid.UUID
    content_md: str
    fact_count: int
    decision_count: int
    cached: bool


@router.get("/digest", response_model=DigestOut)
def get_digest(
    project: str = Query(...),
    depth: str = Query("standard"),
    since: str | None = Query(None),
    use_cache: bool = Query(True),
    user: AuthedUser = Depends(current_user),
    db: Session = Depends(get_db),
) -> DigestOut:
    if depth not in DEPTHS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"depth must be one of {DEPTHS}",
        )
    proj = resolve_project(db, project, user)
    s = parse_since(since)
    try:
        res = generate_digest(
            db,
            project_id=proj.id,
            project_name=proj.name,
            since=s,
            depth=depth,
            requested_by=user.id,
            use_cache=use_cache,
        )
    except DigestGenerationError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"upstream model error: {exc}",
        ) from exc
    log_access(
        db,
        user_id=user.id,
        operation="digest",
        project_id=proj.id,
        payload={"depth": depth, "since": since, "cached": res.cached},
    )
    db.commit()
    return DigestOut(
        id=res.id,
        content_md=res.content_md,
        fact_count=res.fact_count,
        decision_count=res.decision_count,
        cached=res.cached,
    )


# ─── /facts (manual log) ─────────────────────────────────────────────


class LogFactIn(BaseModel):
    project: str
    statement: str = Field(..., min_length=3)
    entity: str | None = None
    attribute: str | None = None
    source_session_id: uuid.UUID | None = None
    source_message_id: uuid.UUID | None = None
    confidence: float = 1.0


class LogFactOut(BaseModel):
    id: uuid.UUID
    status: str  # 'logged' | 'updated' | 'duplicate'
    superseded_id: uuid.UUID | None = None
    refines_id: uuid.UUID | None = None


@router.post("/facts", response_model=LogFactOut, status_code=status.HTTP_201_CREATED)
def log_fact(
    body: LogFactIn,
    user: AuthedUser = Depends(current_user),
    db: Session = Depends(get_db),
) -> LogFactOut:
    proj = resolve_project(db, body.project, user)
    try:
        vec = embed(body.statement)
    except Exception as exc:  # noqa: BLE001
        _log.warning("fact_embed_failed", error=str(exc))
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="embedding model unavailable",
        ) from exc

    out = upsert_fact(
        db,
        project_id=proj.id,
        statement=body.statement.strip(),
        entity=body.entity,
        attribute=body.attribute,
        embedding=vec,
        source_session_id=body.source_session_id,
        source_message_id=body.source_message_id,
        created_by=user.id,
        confidence=body.confidence,
    )
    log_access(
        db,
        user_id=user.id,
        operation="fact.log",
        project_id=proj.id,
        payload={"statement": body.statement[:200], "status": out.status},
    )
    db.commit()
    return LogFactOut(
        id=out.fact_id,
        status=out.status,
        superseded_id=out.superseded_id,
        refines_id=out.refines_id,
    )
