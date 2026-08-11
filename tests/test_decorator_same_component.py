"""isDecorator requires the SAME component: W conforms to C AND holds a field of type C.

WHAT WAS WRONG.

`_evaluate_decorator`'s docstring has always said:

    isDecorator(W) -- a class that conforms to a component C AND holds a field of type C.

Same C twice. The code computed two INDEPENDENT sets -- every component W conforms to, and
every component-typed field W holds -- and never required them to intersect. So a textbook
object adapter, which conforms to one abstract type and holds a DIFFERENT one, was recognised
as a Decorator: D2 and D3 are the critical set and both held.

WHY THIS IS A PROPERTY REDEFINITION AND NOT A BUG FIX.

By the rule in PROPERTY_SPEC.md ("does a divergence REDEFINE the predicate, or REMOVE A FALSE
POSITIVE?"), this changes WHICH PROGRAMS SATISFY D2 -- so it is its own separately-measured
change with its own prediction, not something that rides along with other work.

WHY IT BLOCKED THE EXPERIMENT AND NOT JUST THE CHECKER.

Conflict pair F is Adapter/Decorator. Its separator was supposed to be "one type comparison",
which D4 already encodes ("transparent enhancement -- no interface conversion"). But D4 is
weight 2 and NON-CRITICAL, so it cannot decide recognition. Every output for pair F would have
satisfied both rule sets, which makes the pair invalid by the experiment's own design.

That generalises, and the general form is now a rule in PROPERTY_SPEC.md:

    A property that distinguishes one pattern from another must be load-bearing for
    recognition. A non-critical diagnostic cannot be a conflict-pair separator.

D1 IS NOW TAUTOLOGICAL. This is deliberate and recorded rather than hidden. D1 says "conforms
to the same component type as what it wraps", which is now exactly the admission test, so
D1 == D2 for every program. No existing number moved -- D1 was already 1 wherever D2 was 1
across all 82 program units measured by validation/decorator_rule_effect.py -- but the set is now
FOUR independent properties scored as six. `test_d1_is_now_implied_by_d2` pins that, so it
cannot be forgotten, and it is an open decision rather than a settled one.

(This docstring first said "five". That was wrong: the audit in
tests/test_decorator_property_independence.py found D5 tautological as well, by the same kind of
argument -- `d5 = abstract_decorator_base or d2` is True exactly when d2 is. The independent
properties are D2, D3, D4 and D6.)
"""

from __future__ import annotations

import os
import sys

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from piqs.checker import PIQSChecker, _CRITICAL_PROPERTIES  # noqa: E402

FIXTURES = os.path.join(os.path.dirname(os.path.abspath(__file__)), "fixtures_parser")


def _evaluate(slug: str) -> dict:
    with open(os.path.join(FIXTURES, slug + ".java"), encoding="utf-8") as fh:
        src = fh.read()
    return PIQSChecker().evaluate("decorator", {slug + ".java": src})


def vector(slug: str) -> dict[str, int]:
    return {r["property_id"]: r["satisfaction"] for r in _evaluate(slug)["logical_assessment"]}


def recognised(slug: str) -> bool:
    """Recognition is the critical set only -- exactly how the BDT battery decides a verdict."""
    v = vector(slug)
    return all(v.get(p, 0) == 1 for p in _CRITICAL_PROPERTIES["decorator"])


def test_object_adapter_is_not_recognised_as_a_decorator():
    """The reported program, verbatim. Before the rule: D1 0 D2 1 D3 1 D4 0 D5 1 D6 0,
    PIQS 53.33, grade Moderate, and RECOGNISED because {D2,D3} both held."""
    res = _evaluate("object_adapter_not_a_decorator")
    v = {r["property_id"]: r["satisfaction"] for r in res["logical_assessment"]}
    assert v == {"D1": 0, "D2": 0, "D3": 0, "D4": 0, "D5": 0, "D6": 0}
    assert res["final_quality_result_piqs"]["result_percent"] == 0.0
    assert res["grade"] == "Poor"
    assert not recognised("object_adapter_not_a_decorator")


def test_delegation_must_be_to_the_wrapped_component():
    """`Router` conforms to `Pump`, holds a `Pump` AND an unrelated `Valve`, and forwards only
    to the valve. Admitted as a candidate under either form of the rule -- but D3 must ask about
    the field it WRAPS, not about any component-typed field it happens to hold.

    This is the only fixture that separates 'gate admission' from 'filter the field list'.
    Every corpus program holds exactly one component-typed field, so there the two agree.
    """
    v = vector("decorator_delegates_to_unrelated_component")
    assert v["D2"] == 1, "Router holds a Pump and conforms to Pump -- it IS a candidate"
    assert v["D3"] == 0, "it forwards to the valve, never to the pump it wraps"
    assert not recognised("decorator_delegates_to_unrelated_component")


def test_d1_is_now_implied_by_d2():
    """D1 carries no independent information any more. Pinned so the redundancy is visible.

    If D1 is ever redefined to say something D2 does not, this test SHOULD fail -- and that
    failure is the signal to re-decide the Decorator weights, not to edit this expectation.
    """
    for slug in ("object_adapter_not_a_decorator", "decorator_delegates_to_unrelated_component",
                 "abstract_decorator_base"):
        v = vector(slug)
        assert v["D1"] == v["D2"], f"{slug}: D1 and D2 disagree -- D1 is meaningful again"


def test_a_genuine_decorator_is_still_recognised():
    """The control. Same-C holds for a real decorator, so nothing about it may move.

    Without this, 'the adapter is rejected' is satisfied by a checker that rejects everything.
    """
    v = vector("abstract_decorator_base")
    assert v["D2"] == 1 and v["D3"] == 1
    assert recognised("abstract_decorator_base")


@pytest.mark.parametrize("slug", ["object_adapter_not_a_decorator",
                                  "decorator_delegates_to_unrelated_component"])
def test_the_rejection_does_not_depend_on_names(slug):
    """The whole repo's claim, applied to this rule: rename every identifier and the verdict
    must not move. The rule is a type comparison, so it should be indifferent to names --
    but 'should be' is what this repo exists to stop accepting."""
    from piqs.obfuscator import obfuscate

    with open(os.path.join(FIXTURES, slug + ".java"), encoding="utf-8") as fh:
        src = fh.read()
    files = {slug + ".java": src}
    before = PIQSChecker().evaluate("decorator", files)["logical_assessment"]
    after = PIQSChecker().evaluate("decorator", obfuscate(files))["logical_assessment"]
    assert [(r["property_id"], r["satisfaction"]) for r in before] == \
           [(r["property_id"], r["satisfaction"]) for r in after]
