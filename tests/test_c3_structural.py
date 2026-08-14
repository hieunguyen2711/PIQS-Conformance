"""C3 is structural: a Composite is found by shape, not by a method-name verb.

WHAT C3 USED TO BE. `composites` selected any concrete implementor of any abstract type that
declared a method whose name began with the whole token `add` or `remove`, and C3 asked whether
that list was non-empty. So this scored C3 = 1:

    class Watcher implements Signal {          // Signal is an OBSERVER interface
        private List<Record> log = ...;        // a collection of a CONCRETE type
        public void addRecord(Record r) { log.add(r); }
    }

A composite type, in a program containing no Composite at all. That is the POSS/Copilot and
POSS/Gemini shape, and it is the same failure as O3's shopping cart: a name and a collection,
standing in for a structure.

THE CHECKER ALREADY CONTRADICTED ITSELF ABOUT IT. C1 and C4 read `real_components` -- "a concrete
implementor that HOLDS A COLLECTION of the component type" -- which is structural, and both said 0
for those two programs. C3 said 1. Two definitions of "composite" lived in one function. C3 now
reads the same one C1 and C4 do, plus one more condition.

THE RULE. A composite is a concrete type that

  1. conforms to an abstract component type C,
  2. holds a collection whose element type is C, and
  3. accepts a child of type C into one of those collections -- a method whose PARAMETER TYPE is
     C which operates on the field or assigns it.

Condition 3 is what stops C3 from becoming "a component-typed collection exists", which is
condition 2 and already tested by C1. Without it the two would be one rule under two names -- the
tautology that O2/O3 had to be rescued from, checked here before it could be introduced.
`c3_holds_children_but_never_accepts_one.java` is the witness: C1 = 1 and C3 = 0.

None of the three conditions reads a name. `add`, `addComponent` and `graft` all qualify; the
corpus's three real composites use two different verbs, and the fixture here uses a third.

KIM MOVES, BY TWO CELLS, AND THAT IS THE FIX. Kim records C3 = satisfied for POSS/Copilot and
POSS/Gemini; the checker now says 0 for both. Kim's own C1 = 0 on the same two programs is the
internal evidence -- a composite type that implements no abstract component is not a composite.
Agreement 144/160 -> 142/160. This is the second time a correct change has lowered agreement, and
"which cells moved, and what named construct moved each one" remains the measurement.

WITH THIS CHANGE THE RENAMING SUITE IS FULLY GREEN FOR THE FIRST TIME. No verdict in any of the
eight patterns is decided by an identifier.
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

# (slug, expected C1..C5, why)
CASES = [
    (
        "c3_composite_accepts_children",
        {"C1": 1, "C2": 1, "C3": 1, "C4": 1, "C5": 1},
        "Folder <: Node, holds List<Node>, graft(Node) puts one in -- `graft` is not add/remove",
    ),
    (
        "c3_interface_impl_with_an_add_method_is_not_a_composite",
        {"C1": 0, "C2": 1, "C3": 0, "C4": 0, "C5": 0},
        "Watcher implements an OBSERVER interface and holds a collection of a CONCRETE type",
    ),
    (
        "c3_holds_children_but_never_accepts_one",
        {"C1": 1, "C2": 1, "C3": 0, "C4": 1, "C5": 1},
        "holds List<Node> but no method takes a Node into it -- a whole that cannot accept a part",
    ),
    (
        "c3_second_component_collection_KNOWN_LIMITATION",
        {"C1": 1, "C2": 1, "C3": 1, "C4": 1, "C5": 1},
        "grafts into `pending` while walking `kids`; see the fixture header -- recorded, not fixed",
    ),
]


def _evaluate(slug: str, files: dict[str, str] | None = None) -> dict:
    if files is None:
        with open(os.path.join(FIXTURES, slug + ".java"), encoding="utf-8") as fh:
            files = {slug + ".java": fh.read()}
    return PIQSChecker().evaluate("composite", files)


def vector(slug: str, files: dict[str, str] | None = None) -> dict[str, int]:
    return {r["property_id"]: r["satisfaction"] for r in _evaluate(slug, files)["logical_assessment"]}


@pytest.mark.parametrize("slug,expected,why", CASES)
def test_structural_c3_verdict(slug, expected, why):
    assert vector(slug) == expected, f"{slug}: {why}"


@pytest.mark.parametrize("slug,expected,why", CASES)
def test_c3_survives_renaming(slug, expected, why):
    """C3 read `_has_verb_prefix(m.name, "add")`, so renaming `addComponent` to nonsense flipped
    it to 0. That was five of the eight renaming failures this project carried for months.

    These fixtures are not reachable from tests/test_renaming_invariance.py -- `iter_cases()`
    covers the battery directories and Kim only -- so the check is made here explicitly. See
    docs/STATE.md, "KNOWN BLIND SPOT".
    """
    with open(os.path.join(FIXTURES, slug + ".java"), encoding="utf-8") as fh:
        original = {slug + ".java": fh.read()}
    assert vector(slug, obfuscate(original, rename_files=False)) == expected, (
        f"{slug}: the verdict moved under renaming -- C3 still reads an identifier"
    )


def test_an_add_method_on_an_unrelated_interface_is_not_a_composite():
    """The case the change exists for, asserted alone so a regression names itself."""
    v = vector("c3_interface_impl_with_an_add_method_is_not_a_composite")
    assert v["C3"] == 0 and v["C1"] == 0, "a non-Composite program still reports a composite type"


def test_c3_is_strictly_stronger_than_holding_a_collection():
    """THE ANTI-TAUTOLOGY GUARD.

    C1 asks whether a real part-whole hierarchy exists -- a component-typed collection is held.
    If C3 asked only that, the two would be one rule under two names and the generated C prompt
    would carry the same sentence twice. The accepts-a-child condition is what separates them,
    and this fixture is the witness that the separation is non-empty.
    """
    v = vector("c3_holds_children_but_never_accepts_one")
    assert v["C1"] == 1 and v["C3"] == 0, "C3 has collapsed into C1"


def test_composites_has_one_construction_site_and_no_string_literals():
    """The finishing rule, as applied to O1 and O3 before it.

    ONE SITE, because C1, C3 and C4 must not disagree about what a composite is -- they did, and
    that is what this commit fixes. NO STRING LITERAL, because a literal there is the defect.
    Read from the AST so the comments quoting the old verb set do not trip it.
    """
    with open(os.path.join(ROOT, "piqs", "checker.py"), encoding="utf-8") as fh:
        tree = ast.parse(fh.read())
    sites = [
        n
        for n in ast.walk(tree)
        if isinstance(n, ast.Assign)
        and any(isinstance(t, ast.Name) and t.id == "composites" for t in n.targets)
    ]
    assert len(sites) == 1, f"expected one construction site, found {len(sites)}"
    literals = [
        n.value
        for n in ast.walk(sites[0].value)
        if isinstance(n, ast.Constant) and isinstance(n.value, str)
    ]
    assert literals == [], f"composites is built from string literals: {literals}"


def test_the_c3_sentence_states_what_the_code_checks():
    """The statement string becomes a sentence in the generated prompt. "Composite type exists."
    said nothing a reader could check; it now names both conditions."""
    res = _evaluate("c3_composite_accepts_children")
    c3 = {r["property_id"]: r["justification"] for r in res["logical_assessment"]}["C3"]
    assert "holds a collection" in c3 and "accepts a child" in c3
