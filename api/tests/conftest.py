"""Shared pytest fixtures.

DB-touching tests skip (rather than fail) when Postgres isn't reachable.
This lets contributors run `pytest` on a fresh checkout to validate pure
logic (parser, JSON handling) without spinning up Docker. CI does spin
up the service container, so the skipped tests still run there.
"""

from __future__ import annotations

import os

import pytest

os.environ.setdefault("DATABASE_URL", "postgresql+psycopg://geshtu:test@localhost:5432/geshtu")
os.environ.setdefault("REDIS_URL", "redis://localhost:6379/0")
os.environ.setdefault("ANTHROPIC_API_KEY", "test-key-not-real")
os.environ.setdefault("JWT_SECRET", "0" * 64)
os.environ.setdefault("EMBEDDING_DIM", "1024")


def _have_db() -> bool:
    try:
        from sqlalchemy import create_engine, text

        engine = create_engine(os.environ["DATABASE_URL"])
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return True
    except Exception:  # noqa: BLE001
        return False


@pytest.fixture(scope="session")
def have_db() -> bool:
    return _have_db()


@pytest.fixture
def db(have_db):
    if not have_db:
        pytest.skip("no DB reachable")
    from geshtu.db.session import SessionLocal

    with SessionLocal() as s:
        yield s
        s.rollback()
