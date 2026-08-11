"""KNOWN DEFECT, PINNED NOT FIXED: a decorator that forwards nothing scores 100.

READ THIS BEFORE "FIXING" A FAILURE HERE. These tests assert behaviour that is WRONG. They exist
so the defect cannot be forgotten and cannot change unnoticed while the design decision is open.
If a test in this file goes red because the admission rule or the quantifiers changed, that is the
FIX LANDING, and the right response is to update these expectations deliberately and record the
movement -- not to treat it as a regression.

THE DEFECT. `_evaluate_decorator`'s candidate loop reads `w.fields` -- own fields only, never
`_effective_fields`. A concrete decorator extending an abstract decorator base inherits the
component reference and declares no field of its own, so it is never a decorator candidate. That
is the canonical GoF Decorator shape: the base holds the component, the concrete decorators extend
it. **Only the base is ever judged**, and D2/D3/D4/D6 are each an `any(...)` over the candidate
list, so one compliant class carries the whole program.

TWO INDEPENDENT DEFECTS. Measured across all four combinations, not argued:

    admission          quantifier   D2 D3 D4 D6   PIQS
    own fields         any (NOW)     1  1  1  1   100.0
    own fields         all           1  1  1  1   100.0    the base is the only candidate
    effective fields   any           1  1  1  1   100.0    the base still satisfies every any()
    effective fields   all           1  0  1  0    52.22   the only combination that catches it

Fixing the admission rule ALONE leaves the fixture at 100. Both questions are open and belong to
the project owner; nothing here decides either.

IT IS NOT ONLY A CONSTRUCTED FIXTURE. `decorator_filterinputstream_analogue.java`, a corpus case
modelled on the JDK's own decorator hierarchy, has the same invisible class -- see
`validation/decorator_field_scope_effect.py`.
"""

from __future__ import annotations

import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "validation"))

from piqs.checker import PIQSChecker, _CRITICAL_PROPERTIES  # noqa: E402

FIXTURES = os.path.join(ROOT, "tests", "fixtures_parser")
SLUG = "decorator_subclass_forwards_nothing"


def test_a_decorator_that_forwards_nothing_is_recognised_and_scores_100():
    """WRONG, AND PINNED AS WRONG. `Broken` overrides both component operations and forwards
    neither, yet the program is recognised with a clean D6."""
    with open(os.path.join(FIXTURES, SLUG + ".java"), encoding="utf-8") as fh:
        res = PIQSChecker().evaluate("decorator", {SLUG + ".java": fh.read()})
    v = {r["property_id"]: r["satisfaction"] for r in res["logical_assessment"]}

    assert v == {"D2": 1, "D3": 1, "D4": 1, "D6": 1}
    assert res["final_quality_result_piqs"]["result_percent"] == 100.0
    assert all(v[p] == 1 for p in _CRITICAL_PROPERTIES["decorator"]), "recognised as a Decorator"


def test_the_subclass_is_not_even_a_candidate():
    """The mechanism, asserted separately from the score.

    Pinning only the 100 would leave the CAUSE unpinned: a change that made `Broken` a candidate
    but still scored 100 through the `any(...)` would keep the test above green while moving the
    thing it is really about.
    """
    svc = PIQSChecker()
    with open(os.path.join(FIXTURES, SLUG + ".java"), encoding="utf-8") as fh:
        types = svc._extract_types({SLUG + ".java": fh.read()})

    components = svc._component_type_names(types)
    broken = types["Broken"]
    conformed = {c for c in components if svc._conforms_to(broken, c, types)}

    assert "Conduit" in conformed, "Broken IS-A Conduit, through Base"
    assert [f for f in broken.fields if f.field_type in conformed] == [], "declares no own field"
    assert [f.field_type for f in svc._effective_fields(broken, types)
            if f.field_type in conformed] == ["Conduit"], "but inherits one"
