"""Renaming must be decided per call site, not per token.

`_apply` used to swap every identifier token with no context, so a user-declared `add(Node)`
also rewrote `list.add(n)` -- emitting Java that does not compile, because `List` has no `m1`.
A renaming tool that changes which method is called does not measure name-independence.

The fix must not be a blocklist. `update` has to keep being renamed where the receiver is
ours, or the O4 evidence goes with it.
"""

from __future__ import annotations

import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)
sys.path.insert(0, HERE)

from piqs.obfuscator import build_rename_map, obfuscate  # noqa: E402
from test_renaming_invariance import iter_cases  # noqa: E402

FOLDER = (
    "import java.util.List;\n"
    "import java.util.ArrayList;\n"
    "interface Node { void show(); }\n"
    "class Folder implements Node {\n"
    "    private List<Node> kids = new ArrayList<>();\n"
    "    public void add(Node n) { kids.add(n); }\n"
    "    public void show() { for (Node k : kids) k.show(); }\n"
    "}\n"
)


def test_jdk_receiver_call_is_not_renamed() -> None:
    """A user method sharing a name with a JDK member must not rename the JDK call site."""
    src = (
        "import java.util.List;\n"
        "import java.util.ArrayList;\n"
        "interface Node { void show(); }\n"
        "class Folder implements Node {\n"
        "    private List<Node> kids = new ArrayList<>();\n"
        "    public void add(Node n) { kids.add(n); }\n"
        "    public void show() { for (Node k : kids) k.show(); }\n"
        "}\n"
    )
    out = obfuscate({"Folder.java": src}, rename_files=False)["Folder.java"]
    assert ".add(" in out, "the List.add call site must keep its JDK name"


def test_user_receiver_call_is_still_renamed() -> None:
    """The `update` evidence must survive: a user-typed receiver is still renamed.

    The `register` method is not in the task's version of this source, which asserts
    `".add(" in out` over a body that never calls `add`. Added so both halves of the
    assertion mean something: `update` renamed, `List.add` untouched, in one source.
    """
    src = (
        "import java.util.List;\n"
        "import java.util.ArrayList;\n"
        "interface Watcher { void update(String m); }\n"
        "class Station {\n"
        "    private List<Watcher> ws = new ArrayList<>();\n"
        "    public void register(Watcher w) { ws.add(w); }\n"
        "    public void publish(String m) { for (Watcher w : ws) w.update(m); }\n"
        "}\n"
    )
    out = obfuscate({"Station.java": src}, rename_files=False)["Station.java"]
    assert "update" not in out, "a user-typed receiver must still be renamed"
    assert ".add(" in out, "the JDK add call must survive"


# --------------------------------------------------------------------------------------- #
# The two new counters. A field nobody reads is the defect this change is fixing:
# `shadowed_jdk_members` has been written since the module was born and read by nothing.
# --------------------------------------------------------------------------------------- #

def test_jdk_member_sites_counts_the_calls_it_left_alone() -> None:
    rmap = build_rename_map({"Folder.java": FOLDER})
    assert rmap.jdk_member_sites == {"add": 1}, (
        "one `.add(` on a List receiver was left alone, and that decision must be countable"
    )
    assert "add" in rmap.mapping, "the declaration `void add(Node)` is still renamed"


def test_jdk_member_sites_is_non_empty_somewhere_in_the_real_corpus() -> None:
    """The defect was live, not hypothetical: real fixtures call JDK members by user names."""
    hits = {}
    for case in iter_cases():
        for name, count in build_rename_map(case.sources()).jdk_member_sites.items():
            hits[name] = hits.get(name, 0) + count
    assert hits, "no fixture exercises a JDK call site -- the corpus would not test the fix"


def test_a_withheld_name_is_renamed_nowhere_and_says_why() -> None:
    """An unresolvable receiver withholds the whole name, declaration included.

    Renaming the declaration but not the call would be just as broken as the bug being
    fixed, in the other direction, so the only safe answer is to leave the name alone.
    """
    src = (
        "class Box {\n"
        "    public void ship() { }\n"
        "}\n"
        "class Depot {\n"
        "    public void go() { make().ship(); }\n"        # receiver is a call, not a name
        "    public Box make() { return null; }\n"
        "}\n"
    )
    rmap = build_rename_map({"Box.java": src})
    assert "ship" in rmap.withheld_names
    assert "expression" in rmap.withheld_names["ship"], "the reason must be stated, not implied"
    assert "ship" not in rmap.mapping

    out = obfuscate({"Box.java": src}, rename_files=False)["Box.java"]
    assert out.count("ship") == 2, "declaration and call site both keep the original name"


def test_withheld_names_records_ambiguity_with_the_colliding_types() -> None:
    """Resolution is global and by name, so one name with two types resolves to neither."""
    src = (
        "class Item { public int value() { return 1; } }\n"
        "class Crate { }\n"
        "class A { void one(Item thing) { thing.value(); } }\n"
        "class B { void two(Crate thing) { } }\n"
    )
    rmap = build_rename_map({"A.java": src})
    assert "value" in rmap.withheld_names
    why = rmap.withheld_names["value"]
    assert "ambiguous" in why and "Crate" in why and "Item" in why, why


# --------------------------------------------------------------------------------------- #
# The receiver forms of the design table
# --------------------------------------------------------------------------------------- #

def test_this_and_this_field_receivers_resolve() -> None:
    src = (
        "import java.util.List;\n"
        "class Folder {\n"
        "    private List<Folder> kids;\n"
        "    private Folder parent;\n"
        "    public void show() { this.walk(); this.parent.walk(); this.kids.size(); }\n"
        "    public void walk() { }\n"
        "}\n"
    )
    out = obfuscate({"Folder.java": src}, rename_files=False)["Folder.java"]
    assert "walk" not in out, "`this.walk()` and `this.parent.walk()` are both ours"
    assert ".size()" in out, "`this.kids` is a List; `size` is not ours to rename"


def test_super_receiver_resolves_through_the_declared_supertype() -> None:
    src = (
        "class Base { public void show() { } }\n"
        "class Sub extends Base { public void show() { super.show(); } }\n"
    )
    out = obfuscate({"Sub.java": src}, rename_files=False)["Sub.java"]
    assert "show" not in out, "a user supertype means `super.show()` is ours"
    assert "super." in out


def test_super_on_a_foreign_supertype_is_left_alone() -> None:
    src = (
        "class Loud extends Thread { public void run() { super.run(); } }\n"
        "class Quiet { public void run() { } }\n"
    )
    out = obfuscate({"Loud.java": src}, rename_files=False)["Loud.java"]
    assert "super.run()" in out, "Thread is not ours, so `super.run()` must stay"


def test_static_call_on_a_user_type_is_renamed_and_on_a_jdk_type_is_not() -> None:
    src = (
        "class Registry { static void wipe() { } }\n"
        "class App { void go() { Registry.wipe(); System.out.println(); } }\n"
    )
    out = obfuscate({"Registry.java": src}, rename_files=False)["Registry.java"]
    assert "wipe" not in out, "a static call on one of our types is ours"
    assert "System.out.println()" in out


def test_method_reference_receiver_is_resolved_like_a_dot() -> None:
    """`list::add` is a call site too, and `::` hides it from a naive dot check."""
    src = (
        "import java.util.List;\n"
        "class Sink { public void add(String s) { } }\n"
        "class Pipe {\n"
        "    private List<String> buf;\n"
        "    private Sink sink;\n"
        "    void a() { go(buf::add); }\n"
        "    void b() { go(sink::add); }\n"
        "    void go(Object o) { }\n"
        "}\n"
    )
    out = obfuscate({"Pipe.java": src}, rename_files=False)["Pipe.java"]
    assert "::add" in out, "`buf` is a List: its `add` is the JDK's"
    assert out.count("::add") == 1, "`sink` is ours: its `add` is renamed"


def test_string_literal_receiver_is_a_jdk_receiver() -> None:
    src = (
        "class Fmt {\n"
        "    public int length() { return 0; }\n"
        "    void go() { int n = \"abc\".length(); }\n"
        "}\n"
    )
    out = obfuscate({"Fmt.java": src}, rename_files=False)["Fmt.java"]
    assert '"abc".length()' in out, "a literal receiver is never ours"
    assert "length" in build_rename_map({"Fmt.java": src}).mapping, (
        "and the declaration `public int length()` is still renamed"
    )


# --------------------------------------------------------------------------------------- #
# The dangerous case: resolution that is wrong rather than absent.
# --------------------------------------------------------------------------------------- #

def test_a_local_hidden_by_the_local_regex_gap_does_not_produce_a_wrong_answer() -> None:
    """A receiver whose type table is incomplete must not resolve confidently to the JDK.

    `_LOCAL_RE` consumes the `;` ending the previous statement, so `finditer` misses every
    second declaration in a run -- a defect that predates this change. Fed that partial view,
    the resolver saw only `Map<Integer,Integer> inventory` and concluded `inventory.stock(..)`
    was `Map.stock`, left the call alone, and renamed the declaration anyway. javac rejected
    the result. Both declarations must be visible to the type table, which then sees the
    collision and withholds the name.

    Taken from fixtures/kim/RefactoredPOSChatGPT, which failed exactly this way.
    """
    src = (
        "import java.util.Map;\n"
        "import java.util.HashMap;\n"
        "class Inv {\n"
        "    private Map<Integer, Integer> inventory = new HashMap<>();\n"
        "    public void stock(int id, int n) { inventory.put(id, n); }\n"
        "}\n"
        "class App {\n"
        "    public static void main(String[] a) {\n"
        "        int first = 1;\n"
        "        // a comment, between the previous `;` and the declaration\n"
        "        Inv inventory = new Inv();\n"
        "        inventory.stock(first, 10);\n"
        "    }\n"
        "}\n"
    )
    rmap = build_rename_map({"Inv.java": src})
    assert rmap.decls.seen_types["inventory"] == {"Map", "Inv"}, (
        "both declarations must reach the type table, comment and intervening `;` and all"
    )
    assert "inventory" in rmap.decls.ambiguous
    assert "stock" in rmap.withheld_names and "ambiguous" in rmap.withheld_names["stock"]

    out = obfuscate({"Inv.java": src}, rename_files=False)["Inv.java"]
    assert out.count("stock") == 2, "declaration and call must move together, or not at all"
    assert ".put(" in out, "the genuine JDK call is still left alone"


def test_consecutive_declarations_all_reach_the_type_table() -> None:
    src = (
        "class Node { void show() { } }\n"
        "class App {\n"
        "    void go() {\n"
        "        Node one = null;\n"
        "        Node two = null;\n"
        "        Node three = null;\n"
        "        one.show(); two.show(); three.show();\n"
        "    }\n"
        "}\n"
    )
    d = build_rename_map({"App.java": src}).decls
    assert d.type_of.get("one") == "Node"
    assert d.type_of.get("two") == "Node", "the second of a run is the one _LOCAL_RE misses"
    assert d.type_of.get("three") == "Node"

    out = obfuscate({"App.java": src}, rename_files=False)["App.java"]
    assert "show" not in out, "every receiver is ours, so every call site is renamed"
