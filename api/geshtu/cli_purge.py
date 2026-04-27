"""Cascade-delete a user's sessions/messages and detach attribution from their
facts/decisions. GDPR Article 17 (right to deletion).
"""

from __future__ import annotations

import argparse
import sys

from sqlalchemy import update
from sqlalchemy import delete as sqldelete
from sqlalchemy import select

from geshtu.db.models import Decision, Fact, Session_, User
from geshtu.db.session import SessionLocal
from geshtu.logging import configure_logging, get_logger

_log = get_logger(__name__)


def main(argv: list[str] | None = None) -> int:
    configure_logging("info")
    parser = argparse.ArgumentParser(description="GDPR purge for a user.")
    parser.add_argument("--user", required=True, help="Email of the user to purge")
    parser.add_argument(
        "--confirm",
        action="store_true",
        help="Required: this is irreversible.",
    )
    args = parser.parse_args(argv)

    if not args.confirm:
        print("This is irreversible. Re-run with --confirm to proceed.", file=sys.stderr)
        return 2

    with SessionLocal() as db:
        user = db.execute(select(User).where(User.email == args.user)).scalar_one_or_none()
        if user is None:
            print(f"Unknown user: {args.user}", file=sys.stderr)
            return 1

        # GDPR Article 17 lets us choose between deletion and anonymization
        # when the data is collectively held. We anonymize: facts/decisions
        # belong to the team, not the individual. Stripping `created_by` /
        # `decided_by` removes the personal link while preserving the team's
        # memory — the deletion right is satisfied because the user is no
        # longer identifiable from the remaining record.
        db.execute(update(Fact).where(Fact.created_by == user.id).values(created_by=None))
        db.execute(update(Decision).where(Decision.decided_by == user.id).values(decided_by=None))

        # Delete all sessions owned by this user (cascades to messages).
        db.execute(sqldelete(Session_).where(Session_.user_id == user.id))

        # Finally delete the user (cascades tokens).
        db.execute(sqldelete(User).where(User.id == user.id))

        db.commit()
        _log.info("user_purged", email=args.user)

    return 0


if __name__ == "__main__":
    sys.exit(main())
