"""Hybrid search via Reciprocal Rank Fusion (spec §5.2).

A single SQL combines pgvector cosine and pg_trgm similarity, then
fuses the two ranked lists with RRF. Returns top-k facts.

Why RRF and not weighted-sum? Vector cosine and trigram similarity live on
incomparable scales — a 0.85 cosine doesn't mean "more relevant" than a
0.50 trigram. RRF normalizes by collapsing each list to its rank order,
which is invariant to those scales. The constant 60 is the canonical RRF
parameter from the original Cormack/Clarke/Buettcher paper; it's almost
never worth tuning. Only the relative ranks within each list matter.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime

from sqlalchemy import text
from sqlalchemy.orm import Session

from geshtu.embed import embed


@dataclass(frozen=True)
class SearchedFact:
    id: uuid.UUID
    statement: str
    entity: str | None
    attribute: str | None
    score: float
    valid_from: datetime
    confidence: float


_HYBRID_SQL = text(
    """
WITH vec AS (
    SELECT id, statement, entity, attribute, valid_from, confidence,
           1 - (embedding <=> CAST(:query_vec AS vector)) AS score
    FROM facts
    WHERE project_id = :project_id
      AND valid_until IS NULL
      AND embedding IS NOT NULL
    ORDER BY embedding <=> CAST(:query_vec AS vector)
    LIMIT 30
),
kw AS (
    SELECT id, statement, entity, attribute, valid_from, confidence,
           similarity(statement, :query_text) AS score
    FROM facts
    WHERE project_id = :project_id
      AND valid_until IS NULL
      AND statement % :query_text
    ORDER BY similarity(statement, :query_text) DESC
    LIMIT 30
),
unioned AS (
    SELECT id, statement, entity, attribute, valid_from, confidence, score, 'vec' AS src FROM vec
    UNION ALL
    SELECT id, statement, entity, attribute, valid_from, confidence, score, 'kw'  AS src FROM kw
),
ranked AS (
    SELECT id, statement, entity, attribute, valid_from, confidence, src,
           ROW_NUMBER() OVER (PARTITION BY src ORDER BY score DESC) AS rank
    FROM unioned
)
SELECT id, statement, entity, attribute, valid_from, confidence,
       SUM(1.0 / (60 + rank))::float AS rrf_score
FROM ranked
GROUP BY id, statement, entity, attribute, valid_from, confidence
ORDER BY rrf_score DESC
LIMIT :k;
"""
)


def search_facts(
    db: Session,
    project_id: uuid.UUID,
    query: str,
    k: int = 10,
) -> list[SearchedFact]:
    if not query.strip():
        return []
    qvec = embed(query)
    rows = db.execute(
        _HYBRID_SQL,
        {
            "project_id": str(project_id),
            "query_vec": qvec,
            "query_text": query,
            "k": k,
        },
    ).all()
    return [
        SearchedFact(
            id=r.id,
            statement=r.statement,
            entity=r.entity,
            attribute=r.attribute,
            score=float(r.rrf_score),
            valid_from=r.valid_from,
            confidence=float(r.confidence),
        )
        for r in rows
    ]


_DECISION_HYBRID_SQL = text(
    """
WITH vec AS (
    SELECT id, decision, rationale, decided_at, status,
           1 - (embedding <=> CAST(:query_vec AS vector)) AS score
    FROM decisions
    WHERE project_id = :project_id
      AND embedding IS NOT NULL
      AND status = 'active'
    ORDER BY embedding <=> CAST(:query_vec AS vector)
    LIMIT 30
),
kw AS (
    SELECT id, decision, rationale, decided_at, status,
           similarity(decision, :query_text) AS score
    FROM decisions
    WHERE project_id = :project_id
      AND status = 'active'
      AND decision % :query_text
    ORDER BY similarity(decision, :query_text) DESC
    LIMIT 30
),
unioned AS (
    SELECT id, decision, rationale, decided_at, status, score, 'vec' AS src FROM vec
    UNION ALL
    SELECT id, decision, rationale, decided_at, status, score, 'kw'  AS src FROM kw
),
ranked AS (
    SELECT id, decision, rationale, decided_at, status, src,
           ROW_NUMBER() OVER (PARTITION BY src ORDER BY score DESC) AS rank
    FROM unioned
)
SELECT id, decision, rationale, decided_at, status,
       SUM(1.0 / (60 + rank))::float AS rrf_score
FROM ranked
GROUP BY id, decision, rationale, decided_at, status
ORDER BY rrf_score DESC
LIMIT :k;
"""
)


@dataclass(frozen=True)
class SearchedDecision:
    id: uuid.UUID
    decision: str
    rationale: str
    decided_at: datetime
    status: str
    score: float


def search_decisions(
    db: Session,
    project_id: uuid.UUID,
    query: str,
    k: int = 10,
) -> list[SearchedDecision]:
    if not query.strip():
        return []
    qvec = embed(query)
    rows = db.execute(
        _DECISION_HYBRID_SQL,
        {
            "project_id": str(project_id),
            "query_vec": qvec,
            "query_text": query,
            "k": k,
        },
    ).all()
    return [
        SearchedDecision(
            id=r.id,
            decision=r.decision,
            rationale=r.rationale,
            decided_at=r.decided_at,
            status=r.status,
            score=float(r.rrf_score),
        )
        for r in rows
    ]
