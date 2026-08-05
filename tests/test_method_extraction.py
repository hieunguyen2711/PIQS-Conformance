"""A method call is not a method declaration.

`_METHOD_SIG_RE` had no guard against a receiver, so `kids.add(n);` inside a method body
parsed as a declaration of a method named `add`. Those phantom methods land in every
`JavaType.methods` list the checker builds, and any rule of the form "does a method exist
that does X" can then be satisfied by a method that was never declared. Phantoms can only
add satisfied properties, never remove them.

A declaration must carry a return type (or be the enclosing type's constructor) and must not
have a dot immediately before its name.
"""

from __future__ import annotations

import os
import sys

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from piqs.checker import PIQSChecker  # noqa: E402


def names(owner: str, body: str) -> set[str]:
    return {m.name for m in PIQSChecker()._extract_methods_regex(owner, body)}


# --------------------------------------------------------------------------------------- #
# Calls -- must never be read as declarations
# --------------------------------------------------------------------------------------- #

NOT_DECLARATIONS = [
    ("receiver_field", "kids.add(n);", "add"),
    ("receiver_this", "this.helper();", "helper"),
    ("receiver_super", "super.doThing();", "doThing"),
    ("receiver_new", "new Foo().bar();", "bar"),
    ("receiver_chained", "a.b().c();", "c"),
    ("bare_call", "setChanged();", "setChanged"),
    ("bare_call_with_arg", "notifyObservers(logEntry);", "notifyObservers"),
    # Same class of bug: `return` is not a return type.
    ("returned_call", "return compute();", "compute"),
]


@pytest.mark.parametrize(
    "label,statement,phantom",
    NOT_DECLARATIONS,
    ids=[c[0] for c in NOT_DECLARATIONS],
)
def test_call_is_not_a_declaration(label: str, statement: str, phantom: str) -> None:
    body = f"    public void wrapper() {{\n        {statement}\n    }}\n"
    found = names("Holder", body)
    assert found == {"wrapper"}, (
        f"{label}: `{statement}` leaked a phantom method. "
        f"expected {{'wrapper'}}, got {sorted(found)}"
    )
    assert phantom not in found


def test_the_reported_case() -> None:
    """The example from the bug report: Dir declares one method, not two."""
    body = (
        "    private List<String> kids = new ArrayList<>();\n"
        "    public void insert(String n) { kids.add(n); }\n"
    )
    assert names("Dir", body) == {"insert"}


def test_chained_calls_leak_nothing() -> None:
    body = (
        "    public void go() {\n"
        "        registry.lookup(key).activate().flush();\n"
        "        System.out.println(value);\n"
        "        Collections.sort(items);\n"
        "    }\n"
    )
    assert names("Runner", body) == {"go"}


# --------------------------------------------------------------------------------------- #
# Declarations -- must all still be found
# --------------------------------------------------------------------------------------- #

DECLARATIONS = [
    ("ordinary", "Svc", "public void insert(String n) { }", "insert"),
    ("throws_clause", "Svc", "void read() throws IOException { }", "read"),
    ("generic_method", "Svc", "public <T> List<T> map(Function<T> f) { return null; }", "map"),
    ("constructor", "AuditLog", "AuditLog(String name) { }", "AuditLog"),
    ("annotated", "Svc", "@Override public void update() { }", "update"),
    ("abstract_no_body", "Svc", "protected abstract void step();", "step"),
    ("static_main", "Svc", "public static void main(String[] a) { }", "main"),
]


@pytest.mark.parametrize(
    "label,owner,source,expected",
    DECLARATIONS,
    ids=[c[0] for c in DECLARATIONS],
)
def test_declaration_is_found(label: str, owner: str, source: str, expected: str) -> None:
    found = names(owner, f"    {source}\n")
    assert expected in found, f"{label}: lost the declaration `{source}`, got {sorted(found)}"


def test_interface_methods_survive() -> None:
    body = "    void attach(Obs o);\n    int size();\n    Obs find(String key);\n"
    assert names("Subject", body) == {"attach", "size", "find"}


def test_constructor_is_flagged_as_constructor() -> None:
    methods = PIQSChecker()._extract_methods_regex("AuditLog", "    AuditLog(String name) { }\n")
    ctors = [m for m in methods if m.is_constructor]
    assert [m.name for m in ctors] == ["AuditLog"]


def test_return_type_and_params_still_parse() -> None:
    body = "    public Wallet createWallet(String currency, int limit) { return null; }\n"
    m = next(m for m in PIQSChecker()._extract_methods_regex("Factory", body) if m.name == "createWallet")
    assert m.return_type == "Wallet"
    assert m.param_types == ["String", "int"]
    assert m.param_names == ["currency", "limit"]
