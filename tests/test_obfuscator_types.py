"""`_collect` must read the declared type of every name it collects.

The declaration regexes already matched the type -- `_FIELD_RE` and `_LOCAL_RE` have had a
named `type` group all along -- and `_collect` threw it away. Stage 6 needs it to answer one
question about a call site: is the receiver's type one of ours, or the JDK's?

These tests pin the table itself, not the renaming that reads it. `type_of` stores the *base*
type: generics and array brackets are stripped, so a `List<Node>` field resolves to `List`
(the JDK class whose members are actually being called) and not to `Node`.

A name declared twice with two different types is worse than a name with no type at all: it
would resolve confidently and wrongly. Those land in `ambiguous` and are never resolved.
"""

from __future__ import annotations

import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from piqs.obfuscator import _base_type, _collect, _mask, _split_params  # noqa: E402


def decls(src: str):
    return _collect([_mask(src)[0]])


# --------------------------------------------------------------------------------------- #
# One test per declaration form the receiver resolver has to be able to read.
# --------------------------------------------------------------------------------------- #

def test_type_of_a_field() -> None:
    d = decls("class Folder { private Node child; }")
    assert d.type_of["child"] == "Node"


def test_type_of_a_generic_field_is_the_container_not_the_element() -> None:
    """`kids.add(x)` calls `List.add`, so `kids` must resolve to `List`, never to `Node`."""
    d = decls("class Folder { private List<Node> kids = new ArrayList<>(); }")
    assert d.type_of["kids"] == "List"


def test_type_of_an_array_field_is_the_element_type() -> None:
    d = decls("class Folder { private Node[] kids; }")
    assert d.type_of["kids"] == "Node"


def test_type_of_a_local() -> None:
    d = decls("class A { void go() { Node picked = null; } }")
    assert d.type_of["picked"] == "Node"


def test_type_of_a_foreach_element() -> None:
    d = decls("class A { void go() { for (Node kid : kids) { kid.show(); } } }")
    assert d.type_of["kid"] == "Node"


def test_type_of_a_catch_parameter() -> None:
    d = decls("class A { void go() { try { x(); } catch (IOException oops) { } } }")
    assert d.type_of["oops"] == "IOException"


def test_type_of_a_method_parameter() -> None:
    d = decls("class A { void keep(Node child, int depth) { } }")
    assert d.type_of["child"] == "Node"
    assert "depth" not in d.type_of                  # `int` is a keyword, never a receiver


def test_type_of_a_generic_method_parameter() -> None:
    d = decls("class A { void keep(List<Node> kids) { } }")
    assert d.type_of["kids"] == "List"


# --------------------------------------------------------------------------------------- #
# Ambiguity
# --------------------------------------------------------------------------------------- #

def test_a_name_declared_with_two_types_is_ambiguous_and_unresolved() -> None:
    src = (
        "class A { void one(Node item) { } }\n"
        "class B { void two(Shape item) { } }\n"
    )
    d = decls(src)
    assert "item" in d.ambiguous
    assert "item" not in d.type_of, "an ambiguous name must not keep either of its two types"


def test_ambiguity_is_sticky() -> None:
    """A third declaration must not un-ambiguate a name that already collided."""
    src = (
        "class A { void one(Node item) { } }\n"
        "class B { void two(Shape item) { } }\n"
        "class C { void three(Node item) { } }\n"
    )
    d = decls(src)
    assert "item" in d.ambiguous and "item" not in d.type_of


# --------------------------------------------------------------------------------------- #
# fields_of, for `this.f.m()`
# --------------------------------------------------------------------------------------- #

def test_fields_of_is_keyed_by_declaring_class() -> None:
    src = (
        "class Folder { private List<Node> kids; }\n"
        "class Leaf { private Node parent; }\n"
    )
    d = decls(src)
    assert d.fields_of["Folder"]["kids"] == "List"
    assert d.fields_of["Leaf"]["parent"] == "Node"
    assert "parent" not in d.fields_of["Folder"]


def test_fields_of_marks_a_class_local_collision_unusable() -> None:
    """Same class name in two files, same field name, two types -- resolve to nothing."""
    d = _collect([
        _mask("class Folder { private Node kids; }")[0],
        _mask("class Folder { private List<Node> kids; }")[0],
    ])
    assert d.fields_of["Folder"]["kids"] == ""


# --------------------------------------------------------------------------------------- #
# The helpers
# --------------------------------------------------------------------------------------- #

def test_base_type_strips_generics_arrays_and_qualifiers() -> None:
    assert _base_type("List<Node>") == "List"
    assert _base_type("Map<String, List<Node>>") == "Map"
    assert _base_type("Node[]") == "Node"
    assert _base_type("Node[][]") == "Node"
    assert _base_type("java.util.List") == "List"
    assert _base_type("com.example.Node") == "Node"
    assert _base_type("IOException | SQLException") == "", "multi-catch names no single type"
    assert _base_type("") == ""


def test_split_params_returns_type_and_name() -> None:
    assert _split_params("Node child, List<Node> kids") == [("Node", "child"), ("List", "kids")]
    assert _split_params("final Node child") == [("Node", "child")]
    assert _split_params("Node... kids") == [("Node", "kids")]
    assert _split_params("int[] sizes") == [("int", "sizes")]
    assert _split_params("") == []


def test_split_params_reads_the_type_left_of_the_name_not_the_first_token() -> None:
    """A qualified type must not resolve to its package: `java.util.List x` is a `List`."""
    assert _split_params("java.util.List<Node> kids") == [("List", "kids")]
