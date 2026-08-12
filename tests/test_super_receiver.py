"""`super.m()` is a receiver, not the absence of one.

WHAT WAS WRONG. `_qualifier` mapped every receiver that is not a simple reference to `None`. A
`super` receiver landed there with `getX().op()` and `arr[0].op()`, so **`super.read()` and a bare
`read()` were the same recorded fact**:

    FilterInputStream.read     calls=[('in', 'read')]
    BufferedInputStream.read   calls=[(None, 'read')]     <- super.read(), indistinguishable

That is why `decorator_filterinputstream_analogue` looks as though its concrete decorator forwards
to nothing. It forwards with `super.read()` -- through the abstract base that holds the reference
-- and the parser could not see the difference.

WHY THE SENTINEL IS `<super>` AND NOT THE BARE TEXT `"super"`.

The first version of this change stored the bare text, on the reasoning that Java forbids a field
named `super` so no collision was possible. **THIS CHECKER IS NOT javac.** Measured:

    javac                        error: <identifier> expected
    tree-sitter has_error        False
    extract_types fields         [('super', 'Duct')]

Generated code that does not compile is exactly what this project scores -- `run_scorer.py`
records compilation as a separate fact because half the Kim programs fail it. So
tests/fixtures_parser/field_named_super.java is reachable, and with the bare text it scored
**D2 1 D3 1 D4 1 D6 1, PIQS 100**: `_delegates_to_field` matched the receiver of `super.write()`
against a field named `super`, crediting delegation to a field that is never touched.

That was a REGRESSION INTRODUCED by the bare-text version, not a pre-existing hole. Before any
super handling the receiver was `None` and nothing matched.

`<super>` cannot be any identifier: `<` and `>` are not JavaLetters (JLS 3.8). Verified against the
parser rather than argued -- declaring `private Duct <super>;` yields a field whose name is the
empty string, never `<super>`. A plain string also survives the JSON round-trip in the golden
snapshot, which a sentinel object would not, and `calls` IS snapshotted.

THE DETECTION IS KEYED ON NODE TYPE, NEVER ON TEXT. `object.type == "super"` is the fact; the text
is incidental and is exactly what collided.

`this` HAS THE SAME HOLE. A field named `this` parses just as happily. `this.m()` stays `None`
because `this.m()` IS `m()` -- the same call, and not delegation to a field, so no sentinel is
needed. But `Outer.this.m()` returned the string `"this"`, which is the same collision in its other
form; it now returns `None`, because it is a call on the enclosing instance and not on any field.

THIS COMMIT CHANGES NO PREDICATE. Only two things read `method.calls`: `_calls_within`, which
ignores the receiver entirely, and `_delegates_to_field`, which compares it to a field name --
and neither `None` nor `<super>` can equal one. Accepting `super` as delegation is the NEXT
commit, deliberately separate, so that this one can be verified as pure fact-recording.
"""

from __future__ import annotations

import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from piqs.parser import extract_types  # noqa: E402

FIXTURES = os.path.join(ROOT, "tests", "fixtures_parser")
SLUG = "super_receiver_forms"


def _calls() -> dict[str, list[tuple[str | None, str]]]:
    with open(os.path.join(FIXTURES, SLUG + ".java"), encoding="utf-8") as fh:
        types = extract_types({SLUG + ".java": fh.read()})
    return {
        f"{t.name}.{m.name}": m.calls
        for t in types.values()
        for m in t.methods
        if m.calls
    }


def test_a_field_receiver_is_the_field_name():
    assert _calls()["RelayBase.pull"] == [("src", "pull")]


def test_a_super_receiver_is_recorded_as_the_sentinel():
    """The defect. Before any super handling it was `[(None, 'pull')]`; with the bare-text
    sentinel it was `[('super', 'pull')]`, which collided with a field named `super`."""
    from piqs.parser import SUPER_RECEIVER

    assert _calls()["Relay.pull"] == [(SUPER_RECEIVER, "pull")]
    assert SUPER_RECEIVER == "<super>"


def test_a_bare_self_call_has_no_receiver():
    assert _calls()["Relay.selfCall"] == [(None, "pull")]


def test_this_dot_call_is_the_same_fact_as_a_bare_call():
    """DELIBERATE, not a gap. `this.m()` and `m()` are the same call, so both record `None`.

    Pinned so that a later session does not "fix" it into a third receiver value. Neither form is
    delegation to a field, which is the only question `_delegates_to_field` asks.
    """
    c = _calls()
    assert c["Relay.viaThis"] == [(None, "pull")] == c["Relay.selfCall"]


def test_qualified_super_is_super_and_not_the_outer_class_name():
    """`Anchor.super.pull()` from an inner class.

    tree-sitter reports `object = identifier "Anchor"` with the `super` as a SEPARATE child, so
    the old rule returned `"Anchor"` -- a class holding a field named `Anchor` would have counted
    this as delegation to that field. `_qualifier` cannot see it, because it only receives the
    object node; the check belongs in `_invocations`.
    """
    from piqs.parser import SUPER_RECEIVER

    assert _calls()["Nested.reach"] == [(SUPER_RECEIVER, "pull")]


def test_a_field_access_chain_through_this_is_the_field():
    """`this.src.pull()` -- already a `field_access` with an `identifier` field, so it yields the
    FIELD name and must keep doing so. This is the form the `Outer.this` fix must not break."""
    assert _calls()["Relay.viaFieldChain"] == [("src", "pull")]


def test_qualified_this_is_not_a_receiver():
    """`Anchor.this.pull()` -- a call on the ENCLOSING INSTANCE, not on any field of this class.

    It arrives as a `field_access` whose `field` node is the `this` KEYWORD, and the old rule
    returned that keyword's text, `"this"`. A field named `this` parses perfectly well in
    tree-sitter, so that was the `field_named_super` collision in its other form. The rule is now
    keyed on the field node's TYPE: only an `identifier` yields a receiver.
    """
    assert _calls()["Nested.outerInstance"] == [(None, "pull")]


def test_a_field_named_super_is_not_credited_as_delegation():
    """THE COLLISION GUARD, and the reason the sentinel is `<super>` rather than `"super"`.

    `field_named_super.java` does not compile, and that is the point -- this project scores
    generated code, and `run_scorer.py` records compilation precisely because half the Kim
    programs fail it. tree-sitter accepts the file and stores a field named `super`.

    With the bare-text sentinel this program scored D2 1 D3 1 D4 1 D6 1, PIQS 100: the receiver of
    `super.write()` compared equal to the field named `super`, so the checker credited delegation
    to a field that is never touched. Run this test against that version and it goes red -- which
    is what makes the sentinel choice PROVEN rather than a preference.
    """
    from piqs.checker import PIQSChecker

    with open(os.path.join(FIXTURES, "field_named_super.java"), encoding="utf-8") as fh:
        res = PIQSChecker().evaluate("decorator", {"field_named_super.java": fh.read()})
    v = {r["property_id"]: r["satisfaction"] for r in res["logical_assessment"]}

    assert v["D2"] == 1, "it does hold a component-typed field -- the candidate part is genuine"
    assert v["D3"] == 0, (
        "super.write() forwards to the PARENT CLASS, not to the field that happens to be spelled "
        "`super`. A satisfied D3 here means the receiver sentinel collides with an identifier."
    )
    assert v["D6"] == 0


def test_the_three_receiver_kinds_are_distinguishable():
    """The point of the whole fixture, as one assertion.

    A field receiver, a `super` receiver and no receiver must be three different values. Before
    this change the last two were both `None`, which is what made `super.read()` invisible.
    """
    c = _calls()
    field_recv = c["RelayBase.pull"][0][0]
    super_recv = c["Relay.pull"][0][0]
    none_recv = c["Relay.selfCall"][0][0]
    assert len({field_recv, super_recv, none_recv}) == 3, (
        f"receivers collapsed: field={field_recv!r} super={super_recv!r} bare={none_recv!r}"
    )
