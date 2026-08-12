"""`super.m()` is a receiver, not the absence of one.

WHAT WAS WRONG. `_qualifier` mapped every receiver that is not a simple reference to `None`. A
`super` receiver landed there with `getX().op()` and `arr[0].op()`, so **`super.read()` and a bare
`read()` were the same recorded fact**:

    FilterInputStream.read     calls=[('in', 'read')]
    BufferedInputStream.read   calls=[(None, 'read')]     <- super.read(), indistinguishable

That is why `decorator_filterinputstream_analogue` looks as though its concrete decorator forwards
to nothing. It forwards with `super.read()` -- through the abstract base that holds the reference
-- and the parser could not see the difference.

WHY THE SENTINEL IS THE STRING "super". `super` is a Java RESERVED KEYWORD (JLS 3.9), so no field,
local, parameter or type can ever be named `super`. The sentinel therefore cannot collide with a
real identifier. Saying that out loud matters: `_delegates_to_field` works by comparing the
receiver against a field name, and the whole design rests on the comparison being impossible to
satisfy accidentally. A plain string also survives the JSON round-trip in the golden snapshot,
which a sentinel object would not.

THIS COMMIT CHANGES NO PREDICATE. Only two things read `method.calls`: `_calls_within`, which
ignores the receiver entirely, and `_delegates_to_field`, which compares it to a field name --
and neither `None` nor `"super"` can equal one. Accepting `super` as delegation is the NEXT
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


def test_a_super_receiver_is_recorded_as_super():
    """The defect. Before this change it was `[(None, 'pull')]`."""
    assert _calls()["Relay.pull"] == [("super", "pull")]


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
    assert _calls()["Nested.reach"] == [("super", "pull")]


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
