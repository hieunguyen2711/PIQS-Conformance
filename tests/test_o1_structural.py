"""O1 is structural: the abstract Subject role is found by shape, not by method name.

WHAT O1 USED TO BE. `subject_candidates` selected any type declaring a method whose name was in
a hardcoded set -- {attach, detach, notifyObservers, register, remove, notify} -- and O1 asked
whether one of them was abstract. Same structure, different vocabulary, different verdict:

    attach / notifyObservers   ->  O1 = 1
    subscribe / broadcast      ->  O1 = 0

That is the artefact this instrument exists to avoid. The experiment removes the pattern name
from the prompt, so models invent their own vocabulary; a name-matching checker marks them down
for a naming reason that is indistinguishable from the paper's finding.

`o1_supertype_with_contract.java` is that defect as a single file. It is textbook Observer and
every identifier is outside the old set, so it scored O1 = 0 before this change and O1 = 1 after.

IT ALSO ADMITTED THE WRONG ROLE. In SWS/Copilot the only abstract name-match was
`TransactionObserver` -- the OBSERVER interface -- admitted as a SUBJECT because its callback is
named `notify`. The real subject, `Wallet`, is concrete with no supertype, so the program has no
abstract subject at all. Kim also records satisfied, so the checker agreed with the published
ground truth for a structurally false reason. That is the one Kim cell this change moves, 1 -> 0,
and lowering agreement there is the correct outcome. `o1_concrete_subject_no_supertype.java`
pins the shape.

THE RULE, in three parts:

  1. the CONCRETE subject is whichever type actually notifies -- notification sites now carry
     their holder, where the old code kept only a bool and discarded it;
  2. the ABSTRACT subject is normally its SUPERTYPE, so search upward;
  3. a supertype counts only if it declares THE REGISTRATION CONTRACT -- a method whose
     parameter type is the observer type.

PART 3 IS THE PART THE CORPUS CANNOT JUDGE. In all ten Kim observer units a notifying type
either has no abstract supertype at all or has one that declares the contract, so the weak rule
("any abstract supertype") and the strong rule give identical verdicts on every unit. Both
designs pass all five suites. `o1_supertype_without_contract.java` is the only thing that
separates them, and it was verified by BUILDING the weak variant, which scores it O1 = 1.

WHAT THE SEPARATOR TURNED OUT TO FIX, WHICH THE PLAN DID NOT PREDICT. A pure Composite scored
O2 = O3 = O4 = 1 and was FULLY RECOGNISED AS AN OBSERVER, because `Folder.show()` iterating
`List<Node>` and calling `show()` on each element is literally "loop a collection of an abstract
type and call a method on each element". The plan justified the separator as protecting O1 only.
It closes a cross-pattern false positive. `o1_composite_is_not_a_subject.java` pins it, verified
by building the variant with the separator removed, which scores it O2 = O3 = O4 = 1.
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

# (slug, expected vector, expected PIQS, what decides it)
CASES = [
    (
        "o1_supertype_with_contract",
        {"O1": 1, "O2": 1, "O3": 1, "O4": 1},
        100.0,
        "Broadcaster is abstract and declares enrol(Feed) -- the contract",
    ),
    (
        "o1_supertype_without_contract",
        {"O1": 0, "O2": 1, "O3": 1, "O4": 1},
        77.73,
        "Serialisable is abstract but declares no observer-typed parameter",
    ),
    (
        "o1_concrete_subject_no_supertype",
        {"O1": 0, "O2": 1, "O3": 1, "O4": 1},
        77.73,
        "Station notifies correctly but has no supertype at all",
    ),
    (
        "o1_composite_is_not_a_subject",
        {"O1": 0, "O2": 0, "O3": 0, "O4": 0},
        0.0,
        "Folder IS a Node and show() is Node's own operation -- self-recursion, not notification",
    ),
    (
        "o1_dual_role_observer_missing_callback",
        {"O1": 0, "O2": 1, "O3": 1, "O4": 0},
        51.82,
        "Hybrid is a declared Feed observer that does not implement ping()",
    ),
]


def _evaluate(slug: str, files: dict[str, str] | None = None) -> dict:
    if files is None:
        with open(os.path.join(FIXTURES, slug + ".java"), encoding="utf-8") as fh:
            files = {slug + ".java": fh.read()}
    return PIQSChecker().evaluate("observer", files)


def vector(slug: str, files: dict[str, str] | None = None) -> dict[str, int]:
    return {r["property_id"]: r["satisfaction"] for r in _evaluate(slug, files)["logical_assessment"]}


@pytest.mark.parametrize("slug,expected,expected_piqs,why", CASES)
def test_structural_o1_verdict(slug, expected, expected_piqs, why):
    assert vector(slug) == expected, f"{slug}: {why}"
    assert _evaluate(slug)["final_quality_result_piqs"]["result_percent"] == expected_piqs


def test_the_contract_clause_is_what_separates_the_two_supertype_fixtures():
    """The pair is the whole point, so it is asserted as a pair.

    Both files notify identically. They differ only in the supertype: `Broadcaster` declaring
    `enrol(Feed)` versus `Serialisable` declaring `encode()`. If O1 ever reads the same for both,
    the contract clause has stopped doing anything -- which is exactly what the weak variant
    does, and it scores the second file 1.
    """
    assert vector("o1_supertype_with_contract")["O1"] == 1
    assert vector("o1_supertype_without_contract")["O1"] == 0


def test_a_composite_is_not_recognised_as_an_observer():
    """The cross-pattern false positive the plan did not predict.

    Asserted on the whole vector, not just O1: the separator's effect here is on O2/O3/O4, which
    is what made the program count as an Observer in the first place.
    """
    assert vector("o1_composite_is_not_a_subject") == {"O1": 0, "O2": 0, "O3": 0, "O4": 0}


@pytest.mark.parametrize("slug,expected,expected_piqs,why", CASES)
def test_o1_survives_renaming(slug, expected, expected_piqs, why):
    """THE FINISHING RULE, tested behaviourally.

    Every user identifier is machine-renamed to nonsense and the vector must be unchanged. This
    is the direct proof that O1 no longer reads a method name: on the old build, renaming
    `notifyObservers` away flipped O1 from 1 to 0, which is what the three observer failures in
    tests/test_renaming_invariance.py were.

    These fixtures are not reachable from that suite -- `iter_cases()` covers the battery
    directories and Kim only, not tests/fixtures_parser -- so the check is made here explicitly
    rather than assumed.
    """
    with open(os.path.join(FIXTURES, slug + ".java"), encoding="utf-8") as fh:
        original = {slug + ".java": fh.read()}
    renamed = obfuscate(original, rename_files=False)
    assert vector(slug, renamed) == expected, (
        f"{slug}: the verdict moved under renaming -- O1 still reads an identifier"
    )


def test_subject_candidates_has_one_construction_site_and_no_string_literals():
    """The finishing rule, tested structurally as well as behaviourally.

    ONE SITE, because the eight readers of `subject_candidates` must never disagree about what a
    subject is. NO STRING LITERAL, because a literal there is the defect being removed -- and a
    behavioural test alone would not catch a literal that happens to be inert on this corpus.

    Read from the AST, so the prose above and the comments quoting the old hardcoded set do not
    trip it -- comments are not AST nodes.
    """
    with open(os.path.join(ROOT, "piqs", "checker.py"), encoding="utf-8") as fh:
        tree = ast.parse(fh.read())

    sites = [
        node
        for node in ast.walk(tree)
        if isinstance(node, ast.Assign)
        and any(isinstance(t, ast.Name) and t.id == "subject_candidates" for t in node.targets)
    ]
    assert len(sites) == 1, f"expected one construction site, found {len(sites)}"

    literals = [
        n.value
        for n in ast.walk(sites[0].value)
        if isinstance(n, ast.Constant) and isinstance(n.value, str)
    ]
    assert literals == [], f"subject_candidates is built from string literals: {literals}"
