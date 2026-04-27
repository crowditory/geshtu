"""First-run CLI: create the team row, create the admin user, print a token.

Idempotent: if a team or user already exists, only missing pieces are created
and a fresh admin token is issued.
"""

from __future__ import annotations

import argparse
import sys

from sqlalchemy import select

from geshtu.auth import get_auth_provider
from geshtu.db.models import Team, User
from geshtu.db.session import SessionLocal
from geshtu.logging import configure_logging, get_logger

_log = get_logger(__name__)


def run(team_name: str, admin_email: str, admin_name: str) -> str:
    """Returns the issued admin token."""
    with SessionLocal() as db:
        team = db.execute(select(Team)).scalars().first()
        if team is None:
            team = Team(name=team_name)
            db.add(team)
            db.flush()
            _log.info("team_created", id=str(team.id), name=team_name)
        else:
            _log.info("team_exists", id=str(team.id), name=team.name)

        admin = db.execute(select(User).where(User.email == admin_email)).scalar_one_or_none()
        if admin is None:
            admin = User(
                team_id=team.id,
                email=admin_email,
                display_name=admin_name,
                role="admin",
            )
            db.add(admin)
            db.flush()
            _log.info("admin_created", email=admin_email)
        else:
            if admin.role != "admin":
                admin.role = "admin"
                _log.info("admin_promoted", email=admin_email)
            else:
                _log.info("admin_exists", email=admin_email)

        token, _ = get_auth_provider().issue_token(db, admin.id, label="bootstrap")
        db.commit()
        return token


def main(argv: list[str] | None = None) -> int:
    configure_logging("info")
    parser = argparse.ArgumentParser(description="Bootstrap a Geshtu deployment.")
    parser.add_argument("--team", required=True, help="Team display name")
    parser.add_argument("--admin-email", required=True, help="Admin email")
    parser.add_argument("--admin-name", required=True, help="Admin display name")
    args = parser.parse_args(argv)

    token = run(args.team, args.admin_email, args.admin_name)

    print()
    print("─" * 64)
    print("Bootstrap complete.")
    print()
    print(f"Team:       {args.team}")
    print(f"Admin:      {args.admin_email}  ({args.admin_name})")
    print(f"Admin token (save it — shown ONLY once):")
    print()
    print(f"   {token}")
    print()
    print("Use this token in the Authorization header as `Bearer <token>`.")
    print("Drop it into your MCP client config, or paste into the admin UI to log in.")
    print("─" * 64)
    return 0


if __name__ == "__main__":
    sys.exit(main())
