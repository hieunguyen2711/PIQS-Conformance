"""Field-scope: a decorator that forwards nothing is no longer recognised.

THIS FILE WAS `test_decorator_field_scope_known_defect.py`, and it pinned the WRONG behaviour on
purpose while the design question was open. It went red when the fix landed -- which is what it
was for -- and was converted rather than deleted, so the history stays legible.

THE DEFECT, AS IT WAS. `_evaluate_decorator`'s candidate loop read `w.fields` -- own fields only.
In the canonical GoF shape the abstract base declares the component reference and the concrete
decorators extend it, so a concrete decorator has no component-typed field of its own and was
**never a decorator candidate at all**. Only the base was ever judged. And D2, D3, D4 and D6 were
each an `any(...)` over the candidate list, so one compliant base carried the whole program:

    D2 1   D3 1   D4 1   D6 1      PSR 100.0   CPC 100.0   PIQS 100.0

for a `Broken` that overrides both component operations and forwards neither.

WHY IT WAS FIXED RATHER THAN DISCLOSED. Not because the score was wrong, but because of the
DIRECTION it was wrong in. The defect rewarded the abstract-base shape -- if the base forwards, no
subclass is examined. That is the textbook shape a model reproduces from memory under condition N.
Under O the model works from rule sentences and is likelier to write one flat class, which IS
examined and CAN fail. Same quality of code, higher score in the shape N produces, inflating
C1 = N - O. The defect manufactured the headline effect.

TWO CHANGES, ONE BEHAVIOUR -- either alone is wrong:

  * admission reads `_effective_fields`, so an inheriting subclass becomes a candidate;
  * D3 and D6 became `bool(decorators) and all(...)`, so every candidate must forward.

Admission alone leaves `any(...)` satisfied by the compliant base. `all(...)` alone never sees the
subclass. Measured across all four combinations in docs/STATE.md 5e: three of the four leave this
program at 100.

AND THE GUARD ON THE GUARD. `all([])` is True in Python, so without `bool(decorators)` a program
containing NO decorator scores D3 1 D6 1. That is pinned below, and it is the reason the fix is not
simply `all(...)`.
"""

from __future__ import annotations

import os
import sys

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from piqs.checker import PIQSChecker, _CRITICAL_PROPERTIES  # noqa: E402

FIXTURES = os.path.join(ROOT, "tests", "fixtures_parser")
SLUG = "decorator_subclass_forwards_nothing"


def _evaluate(path: str) -> dict:
    with open(path, encoding="utf-8") as fh:
        return PIQSChecker().evaluate("decorator", {os.path.basename(path): fh.read()})


def _fixture(slug: str) -> dict:
    return _evaluate(os.path.join(FIXTURES, slug + ".java"))


def test_a_decorator_that_forwards_nothing_is_no_longer_recognised():
    """The conversion. This asserted `D3 1 D6 1, PIQS 100` while the defect was open."""
    res = _fixture(SLUG)
    v = {r["property_id"]: r["satisfaction"] for r in res["logical_assessment"]}

    assert v == {"D2": 1, "D3": 0, "D4": 1, "D6": 0}
    assert res["breadth_calculation_psr"]["result_percent"] == 50.0
    assert res["depth_calculation_cpc"]["result_percent"] == 55.56
    assert res["final_quality_result_piqs"]["result_percent"] == 52.22
    assert not all(v[p] == 1 for p in _CRITICAL_PROPERTIES["decorator"]), "must NOT be recognised"


def test_the_subclass_is_now_a_candidate():
    """The mechanism, asserted separately from the score.

    Pinning only the number would leave the CAUSE unpinned: a change that dropped the score for
    some other reason while leaving `Broken` invisible would keep the test above green.
    """
    svc = PIQSChecker()
    with open(os.path.join(FIXTURES, SLUG + ".java"), encoding="utf-8") as fh:
        types = svc._extract_types({SLUG + ".java": fh.read()})

    components = svc._component_type_names(types)
    broken = types["Broken"]
    conformed = {c for c in components if svc._conforms_to(broken, c, types)}

    assert [f for f in broken.fields if f.field_type in conformed] == [], "still declares none"
    assert [f.field_type for f in svc._effective_fields(broken, types)
            if f.field_type in conformed] == ["Conduit"], "but inherits one, so it IS judged now"


def test_the_compliant_base_alone_does_not_carry_the_program():
    """`Base` forwards both operations perfectly. Under `any(...)` that was enough to score the
    whole program 100 regardless of what `Broken` did. Under `all(...)` it is not."""
    svc = PIQSChecker()
    with open(os.path.join(FIXTURES, SLUG + ".java"), encoding="utf-8") as fh:
        types = svc._extract_types({SLUG + ".java": fh.read()})

    base_write = next(m for m in types["Base"].methods if m.name == "write")
    broken_write = next(m for m in types["Broken"].methods if m.name == "write")

    assert svc._delegates_to_field(base_write, "inner"), "Base forwards"
    assert not svc._delegates_to_field(broken_write, "inner"), "Broken does not"


@pytest.mark.parametrize(
    "slug,why",
    [
        ("object_adapter_not_a_decorator", "conforms to Target, holds Source -- no same-C field"),
        ("super_call_base_holds_nothing", "Leaky IS a candidate; this one has a decorator"),
    ],
)
def test_a_program_with_no_decorator_scores_no_satisfied_property(slug, why):
    """THE VACUOUS-`all` GUARD. `all([])` is True in Python.

    Without `bool(decorators) and ...`, a program containing no decorator at all scores
    `D3 1 D4 1 D6 1`. Measured before the guard: `t5_object_adapter_rejected_as_decorator__FAIL`
    and `decorator_plain_inheritance_no_ref__FAIL` both go from PIQS 0 to **47.78**.

    Their LABELS survive, because recognition is `D2 AND D3` and `D2 = 0`. That is exactly why
    labels are not enough: the paper reports per-rule verdicts, and three falsely satisfied rules
    on a program with no decorator is worse than the defect being fixed.

    `super_call_base_holds_nothing` is included as the CONTRAST -- it does have a candidate, so it
    is held at `D3 0` by the strict `super` rule rather than by this guard. A test that only
    covered the empty case could pass with a checker that scores everything zero.
    """
    res = _fixture(slug)
    v = {r["property_id"]: r["satisfaction"] for r in res["logical_assessment"]}

    assert v["D3"] == 0, f"{slug}: {why}"
    assert v["D6"] == 0, f"{slug}: {why}"
    if slug == "object_adapter_not_a_decorator":
        assert v == {"D2": 0, "D3": 0, "D4": 0, "D6": 0}
        assert res["final_quality_result_piqs"]["result_percent"] == 0.0


def test_the_must_pass_jdk_decorator_survives_the_stricter_rule():
    """`decorator_filterinputstream_analogue` is a MUST-PASS battery case, and it is the one this
    commit could most easily have broken.

    `BufferedInputStream` becomes a candidate here for the first time, and it forwards with
    `super.read()` rather than `in.read()`. It stays PASS **only because F2 landed first** and
    taught `_delegates_to_field` to accept a `super` receiver through a base that holds the
    component. Without F2, `all(...)` fails on it and the MUST-PASS case flips.
    """
    path = os.path.join(ROOT, "fixtures", "mutation_battery_bdt",
                        "decorator_filterinputstream_analogue.java")
    res = _evaluate(path)
    v = {r["property_id"]: r["satisfaction"] for r in res["logical_assessment"]}

    assert v == {"D2": 1, "D3": 1, "D4": 1, "D6": 1}
    assert res["final_quality_result_piqs"]["result_percent"] == 100.0
    assert all(v[p] == 1 for p in _CRITICAL_PROPERTIES["decorator"])
