"""Golden-set extraction test (spec §9). Skipped unless RUN_GOLDEN=1
is set, since it costs Anthropic API credits.

Asserts ≥80% match: each example's facts/decisions counts must satisfy
the lower bounds declared in golden_extraction.json.
"""

from __future__ import annotations

import json
import os
from pathlib import Path

import pytest

from geshtu.extract import extract_from_message

GOLDEN = Path(__file__).parent / "golden_extraction.json"


@pytest.mark.skipif(
    os.environ.get("RUN_GOLDEN") != "1",
    reason="set RUN_GOLDEN=1 to spend API credits on the golden test",
)
def test_extraction_golden_set():
    cases = json.loads(GOLDEN.read_text(encoding="utf-8"))
    passed = 0
    for c in cases:
        out = extract_from_message(c["input"], project_name="Test")
        ok_f = len(out.facts) >= c["expect_facts_min"]
        ok_d = len(out.decisions) >= c["expect_decisions_min"]
        if ok_f and ok_d:
            passed += 1
        else:
            print(
                f"  miss[{c['name']}] facts={len(out.facts)}/{c['expect_facts_min']} "
                f"decs={len(out.decisions)}/{c['expect_decisions_min']}"
            )
    assert passed / len(cases) >= 0.8, f"only {passed}/{len(cases)} golden cases passed"
