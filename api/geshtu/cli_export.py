"""Export a user's or project's data as JSON. GDPR Article 15 + anti-lock-in."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from geshtu.db.models import Decision, Fact, Message, Project, Session_, SessionSummary, User
from geshtu.db.session import SessionLocal


def _serialize(o: Any) -> Any:
    if isinstance(o, datetime):
        return o.isoformat()
    if hasattr(o, "hex"):  # UUID
        return str(o)
    raise TypeError(type(o))


def export_user(db: Session, email: str) -> dict:
    user = db.execute(select(User).where(User.email == email)).scalar_one_or_none()
    if user is None:
        raise SystemExit(f"unknown user: {email}")

    sessions = list(db.execute(select(Session_).where(Session_.user_id == user.id)).scalars())
    msgs: list[Message] = []
    for s in sessions:
        msgs.extend(db.execute(select(Message).where(Message.session_id == s.id)).scalars())

    facts = list(db.execute(select(Fact).where(Fact.created_by == user.id)).scalars())
    decs = list(db.execute(select(Decision).where(Decision.decided_by == user.id)).scalars())

    return {
        "user": {
            "id": user.id,
            "email": user.email,
            "display_name": user.display_name,
            "role": user.role,
            "created_at": user.created_at,
        },
        "sessions": [
            {"id": s.id, "project_id": s.project_id, "title": s.title, "started_at": s.started_at}
            for s in sessions
        ],
        "messages": [
            {
                "id": m.id,
                "session_id": m.session_id,
                "role": m.role,
                "content": m.content,
                "created_at": m.created_at,
            }
            for m in msgs
        ],
        "facts": [
            {"id": f.id, "project_id": f.project_id, "statement": f.statement, "valid_from": f.valid_from}
            for f in facts
        ],
        "decisions": [
            {
                "id": d.id,
                "project_id": d.project_id,
                "decision": d.decision,
                "rationale": d.rationale,
                "decided_at": d.decided_at,
            }
            for d in decs
        ],
    }


def export_project(db: Session, slug: str) -> dict:
    project = db.execute(select(Project).where(Project.slug == slug)).scalar_one_or_none()
    if project is None:
        raise SystemExit(f"unknown project: {slug}")

    facts = list(db.execute(select(Fact).where(Fact.project_id == project.id)).scalars())
    decs = list(db.execute(select(Decision).where(Decision.project_id == project.id)).scalars())
    sessions = list(
        db.execute(select(Session_).where(Session_.project_id == project.id)).scalars()
    )
    summaries = list(
        db.execute(
            select(SessionSummary).where(
                SessionSummary.session_id.in_([s.id for s in sessions])
            )
        ).scalars()
    )

    return {
        "project": {"id": project.id, "slug": project.slug, "name": project.name},
        "facts": [
            {
                "id": f.id,
                "statement": f.statement,
                "entity": f.entity,
                "attribute": f.attribute,
                "valid_from": f.valid_from,
                "valid_until": f.valid_until,
                "confidence": f.confidence,
            }
            for f in facts
        ],
        "decisions": [
            {
                "id": d.id,
                "decision": d.decision,
                "rationale": d.rationale,
                "decided_at": d.decided_at,
                "status": d.status,
            }
            for d in decs
        ],
        "session_summaries": [
            {
                "id": s.id,
                "session_id": s.session_id,
                "summary_md": s.summary_md,
                "open_questions": s.open_questions,
                "next_actions": s.next_actions,
            }
            for s in summaries
        ],
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Export Geshtu data as JSON.")
    grp = parser.add_mutually_exclusive_group(required=True)
    grp.add_argument("--user", help="Export everything attributed to this user (email)")
    grp.add_argument("--project", help="Export everything in this project (slug)")
    args = parser.parse_args(argv)

    with SessionLocal() as db:
        if args.user:
            data = export_user(db, args.user)
        else:
            data = export_project(db, args.project)
    json.dump(data, sys.stdout, default=_serialize, indent=2, ensure_ascii=False)
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
