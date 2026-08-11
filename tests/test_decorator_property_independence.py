"""Which Decorator properties actually measure something D2 does not?

A property that is always equal to another property is not a measurement. It has three costs,
and the third is the one with a deadline:

  * it inflates PSR (the denominator counts it) and CPC (its weight counts it);
  * in the per-rule model it makes one fact count twice on one side of the Look-vs-Wiring
    comparison, which is the headline result;
  * **the rule list IS the prompt.** The experiment generates its prompts as one sentence per
    rule. A duplicated rule becomes a duplicated sentence, contaminating the conditions directly.
    So this has to be settled before any prompt sentence is written, not after.

THE AUDIT RESULT, measured over 82 program units (12 Kim programs with all their files together,
12 mutation battery, 28 BDT, 30 parser fixtures), every one evaluated as `decorator`:

    D1  NOT independent -- identical to D2 on every unit, and identical BY CONSTRUCTION
    D3  independent     -- 3 separating programs
    D4  independent     -- 1 separating program, and it had to be BUILT (see below)
    D5  NOT independent -- identical to D2 on every unit, and identical BY CONSTRUCTION
    D6  independent     -- 4 separating programs

So four properties carry information and six are scored.

WHY D1 AND D5 CANNOT BE SEPARATED BY ANY PROGRAM. This is an argument from the code, not from the
corpus -- a corpus can only ever say "no case here".

    D1:  wrapped_fields = [f for f in w.fields if f.field_type in conformed]
         d1 = any(any(ctype in conformed for (_f, ctype) in wrapped_fields) for ... in decorators)

    Every ctype in that list is in `conformed` BY CONSTRUCTION OF THE LIST -- the quantifier
    ranges over a list built by filtering on exactly the predicate it then tests. A candidate is
    appended only when wrapped_fields is non-empty. So d1 == bool(decorators) == d2, always.

    D5:  abstract_decorator_base = any(w.is_abstract for (w, _c, _wf) in decorators)
         d5 = abstract_decorator_base or d2

    Two exhaustive cases. `decorators` empty -> d2 False, and `any` over an empty list is False,
    so d5 False. `decorators` non-empty -> d2 True -> d5 True by the `or`, whatever the left side
    is. So d5 == d2, always. `abstract_decorator_base` is not dead code -- D5's description reads
    on it -- but it can never change D5's value.

WHY D4 NEEDED A CONSTRUCTED PROBE. In the BDT battery D4 == 1 in all 8 recognised decorators,
which proves nothing: `d4` is an `any(...)` over every decorator in the program, and for a
CONCRETE class the Java compiler already forces the implemented method set to cover the whole
interface. One concrete decorator sets D4 for the whole program, and every battery case has one.
`d4_abstract_base_partial_api.java` is an abstract decorator base that implements part of the
component API with no concrete decorator present, and it scores D2 = 1 with D4 = 0. D4 survives.

This file DELETES NOTHING. It records what the audit found so the removal, if it happens, is a
separate measured change.
"""

from __future__ import annotations

import os
import sys

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "validation"))

from decorator_rule_effect import programs  # noqa: E402
from piqs.checker import PIQSChecker, _PATTERN_WEIGHTS  # noqa: E402

FIXTURES = os.path.join(ROOT, "tests", "fixtures_parser")


def _vector(files: dict[str, str]) -> dict[str, int]:
    res = PIQSChecker().evaluate("decorator", files)
    return {r["property_id"]: r["satisfaction"] for r in res["logical_assessment"]}


def _fixture_vector(slug: str) -> dict[str, int]:
    with open(os.path.join(FIXTURES, slug + ".java"), encoding="utf-8") as fh:
        return _vector({slug + ".java": fh.read()})


ALL_UNITS = [(label, _vector(files)) for label, files in programs()]


# `test_property_is_identical_to_d2_on_every_unit` lived here, parametrised over ["D1", "D5"].
# Both properties are now DELETED, so it has no parameters left and is gone with them. It is not
# missing: its job -- "no redundant property may exist in the Decorator set" -- passed to
# `test_decorator_property_set_is_exactly_the_surviving_ids` below, which states the whole set
# rather than checking two known offenders one at a time. That is the stronger form: it also
# catches a redundant property nobody has named yet.


def test_d4_is_independent_of_d2():
    """The constructed probe. An abstract decorator base implementing part of the component API,
    with NO concrete decorator to satisfy the any(...) on its behalf.

    `_effective_methods` walks `extends` only, never `implements` (checker.py:353), so the
    wrapper's effective method set here is {write} while the component's is {write, flush}.
    """
    v = _fixture_vector("d4_abstract_base_partial_api")
    assert v["D2"] == 1, "the probe must still BE a decorator, or it proves nothing about D4"
    assert v["D4"] == 0, "D4 has collapsed into D2 -- the property set is down to three"
    assert v == {"D2": 1, "D3": 1, "D4": 0, "D6": 1}


@pytest.mark.parametrize(
    "pid,slug",
    [
        ("D3", "decorator_delegates_to_unrelated_component"),
        ("D6", "t1_decorator_partial_delegation_accepted"),
    ],
)
def test_property_has_a_separating_program(pid: str, slug: str):
    """D3 and D6 each have at least one program where they disagree with D2.

    D3: `Router` wraps a `Pump` and forwards only to an unrelated `Valve` -- D2 = 1, D3 = 0.
        Measured separators: decorator_no_delegation__FAIL, decorator_delegates_to_unrelated_
        component, div5_chain_not_delegation.
    D6: `t1_decorator_partial_delegation_accepted` forwards foo() and hard-codes bar() -- the
        standing BDT diagnostic for partial delegation. Measured separators: that one,
        decorator_no_delegation__FAIL, decorator_delegates_to_unrelated_component,
        div5_chain_not_delegation.

    NOTE: `abstract_decorator_base` does NOT separate D6 -- it scores D6 = 1. The first version
    of this test named it and went red. Recorded because "the abstract base fixture is the D6
    fixture" is an easy and wrong assumption: it is the fixture for D6's `not m.has_body` clause,
    which is a different question from whether D6 disagrees with D2.
    """
    seen = {label: v for label, v in ALL_UNITS}
    separating = [label for label, v in seen.items() if v[pid] != v["D2"]]
    assert separating, f"{pid} never disagrees with D2 anywhere -- it may be redundant too"
    assert any(slug in label for label in separating), (
        f"{slug} no longer separates {pid} from D2; the remaining separators are {separating}"
    )


def test_decorator_property_set_is_exactly_the_surviving_ids():
    """THE REPLACEMENT for `test_d1_is_now_implied_by_d2`, which became meaningless when D1 was
    deleted. Adding a redundant property back must fail loudly, here.

    D1 was removed because it was a proven tautology: `D1 == D2` for every program, by
    construction rather than by corpus. The reason to remove it is NOT primarily that it inflates
    PSR -- see PROPERTY_SPEC.md. It is that **the rule list is the prompt**: the experiment emits
    one sentence per rule, so a duplicated rule is a duplicated sentence in conditions O and P,
    which contaminates the experiment directly. A future session must not be able to argue this
    back on scoring grounds alone.

    D5 is still listed here and is next; D4 is deliberately still alive pending the field-scope
    audit, which may change what it measures.
    """
    assert sorted(_PATTERN_WEIGHTS["decorator"]) == ["D2", "D3", "D4", "D6"]
