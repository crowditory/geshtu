"""Migration runner sanity tests."""

from __future__ import annotations

import pytest
from sqlalchemy import text

from geshtu.db.session import engine
from geshtu.migrate import _list_migrations, main


def test_lists_at_least_one_migration():
    migs = _list_migrations()
    assert len(migs) >= 1
    versions = [v for v, _ in migs]
    assert "001_init" in versions


def test_migrate_is_idempotent(have_db):
    """Running migrate twice on the same DB must not error or duplicate work."""
    if not have_db:
        pytest.skip("no DB reachable")

    # First run is whatever the test box already has applied — should be a no-op
    # if migrations were applied during box setup (they were).
    rc1 = main([])
    assert rc1 == 0

    rc2 = main([])
    assert rc2 == 0

    # Verify the bookkeeping table reflects exactly one row per known migration.
    with engine.connect() as conn:
        rows = conn.execute(text("SELECT version, count(*) FROM schema_migrations GROUP BY version")).all()
    counts = {r.version: r.count for r in rows}
    for version, _ in _list_migrations():
        assert counts.get(version) == 1, f"{version} applied {counts.get(version)} times"


def test_dry_run_does_not_apply(have_db):
    """--dry-run must not insert into schema_migrations or alter anything."""
    if not have_db:
        pytest.skip("no DB reachable")

    with engine.connect() as conn:
        before = conn.execute(text("SELECT count(*) FROM schema_migrations")).scalar_one()

    rc = main(["--dry-run"])
    assert rc == 0

    with engine.connect() as conn:
        after = conn.execute(text("SELECT count(*) FROM schema_migrations")).scalar_one()
    assert after == before
