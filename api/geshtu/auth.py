"""Auth as a swappable interface (spec §15.6.2).

Routes call ``current_user(request, db)``; they never import JWT primitives
directly. To swap in OAuth later, implement ``AuthProvider`` and bind it
in ``main.py`` via ``set_auth_provider``.
"""

from __future__ import annotations

import hashlib
import hmac
import secrets
import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Protocol

import bcrypt
import jwt
from fastapi import Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from geshtu.config import get_settings
from geshtu.db.models import AccessToken, User
from geshtu.db.session import get_db


# ─── Public types ────────────────────────────────────────────────────


@dataclass(frozen=True)
class AuthedUser:
    id: uuid.UUID
    email: str
    display_name: str
    role: str
    token_id: uuid.UUID

    @property
    def is_admin(self) -> bool:
        return self.role == "admin"


class AuthProvider(Protocol):
    def authenticate(self, request: Request, db: Session) -> AuthedUser | None: ...
    def issue_token(
        self, db: Session, user_id: uuid.UUID, label: str | None = None
    ) -> tuple[str, AccessToken]: ...


# ─── Token format ────────────────────────────────────────────────────
#
# A Geshtu access token is a JWT signed with JWT_SECRET (HS256).
# Payload: {"sub": user_id, "tid": token_id, "iat": ..., "exp": ...}
# A bcrypt hash of the JWT string is stored in access_tokens.token_hash —
# revocation works by setting access_tokens.revoked_at, and we re-check
# the hash on every request to ensure the issued token is still active.
#
# Tokens are surfaced to operators with the ``tk_`` prefix for easy
# recognition; the prefix is purely cosmetic and stripped before verify.

_TOKEN_PREFIX = "tk_"


def _strip_prefix(t: str) -> str:
    return t[len(_TOKEN_PREFIX):] if t.startswith(_TOKEN_PREFIX) else t


def _bcrypt_hash(token: str) -> str:
    # bcrypt silently truncates input at 72 bytes — JWTs are larger than that.
    # Pre-hashing with SHA-256 makes the input a fixed 32 bytes and prevents
    # two distinct long tokens from colliding on bcrypt's 72-byte prefix.
    digest = hashlib.sha256(token.encode("utf-8")).digest()
    return bcrypt.hashpw(digest, bcrypt.gensalt(rounds=12)).decode("utf-8")


def _bcrypt_check(token: str, hashed: str) -> bool:
    digest = hashlib.sha256(token.encode("utf-8")).digest()
    try:
        return bcrypt.checkpw(digest, hashed.encode("utf-8"))
    except ValueError:
        return False


# ─── JWT provider (default) ──────────────────────────────────────────


class JWTAuthProvider:
    def __init__(self, secret: str, algorithm: str = "HS256", ttl_days: int = 365):
        self._secret = secret
        self._algorithm = algorithm
        self._ttl = timedelta(days=ttl_days)

    def issue_token(
        self,
        db: Session,
        user_id: uuid.UUID,
        label: str | None = None,
    ) -> tuple[str, AccessToken]:
        token_id = uuid.uuid4()
        now = datetime.now(tz=timezone.utc)
        payload = {
            "sub": str(user_id),
            "tid": str(token_id),
            "iat": int(now.timestamp()),
            "exp": int((now + self._ttl).timestamp()),
            "jti": secrets.token_hex(8),
        }
        encoded = jwt.encode(payload, self._secret, algorithm=self._algorithm)
        token_str = _TOKEN_PREFIX + encoded

        record = AccessToken(
            id=token_id,
            user_id=user_id,
            token_hash=_bcrypt_hash(token_str),
            label=label,
        )
        db.add(record)
        db.flush()
        return token_str, record

    def authenticate(self, request: Request, db: Session) -> AuthedUser | None:
        token = _extract_bearer(request)
        if not token:
            return None
        try:
            decoded = jwt.decode(
                _strip_prefix(token),
                self._secret,
                algorithms=[self._algorithm],
            )
        except jwt.PyJWTError:
            return None

        try:
            user_id = uuid.UUID(decoded["sub"])
            token_id = uuid.UUID(decoded["tid"])
        except (KeyError, ValueError):
            return None

        record = db.execute(
            select(AccessToken).where(AccessToken.id == token_id)
        ).scalar_one_or_none()
        if record is None or record.revoked_at is not None:
            return None
        # JWT signature is already verified above; the bcrypt check defends
        # against the case where JWT_SECRET leaks but the DB doesn't —
        # an attacker could forge JWTs but not the hashed token row.
        if not _bcrypt_check(token, record.token_hash):
            return None
        # Constant-time compare to avoid leaking whether the JWT's `sub`
        # matches the access_tokens.user_id via timing.
        if not hmac.compare_digest(str(record.user_id), str(user_id)):
            return None

        user = db.execute(select(User).where(User.id == user_id)).scalar_one_or_none()
        if user is None:
            return None

        record.last_used_at = datetime.now(tz=timezone.utc)
        user.last_seen_at = datetime.now(tz=timezone.utc)

        return AuthedUser(
            id=user.id,
            email=user.email,
            display_name=user.display_name,
            role=user.role,
            token_id=record.id,
        )


def _extract_bearer(request: Request) -> str | None:
    auth = request.headers.get("authorization") or request.headers.get("Authorization")
    if auth and auth.lower().startswith("bearer "):
        return auth.split(" ", 1)[1].strip()
    # Some MCP / SSE clients can't set arbitrary headers and need the token
    # in the URL. Tradeoff: query params land in access logs / referrer
    # headers — operators should prefer header auth when possible.
    qp = request.query_params.get("token")
    return qp


# ─── Provider registry ───────────────────────────────────────────────

_provider: AuthProvider | None = None


def set_auth_provider(provider: AuthProvider) -> None:
    global _provider
    _provider = provider


def get_auth_provider() -> AuthProvider:
    global _provider
    if _provider is None:
        s = get_settings()
        _provider = JWTAuthProvider(
            secret=s.jwt_secret,
            algorithm=s.jwt_algorithm,
            ttl_days=s.jwt_default_ttl_days,
        )
    return _provider


# ─── FastAPI dependencies ────────────────────────────────────────────


def current_user(
    request: Request,
    db: Session = Depends(get_db),
) -> AuthedUser:
    user = get_auth_provider().authenticate(request, db)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="invalid or missing token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user


def require_admin(user: AuthedUser = Depends(current_user)) -> AuthedUser:
    if not user.is_admin:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="admin required")
    return user
