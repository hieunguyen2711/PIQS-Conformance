"""O3 means what its sentence says: the subject notifies its REGISTERED observers.

THE DEFECT. O3 is weight 3 and critical, and its published sentence has always been "Subject
notifies all registered observers." The code checked only the first half -- "a loop over a
collection calls a method on each element". So this program, which contains no Observer at all,
scored O3 = 1 on 882660d:

    class Cart {
        private List<LineItem> lines = new ArrayList<>();
        public void add(LineItem l) { lines.add(l); }
        public int total() { int t = 0; for (LineItem l : lines) { t += l.getSubTotal(); } return t; }
    }

A shopping cart adding up prices notifies nobody. Three of eleven points, at critical weight,
free in every experimental condition.

TWO CANDIDATE RULES WERE PROTOTYPED AND MEASURED. Neither works alone, and the reasons are
different, so both are implemented:

  "the holder must maintain the collection", alone
      the Cart STILL scores O3 = 1 -- `add(LineItem l) { lines.add(l); }` is exactly the
      maintenance shape -- and constructor injection and a List-taking setter both collapse to
      0 0 0 0, breaking two real styles. Measured, not argued.

  "the element type must be abstract", alone
      fixes the Cart, keeps every Observer style -- but makes O2 <=> O3. `observer_type_names`
      is populated only at notification sites, so O2 already implied O3; requiring an abstract
      element removes exactly the loops that made O3 true while O2 was false. Verified by
      scoring all 54 observer fixtures under that build: ZERO separate the two.

O2 <=> O3 is not merely redundant scoring. Prompts are generated one sentence per rule, so it
puts the same sentence into the O prompt twice -- the D1/D5 defect class, which contaminates the
experiment rather than the score.

WHY THE PROPERTY WAS NOT DELETED INSTEAD, as D1 and D5 were. Kim never scored Decorator, so
deleting a Decorator property cost nothing. Kim scored Observer: 10 units x 4 properties. Deleting
O3 would drop the headline denominator 160 -> 150 and remove a column of the external-validity
argument to save a rule. Redefining O3 so that it is not a duplicate keeps both. Four properties
stay.

THE RULE. A notification site is: an abstract element type, not self-recursion, a loop calling a
method on each element. O2 asks whether such a site exists. O3 asks whether the field it notifies
through is also the field observers REGISTER into -- a method whose parameter type is the observer
type, which operates on that field or assigns it.

    O3 => O2.  O2 does NOT imply O3.

`o3_constructor_injected_never_registered.java` is the witness that the implication is strict, and
it is also the fixture on which the rejected "abstract element alone" design gives O2 = O3 = 1.

THE COST, STATED SO IT CAN BE DISAGREED WITH KNOWINGLY. A subject handed its observer list at
construction and never added to loses O3 and is not recognised. That is a deliberate narrowing,
defended from the Strict General Rules for Observer -- required: "a registration mechanism
adds/removes observers at runtime"; what varies: "the set and identity of dependents at runtime".
A list fixed at construction has no runtime dependent set. The fixture states the cost in its own
header rather than hiding it.
"""

from __future__ import annotations

import ast
import os
import sys

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from piqs.checker import PIQSChecker  # noqa: E402
from piqs.obfuscator import obfuscate  # noqa: E402

FIXTURES = os.path.join(os.path.dirname(os.path.abspath(__file__)), "fixtures_parser")

# (slug, expected vector, why)
CASES = [
    (
        "o3_cart_aggregation_is_not_notification",
        {"O1": 0, "O2": 0, "O3": 0, "O4": 0},
        "LineItem is concrete -- arithmetic over records, not notification",
    ),
    (
        "o3_registration_via_add",
        {"O1": 0, "O2": 1, "O3": 1, "O4": 1},
        "enrol(Feed) writes the same field publish() iterates",
    ),
    (
        "o3_constructor_injected_never_registered",
        {"O1": 0, "O2": 1, "O3": 0, "O4": 1},
        "notifies correctly, but nothing can ever register",
    ),
    (
        "o3_registration_into_a_different_collection",
        {"O1": 0, "O2": 1, "O3": 0, "O4": 1},
        "registers into `spare`, notifies `sinks` -- nobody registered is notified",
    ),
    (
        "o3_registration_via_setter_taking_a_list",
        {"O1": 0, "O2": 1, "O3": 0, "O4": 1},
        "the parameter is a List, so no individual observer can subscribe",
    ),
    (
        "o3_single_observer_registered_by_setter",
        {"O1": 0, "O2": 1, "O3": 1, "O4": 1},
        "branch (b): a method taking Feed ASSIGNS the field",
    ),
]


def _evaluate(slug: str, files: dict[str, str] | None = None) -> dict:
    if files is None:
        with open(os.path.join(FIXTURES, slug + ".java"), encoding="utf-8") as fh:
            files = {slug + ".java": fh.read()}
    return PIQSChecker().evaluate("observer", files)


def vector(slug: str, files: dict[str, str] | None = None) -> dict[str, int]:
    return {r["property_id"]: r["satisfaction"] for r in _evaluate(slug, files)["logical_assessment"]}


@pytest.mark.parametrize("slug,expected,why", CASES)
def test_o3_verdict(slug, expected, why):
    assert vector(slug) == expected, f"{slug}: {why}"


@pytest.mark.parametrize("slug,expected,why", CASES)
def test_o3_survives_renaming(slug, expected, why):
    """No identifier is read. The parameter type and the field name come from the holder's own
    declarations and are compared to each other, so renaming moves both together.

    These fixtures are not reachable from tests/test_renaming_invariance.py -- `iter_cases()`
    covers the battery directories and Kim only, not tests/fixtures_parser -- so the check is
    made here explicitly rather than assumed. See docs/STATE.md, "KNOWN BLIND SPOT".
    """
    with open(os.path.join(FIXTURES, slug + ".java"), encoding="utf-8") as fh:
        original = {slug + ".java": fh.read()}
    assert vector(slug, obfuscate(original, rename_files=False)) == expected, (
        f"{slug}: the verdict moved under renaming"
    )


def test_a_shopping_cart_is_not_an_observer():
    """The case the change exists for, asserted on its own so a regression names itself."""
    assert vector("o3_cart_aggregation_is_not_notification") == {"O1": 0, "O2": 0, "O3": 0, "O4": 0}


def test_o3_implies_o2_but_o2_does_not_imply_o3():
    """THE ANTI-TAUTOLOGY GUARD, and the reason O3 was redefined instead of deleted.

    If these two ever coincide on every program again, they are one rule under two names and the
    generated O prompt carries the same sentence twice. The constructor-injected fixture is the
    witness that keeps them apart: an abstract observer role with no registration.

    Checked in both directions across every fixture in this file, so the guard cannot be
    satisfied by a checker that simply answers 0 to both.
    """
    separated = False
    for slug, expected, _why in CASES:
        v = vector(slug)
        assert not (v["O3"] == 1 and v["O2"] == 0), f"{slug}: O3 without O2 -- the implication broke"
        if v["O2"] == 1 and v["O3"] == 0:
            separated = True
    assert separated, "no fixture separates O2 from O3 -- they have collapsed into one rule"


def test_the_registered_field_must_be_the_notified_field():
    """The field identity is the whole content of the maintenance rule.

    "Some method taking the element type touches some collection" passes a program that registers
    into one field and notifies another, where nobody who registers is ever notified.
    """
    assert vector("o3_registration_into_a_different_collection")["O3"] == 0
    assert vector("o3_registration_via_add")["O3"] == 1


def test_o3_is_computed_from_registered_sites_not_from_the_raw_bool():
    """Requirement 2, tested structurally.

    `o3 = notifies_observers` is the defect. Read from the AST so that comments quoting the old
    form do not satisfy or trip it.
    """
    with open(os.path.join(ROOT, "piqs", "checker.py"), encoding="utf-8") as fh:
        tree = ast.parse(fh.read())
    assigns = [
        n
        for n in ast.walk(tree)
        if isinstance(n, ast.Assign)
        and any(isinstance(t, ast.Name) and t.id == "o3" for t in n.targets)
    ]
    assert len(assigns) == 1, f"expected one o3 assignment, found {len(assigns)}"
    names = {n.id for n in ast.walk(assigns[0].value) if isinstance(n, ast.Name)}
    assert "registered_notifications" in names, "o3 no longer reads the registered subset"
    assert "notifies_observers" not in names, "o3 is back on the raw notification bool"


def test_the_o2_and_o3_sentences_state_what_the_code_checks():
    """These strings are published: they become sentences in the generated prompts.

    O3's sentence claimed "registered" for a long time while nothing checked it. A sentence that
    overstates the code is worse than a missing rule, because it is copied into the prompt and
    into the paper.
    """
    with open(os.path.join(FIXTURES, "o3_registration_via_add.java"), encoding="utf-8") as fh:
        res = PIQSChecker().evaluate("observer", {"x.java": fh.read()})
    sentences = {r["property_id"]: r["justification"] for r in res["logical_assessment"]}
    assert "register" in sentences["O3"] and "iterates" in sentences["O3"]
    assert "element type of a notification" in sentences["O2"]
