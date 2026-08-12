"""`super.<op>()` is delegation -- but only through a base that actually holds the component.

WHY THE RULE EXISTS. `_delegates_to_field` asks whether a wrapper forwards to the held reference.
In the canonical GoF shape the abstract base holds the component and the concrete decorators
extend it, so a concrete decorator forwards by calling `super.m()`. That is delegation, one link
longer. `decorator_filterinputstream_analogue` is exactly this: `BufferedInputStream.read()`
forwards with `super.read()`, not with `in.read()`.

WHY THE RULE IS STRICT. "Forwards through the base that HOLDS the reference" contains a condition,
and the condition has to be checked. A `<super>` receiver counts only when a project-defined
ancestor of the wrapper is ITSELF a decorator candidate.

The loose alternative -- accept any `super` call -- was not rejected on taste. It re-opens the hole
F1b closed, by a different route:

    class Weird implements Duct {          // no `extends`: its super is Object
        private Duct super;
        public void write(String s) { super.write(s); }
    }

`Weird` is a candidate (implements `Duct`, declares a `Duct` field). Under the loose rule its
`super.write()` counts and it scores D3 = 1, D6 = 1 -- the precise verdict F1b was written to
eliminate. One fix would have undone the other. Pinned below.

WHAT THIS COMMIT DOES NOT DO. It moves no verdict, and that is expected rather than disappointing.
Under today's own-fields admission a class must DECLARE a component-typed field to be examined at
all, so `BufferedInputStream`, `Relay` and `Nested` -- every super-caller that inherits its field
-- are never candidates. This commit becomes load-bearing only when `_effective_fields` admission
lands and the `all` quantifier starts asking whether those classes forward.
"""

from __future__ import annotations

import os
import sys

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from piqs.checker import PIQSChecker, _CRITICAL_PROPERTIES  # noqa: E402

FIXTURES = os.path.join(ROOT, "tests", "fixtures_parser")


def _vector(slug: str) -> dict[str, int]:
    with open(os.path.join(FIXTURES, slug + ".java"), encoding="utf-8") as fh:
        res = PIQSChecker().evaluate("decorator", {slug + ".java": fh.read()})
    return {r["property_id"]: r["satisfaction"] for r in res["logical_assessment"]}


def test_super_call_through_a_base_that_holds_nothing_is_not_delegation():
    """`Leaky extends Plain implements Spout`, declares a `Spout`, and forwards with
    `super.emit()`. `Plain` holds nothing, so the call reaches a class that wraps nothing and the
    declared `Spout` is never touched.

    Under the LOOSE rule this scores D3 = 1, D6 = 1. That is the difference the strict rule buys.
    """
    v = _vector("super_call_base_holds_nothing")
    assert v["D2"] == 1, "Leaky does declare a Spout and conform to Spout -- it IS a candidate"
    assert v["D3"] == 0, "super.emit() reaches Plain, which holds nothing"
    assert v["D6"] == 0


def test_the_loose_rule_would_undo_f1b():
    """The reason the rule is strict, stated as a test rather than as a comment.

    A field named `super` on a class with no `extends`. If accepting `<super>` were unconditional,
    this would score D3 = 1 again -- the exact verdict F1b removed. The strict rule rejects it
    because `Weird` has no project-defined ancestor at all, let alone one holding the component.
    """
    v = _vector("field_named_super")
    assert v["D2"] == 1
    assert v["D3"] == 0, "super.write() reaches Object; nothing is wrapped"
    assert v["D6"] == 0


def test_the_jdk_super_call_in_div1_is_unaffected():
    """`Assembler.handOff` calls `super.hashCode()` -- a JDK method on a base holding nothing.

    It is the loose-rule case, already present in the tree before this commit. `Assembler` is a
    Builder fixture with no component interface, so it is not a decorator candidate and the
    question never arises. Asserted rather than assumed, because "it cannot matter" is the claim
    this repository exists to stop accepting.
    """
    v = _vector("div1_this_keyword")
    assert v["D2"] == 0, "not a decorator candidate, so no super call of its can count"
    assert v["D3"] == 0


def test_the_must_pass_jdk_decorator_is_not_disturbed():
    """`decorator_filterinputstream_analogue` is a MUST-PASS battery case that passes TODAY.

    Its only candidate is `FilterInputStream`, which forwards with `in.read()` and has no `super`
    call. This commit must not be what moves it -- in either direction.
    """
    path = os.path.join(ROOT, "fixtures", "mutation_battery_bdt",
                        "decorator_filterinputstream_analogue.java")
    with open(path, encoding="utf-8") as fh:
        res = PIQSChecker().evaluate("decorator", {os.path.basename(path): fh.read()})
    v = {r["property_id"]: r["satisfaction"] for r in res["logical_assessment"]}

    assert v["D6"] == 1
    assert all(v[p] == 1 for p in _CRITICAL_PROPERTIES["decorator"]), "must stay recognised"
    assert res["final_quality_result_piqs"]["result_percent"] == 100.0


@pytest.mark.parametrize("slug", ["super_call_base_holds_nothing", "field_named_super"])
def test_the_strict_rule_does_not_depend_on_names(slug):
    """A type comparison should be indifferent to identifiers. `should be` is what this repo
    exists to stop accepting, so it is measured."""
    from piqs.obfuscator import obfuscate

    with open(os.path.join(FIXTURES, slug + ".java"), encoding="utf-8") as fh:
        files = {slug + ".java": fh.read()}
    before = PIQSChecker().evaluate("decorator", files)["logical_assessment"]
    after = PIQSChecker().evaluate("decorator", obfuscate(files))["logical_assessment"]
    assert [(r["property_id"], r["satisfaction"]) for r in before] == \
           [(r["property_id"], r["satisfaction"]) for r in after]
