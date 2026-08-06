"""Guards the `not m.has_body` skip in `_fully_delegates` (Decorator D6, piqs/checker.py).

    for m in w.methods:
        if m.is_constructor or not m.has_body:   # <-- the line this file exists to protect
            continue
        w_ops.setdefault(m.name, m)

That line's original comment said it skipped phantom methods harvested by the old signature
regex. The tree-sitter extractor produces no phantoms, so that reason is gone -- but the line
is still load-bearing for a different one: an abstract decorator base may implement part of the
component API by forwarding and leave the rest abstract for its concrete decorators. A bodyless
declaration is not implemented, so it is out of D6's scope. Without the skip it enters
`implemented`, `_delegates_to_field("")` returns False, and a correct abstract base scores D6=0.

NO FILE IN THE CORPUS EXERCISES THIS. Deleting that line passes all four suites --
Kim, both mutation batteries and the invariance suite -- while silently changing behaviour.
`tests/fixtures_parser/abstract_decorator_base.java` and this test are the only thing standing
between that line and a future deletion that looks safe and is not.

Verified by instrumenting `_fully_delegates` on the fixture:

    skip present   implemented = ['read']              -> D6=1, PIQS 100.0
    skip removed   implemented = ['describe', 'read']  -> D6=0, PIQS 86.67
                   describe: has_body=False body='' delegates=False

The preconditions below are asserted first and on purpose. This case is easy to render
vacuous -- give LoudDecorator its own Component field and D6 is 1 either way -- so the fixture's
shape is pinned rather than assumed.
"""

from __future__ import annotations

import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from piqs.checker import PIQSChecker  # noqa: E402
from piqs.parser import extract_types  # noqa: E402

FIXTURE = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                       "fixtures_parser", "abstract_decorator_base.java")


def _files() -> dict[str, str]:
    with open(FIXTURE, encoding="utf-8") as fh:
        return {os.path.basename(FIXTURE): fh.read()}


def _props() -> dict[str, int]:
    result = PIQSChecker().evaluate("decorator", _files())
    return {row["property_id"]: row["satisfaction"] for row in result["logical_assessment"]}


# --------------------------------------------------------------------------------------- #
# Preconditions -- without these the D6 assertion below proves nothing
# --------------------------------------------------------------------------------------- #

def test_fixture_shape_still_reaches_the_branch() -> None:
    types = extract_types(_files())

    deco = types["ComponentDecorator"]
    assert deco.is_abstract, "the decorator base must be abstract"
    assert "Component" in deco.implements
    assert [f.field_type for f in deco.fields] == ["Component"], "must hold the component field"

    by_name = {m.name: m for m in deco.methods if not m.is_constructor}
    assert by_name["read"].has_body is True, "one component op must be implemented by forwarding"
    assert by_name["describe"].has_body is False, (
        "one component op must be left ABSTRACT -- that bodyless method is the whole point"
    )

    # The concrete subclass must NOT declare its own component-typed field. `decorators` is
    # built from w.fields (own fields only); a field here would add LoudDecorator to the list,
    # d6 = any(...) would be satisfied by its fully-forwarding self, and D6 would be 1 whether
    # or not the guarded line exists.
    loud = types["LoudDecorator"]
    assert loud.extends == "ComponentDecorator"
    assert [f.field_type for f in loud.fields if f.field_type in {"Component", "ComponentDecorator"}] == [], (
        "LoudDecorator must inherit `inner`, not declare its own -- otherwise this case is vacuous"
    )

    # Component must expose exactly the two operations the reasoning above depends on.
    assert {m.name for m in types["Component"].methods if not m.is_constructor} == {"read", "describe"}


# --------------------------------------------------------------------------------------- #
# The guard
# --------------------------------------------------------------------------------------- #

def test_abstract_decorator_base_is_fully_delegating() -> None:
    """D6=1: every component operation this wrapper IMPLEMENTS forwards to the wrapped reference.

    `describe` is declared and not implemented, so it is not in scope. If this fails with D6=0,
    the `not m.has_body` skip in `_fully_delegates` has been removed -- restore it rather than
    relaxing this assertion.
    """
    props = _props()
    assert props["D6"] == 1, (
        "D6=0 means a correct abstract decorator base was penalised for an operation it "
        "declares but does not implement -- see the `not m.has_body` skip in _fully_delegates"
    )
    # Recognition is unaffected either way; the critical set is {D2, D3}. Pinned so a future
    # failure is attributable to D6 alone rather than to the case ceasing to be a decorator.
    assert props["D2"] == 1 and props["D3"] == 1
    assert props == {"D1": 1, "D2": 1, "D3": 1, "D4": 1, "D5": 1, "D6": 1}
