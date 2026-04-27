"""CRUD for projects."""

from __future__ import annotations

import re
import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from geshtu.auth import AuthedUser, current_user, require_admin
from geshtu.db.models import Project
from geshtu.db.session import get_db

router = APIRouter(prefix="/projects", tags=["projects"])

_SLUG_RE = re.compile(r"^[a-z0-9][a-z0-9-]{1,62}[a-z0-9]$")


class ProjectIn(BaseModel):
    slug: str = Field(..., examples=["playserv-core"])
    name: str
    description: str | None = None


class ProjectOut(BaseModel):
    id: uuid.UUID
    slug: str
    name: str
    description: str | None
    created_at: datetime


def _to_out(p: Project) -> ProjectOut:
    return ProjectOut(
        id=p.id,
        slug=p.slug,
        name=p.name,
        description=p.description,
        created_at=p.created_at,
    )


@router.get("", response_model=list[ProjectOut])
def list_projects(
    _user: AuthedUser = Depends(current_user),
    db: Session = Depends(get_db),
) -> list[ProjectOut]:
    rows = db.execute(select(Project).order_by(Project.created_at.desc())).scalars().all()
    return [_to_out(p) for p in rows]


@router.post("", response_model=ProjectOut, status_code=status.HTTP_201_CREATED)
def create_project(
    body: ProjectIn,
    _admin: AuthedUser = Depends(require_admin),
    db: Session = Depends(get_db),
) -> ProjectOut:
    if not _SLUG_RE.match(body.slug):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="slug must be 3-64 chars, lowercase alphanumeric or '-'",
        )
    if db.execute(select(Project).where(Project.slug == body.slug)).scalar_one_or_none():
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="slug already exists")

    p = Project(slug=body.slug, name=body.name, description=body.description)
    db.add(p)
    db.commit()
    db.refresh(p)
    return _to_out(p)


@router.get("/{slug}", response_model=ProjectOut)
def get_project(
    slug: str,
    _user: AuthedUser = Depends(current_user),
    db: Session = Depends(get_db),
) -> ProjectOut:
    p = db.execute(select(Project).where(Project.slug == slug)).scalar_one_or_none()
    if p is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="project not found")
    return _to_out(p)
