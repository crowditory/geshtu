"""JWT issue/verify roundtrip — DB-backed."""

from __future__ import annotations

from sqlalchemy import select

from geshtu.auth import JWTAuthProvider, _bcrypt_check
from geshtu.db.models import AccessToken, Team, User


def test_issue_and_verify_token(db):
    # Ensure there's a team + user
    team = Team(name="Test")
    db.add(team)
    db.flush()
    user = User(team_id=team.id, email=f"u-{team.id}@example.com", display_name="U", role="admin")
    db.add(user)
    db.flush()

    provider = JWTAuthProvider(secret="x" * 64)
    token, record = provider.issue_token(db, user.id, label="test")
    db.commit()

    assert token.startswith("tk_")
    saved = db.execute(select(AccessToken).where(AccessToken.id == record.id)).scalar_one()
    assert saved.label == "test"
    assert _bcrypt_check(token, saved.token_hash)


def test_revoked_token_does_not_validate(db):
    from datetime import datetime, timezone

    from fastapi import Request

    team = Team(name="Test2")
    db.add(team)
    db.flush()
    user = User(team_id=team.id, email=f"u2-{team.id}@example.com", display_name="U2")
    db.add(user)
    db.flush()

    provider = JWTAuthProvider(secret="y" * 64)
    token, record = provider.issue_token(db, user.id)
    db.commit()

    # Revoke
    record.revoked_at = datetime.now(tz=timezone.utc)
    db.commit()

    scope = {
        "type": "http",
        "headers": [(b"authorization", f"Bearer {token}".encode())],
        "query_string": b"",
    }
    req = Request(scope)
    assert provider.authenticate(req, db) is None
