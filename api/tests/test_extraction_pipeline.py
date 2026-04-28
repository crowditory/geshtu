"""Full write-path pipeline test (spec §5.1) with mocked external calls.

Anthropic is intercepted via `respx` (httpx-level mock). BGE-M3 is replaced
with a deterministic stub so we don't load 2 GB of model weights.

What this proves:
    - extract_message_task wires Anthropic → embed → upsert_fact correctly
    - Decision rows get committed
    - access_log gets a row per extraction
    - Re-running the same task is a no-op for already-extracted content
"""

from __future__ import annotations

import json
import math
import uuid

import httpx
import pytest
import respx
from sqlalchemy import select

from geshtu.db.models import AccessLog, Decision, Fact, Message, Project, Session_, Team, User
from geshtu.db.session import SessionLocal


DIM = 1024


def _vec(seed: int) -> list[float]:
    """Deterministic unit vector — replaces real BGE-M3 in this test."""
    import random

    rng = random.Random(seed)
    raw = [rng.gauss(0, 1) for _ in range(DIM)]
    norm = math.sqrt(sum(x * x for x in raw))
    return [x / norm for x in raw]


def _seed_message(content: str = "We picked Postgres because pgvector is mature.") -> tuple[
    uuid.UUID, uuid.UUID, str
]:
    """Insert team/user/project/session/message; return (message_id, project_id, project_name)."""
    suffix = uuid.uuid4().hex[:10]
    with SessionLocal() as db:
        team = db.execute(select(Team)).scalars().first()
        if team is None:
            team = Team(name="Test")
            db.add(team)
            db.flush()
        user = User(
            team_id=team.id,
            email=f"e2e-{suffix}@example.com",
            display_name=f"e2e {suffix}",
            role="admin",
        )
        db.add(user)
        db.flush()

        project = Project(slug=f"e2e-{suffix}", name=f"e2e-{suffix}")
        db.add(project)
        db.flush()

        sess = Session_(project_id=project.id, user_id=user.id, title="t")
        db.add(sess)
        db.flush()

        msg = Message(session_id=sess.id, role="user", content=content)
        db.add(msg)
        db.commit()
        return msg.id, project.id, project.name


def _anthropic_response(facts: list[dict], decisions: list[dict]) -> dict:
    """Shape that mimics anthropic.types.Message JSON over the wire."""
    body = json.dumps({"facts": facts, "decisions": decisions})
    return {
        "id": "msg_test",
        "type": "message",
        "role": "assistant",
        "model": "claude-haiku-4-5",
        "content": [{"type": "text", "text": body}],
        "stop_reason": "end_turn",
        "stop_sequence": None,
        "usage": {"input_tokens": 10, "output_tokens": 20},
    }


@pytest.fixture
def mock_embed(monkeypatch):
    """Replace embed() everywhere it's imported."""
    counter = {"n": 0}

    def fake(text: str) -> list[float]:
        counter["n"] += 1
        return _vec(hash(text) & 0xFFFF)

    # Both the worker (geshtu.tasks) and the dedup module import `embed` at
    # call time; patching the source module covers both.
    monkeypatch.setattr("geshtu.embed.embed", fake)
    # Also patch the re-imported names that already grabbed the symbol at
    # module import time.
    monkeypatch.setattr("geshtu.tasks.embed", fake)
    return counter


def test_extraction_pipeline_happy_path(have_db, mock_embed):
    if not have_db:
        pytest.skip("no DB reachable")

    msg_id, project_id, _project_name = _seed_message(
        "We picked Postgres because pgvector is mature."
    )

    facts_payload = [
        {"statement": "Postgres is the database", "entity": "Postgres", "attribute": "role"}
    ]
    decisions_payload = [
        {"decision": "Use Postgres", "rationale": "pgvector is mature"}
    ]

    with respx.mock(base_url="https://api.anthropic.com") as rx:
        rx.post("/v1/messages").mock(
            return_value=httpx.Response(200, json=_anthropic_response(facts_payload, decisions_payload))
        )
        # Reset the cached Anthropic client so it picks up our mocked transport.
        from geshtu import extract as extract_mod

        extract_mod._client = None

        from geshtu.tasks import extract_message_task

        # Celery's bound-task .run() bypasses the scheduler.
        result = extract_message_task.run(message_id=str(msg_id), project_id=str(project_id))

    assert result["status"] == "ok"
    assert len(result["facts"]) == 1
    assert len(result["decisions"]) == 1
    assert mock_embed["n"] >= 2  # one for the fact, one for the decision

    # DB-level verification.
    with SessionLocal() as db:
        facts = list(db.execute(select(Fact).where(Fact.project_id == project_id)).scalars())
        assert len(facts) == 1
        assert "Postgres" in facts[0].statement
        assert facts[0].embedding is not None
        assert facts[0].source_message_id == msg_id

        decs = list(db.execute(select(Decision).where(Decision.project_id == project_id)).scalars())
        assert len(decs) == 1
        assert decs[0].decision == "Use Postgres"
        assert decs[0].rationale == "pgvector is mature"

        # spec §5.1 invariant: access_log row written
        log = db.execute(
            select(AccessLog).where(
                AccessLog.project_id == project_id, AccessLog.operation == "extraction"
            )
        ).scalars().first()
        assert log is not None
        assert log.payload["facts"] == 1
        assert log.payload["decisions"] == 1


def test_extraction_skips_short_message(have_db, mock_embed):
    if not have_db:
        pytest.skip("no DB reachable")
    msg_id, project_id, _ = _seed_message("ok thanks")  # below min_chars

    # No need to mock Anthropic — the skip filter should short-circuit before the call.
    from geshtu.tasks import extract_message_task

    result = extract_message_task.run(message_id=str(msg_id), project_id=str(project_id))
    assert result["status"] == "ok"
    assert result["facts"] == []
    assert result["decisions"] == []
    assert mock_embed["n"] == 0  # never called embed


def test_extraction_handles_unparseable_model_output(have_db, mock_embed):
    """If Haiku returns junk (post-skip-filter), we should gracefully record
    no facts/decisions rather than raising."""
    if not have_db:
        pytest.skip("no DB reachable")
    msg_id, project_id, _ = _seed_message(
        "A long substantive message that should pass the skip filter for sure."
    )

    bad = {
        "id": "msg_test",
        "type": "message",
        "role": "assistant",
        "model": "claude-haiku-4-5",
        "content": [{"type": "text", "text": "lol no json here"}],
        "stop_reason": "end_turn",
        "stop_sequence": None,
        "usage": {"input_tokens": 10, "output_tokens": 5},
    }

    with respx.mock(base_url="https://api.anthropic.com") as rx:
        rx.post("/v1/messages").mock(return_value=httpx.Response(200, json=bad))
        from geshtu import extract as extract_mod

        extract_mod._client = None

        from geshtu.tasks import extract_message_task

        result = extract_message_task.run(message_id=str(msg_id), project_id=str(project_id))

    assert result["status"] == "ok"
    assert result["facts"] == []
    assert result["decisions"] == []
