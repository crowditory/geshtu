"""Celery task definitions. Registered via geshtu.celery_app's include=...

Tasks intentionally take only primitive args (UUIDs as strings) so they
serialize cleanly. All DB work happens inside the task body.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta

from sqlalchemy import select, text

from geshtu.celery_app import app
from geshtu.config import get_settings
from geshtu.db.models import Decision, Message, Project, Session_
from geshtu.db.session import SessionLocal
from geshtu.dedup import upsert_fact
from geshtu.embed import embed
from geshtu.extract import extract_from_message
from geshtu.logging import get_logger
from geshtu.routes.common import log_access

_log = get_logger(__name__)


@app.task(name="geshtu.extract_message", bind=True, max_retries=3, default_retry_delay=10)
def extract_message_task(self, message_id: str, project_id: str) -> dict:
    """Run the spec §5.1 write-path pipeline for one message.

    Retries on transient Anthropic / network failures (extract_from_message
    propagates them). After ``max_retries`` exhausts, Celery delivers the
    task to the dead-letter queue; the message itself is already saved, so
    extraction can be re-triggered later by republishing the job.
    """
    msg_id = uuid.UUID(message_id)
    proj_id = uuid.UUID(project_id)

    with SessionLocal() as db:
        msg = db.get(Message, msg_id)
        if msg is None:
            _log.warning("extract_message_skipped_missing", message_id=str(msg_id))
            return {"status": "missing"}

        project = db.get(Project, proj_id)
        if project is None:
            _log.warning("extract_message_skipped_no_project", project_id=str(proj_id))
            return {"status": "no_project"}

        sess = db.get(Session_, msg.session_id)
        try:
            extraction = extract_from_message(msg.content, project.name)
        except Exception as exc:  # noqa: BLE001
            _log.warning("extraction_retry", error=str(exc), attempt=self.request.retries)
            raise self.retry(exc=exc) from exc

        new_facts: list[dict] = []
        for f in extraction.facts:
            try:
                vec = embed(f.statement)
            except Exception as exc:  # noqa: BLE001
                _log.warning("embed_failed_skip_fact", error=str(exc))
                continue
            out = upsert_fact(
                db,
                project_id=proj_id,
                statement=f.statement,
                entity=f.entity,
                attribute=f.attribute,
                embedding=vec,
                source_session_id=msg.session_id,
                source_message_id=msg.id,
                created_by=sess.user_id if sess else None,
            )
            new_facts.append({"id": str(out.fact_id), "status": out.status})

        new_decs: list[str] = []
        for d in extraction.decisions:
            try:
                # Embed decision + rationale together: when the AI later
                # searches for "why did we pick X", a query that mentions
                # the rationale should also surface the matching decision.
                dvec = embed(f"{d.decision}\n\n{d.rationale}")
            except Exception:  # noqa: BLE001
                dvec = None
            dec = Decision(
                project_id=proj_id,
                decision=d.decision,
                rationale=d.rationale,
                embedding=dvec,
                decided_by=sess.user_id if sess else None,
                source_session_id=msg.session_id,
                source_message_id=msg.id,
            )
            db.add(dec)
            db.flush()
            new_decs.append(str(dec.id))

        log_access(
            db,
            user_id=sess.user_id if sess else None,
            operation="extraction",
            project_id=proj_id,
            payload={
                "message_id": str(msg_id),
                "facts": len(new_facts),
                "decisions": len(new_decs),
            },
        )
        db.commit()

    return {"status": "ok", "facts": new_facts, "decisions": new_decs}


@app.task(name="geshtu.summarize_session")
def summarize_session_task(session_id: str) -> dict:
    """Generate or refresh a session_summaries row from raw messages."""
    from geshtu.digest import summarize_session

    sid = uuid.UUID(session_id)
    with SessionLocal() as db:
        sess = db.get(Session_, sid)
        if sess is None:
            return {"status": "missing"}
        text_md = summarize_session(db, sid)
        if not text_md:
            return {"status": "empty"}
        from geshtu.db.models import SessionSummary

        existing = db.execute(
            select(SessionSummary).where(SessionSummary.session_id == sid)
        ).scalar_one_or_none()
        if existing is None:
            db.add(SessionSummary(session_id=sid, summary_md=text_md))
        else:
            existing.summary_md = text_md
        db.commit()
        return {"status": "ok", "session_id": session_id}


@app.task(name="geshtu.retention_sweep")
def retention_sweep_task() -> dict:
    """Zero message bodies older than ``MESSAGES_RETENTION_DAYS`` (spec §18.2).

    Why zero, not DELETE? Facts and decisions have FK references to messages
    via `source_message_id` for audit. We keep the row + ID intact so those
    citations don't break, and only erase the high-sensitivity column
    (`content`). The fact statement remains, but it's already paraphrased
    by the extraction step, not the raw message verbatim.
    """
    s = get_settings()
    if s.messages_retention_days <= 0:
        return {"status": "disabled"}

    cutoff = datetime.now(tz=UTC) - timedelta(days=s.messages_retention_days)
    with SessionLocal() as db:  # type: Session
        result = db.execute(
            text(
                """
                UPDATE messages
                SET content = ''
                WHERE created_at < :cutoff AND content <> ''
                """
            ),
            {"cutoff": cutoff},
        )
        db.commit()
        return {"status": "ok", "rows": result.rowcount, "cutoff": cutoff.isoformat()}
