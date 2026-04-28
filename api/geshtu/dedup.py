"""Fact dedup: UPDATE / REFINE / ADD (spec §5.1).

Cosine ≥ 0.92 → supersede the closest active fact.
Cosine 0.75–0.92 → refine (insert + link via ``refines``).
Cosine < 0.75 → pure insert.

Decisions are never deduped; their context is unique by construction.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import UTC, datetime

from sqlalchemy import text
from sqlalchemy.orm import Session

from geshtu.config import get_settings
from geshtu.db.models import Fact


@dataclass(frozen=True)
class DedupOutcome:
    fact_id: uuid.UUID
    status: str  # 'logged' | 'updated' | 'duplicate'
    superseded_id: uuid.UUID | None = None
    refines_id: uuid.UUID | None = None


_NEAREST_ACTIVE_SQL = text(
    """
SELECT id, 1 - (embedding <=> CAST(:vec AS vector)) AS sim
FROM facts
WHERE project_id = :project_id
  AND valid_until IS NULL
  AND embedding IS NOT NULL
ORDER BY embedding <=> CAST(:vec AS vector)
LIMIT 1;
"""
)


def upsert_fact(
    db: Session,
    *,
    project_id: uuid.UUID,
    statement: str,
    embedding: list[float],
    entity: str | None = None,
    attribute: str | None = None,
    source_session_id: uuid.UUID | None = None,
    source_message_id: uuid.UUID | None = None,
    created_by: uuid.UUID | None = None,
    confidence: float = 1.0,
) -> DedupOutcome:
    """Insert a fact with dedup rules. Caller commits."""
    s = get_settings()

    nearest = db.execute(
        _NEAREST_ACTIVE_SQL,
        {"project_id": str(project_id), "vec": embedding},
    ).first()

    superseded_id: uuid.UUID | None = None
    refines_id: uuid.UUID | None = None
    sim = float(nearest.sim) if nearest is not None else 0.0

    # Three-way decision (spec §5.1). Note we use cosine SIMILARITY here
    # (1 − cosine distance), so higher = more similar.
    #   ≥ 0.92  → near-identical claim, mark old as superseded
    #   0.75 ≤ … < 0.92 → related but distinct, link via `refines`
    #   < 0.75  → independent, plain insert
    if nearest is not None and sim >= s.dedup_supersede_threshold:
        old_id = nearest.id
        now = datetime.now(tz=UTC)
        # The `valid_until IS NULL` guard prevents a race where two workers
        # try to supersede the same fact concurrently — only one wins.
        db.execute(
            text("UPDATE facts SET valid_until = :now WHERE id = :id AND valid_until IS NULL"),
            {"now": now, "id": str(old_id)},
        )
        superseded_id = old_id
    elif nearest is not None and sim >= s.dedup_refine_threshold:
        refines_id = nearest.id

    new_fact = Fact(
        project_id=project_id,
        statement=statement,
        entity=entity,
        attribute=attribute,
        embedding=embedding,
        confidence=confidence,
        source_session_id=source_session_id,
        source_message_id=source_message_id,
        created_by=created_by,
        refines=refines_id,
    )
    db.add(new_fact)
    # flush() so the new fact has an ID we can reference from the old row.
    db.flush()

    if superseded_id is not None:
        db.execute(
            text("UPDATE facts SET superseded_by = :new WHERE id = :old"),
            {"new": str(new_fact.id), "old": str(superseded_id)},
        )
        status = "updated"
    elif refines_id is not None:
        status = "logged"
    else:
        status = "logged"

    return DedupOutcome(
        fact_id=new_fact.id,
        status=status,
        superseded_id=superseded_id,
        refines_id=refines_id,
    )
