"""Pure-function tests for the extraction JSON parser. No API calls."""

from __future__ import annotations

from geshtu.extract import _parse_extraction, should_skip


def test_parses_clean_json():
    raw = '{"facts": [{"statement": "X is Y", "entity": "X", "attribute": "Y"}], "decisions": []}'
    out = _parse_extraction(raw)
    assert len(out.facts) == 1
    assert out.facts[0].statement == "X is Y"
    assert out.decisions == []


def test_parses_fenced_json():
    raw = '```json\n{"facts": [], "decisions": [{"decision": "use Postgres", "rationale": "team knows it"}]}\n```'
    out = _parse_extraction(raw)
    assert out.facts == []
    assert len(out.decisions) == 1
    assert out.decisions[0].decision == "use Postgres"


def test_recovers_from_extra_prose():
    raw = 'Sure, here you go:\n{"facts":[{"statement":"S"}],"decisions":[]}\nThat is all.'
    out = _parse_extraction(raw)
    assert len(out.facts) == 1


def test_drops_decisions_without_rationale():
    raw = '{"facts":[],"decisions":[{"decision":"use X"}]}'  # no rationale
    out = _parse_extraction(raw)
    assert out.decisions == []


def test_drops_facts_without_statement():
    raw = '{"facts":[{"entity":"X"}],"decisions":[]}'
    out = _parse_extraction(raw)
    assert out.facts == []


def test_empty_on_garbage():
    assert _parse_extraction("not json at all").facts == []
    assert _parse_extraction("").decisions == []


def test_should_skip_short():
    assert should_skip("hi", min_chars=40)
    assert should_skip("", min_chars=40)
    assert should_skip("ok thanks", min_chars=40)


def test_should_not_skip_substantive():
    msg = "We chose Postgres 16 because the team already runs it for billing."
    assert not should_skip(msg, min_chars=40)
