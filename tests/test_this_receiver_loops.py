"""`this.collection` must score identically to `collection`. It did not.

THE DEFECT. A textbook Observer, written the ordinary way:

    public void setNews(String news) {
        this.news = news;
        for (Channel channel : this.channels) {   // <-- this.
            channel.update(this.news);
        }
    }

scored `O1 0 · O2 0 · O3 0 · O4 0`, PIQS 0 -- NOT RECOGNISED AS OBSERVER AT ALL. Deleting the
four characters `this.` and changing nothing else scored `O1 0 · O2 1 · O3 1 · O4 1`, PIQS 77.73.
The two programs are the same program.

WHY THE WHOLE CRITICAL SET WENT TO 0. O2, O3 and O4 all flow from detecting the notification
loop, and all three are weight 3. O1 does not depend on the loop, which is why it reads 0 in both
columns here and is not what this file measures.

ALL SIX LOOP FORMS WERE AFFECTED, not the enhanced-for alone, and the Phase 2 step 3 traversal
work did not cover it -- the parser-reported traversals key on the collection name too.

TWO SITES, because the collection is resolved in two different places:

    form 1        `foreach_re` in piqs/checker.py -- a regex whose collection group matched a
                  bare identifier, so `this.channels` did not match
    forms 2-6     `_collection_of` in piqs/parser.py -- returned None for any node that was not
                  an `identifier`, and `this.channels` is a `field_access`

Fixing one and reporting the defect closed would have left five forms broken. Each site has its
own negative control below so a leak is attributable to the site that leaked.

WHY NO EXISTING SUITE CAUGHT IT. Kim's corpus contains zero `this.`-prefixed traversals -- the
grep is in the commit message -- so all five suites stay green with the defect present. And it
reads no identifier name, so tests/test_renaming_invariance.py cannot see it either: renaming
`channels` to `f2` leaves `this.f2` just as invisible as `this.channels`, so the verdicts are
unchanged and invariance holds. It is a SHAPE defect, the same class as the Decorator
field-scope defect -- it does not ask what a program is called, it scores one way of writing a
program far above another.

WHY THAT IS A VALIDITY PROBLEM AND NOT ONLY A SCORING ONE. `this.field` is the ordinary style
when a parameter shadows a field, which is what every setter does. Under generation, two models
writing the same design would score 0 and 77.73 on the receiver alone. Any difference between the
two conditions in how often they emit `this.` lands directly in C1 and is indistinguishable from
the effect the paper is measuring.

THE TWINS. `loopT<n>_*.java` is generated from `loop<n>_*.java` by a mechanical receiver rewrite
and differs in nothing else, so the comparison is verified by diff rather than asserted. The
plain twin is carried through every assertion as the control: a checker that scored everything 0
would satisfy "the two agree" and must fail here too.
"""

from __future__ import annotations

import os
import sys

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from piqs.checker import PIQSChecker  # noqa: E402

FIXTURES = os.path.join(os.path.dirname(os.path.abspath(__file__)), "fixtures_parser")

# (plain fixture, `this.` twin, which site resolves the collection for this form)
PAIRS = [
    ("loop1_enhanced_for", "loopT1_enhanced_for", "foreach_re (checker)"),
    ("loop2_indexed", "loopT2_indexed", "_collection_of (parser)"),
    ("loop3_lambda", "loopT3_lambda", "_collection_of (parser)"),
    ("loop4_method_ref", "loopT4_method_ref", "_collection_of (parser)"),
    ("loop5_stream", "loopT5_stream", "_collection_of (parser)"),
    ("loop6_iterator", "loopT6_iterator", "_collection_of (parser)"),
]


def _evaluate(slug: str) -> dict:
    with open(os.path.join(FIXTURES, slug + ".java"), encoding="utf-8") as fh:
        src = fh.read()
    return PIQSChecker().evaluate("observer", {slug + ".java": src})


def vector(slug: str) -> dict[str, int]:
    return {r["property_id"]: r["satisfaction"] for r in _evaluate(slug)["logical_assessment"]}


def piqs(slug: str) -> float:
    return _evaluate(slug)["final_quality_result_piqs"]["result_percent"]


@pytest.mark.parametrize("plain,twin,site", PAIRS)
def test_this_receiver_scores_identically_to_bare_identifier(plain, twin, site):
    """The whole point. Same program, one written `this.observers`, the other `observers`.

    Asserted as equality of the two vectors AND against the expected value, because equality
    alone is satisfied by a checker that returns 0 for both.
    """
    assert vector(plain) == vector(twin), (
        f"{twin} disagrees with {plain}: the receiver changed the verdict. Site: {site}"
    )
    assert vector(twin) == {"O1": 1, "O2": 1, "O3": 1, "O4": 1}, (
        f"{twin} is not recognised as Observer"
    )
    assert piqs(plain) == piqs(twin) == 100.0


@pytest.mark.parametrize("plain,twin,site", PAIRS)
def test_the_critical_set_is_what_the_defect_zeroed(plain, twin, site):
    """O2, O3 and O4 are the weight-3 critical set, and all three flow from loop detection.

    Stated separately from the vector equality because the vector test would still pass if a
    future change moved BOTH twins to 0 together. This one pins the direction.
    """
    v = vector(twin)
    assert v["O2"] == 1 and v["O3"] == 1 and v["O4"] == 1, (
        f"{twin}: critical set not satisfied -- the notification loop was not detected"
    )


NEGATIVES = [
    ("loopTN1_other_receiver_enhanced_for", "foreach_re (checker)"),
    ("loopTN2_other_receiver_for_each", "_collection_of (parser)"),
]


@pytest.mark.parametrize("slug,site", NEGATIVES)
def test_a_foreign_receiver_is_not_resolved_to_our_own_field(slug, site):
    """THE FALSIFIER. Only `this.` may resolve.

    `other.observers` is another object's collection. The trivial way to make all six twins pass
    is to strip any receiver and keep the trailing name -- that would light these up too, so
    without them the widening is unfalsifiable.
    """
    v = vector(slug)
    assert v == {"O1": 1, "O2": 0, "O3": 0, "O4": 0}, (
        f"{slug}: a foreign receiver resolved to our own field. The widening is too wide at {site}"
    )
    assert piqs(slug) == 22.27


def test_the_twins_differ_from_their_originals_only_in_the_receiver():
    """The comparison is worthless if the two files differ in anything else.

    Re-derives each twin from its original by the same mechanical rewrite and requires the file
    on disk to match, so an edit to one fixture that is not mirrored in the other fails here
    rather than silently weakening every assertion above.
    """
    for plain, twin, _site in PAIRS:
        with open(os.path.join(FIXTURES, plain + ".java"), encoding="utf-8") as fh:
            plain_body = fh.read().split("import java.util.*;", 1)[1]
        with open(os.path.join(FIXTURES, twin + ".java"), encoding="utf-8") as fh:
            twin_body = fh.read().split("import java.util.*;", 1)[1]
        rewritten = plain_body.replace("observers.", "this.observers.").replace(
            ": observers)", ": this.observers)"
        )
        assert rewritten == twin_body, (
            f"{twin}.java is no longer its original's receiver-rewrite of {plain}.java"
        )
        assert "this.observers" in twin_body and "this.observers" not in plain_body
