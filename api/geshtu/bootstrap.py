"""First-run CLI: create the team row, create the admin user, print a token.

Idempotent on team + user, but always issues a NEW token. Rationale: the
original token is bcrypt-hashed in the DB, so we cannot recover it if the
admin lost it. Re-running bootstrap is the supported recovery path. Old
tokens remain valid (revoke them via the admin UI if needed).
"""

from __future__ import annotations

import argparse
import sys
from dataclasses import dataclass

from sqlalchemy import select

from geshtu.auth import get_auth_provider
from geshtu.db.models import Project, Team, User
from geshtu.db.session import SessionLocal
from geshtu.logging import configure_logging, get_logger

_log = get_logger(__name__)


@dataclass
class BootstrapResult:
    admin_token: str
    project_token: str | None
    project_slug: str | None


def run(
    team_name: str,
    admin_email: str,
    admin_name: str,
    project_slug: str | None = None,
    project_name: str | None = None,
) -> BootstrapResult:
    """Idempotent on team + admin user. Always issues a fresh admin token.

    If ``project_slug`` and ``project_name`` are both provided, also creates
    that project (idempotent on slug) and issues a project-scoped admin
    token — that pair is what the operator actually wants to paste into
    their Claude Desktop config most of the time.
    """
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

        admin_token, _ = get_auth_provider().issue_token(db, admin.id, label="bootstrap")

        proj_token: str | None = None
        proj_slug: str | None = None
        if project_slug and project_name:
            project = db.execute(
                select(Project).where(Project.slug == project_slug)
            ).scalar_one_or_none()
            if project is None:
                project = Project(team_id=team.id, slug=project_slug, name=project_name)
                db.add(project)
                db.flush()
                _log.info("project_created", slug=project_slug)
            else:
                _log.info("project_exists", slug=project_slug)
            proj_token, _ = get_auth_provider().issue_token(
                db, admin.id, label=f"{project_slug}-bootstrap", project_id=project.id
            )
            proj_slug = project.slug

        db.commit()
        return BootstrapResult(
            admin_token=admin_token,
            project_token=proj_token,
            project_slug=proj_slug,
        )


def main(argv: list[str] | None = None) -> int:
    configure_logging("info")
    parser = argparse.ArgumentParser(description="Bootstrap a Geshtu deployment.")
    parser.add_argument("--team", required=True, help="Team display name")
    parser.add_argument("--admin-email", required=True, help="Admin email")
    parser.add_argument("--admin-name", required=True, help="Admin display name")
    parser.add_argument(
        "--project-slug",
        help="Optional: also create a first project with this slug",
    )
    parser.add_argument(
        "--project-name",
        help="Optional: display name for the first project (required if --project-slug)",
    )
    args = parser.parse_args(argv)

    if args.project_slug and not args.project_name:
        parser.error("--project-name is required when --project-slug is given")

    res = run(
        args.team,
        args.admin_email,
        args.admin_name,
        project_slug=args.project_slug,
        project_name=args.project_name,
    )

    bar = "─" * 64
    print()
    print(bar)
    print("Bootstrap complete.")
    print()
    print(f"Team:       {args.team}")
    print(f"Admin:      {args.admin_email}  ({args.admin_name})")
    print()
    print("Admin token — full access, all projects (save it; shown only once):")
    print(f"   {res.admin_token}")
    if res.project_token:
        print()
        print(f"Project-scoped token for '{res.project_slug}' — recommended for")
        print("daily use; paste this into your MCP client:")
        print(f"   {res.project_token}")
    print()
    print("Use as `Authorization: Bearer <token>` or paste into the admin UI to log in.")
    print(bar)
    return 0


if __name__ == "__main__":
    sys.exit(main())
