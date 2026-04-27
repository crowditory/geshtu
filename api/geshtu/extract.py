"""Fact + decision extraction via Claude Haiku 4.5 (spec §5.1).

Returns strict JSON. Never invents rationale. Returns empty arrays
when nothing qualifies.
"""

from __future__ import annotations

import json
from dataclasses import dataclass

from anthropic import Anthropic

from geshtu.config import get_settings
from geshtu.logging import get_logger

_log = get_logger(__name__)

SYSTEM_PROMPT = """\
You are a fact-and-decision extractor for a team memory system.
Project: {project_name}.

Given the message, return strict JSON with this exact shape (no prose,
no code fences):

{{
  "facts": [{{"statement": str, "entity": str | null, "attribute": str | null}}],
  "decisions": [{{"decision": str, "rationale": str}}]
}}

Rules:
- Facts = stable claims about entities, not opinions or in-the-moment reactions.
- Decisions = explicit choices, with the rationale stated or clearly implied.
- Never invent rationale. If rationale is not present in the message, do NOT
  emit a decision.
- Return [] for either array if nothing qualifies. Return [] for both if the
  message is small-talk, a greeting, or a question with no answer.
- Statements should be self-contained — readable months later without context.
"""


@dataclass(frozen=True)
class ExtractedFact:
    statement: str
    entity: str | None
    attribute: str | None


@dataclass(frozen=True)
class ExtractedDecision:
    decision: str
    rationale: str


@dataclass(frozen=True)
class Extraction:
    facts: list[ExtractedFact]
    decisions: list[ExtractedDecision]

    @classmethod
    def empty(cls) -> "Extraction":
        return cls(facts=[], decisions=[])


def should_skip(content: str, min_chars: int) -> bool:
    """Cheap pre-filter; saves an API round-trip for trivial messages."""
    if not content:
        return True
    stripped = content.strip()
    if len(stripped) < min_chars:
        return True
    # crude small-talk detection
    lower = stripped.lower()
    GREETINGS = ("hi", "hello", "hey", "thanks", "thank you", "ok", "okay", "yes", "no")
    if lower in GREETINGS or any(lower.startswith(g + " ") for g in GREETINGS) and len(stripped) < 60:
        return True
    return False


_client: Anthropic | None = None


def _client_singleton() -> Anthropic:
    global _client
    if _client is None:
        _client = Anthropic(api_key=get_settings().anthropic_api_key)
    return _client


def extract_from_message(content: str, project_name: str) -> Extraction:
    s = get_settings()
    if should_skip(content, s.extraction_min_chars):
        return Extraction.empty()

    client = _client_singleton()
    try:
        resp = client.messages.create(
            model=s.extraction_model,
            max_tokens=1024,
            system=SYSTEM_PROMPT.format(project_name=project_name),
            messages=[{"role": "user", "content": content}],
        )
    except Exception as exc:  # noqa: BLE001
        _log.warning("extraction_api_error", error=str(exc))
        return Extraction.empty()

    text = "".join(block.text for block in resp.content if getattr(block, "type", "") == "text")
    return _parse_extraction(text)


def _parse_extraction(text: str) -> Extraction:
    if not text:
        return Extraction.empty()

    cleaned = text.strip()
    if cleaned.startswith("```"):
        # Strip ``` fences if the model added them
        cleaned = cleaned.strip("`")
        if cleaned.lower().startswith("json"):
            cleaned = cleaned[4:].strip()

    try:
        data = json.loads(cleaned)
    except json.JSONDecodeError:
        # Try to locate the first { ... } JSON object
        start = cleaned.find("{")
        end = cleaned.rfind("}")
        if start == -1 or end == -1 or end <= start:
            _log.warning("extraction_parse_error", text=cleaned[:300])
            return Extraction.empty()
        try:
            data = json.loads(cleaned[start : end + 1])
        except json.JSONDecodeError:
            _log.warning("extraction_parse_error", text=cleaned[:300])
            return Extraction.empty()

    facts_in = data.get("facts") or []
    decisions_in = data.get("decisions") or []

    facts = [
        ExtractedFact(
            statement=str(f["statement"]).strip(),
            entity=(f.get("entity") or None) and str(f["entity"]).strip(),
            attribute=(f.get("attribute") or None) and str(f["attribute"]).strip(),
        )
        for f in facts_in
        if isinstance(f, dict) and f.get("statement")
    ]
    decisions = [
        ExtractedDecision(
            decision=str(d["decision"]).strip(),
            rationale=str(d["rationale"]).strip(),
        )
        for d in decisions_in
        if isinstance(d, dict) and d.get("decision") and d.get("rationale")
    ]
    return Extraction(facts=facts, decisions=decisions)
