"""User + token management. Admin-only endpoints."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from geshtu.auth import AuthedUser, current_user, get_auth_provider, require_admin
from geshtu.db.models import AccessToken, User
from geshtu.db.session import get_db

router = APIRouter(prefix="/users", tags=["users"])


class UserOut(BaseModel):
    id: uuid.UUID
    email: str
    display_name: str
    role: str
    created_at: datetime
    last_seen_at: datetime


class UserIn(BaseModel):
    email: EmailStr
    display_name: str
    role: str = Field("member", pattern="^(admin|member)$")


class UserWithTokenOut(UserOut):
    token: str


class TokenIssueIn(BaseModel):
    label: str | None = None


class TokenOut(BaseModel):
    id: uuid.UUID
    label: str | None
    created_at: datetime
    last_used_at: datetime | None
    revoked_at: datetime | None


def _u_out(u: User) -> UserOut:
    return UserOut(
        id=u.id,
        email=u.email,
        display_name=u.display_name,
        role=u.role,
        created_at=u.created_at,
        last_seen_at=u.last_seen_at,
    )


@router.get("/me", response_model=UserOut)
def me(user: AuthedUser = Depends(current_user), db: Session = Depends(get_db)) -> UserOut:
    u = db.get(User, user.id)
    if u is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
    return _u_out(u)


@router.get("", response_model=list[UserOut])
def list_users(
    _admin: AuthedUser = Depends(require_admin),
    db: Session = Depends(get_db),
) -> list[UserOut]:
    rows = db.execute(select(User).order_by(User.created_at.desc())).scalars().all()
    return [_u_out(u) for u in rows]


@router.post("", response_model=UserWithTokenOut, status_code=status.HTTP_201_CREATED)
def create_user(
    body: UserIn,
    _admin: AuthedUser = Depends(require_admin),
    db: Session = Depends(get_db),
) -> UserWithTokenOut:
    if db.execute(select(User).where(User.email == body.email)).scalar_one_or_none():
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="email already exists")

    u = User(email=body.email, display_name=body.display_name, role=body.role)
    db.add(u)
    db.flush()

    token, _ = get_auth_provider().issue_token(db, u.id, label="initial")
    db.commit()
    db.refresh(u)
    out = _u_out(u).model_dump()
    out["token"] = token
    return UserWithTokenOut(**out)


@router.post("/{user_id}/tokens", response_model=dict)
def issue_token(
    user_id: uuid.UUID,
    body: TokenIssueIn,
    _admin: AuthedUser = Depends(require_admin),
    db: Session = Depends(get_db),
) -> dict:
    u = db.get(User, user_id)
    if u is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="user not found")
    token, record = get_auth_provider().issue_token(db, u.id, label=body.label)
    db.commit()
    return {"id": str(record.id), "token": token, "label": record.label}


@router.get("/{user_id}/tokens", response_model=list[TokenOut])
def list_tokens(
    user_id: uuid.UUID,
    _admin: AuthedUser = Depends(require_admin),
    db: Session = Depends(get_db),
) -> list[TokenOut]:
    rows = (
        db.execute(
            select(AccessToken).where(AccessToken.user_id == user_id).order_by(
                AccessToken.created_at.desc()
            )
        )
        .scalars()
        .all()
    )
    return [
        TokenOut(
            id=t.id,
            label=t.label,
            created_at=t.created_at,
            last_used_at=t.last_used_at,
            revoked_at=t.revoked_at,
        )
        for t in rows
    ]


@router.post("/tokens/{token_id}/revoke", status_code=status.HTTP_204_NO_CONTENT)
def revoke_token(
    token_id: uuid.UUID,
    _admin: AuthedUser = Depends(require_admin),
    db: Session = Depends(get_db),
) -> None:
    t = db.get(AccessToken, token_id)
    if t is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
    if t.revoked_at is None:
        t.revoked_at = datetime.now(tz=UTC)
    db.commit()
    return None
