"""Per-project token scope (migration 002 + auth changes).

Asserts that:
    - A token issued without `project` works for any project.
    - A token issued with `project=foo` works for project foo only;
      hitting any route that references project bar returns 403.
    - GET /projects filters to the scoped project (only one row visible).
    - GET /projects/{slug} 404s for out-of-scope slugs (no leak).
    - Session/message endpoints respect the scope via the indirect
      project_id lookup.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass

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


def _h(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


@dataclass(frozen=True)
class ProjectRef:
    """Detached snapshot of a Project — safe to use after the session closes."""
    id: uuid.UUID
    slug: str
    name: str


def _setup() -> tuple[uuid.UUID, str, str, ProjectRef, ProjectRef]:
    """Create user + two projects + scoped token.

    Returns plain values (not ORM objects) so callers don't trip
    ``DetachedInstanceError`` when reading attributes outside the session.
    """
    suffix = uuid.uuid4().hex[:8]
    with SessionLocal() as db:
        team = db.execute(select(Team)).scalars().first()
        if team is None:
            team = Team(name="Test")
            db.add(team)
            db.flush()
        user = User(
            team_id=team.id,
            email=f"scope-{suffix}@example.com",
            display_name=f"Scope {suffix}",
            role="admin",
        )
        db.add(user)
        db.flush()

        proj_a = Project(slug=f"a-{suffix}", name=f"Project A {suffix}")
        proj_b = Project(slug=f"b-{suffix}", name=f"Project B {suffix}")
        db.add(proj_a)
        db.add(proj_b)
        db.flush()

        provider = get_auth_provider()
        scoped, _ = provider.issue_token(db, user.id, label="scoped", project_id=proj_a.id)
        unscoped, _ = provider.issue_token(db, user.id, label="unscoped")

        ref_a = ProjectRef(id=proj_a.id, slug=proj_a.slug, name=proj_a.name)
        ref_b = ProjectRef(id=proj_b.id, slug=proj_b.slug, name=proj_b.name)
        uid = user.id
        db.commit()
        return uid, scoped, unscoped, ref_a, ref_b


def test_unscoped_token_sees_both_projects(client: TestClient):
    _, _scoped, unscoped, proj_a, proj_b = _setup()
    listed = {p["slug"] for p in client.get("/projects", headers=_h(unscoped)).json()}
    assert proj_a.slug in listed
    assert proj_b.slug in listed


def test_scoped_token_sees_only_its_project(client: TestClient):
    _, scoped, _u, proj_a, proj_b = _setup()
    listed = {p["slug"] for p in client.get("/projects", headers=_h(scoped)).json()}
    assert proj_a.slug in listed
    assert proj_b.slug not in listed


def test_scoped_token_get_other_project_returns_404(client: TestClient):
    _, scoped, _u, _a, proj_b = _setup()
    r = client.get(f"/projects/{proj_b.slug}", headers=_h(scoped))
    # 404, not 403, on purpose: don't leak that the project even exists.
    assert r.status_code == 404


def test_scoped_token_search_in_scope_works(client: TestClient):
    _, scoped, _u, proj_a, _b = _setup()
    r = client.get(
        "/search",
        params={"project": proj_a.slug, "q": "anything", "k": 5},
        headers=_h(scoped),
    )
    # No facts seeded — empty result is fine, but the route must return 200,
    # not 403.
    assert r.status_code == 200
    assert r.json()["facts"] == []


def test_scoped_token_search_out_of_scope_returns_403(client: TestClient):
    _, scoped, _u, _a, proj_b = _setup()
    r = client.get(
        "/search",
        params={"project": proj_b.slug, "q": "anything"},
        headers=_h(scoped),
    )
    assert r.status_code == 403


def test_scoped_token_log_decision_in_scope_works(client: TestClient):
    _, scoped, _u, proj_a, _b = _setup()
    r = client.post(
        "/decisions",
        json={
            "project": proj_a.slug,
            "decision": "scoped decision works",
            "rationale": "smoke test",
        },
        headers=_h(scoped),
    )
    assert r.status_code == 201


def test_scoped_token_log_decision_out_of_scope_blocked(client: TestClient):
    _, scoped, _u, _a, proj_b = _setup()
    r = client.post(
        "/decisions",
        json={
            "project": proj_b.slug,
            "decision": "should not land",
            "rationale": "wrong project",
        },
        headers=_h(scoped),
    )
    assert r.status_code == 403


def test_scoped_token_session_then_message(client: TestClient):
    """Session creation goes through resolve_project; message append goes
    through assert_project_in_scope on the resolved session.project_id."""
    _, scoped, _u, proj_a, proj_b = _setup()
    r = client.post(
        "/sessions",
        json={"project": proj_a.slug},
        headers=_h(scoped),
    )
    assert r.status_code == 201
    sid = r.json()["id"]

    # In-scope: succeeds.
    r = client.post(
        "/messages",
        json={
            "session_id": sid,
            "role": "user",
            "content": "Long enough message for the skip filter to let through.",
            "extract": False,
        },
        headers=_h(scoped),
    )
    assert r.status_code == 201

    # Out-of-scope session creation: blocked.
    r = client.post(
        "/sessions",
        json={"project": proj_b.slug},
        headers=_h(scoped),
    )
    assert r.status_code == 403


def test_token_issue_endpoint_accepts_project_slug(client: TestClient):
    user_id, _scoped, unscoped, proj_a, _b = _setup()
    r = client.post(
        f"/users/{user_id}/tokens",
        json={"label": "via-api", "project": proj_a.slug},
        headers=_h(unscoped),
    )
    assert r.status_code == 200
    body = r.json()
    assert body["project_slug"] == proj_a.slug
    assert body["token"].startswith("tk_")

    # The freshly issued token should now see only proj_a.
    listed = {p["slug"] for p in client.get("/projects", headers=_h(body["token"])).json()}
    assert listed == {proj_a.slug}
