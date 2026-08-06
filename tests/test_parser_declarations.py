"""Permanent regression tests for the three regex bugs the tree-sitter migration fixed.

One fixture and one test per category from the Step 3 difference table. Each asserts the
PARSER's answer -- the answer that is correct about the Java source -- so these keep holding
after the regex extractor is deleted. Each fixture carries an in-source comment explaining why
the regex got it wrong; the test names the category.

These are declaration-level facts only (phase 1). Method bodies are still text.
"""

from __future__ import annotations

import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from piqs.parser import extract_types  # noqa: E402

FIXTURES = os.path.join(os.path.dirname(os.path.abspath(__file__)), "fixtures_parser")


def load(name: str) -> dict:
    path = os.path.join(FIXTURES, name)
    with open(path, encoding="utf-8") as fh:
        return extract_types({name: fh.read()})


def fields_of(t) -> dict[str, str]:
    return {f.name: f.field_type for f in t.fields}


def methods_of(t) -> set[str]:
    return {m.name for m in t.methods}


# --------------------------------------------------------------------------------------- #
# generics
# --------------------------------------------------------------------------------------- #

def test_generics_two_type_arguments_field_is_found() -> None:
    """A field whose type carries two type arguments must be extracted, with its base type.

    The regex's field type group admitted no comma and no space, so `Map<String, Handler>`
    could not be spanned and the declaration vanished from the model entirely.
    """
    types = load("generic_map_field.java")
    reg = types["Registry"]
    got = fields_of(reg)

    assert got == {
        "handlers": "Map",
        "RATES": "Map",
        "grouped": "Map",
        "ordered": "List",
        "cached": "Handler",
        "primary": "Handler",
    }, f"field model wrong: {got}"

    # Modifiers still ride along on a recovered field.
    rates = next(f for f in reg.fields if f.name == "RATES")
    assert rates.modifiers == {"private", "static", "final"}

    # _base_name semantics: the ELEMENT type is not recorded. `Map<String, Handler>` is a
    # field of type Map, not of type Handler -- which is exactly why recovering these fields
    # cannot make a container look like a held reference to a project type.
    assert "Handler" not in {f.field_type for f in reg.fields if f.name in {"handlers", "grouped", "ordered"}}


# --------------------------------------------------------------------------------------- #
# nested-type
# --------------------------------------------------------------------------------------- #

def test_nested_type_members_belong_to_the_nested_type() -> None:
    """A nested type's methods and fields belong to it, not to the enclosing type -- and both
    types are still flattened to top-level entries keyed by simple name."""
    types = load("nested_type_members.java")

    assert set(types) == {"Outer", "Inner"}, "nested types must be flattened to top level"

    assert methods_of(types["Outer"]) == {"getValue"}, (
        "Inner's members leaked onto Outer -- the regex scanned the enclosing body text, "
        "which contains the nested body"
    )
    assert methods_of(types["Inner"]) == {"label", "build"}

    assert fields_of(types["Outer"]) == {"value": "int"}
    assert fields_of(types["Inner"]) == {"label": "String"}

    # Owners are attributed to the declaring type.
    assert {m.owner for m in types["Inner"].methods} == {"Inner"}
    assert {m.owner for m in types["Outer"].methods} == {"Outer"}


# --------------------------------------------------------------------------------------- #
# modifier
# --------------------------------------------------------------------------------------- #

def test_interface_default_and_static_modifiers_are_recorded() -> None:
    """`default` is recorded as a modifier, and has_body still separates concrete from abstract.

    The regex's modifier alternation had no `default`, so an interface default method was
    extracted with an empty modifier set.
    """
    types = load("interface_default_method.java")
    report = types["Report"]
    by_name = {m.name: m for m in report.methods}

    assert set(by_name) == {"header", "body", "render", "empty"}

    assert by_name["render"].modifiers == {"default"}
    assert by_name["render"].has_body is True
    assert by_name["render"].return_type == "String"

    assert by_name["empty"].modifiers == {"static"}
    assert by_name["empty"].has_body is True

    # The abstract primitives: no modifiers, no body. has_body is what Template Method reads,
    # and it must keep distinguishing `;` from `{ }`.
    for name in ("header", "body"):
        assert by_name[name].modifiers == set(), name
        assert by_name[name].has_body is False, name

    # An interface is an abstract type regardless of an explicit modifier.
    assert report.is_abstract is True
    assert report.kind == "interface"
