"""The tree-sitter obfuscator: what it renames, and what it must never touch.

Each test names one construct the regex module either got wrong or could not see. The two
headline cases are pinned first because they are the reason this module exists:

* `test_ts_renames_all_consecutive_locals` -- `_LOCAL_RE` opens with `(?:^|[;{}])`, which
  CONSUMES the `;` ending the previous statement, leaving `finditer` no anchor for the next
  one. Every second declaration in a run is skipped. Run against `piqs.obfuscator`, this test
  fails with `declarations absent from the rename map: ['b', 'alpha', 'gamma']` -- `a` renamed,
  `b` missed, `alpha` missed, `beta` renamed, `gamma` missed, exactly the alternating pattern
  the consumed `;` predicts.

* `test_ts_does_not_rename_a_constructor_call_type` -- `_METHOD_SIG_RE` matches *word word `(`*,
  so `new DecimalFormat("$0.00")` reads as a declaration named `DecimalFormat` with return type
  `new`, and a JDK class is renamed to a method name. The output does not compile.
"""

from __future__ import annotations

import os
import re
import sys

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from piqs.obfuscator_ts import (  # noqa: E402
    JavaParseError,
    build_rename_map,
    obfuscate,
)


def _one(src: str, name: str = "T.java") -> str:
    return obfuscate({name: src}, rename_files=False)[name]


def _tokens(text: str) -> set[str]:
    return set(re.findall(r"[A-Za-z_$][A-Za-z0-9_$]*", text))


# --------------------------------------------------------------------------------------- #
# The two defects the regex module has
# --------------------------------------------------------------------------------------- #

CONSECUTIVE = """\
class Runner {
    void go() {
        int a = 1, b = 2;
        Alpha alpha = new Alpha();
        Beta beta = new Beta();
        Gamma gamma = new Gamma();
    }
}
class Alpha { }
class Beta { }
class Gamma { }
"""


def test_ts_renames_all_consecutive_locals() -> None:
    """`int a = 1, b = 2;` is ONE node with TWO declarators, and a run of declarations has no
    alternating hole. The regex module misses `b`, `alpha` and `gamma`."""
    rmap = build_rename_map({"Runner.java": CONSECUTIVE})
    missed = [n for n in ("a", "b", "alpha", "beta", "gamma") if n not in rmap.mapping]
    assert not missed, f"declarations absent from the rename map: {missed}"

    out = _one(CONSECUTIVE, "Runner.java")
    survivors = [n for n in ("a", "b", "alpha", "beta", "gamma")
                 if re.search(rf"\b{n}\b", out)]
    assert not survivors, f"names still present in the output: {survivors}"


def test_ts_does_not_rename_a_constructor_call_type() -> None:
    """`new DecimalFormat("$0.00")` is an object_creation_expression, not a declaration."""
    src = (
        "import java.text.DecimalFormat;\n"
        "class Till {\n"
        "    void show(double amount) {\n"
        "        DecimalFormat df = new DecimalFormat(\"$0.00\");\n"
        "        System.out.println(df.format(amount));\n"
        "    }\n"
        "}\n"
    )
    rmap = build_rename_map({"Till.java": src})
    assert "DecimalFormat" not in rmap.mapping

    out = _one(src, "Till.java")
    assert "new DecimalFormat(\"$0.00\")" in out
    assert "import java.text.DecimalFormat;" in out
    assert "df" not in _tokens(out)          # the LOCAL was renamed
    assert ".format(" in out                 # the JDK member was not


# --------------------------------------------------------------------------------------- #
# Declaration sites
# --------------------------------------------------------------------------------------- #

def test_ts_constructor_name_follows_class_name() -> None:
    """A constructor's name MUST equal its class's. It is never assigned a name of its own."""
    src = "class Foo {\n    Foo() { }\n    Foo(int x) { this(); }\n}\n"
    rmap = build_rename_map({"Foo.java": src})
    new = rmap.mapping["Foo"]
    assert new.startswith("C")

    out = _one(src, "Foo.java")
    assert f"class {new} {{" in out
    assert out.count(f"{new}(") == 2         # both constructors follow the class
    assert "Foo" not in _tokens(out)


def test_ts_unqualified_call_is_renamed() -> None:
    """`helper()` has no `object` field: an implicit `this` call is never a foreign member."""
    src = "class A {\n    void helper() { }\n    void go() { helper(); }\n}\n"
    rmap = build_rename_map({"A.java": src})
    new = rmap.mapping["helper"]
    out = _one(src, "A.java")
    assert f"void {new}()" in out and f"{new}();" in out
    assert "helper" not in _tokens(out)


def test_ts_this_receiver_is_renamed() -> None:
    """`this.helper()` resolves through the enclosing class, which is one of ours."""
    src = "class A {\n    void helper() { }\n    void go() { this.helper(); }\n}\n"
    rmap = build_rename_map({"A.java": src})
    new = rmap.mapping["helper"]
    out = _one(src, "A.java")
    assert f"this.{new}();" in out
    assert "helper" not in _tokens(out)


# --------------------------------------------------------------------------------------- #
# The receiver rule
# --------------------------------------------------------------------------------------- #

def test_ts_jdk_receiver_is_not_renamed() -> None:
    """`kids.add(n)` where `kids` is a `List` is `java.util.List.add` and must survive.

    The user's own `add(Node)` IS renamed -- it is a user declaration -- and so are its call
    sites. Both facts have to hold at once, which is what makes the output compile.
    """
    src = (
        "import java.util.List;\n"
        "import java.util.ArrayList;\n"
        "class Node {\n"
        "    private List<Node> kids = new ArrayList<>();\n"
        "    void add(Node n) { kids.add(n); }\n"
        "    void copy(Node other) { other.add(this); }\n"
        "}\n"
    )
    rmap = build_rename_map({"Node.java": src})
    new_add = rmap.mapping["add"]
    new_node = rmap.mapping["Node"]
    new_kids = rmap.mapping["kids"]

    out = _one(src, "Node.java")
    assert f"{new_kids}.add(" in out, "the JDK List.add call site was renamed"
    assert f"void {new_add}({new_node} " in out, "the user declaration was not renamed"
    assert f".{new_add}(this)" in out, "the user call site was not renamed"
    assert rmap.jdk_member_sites.get("add") == 1


def test_ts_method_reference_follows_the_same_rule() -> None:
    """`Watcher::update` is ours; `list::add` is not. The member after `::` obeys the rule
    that governs the member after `.`."""
    src = (
        "import java.util.List;\n"
        "import java.util.ArrayList;\n"
        "interface Watcher { void ping(); }\n"
        "class Bus {\n"
        "    private List<String> log = new ArrayList<>();\n"
        "    Runnable a(Watcher w) { return w::ping; }\n"
        "    void b() { log.forEach(log::add); }\n"
        "}\n"
    )
    rmap = build_rename_map({"Bus.java": src})
    new_ping = rmap.mapping["ping"]
    new_log = rmap.mapping["log"]

    out = _one(src, "Bus.java")
    assert f"::{new_ping};" in out, "the user method reference was not renamed"
    assert f"{new_log}::add" in out, "the JDK method reference was renamed"


def test_ts_qualified_super_call_resolves_through_the_supertype() -> None:
    """`Anchor.super.pull()` names a member of Anchor's SUPERTYPE, not of Anchor.

    tree-sitter reports `object = identifier "Anchor"` with the `super` as a separate child.
    Reading the object alone names the wrong type; the regex module instead rebuilds the chain
    `Anchor.super`, looks for a FIELD called `super` on Anchor, finds none, and withholds
    `pull` everywhere.
    """
    src = (
        "interface Feed { int pull(); }\n"
        "class Base implements Feed { public int pull() { return 1; } }\n"
        "class Anchor extends Base {\n"
        "    class Nested { int reach() { return Anchor.super.pull(); } }\n"
        "}\n"
    )
    rmap = build_rename_map({"Feed.java": src})
    assert "pull" not in rmap.withheld_names
    new = rmap.mapping["pull"]

    out = _one(src, "Feed.java")
    assert f".super.{new}()" in out
    assert "pull" not in _tokens(out)


# --------------------------------------------------------------------------------------- #
# What must never change
# --------------------------------------------------------------------------------------- #

def test_ts_import_and_package_untouched() -> None:
    src = (
        "package com.demo.app;\n"
        "import java.util.List;\n"
        "import static java.util.Arrays.asList;\n"
        "class App { }\n"
    )
    out = _one(src, "App.java")
    assert "package com.demo.app;" in out
    assert "import java.util.List;" in out
    assert "import static java.util.Arrays.asList;" in out


def test_ts_annotation_untouched() -> None:
    """An annotation NAME is not ours. Its arguments are ordinary expressions and are renamed."""
    src = (
        "interface Greeter { String greet(); }\n"
        "class Loud implements Greeter {\n"
        "    static final String TAG = \"x\";\n"
        "    @Override\n"
        "    @SuppressWarnings(\"unchecked\")\n"
        "    public String greet() { return TAG; }\n"
        "}\n"
    )
    rmap = build_rename_map({"G.java": src})
    out = _one(src, "G.java")
    assert "@Override" in out
    assert "@SuppressWarnings(\"unchecked\")" in out
    assert rmap.mapping["TAG"] in out and "TAG" not in _tokens(out)


def test_ts_label_untouched() -> None:
    """A label and its `break` / `continue` target must both stay or both change. Never
    renaming either is the simplest choice that is always correct."""
    src = (
        "class L {\n"
        "    void go() {\n"
        "        outer: for (int i = 0; i < 3; i++) {\n"
        "            for (int j = 0; j < 3; j++) {\n"
        "                if (j == 1) continue outer;\n"
        "                if (i == 2) break outer;\n"
        "            }\n"
        "        }\n"
        "    }\n"
        "}\n"
    )
    out = _one(src, "L.java")
    assert "outer:" in out
    assert "continue outer;" in out
    assert "break outer;" in out


def test_ts_string_and_comment_untouched() -> None:
    src = (
        "class Tree {\n"
        "    // add(Node) is the interesting one\n"
        "    /* also add(Node) */\n"
        "    void add(Node n) { System.out.println(\"add\"); }\n"
        "}\n"
        "class Node { }\n"
    )
    out = _one(src, "Tree.java")
    assert "// add(Node) is the interesting one" in out
    assert "/* also add(Node) */" in out
    assert '"add"' in out
    assert "void add(" not in out              # the declaration WAS renamed


def test_ts_whitespace_is_byte_identical_outside_renames() -> None:
    """Only identifier spans are spliced, so line count and punctuation counts cannot move."""
    src = (
        "class   Spaced {\n"
        "\n"
        "\t void  go ( int x )  {   int y = x ;  }\n"
        "\n"
        "}\n"
    )
    out = _one(src, "Spaced.java")
    assert len(out.splitlines()) == len(src.splitlines())
    for ch in "{};()\t":
        assert out.count(ch) == src.count(ch), ch


# --------------------------------------------------------------------------------------- #
# Cross-cutting policy
# --------------------------------------------------------------------------------------- #

def test_ts_overriding_methods_get_the_same_new_name() -> None:
    """Renaming is global BY NAME, which is what keeps an override attached to its contract.

    Per-declaration-site renaming looks more correct with a parser in hand and silently breaks
    this: the interface method and the implementing method would get different names, and the
    subclass would no longer override anything.
    """
    files = {
        "Watcher.java": "interface Watcher { void notifyOf(String m); }\n",
        "Screen.java": (
            "class Screen implements Watcher {\n"
            "    public void notifyOf(String m) { }\n"
            "}\n"
        ),
    }
    rmap = build_rename_map(files)
    new = rmap.mapping["notifyOf"]
    assert new.startswith("m")

    new_param = rmap.mapping["m"]
    out = obfuscate(files, rename_files=False)
    assert f"void {new}(String {new_param})" in out["Watcher.java"]
    assert f"public void {new}(String {new_param})" in out["Screen.java"]
    for src in out.values():
        assert "notifyOf" not in _tokens(src)


def test_ts_unparseable_input_raises() -> None:
    """tree-sitter is error-tolerant and always returns a tree, so a walk over a broken file
    yields an EMPTY result -- indistinguishable from "this file declares nothing". Refusing is
    the only way that failure is visible."""
    broken = "class Broken { void go() { if ( } }\n"
    with pytest.raises(JavaParseError):
        obfuscate({"Broken.java": broken})
    with pytest.raises(JavaParseError):
        build_rename_map({"Broken.java": broken})


def test_ts_enum_constants_are_renamed() -> None:
    """`enum E { A, B; }` -- the regex needs `type name;` and `A, B;` has a comma, so it never
    saw an enum constant at all."""
    src = "enum Flavour { A, B;\n    void use() { }\n}\n"
    rmap = build_rename_map({"Flavour.java": src})
    assert "A" in rmap.mapping and "B" in rmap.mapping
    out = _one(src, "Flavour.java")
    assert "A" not in _tokens(out) and "B" not in _tokens(out)


def test_ts_lambda_parameters_are_renamed() -> None:
    """`(observable, arg) -> ...` is an `inferred_parameters` node. The regex has no
    lambda-parameter handling of any kind."""
    src = (
        "import java.util.Observable;\n"
        "class Audit {\n"
        "    void wire(Observable o) {\n"
        "        o.addObserver((observable, arg) -> System.out.println(arg));\n"
        "    }\n"
        "}\n"
    )
    rmap = build_rename_map({"Audit.java": src})
    assert "observable" in rmap.mapping and "arg" in rmap.mapping
    out = _one(src, "Audit.java")
    assert "observable" not in _tokens(out) and "arg" not in _tokens(out)
    assert ".addObserver(" in out              # the JDK member survives


def test_ts_type_parameters_are_left_alone() -> None:
    """`T` in `class Box<T>` is a type VARIABLE, not a user class. It is never in the type
    table, so `T` in the body is never in the map either."""
    src = "class Box<T> {\n    private T held;\n    T get() { return held; }\n}\n"
    rmap = build_rename_map({"Box.java": src})
    assert "T" not in rmap.mapping
    out = _one(src, "Box.java")
    assert "<T>" in out and "private T " in out and "T " in out


def test_ts_the_rename_map_is_a_bijection() -> None:
    """Distinct originals must map to distinct targets, or two names collapse into one and the
    output stops being a faithful renaming of the input. See `Holder` in
    tests/test_obfuscator_collision.py for the case that makes this bite."""
    src = (
        "class Holder {\n"
        "    private int f1;\n"
        "    private int amount;\n"
        "    public void set(int v1) { int p1 = v1; this.amount = p1; }\n"
        "    public void m1() { }\n"
        "    public void store() { }\n"
        "}\n"
    )
    rmap = build_rename_map({"Holder.java": src})
    targets = list(rmap.mapping.values())
    assert len(targets) == len(set(targets)), f"not a bijection: {rmap.mapping}"
