"""Apply SQL migrations from db/migrations/*.sql in lexicographic order."""

from __future__ import annotations

import sys
from importlib import resources
from pathlib import Path

from sqlalchemy import text

from geshtu.db.session import engine
from geshtu.logging import configure_logging, get_logger

_log = get_logger(__name__)


def _list_migrations() -> list[tuple[str, str]]:
    """Return [(version, sql_text), ...] sorted by version."""
    pkg = resources.files("geshtu.db") / "migrations"
    out: list[tuple[str, str]] = []
    for f in sorted(p for p in pkg.iterdir() if p.name.endswith(".sql")):
        version = Path(f.name).stem
        sql = f.read_text(encoding="utf-8")
        out.append((version, sql))
    return out


def main(argv: list[str] | None = None) -> int:
    configure_logging("info")
    args = argv or sys.argv[1:]
    dry = "--dry-run" in args

    migrations = _list_migrations()
    if not migrations:
        _log.warning("no_migrations_found")
        return 0

    with engine.begin() as conn:
        # Ensure the bookkeeping table exists (idempotent w/ CREATE IF NOT EXISTS).
        conn.execute(
            text(
                """
                CREATE TABLE IF NOT EXISTS schema_migrations (
                    version TEXT PRIMARY KEY,
                    applied_at TIMESTAMPTZ NOT NULL DEFAULT now()
                );
                """
            )
        )
        applied = {
            row.version
            for row in conn.execute(text("SELECT version FROM schema_migrations")).all()
        }

    for version, sql in migrations:
        if version in applied:
            _log.info("migration_skip", version=version)
            continue
        if dry:
            _log.info("migration_would_apply", version=version, bytes=len(sql))
            continue
        _log.info("migration_apply", version=version)
        with engine.begin() as conn:
            conn.execute(text(sql))
            conn.execute(
                text(
                    "INSERT INTO schema_migrations(version) VALUES (:v) ON CONFLICT DO NOTHING"
                ),
                {"v": version},
            )
        _log.info("migration_done", version=version)

    return 0


if __name__ == "__main__":
    sys.exit(main())
