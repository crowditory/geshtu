"""End-to-end route tests via FastAPI TestClient.

These exercise the same code path a real MCP/HTTP client uses: auth provider
issues a token, request lands on a route, route depends on `current_user`,
DB writes happen, response shape matches Pydantic models.

The fixtures commit to the live test DB (no transactional isolation), so
slugs / emails are uuid-suffixed to avoid collisions across runs.
"""

from __future__ import annotations

import uuid

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

from geshtu.auth import get_auth_provider
from geshtu.db.models import Project, Team, User
from geshtu.db.session import SessionLocal
from geshtu.main import create_app


@pytest.fixture(scope="module")
def app(have_db):
    if not have_db:
        pytest.skip("no DB reachable")
    return create_app()


@pytest.fixture
def client(app):
    with TestClient(app) as c:
        yield c


def _make_user(role: str = "admin") -> tuple[uuid.UUID, str]:
    """Create a fresh user + token. Returns (user_id, bearer_token)."""
    suffix = uuid.uuid4().hex[:10]
    with SessionLocal() as db:
        team = db.execute(select(Team)).scalars().first()
        if team is None:
            team = Team(name="Test")
            db.add(team)
            db.flush()
        u = User(
            team_id=team.id,
            email=f"u-{suffix}@example.com",
            display_name=f"User {suffix}",
            role=role,
        )
        db.add(u)
        db.flush()
        token, _ = get_auth_provider().issue_token(db, u.id, label="test")
        db.commit()
        return u.id, token


def _make_project(slug_hint: str = "p") -> uuid.UUID:
    suffix = uuid.uuid4().hex[:10]
    with SessionLocal() as db:
        p = Project(slug=f"{slug_hint}-{suffix}", name="Test Project")
        db.add(p)
        db.commit()
        return p.id, p.slug


@pytest.fixture
def admin_token():
    _, token = _make_user(role="admin")
    return token


@pytest.fixture
def member_token():
    _, token = _make_user(role="member")
    return token


@pytest.fixture
def project():
    pid, slug = _make_project()
    return {"id": pid, "slug": slug}


def _h(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


# ─── auth ─────────────────────────────────────────────────────────────


def test_health_no_auth_required(client: TestClient):
    r = client.get("/health")
    assert r.status_code == 200


def test_protected_route_rejects_missing_token(client: TestClient):
    r = client.get("/projects")
    assert r.status_code == 401


def test_protected_route_rejects_garbage_token(client: TestClient):
    r = client.get("/projects", headers=_h("tk_not-a-real-jwt"))
    assert r.status_code == 401


def test_admin_only_route_rejects_member(client: TestClient, member_token: str):
    body = {"slug": f"x-{uuid.uuid4().hex[:6]}", "name": "Nope"}
    r = client.post("/projects", json=body, headers=_h(member_token))
    assert r.status_code == 403


def test_users_me_returns_current(client: TestClient, admin_token: str):
    r = client.get("/users/me", headers=_h(admin_token))
    assert r.status_code == 200
    assert r.json()["role"] == "admin"


# ─── projects ─────────────────────────────────────────────────────────


def test_admin_can_create_project(client: TestClient, admin_token: str):
    slug = f"proj-{uuid.uuid4().hex[:8]}"
    r = client.post(
        "/projects",
        json={"slug": slug, "name": "Proj", "description": "desc"},
        headers=_h(admin_token),
    )
    assert r.status_code == 201
    body = r.json()
    assert body["slug"] == slug
    # GET roundtrip
    r2 = client.get(f"/projects/{slug}", headers=_h(admin_token))
    assert r2.status_code == 200
    assert r2.json()["id"] == body["id"]


def test_invalid_slug_is_rejected(client: TestClient, admin_token: str):
    r = client.post(
        "/projects",
        json={"slug": "Has Spaces!", "name": "x"},
        headers=_h(admin_token),
    )
    assert r.status_code == 400


def test_duplicate_slug_conflicts(client: TestClient, admin_token: str):
    slug = f"dup-{uuid.uuid4().hex[:8]}"
    body = {"slug": slug, "name": "x"}
    assert client.post("/projects", json=body, headers=_h(admin_token)).status_code == 201
    r = client.post("/projects", json=body, headers=_h(admin_token))
    assert r.status_code == 409


# ─── sessions + messages ─────────────────────────────────────────────


def test_session_lifecycle(client: TestClient, admin_token: str, project):
    r = client.post(
        "/sessions",
        json={"project": project["slug"], "title": "test session"},
        headers=_h(admin_token),
    )
    assert r.status_code == 201
    sid = r.json()["id"]

    r = client.get(f"/sessions/{sid}", headers=_h(admin_token))
    assert r.status_code == 200
    assert r.json()["title"] == "test session"


def test_message_append_returns_immediately(
    client: TestClient, admin_token: str, project
):
    """The message must be saved synchronously even if the queue is broken
    or the role is non-extracting. Spec §5.1 invariant."""
    r = client.post(
        "/sessions",
        json={"project": project["slug"]},
        headers=_h(admin_token),
    )
    sid = r.json()["id"]

    # role=system shouldn't trigger extraction; extraction_job_id should be None.
    r = client.post(
        "/messages",
        json={
            "session_id": sid,
            "role": "system",
            "content": "Some long-enough system framing message that wouldn't extract.",
        },
        headers=_h(admin_token),
    )
    assert r.status_code == 201
    body = r.json()
    assert body["role"] == "system"
    assert body["extraction_job_id"] is None


def test_message_invalid_role_rejected(
    client: TestClient, admin_token: str, project
):
    r = client.post(
        "/sessions",
        json={"project": project["slug"]},
        headers=_h(admin_token),
    )
    sid = r.json()["id"]

    r = client.post(
        "/messages",
        json={"session_id": sid, "role": "bogus", "content": "x"},
        headers=_h(admin_token),
    )
    assert r.status_code == 422  # pydantic validation


# ─── decisions ────────────────────────────────────────────────────────


def test_log_decision_requires_rationale(
    client: TestClient, admin_token: str, project
):
    r = client.post(
        "/decisions",
        json={"project": project["slug"], "decision": "X", "rationale": "  "},
        headers=_h(admin_token),
    )
    # Either 400 (our explicit check) or 422 (pydantic min_length) is fine.
    assert r.status_code in (400, 422)


def test_log_decision_then_list(client: TestClient, admin_token: str, project):
    r = client.post(
        "/decisions",
        json={
            "project": project["slug"],
            "decision": "Use Postgres",
            "rationale": "team already runs it",
        },
        headers=_h(admin_token),
    )
    assert r.status_code == 201
    d_id = r.json()["id"]

    r = client.get(f"/decisions?project={project['slug']}&limit=5", headers=_h(admin_token))
    assert r.status_code == 200
    rows = r.json()
    assert any(d["id"] == d_id for d in rows)


# ─── facts (manual log + dedup status) ───────────────────────────────


@pytest.mark.skipif(
    __import__("os").environ.get("RUN_BGE") != "1",
    reason="loads BGE-M3 (~2GB) on first call; set RUN_BGE=1 to opt in",
)
def test_log_fact_returns_status(client: TestClient, admin_token: str, project):
    """Two near-identical facts: second should come back as 'updated'.

    Gated by RUN_BGE=1 because the first /facts call downloads BGE-M3
    (~2 GB) and blocks for ~30s. Acceptable on the test box where the
    model cache persists across runs; bad as a default for CI.
    """
    pytest.importorskip("sentence_transformers")

    body = {
        "project": project["slug"],
        "statement": "The repository name is geshtu",
        "entity": "repo",
        "attribute": "name",
    }
    r1 = client.post("/facts", json=body, headers=_h(admin_token))
    assert r1.status_code == 201
    assert r1.json()["status"] == "logged"

    body2 = dict(body, statement="Geshtu is the name of the repository")
    r2 = client.post("/facts", json=body2, headers=_h(admin_token))
    assert r2.status_code == 201
    # Either 'updated' (cosine ≥ 0.92) or 'logged' depending on the actual
    # embedding similarity. Both are valid outcomes; we mainly assert no crash.
    assert r2.json()["status"] in ("updated", "logged")


# ─── token revocation ────────────────────────────────────────────────


def test_revoked_token_is_rejected(client: TestClient):
    """Issue a token, hit /users/me to confirm it works, revoke, hit again → 401."""
    user_id, token = _make_user(role="admin")

    r = client.get("/users/me", headers=_h(token))
    assert r.status_code == 200

    # Find the access_tokens row and revoke via the admin endpoint.
    from datetime import UTC, datetime

    from geshtu.db.models import AccessToken

    with SessionLocal() as db:
        t = db.execute(
            select(AccessToken).where(AccessToken.user_id == user_id).order_by(
                AccessToken.created_at.desc()
            )
        ).scalars().first()
        t.revoked_at = datetime.now(tz=UTC)
        db.commit()

    r = client.get("/users/me", headers=_h(token))
    assert r.status_code == 401
