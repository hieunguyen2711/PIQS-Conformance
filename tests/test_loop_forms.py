"""Observer notification loops: six forms that must be detected, four that must not.

Phase 2 step 3. `foreach_re` in `_evaluate_observer` matches ONE loop form. Five more express the
same structure and are silently missed -- and the failure looks exactly like a model that failed
to write Observer at all, which is precisely the confound this checker exists to remove.

WHY THE FOUR NEGATIVES MATTER MORE THAN THE SIX POSITIVES.

Every positive says "this MUST be detected". A widening change measured only against positives can
only look successful: the trivial way to pass all six is to detect everything. The negatives are
what make the widening falsifiable. If one of them flips, the change is too wide and it stops.

`loopN4_single_call_no_loop` is the sharpest, and it guards a rule rather than a case:

    FOR FORMS 2 AND 6, THE ENCLOSING LOOP IS PART OF THE PATTERN, NOT CONTEXT.

Forms 1 and 3 carry their own repetition -- the enhanced-for IS the loop, `forEach` IS the loop,
and you cannot write either and have it run once by accident. Forms 2 and 6 do not: `get(i)` and
`next()` are single calls, and the repetition lives in the `for`/`while` around them. So

    for (int i = 0; i < obs.size(); i++) obs.get(i).update();   traversal
    obs.get(0).update();                                        NOT traversal -- one observer

have the same call shape. A matcher keyed on shape alone says yes to both. O3 asks whether the
subject notifies EVERY observer, so form 2 must require an enclosing `for_statement` and form 6 an
enclosing `while_statement`. None of the six positives can raise this alarm, because every one of
them contains a loop.

WHY O1 IS 1 EVERYWHERE, AND WHY THAT WILL CHANGE.

O1 is 1 in all ten fixtures, and it has nothing to do with loops. `subject_candidates` in
`_evaluate_observer` selects types declaring a method whose name is in a hardcoded set --
{attach, detach, notifyObservers, register, remove, notify} -- and every fixture declares
`attach` and `notifyObservers` on an interface. O1 then asks whether any such candidate is
abstract, which the interface is.

**Stage 3 makes O1 structural.** When it does, these expected vectors will change, and that will
be CORRECT, not a regression. A future session reading a Stage 3 movement as a Step 3 breakage
would be reading it wrong. The properties that are currently name-dependent:

    O1  name-based via subject_candidates          -- WILL move in Stage 3
    O2  structural (abstract observer type)        -- loop-dependent
    O3  structural (subject notifies)              -- loop-dependent
    O4  structural (concrete observers implement)  -- loop-dependent

Only O2/O3/O4 are what Step 3 is measuring.
"""

from __future__ import annotations

import os
import sys

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from piqs.checker import PIQSChecker  # noqa: E402

FIXTURES = os.path.join(os.path.dirname(os.path.abspath(__file__)), "fixtures_parser")


def vector(slug: str) -> dict[str, int]:
    with open(os.path.join(FIXTURES, slug + ".java"), encoding="utf-8") as fh:
        src = fh.read()
    res = PIQSChecker().evaluate("observer", {slug + ".java": src})
    return {r["property_id"]: r["satisfaction"] for r in res["logical_assessment"]}


def piqs(slug: str) -> float:
    with open(os.path.join(FIXTURES, slug + ".java"), encoding="utf-8") as fh:
        src = fh.read()
    res = PIQSChecker().evaluate("observer", {slug + ".java": src})
    return res["final_quality_result_piqs"]["result_percent"]


# --------------------------------------------------------------------------------------- #
# The four NEGATIVE controls. These must not move, whatever is done to loop detection.
# Vectors recorded 2026-08-07, BEFORE any detection change.
# --------------------------------------------------------------------------------------- #

NEGATIVES = [
    "loopN1_not_a_notification",
    "loopN2_no_callback_call",
    "loopN3_wrong_element_type",
    "loopN4_single_call_no_loop",
    "loopN5_stream_map_changes_type",
    "loopN6_method_ref_element_is_argument",
]


@pytest.mark.parametrize("slug", NEGATIVES)
def test_negative_control_is_not_detected_as_notification(slug):
    """O2/O3/O4 must stay 0. O1 stays 1 for the name-based reason in the module docstring."""
    v = vector(slug)
    assert v == {"O1": 1, "O2": 0, "O3": 0, "O4": 0}, f"{slug} moved -- the widening is too wide"
    assert piqs(slug) == 22.27


def test_single_call_without_a_loop_is_not_traversal():
    """The rule, stated as its own test because it is a rule and not a case.

    `observers.get(0).update()` and `it.next().update()` have the SAME call shape as the form 2
    and form 6 traversals. Only the enclosing for/while distinguishes them, so for those two forms
    the loop is part of the pattern.
    """
    assert vector("loopN4_single_call_no_loop")["O3"] == 0


def test_method_reference_qualifier_must_name_the_element_type():
    """`observers.forEach(logger::record)` passes each observer as an ARGUMENT to something else
    -- the loopN2 failure mode in method-reference clothes. Only `Observer::update`, whose
    qualifier NAMES the element type, is a notification.

    The check is a name comparison in the checker, not a node-kind test in the parser:
    tree-sitter reports an `identifier` for the qualifier of both `Observer::update` and
    `logger::record`, because Java resolves type-vs-variable semantically.
    """
    assert vector("loopN6_method_ref_element_is_argument")["O3"] == 0


def test_element_must_be_the_receiver_not_merely_present():
    """`observers.forEach(o -> log(o))` iterates the right collection and names the element, but
    calls nothing ON it. A form-3 matcher that only checks "the parameter appears in the body"
    fires here wrongly."""
    assert vector("loopN2_no_callback_call")["O3"] == 0


# --------------------------------------------------------------------------------------- #
# The six POSITIVE forms. loop1 is detected today; the rest are the work of step 3.
#
# `DETECTED` is updated as each form lands, one at a time, so this file always states which
# forms are implemented rather than which are aspirational.
# --------------------------------------------------------------------------------------- #

FORMS = [
    ("loop1_enhanced_for", "for (Observer o : observers) o.update();"),
    ("loop2_indexed", "for (int i = 0; i < observers.size(); i++) observers.get(i).update();"),
    ("loop3_lambda", "observers.forEach(o -> o.update());"),
    ("loop4_method_ref", "observers.forEach(Observer::update);"),
    ("loop5_stream", "observers.stream().forEach(o -> o.update());"),
    ("loop6_iterator", "while (it.hasNext()) it.next().update();"),
]

DETECTED: set[str] = {"loop1_enhanced_for", "loop3_lambda", "loop4_method_ref", "loop5_stream"}


@pytest.mark.parametrize("slug,shape", FORMS)
def test_loop_form(slug, shape):
    """A detected form scores 100; an undetected one scores 22.27 -- 77.73 points of difference
    between programs that are byte-identical outside the loop."""
    v = vector(slug)
    if slug in DETECTED:
        assert v == {"O1": 1, "O2": 1, "O3": 1, "O4": 1}, f"{slug} ({shape}) regressed"
        assert piqs(slug) == 100.0
    else:
        assert v == {"O1": 1, "O2": 0, "O3": 0, "O4": 0}, (
            f"{slug} ({shape}) is detected but not listed in DETECTED -- "
            "if that was intended, move it and record the movement"
        )
        assert piqs(slug) == 22.27


def test_the_six_differ_only_in_the_loop():
    """The comparison is worthless if the fixtures differ in anything else. Strip the title line
    and the notifyObservers body; the remainder must be byte-identical across all six."""
    import hashlib

    def skeleton(slug: str) -> str:
        with open(os.path.join(FIXTURES, slug + ".java"), encoding="utf-8") as fh:
            lines = fh.read().split("\n")[1:]
        out, inside = [], False
        for line in lines:
            if "public void notifyObservers()" in line:
                out.append(line)
                inside = True
                continue
            if inside:
                if line.startswith("    }"):
                    inside = False
                    out.append("<<<LOOP>>>")
                    out.append(line)
                continue
            out.append(line)
        return "\n".join(out)

    hashes = {hashlib.sha256(skeleton(s).encode()).hexdigest() for s, _ in FORMS}
    assert len(hashes) == 1, "the six fixtures differ outside the loop -- the comparison is void"
