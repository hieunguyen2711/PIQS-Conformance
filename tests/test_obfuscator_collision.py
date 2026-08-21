"""The `Holder` fixture: source that already contains the names the obfuscator generates.

    class Holder {
        private int f1;
        private int amount;
        public void set(int v1) { int p1 = v1; this.amount = p1; }
        public void m1() { }
        public void store() { }
    }

`f1`, `v1`, `p1` and `m1` are exactly what the renamer emits. A tool that renames ONE NAME AT A
TIME can transiently create two `p1` in the same scope -- rename `v1 -> p1` while the parameter
`p1` is still called `p1` -- and either collide or silently capture the wrong binding.

Both Python obfuscators substitute EVERY name at once from a map that is checked to be a
bijection, so a swap (`f1 -> f2`, `amount -> f1`) stays a permutation and no intermediate state
exists. The assertions below pin that:

  * the map is injective -- two originals never share a target
  * the map is a permutation on the colliding subset -- no original is lost
  * the output still parses
  * the two Python tools agree on the SET of renamed names

Spoon renames one AST node at a time and its `CtRenameGenericVariableRefactoring` documents
that it "provides no variable rename checking, so renaming variables to a name that already
exists is possible". Whether it survives this fixture is checked by the Spoon arm; see
tools/spoon-obfuscator/ and validation/three_way_agreement.py.
"""

from __future__ import annotations

import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from piqs import obfuscator as regex_mod  # noqa: E402
from piqs import obfuscator_ts as ts_mod  # noqa: E402

HOLDER = """\
class Holder {
    private int f1;
    private int amount;
    public void set(int v1) { int p1 = v1; this.amount = p1; }
    public void m1() { }
    public void store() { }
}
"""

# The generated-looking names the fixture already contains.
COLLIDING = {"f1", "v1", "p1", "m1"}


def _bijection_check(mapping: dict[str, str]) -> None:
    targets = list(mapping.values())
    assert len(targets) == len(set(targets)), (
        "rename map is not injective; two names would collapse into one: "
        + repr(sorted(mapping.items()))
    )


def test_holder_map_is_a_bijection_in_both_python_tools() -> None:
    for label, build in (("regex", regex_mod.build_rename_map_regex),
                         ("tree-sitter", ts_mod.build_rename_map)):
        rmap = build({"Holder.java": HOLDER})
        _bijection_check(rmap.mapping)
        assert COLLIDING <= set(rmap.mapping), (
            f"{label}: the colliding names were not all discovered; "
            f"missing {sorted(COLLIDING - set(rmap.mapping))}"
        )


def test_holder_output_parses_and_loses_no_declaration() -> None:
    """A collapsed rename would show up as a name appearing twice where it appeared once."""
    out = ts_mod.obfuscate({"Holder.java": HOLDER}, rename_files=False)["Holder.java"]
    # Re-parsing is the check that the splice produced valid Java, not merely different text.
    ts_mod.parse("Holder.java", out)

    rmap = ts_mod.build_rename_map({"Holder.java": HOLDER})
    # Every field/param/local target must occur exactly as often as its original did.
    for original, new in rmap.mapping.items():
        assert HOLDER.count(original) == out.count(new), (
            f"{original!r} -> {new!r}: {HOLDER.count(original)} occurrences became "
            f"{out.count(new)}"
        )


def test_holder_is_a_swap_not_a_collision() -> None:
    """`f1` and `amount` both want an `f`-slot. The result must be a permutation."""
    rmap = ts_mod.build_rename_map({"Holder.java": HOLDER})
    assert rmap.mapping["f1"] != "f1", "f1 must move, or it is not being renamed at all"
    assert rmap.mapping["f1"] != rmap.mapping["amount"]
    assert {rmap.mapping["f1"], rmap.mapping["amount"]} == {"f1", "f2"}, (
        f"expected the two int fields to permute over f1/f2, got "
        f"{rmap.mapping['f1']} and {rmap.mapping['amount']}"
    )


def test_holder_both_python_tools_rename_the_same_names() -> None:
    """The VALUES may differ (numbering shifts); the SET of renamed names may not."""
    a = regex_mod.build_rename_map_regex({"Holder.java": HOLDER})
    b = ts_mod.build_rename_map({"Holder.java": HOLDER})
    assert set(a.mapping) == set(b.mapping), (
        f"regex only: {sorted(set(a.mapping) - set(b.mapping))}; "
        f"tree-sitter only: {sorted(set(b.mapping) - set(a.mapping))}"
    )
