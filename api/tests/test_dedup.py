"""Dedup behaviour tests — DB-backed.

Uses synthetic embeddings (small, hand-rolled) so tests don't need to
load BGE-M3.
"""

from __future__ import annotations

import math
import uuid

import pytest

from geshtu.config import get_settings
from geshtu.db.models import Project
from geshtu.dedup import upsert_fact

DIM = 1024


def _vec(seed: int, sim_to: list[float] | None = None, blend: float = 1.0) -> list[float]:
    """Build a deterministic unit vector; optionally blend toward another vector."""
    import random

    rng = random.Random(seed)
    raw = [rng.gauss(0, 1) for _ in range(DIM)]
    if sim_to is not None:
        raw = [blend * sim_to[i] + (1 - blend) * raw[i] for i in range(DIM)]
    norm = math.sqrt(sum(x * x for x in raw))
    return [x / norm for x in raw]


@pytest.fixture
def project(db):
    # uuid in the slug avoids UNIQUE collisions when tests run repeatedly
    # against a persistent dev DB (the fixture commits, so cleanup is partial).
    p = Project(slug=f"dedup-test-{uuid.uuid4().hex[:12]}", name="Dedup Test")
    db.add(p)
    db.commit()
    db.refresh(p)
    return p


def test_first_fact_is_pure_insert(db, project):
    out = upsert_fact(
        db,
        project_id=project.id,
        statement="Postgres 16 is the primary database",
        entity="Postgres",
        attribute="version",
        embedding=_vec(1),
    )
    db.commit()
    assert out.status == "logged"
    assert out.superseded_id is None
    assert out.refines_id is None


def test_near_identical_supersedes(db, project):
    base = _vec(2)
    upsert_fact(
        db,
        project_id=project.id,
        statement="Postgres 16 is the primary database",
        entity="Postgres",
        attribute="version",
        embedding=base,
    )
    db.commit()
    s = get_settings()
    near = _vec(2, sim_to=base, blend=0.99)  # ~0.99 cosine, well above supersede
    assert s.dedup_supersede_threshold <= 0.99
    out = upsert_fact(
        db,
        project_id=project.id,
        statement="The primary database is Postgres 16",
        entity="Postgres",
        attribute="version",
        embedding=near,
    )
    db.commit()
    assert out.status == "updated"
    assert out.superseded_id is not None


def test_dissimilar_inserts(db, project):
    upsert_fact(
        db,
        project_id=project.id,
        statement="Postgres is the database",
        embedding=_vec(3),
    )
    db.commit()
    out = upsert_fact(
        db,
        project_id=project.id,
        statement="Customer A signed in March",
        embedding=_vec(99),
    )
    db.commit()
    assert out.status == "logged"
    assert out.superseded_id is None
    assert out.refines_id is None
