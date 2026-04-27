"""Async digest generator (spec §5.3).

Pulls facts, decisions, and session summaries since a timestamp, then
asks Sonnet 4.6 to format them at the requested depth. Results are
cached in the ``digests`` table for ``digest_cache_ttl_seconds``.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from anthropic import Anthropic
from sqlalchemy import select, text
from sqlalchemy.orm import Session

from geshtu.config import get_settings
from geshtu.db.models import Decision, Digest, Fact, SessionSummary, Session_
from geshtu.logging import get_logger

_log = get_logger(__name__)

DEPTHS = ("quick", "standard", "deep")

_TEMPLATE_QUICK = """\
Summarize project activity in 4 sections, in this order:
[Changed], [Decided], [Open Questions], [Next].
Keep each section to 1–3 lines. Target ~300 words total. Markdown format.
"""

_TEMPLATE_STANDARD = """\
Summarize project activity in 4 sections, in this order:
[Changed], [Decided], [Open Questions], [Next].
Include 1–2 sentences of context per item and cite source dates inline like (Apr 12).
Target ~800 words. Markdown format.
"""

_TEMPLATE_DEEP = """\
Reconstruct project activity in narrative form. Group related decisions
together, surface dropped threads and dead ends, attribute decisions to
their authors when known. Cite source dates inline. Target ~2500 words.
Markdown format.
"""

_TEMPLATES = {
    "quick": _TEMPLATE_QUICK,
    "standard": _TEMPLATE_STANDARD,
    "deep": _TEMPLATE_DEEP,
}


@dataclass
class DigestResult:
    id: uuid.UUID
    content_md: str
    fact_count: int
    decision_count: int
    cached: bool


_client: Anthropic | None = None


def _client_singleton() -> Anthropic:
    global _client
    if _client is None:
        _client = Anthropic(api_key=get_settings().anthropic_api_key)
    return _client


def _cached(
    db: Session, project_id: uuid.UUID, depth: str, since: datetime | None, ttl: int
) -> Digest | None:
    """Return a fresh-enough cached digest, or None.

    Cache key is (project, depth, since): if Monday morning everyone on the
    team asks "what's new this week" with the same `since`, only the first
    request hits Sonnet. Different `since` values get distinct cache entries
    by design — a digest "since Monday" is not interchangeable with one
    "since last Friday" even if generated 10 seconds apart.
    """
    cutoff = datetime.now(tz=timezone.utc) - timedelta(seconds=ttl)
    stmt = (
        select(Digest)
        .where(
            Digest.project_id == project_id,
            Digest.depth == depth,
            Digest.created_at >= cutoff,
        )
        .order_by(Digest.created_at.desc())
        .limit(1)
    )
    if since is None:
        stmt = stmt.where(Digest.since_timestamp.is_(None))
    else:
        stmt = stmt.where(Digest.since_timestamp == since)
    return db.execute(stmt).scalar_one_or_none()


def generate_digest(
    db: Session,
    project_id: uuid.UUID,
    project_name: str,
    since: datetime | None,
    depth: str,
    requested_by: uuid.UUID | None = None,
    use_cache: bool = True,
) -> DigestResult:
    if depth not in DEPTHS:
        raise ValueError(f"depth must be one of {DEPTHS}")

    s = get_settings()

    if use_cache:
        hit = _cached(db, project_id, depth, since, s.digest_cache_ttl_seconds)
        if hit is not None:
            return DigestResult(
                id=hit.id,
                content_md=hit.content_md,
                fact_count=hit.fact_count,
                decision_count=hit.decision_count,
                cached=True,
            )

    facts_q = select(Fact).where(Fact.project_id == project_id)
    decs_q = select(Decision).where(Decision.project_id == project_id)
    if since is not None:
        facts_q = facts_q.where(Fact.created_at >= since)
        decs_q = decs_q.where(Decision.decided_at >= since)
    # Hard ceilings keep Sonnet's input (and our bill) bounded for projects
    # that produce thousands of facts a week. Items beyond the ceiling are
    # dropped silently — if you're hitting these, narrow `since` instead.
    facts_q = facts_q.order_by(Fact.created_at.desc()).limit(500)
    decs_q = decs_q.order_by(Decision.decided_at.desc()).limit(200)

    facts = list(db.execute(facts_q).scalars())
    decisions = list(db.execute(decs_q).scalars())

    # Session summaries linked to project sessions in window
    summaries_q = (
        select(SessionSummary, Session_)
        .join(Session_, SessionSummary.session_id == Session_.id)
        .where(Session_.project_id == project_id)
    )
    if since is not None:
        summaries_q = summaries_q.where(SessionSummary.created_at >= since)
    summaries_q = summaries_q.order_by(SessionSummary.created_at.desc()).limit(50)
    summaries = list(db.execute(summaries_q).all())

    # Build the user-content payload Sonnet will summarize
    payload = _build_payload(project_name, since, facts, decisions, summaries)
    template = _TEMPLATES[depth]

    if not facts and not decisions and not summaries:
        # Skip the LLM call when there's literally nothing to summarize.
        # Cached so a project with no activity doesn't keep generating empty
        # digests on every request.
        content_md = (
            f"# {project_name} — digest\n\n"
            f"_No activity recorded since {since.isoformat() if since else 'project start'}._\n"
        )
    else:
        content_md = _call_sonnet(template, payload)

    digest = Digest(
        project_id=project_id,
        requested_by=requested_by,
        since_timestamp=since,
        depth=depth,
        content_md=content_md,
        fact_count=len(facts),
        decision_count=len(decisions),
    )
    db.add(digest)
    db.flush()

    return DigestResult(
        id=digest.id,
        content_md=content_md,
        fact_count=len(facts),
        decision_count=len(decisions),
        cached=False,
    )


def _build_payload(
    project_name: str,
    since: datetime | None,
    facts: list[Fact],
    decisions: list[Decision],
    summaries: list,
) -> str:
    lines: list[str] = []
    since_s = since.isoformat() if since else "project start"
    lines.append(f"Project: {project_name}")
    lines.append(f"Window: since {since_s}")
    lines.append(f"Counts: {len(facts)} facts, {len(decisions)} decisions, {len(summaries)} summaries")
    lines.append("")

    if facts:
        lines.append("## Facts (most recent first)")
        for f in facts:
            stat = "active" if f.valid_until is None else "superseded"
            date = f.created_at.date().isoformat()
            ent = f" [{f.entity}]" if f.entity else ""
            lines.append(f"- ({date}, {stat}){ent} {f.statement}")
        lines.append("")

    if decisions:
        lines.append("## Decisions (most recent first)")
        for d in decisions:
            date = d.decided_at.date().isoformat()
            lines.append(f"- ({date}, {d.status}) DECISION: {d.decision}")
            lines.append(f"  RATIONALE: {d.rationale}")
        lines.append("")

    if summaries:
        lines.append("## Session summaries (most recent first)")
        for ss, sess in summaries:
            date = ss.created_at.date().isoformat()
            lines.append(f"### Session {sess.title or sess.id} ({date})")
            lines.append(ss.summary_md)
            if ss.open_questions:
                lines.append("Open questions: " + "; ".join(ss.open_questions))
            if ss.next_actions:
                lines.append("Next actions: " + "; ".join(ss.next_actions))
            lines.append("")

    return "\n".join(lines)


class DigestGenerationError(RuntimeError):
    """Sonnet was unreachable / errored. Caller decides how to surface it."""


def _call_sonnet(template: str, payload: str) -> str:
    # Errors propagate so the route returns 5xx and the digest is NOT cached.
    # Caching a failure would persist it for an hour; better to fail loudly.
    s = get_settings()
    client = _client_singleton()
    try:
        resp = client.messages.create(
            model=s.digest_model,
            max_tokens=4096,
            system=template,
            messages=[{"role": "user", "content": payload}],
        )
    except Exception as exc:  # noqa: BLE001
        _log.warning("digest_api_error", error=str(exc))
        raise DigestGenerationError(str(exc)) from exc

    return "".join(b.text for b in resp.content if getattr(b, "type", "") == "text")


# Convenience used by the worker for session summaries
def summarize_session(db: Session, session_id: uuid.UUID) -> str | None:
    """Generate a markdown summary from raw messages of a session."""
    rows = db.execute(
        text(
            """
            SELECT role, content, created_at
            FROM messages
            WHERE session_id = :sid
            ORDER BY created_at ASC
            """
        ),
        {"sid": str(session_id)},
    ).all()
    if not rows:
        return None

    transcript = "\n\n".join(f"[{r.role}] {r.content}" for r in rows)
    s = get_settings()
    client = _client_singleton()
    try:
        resp = client.messages.create(
            model=s.digest_model,
            max_tokens=1024,
            system=(
                "Summarize this session as terse markdown. Sections: "
                "[Summary] (3-6 lines), [Open Questions] (bullets), "
                "[Next Actions] (bullets). No preamble."
            ),
            messages=[{"role": "user", "content": transcript[:60000]}],
        )
    except Exception as exc:  # noqa: BLE001
        _log.warning("session_summary_api_error", error=str(exc))
        return None
    return "".join(b.text for b in resp.content if getattr(b, "type", "") == "text")
