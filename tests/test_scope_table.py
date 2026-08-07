"""The Phase 2 scope table: `JavaMethod.locals` and `PIQSChecker._scope`.

Nothing reads the table yet. It is built and tested on its own so the verdict-moving step --
replacing the `t.body` text matching in `_evaluate_observer` / `_evaluate_composite` -- lands
separately and is measured separately.

WHY THE NEGATIVE CASES ARE THE POINT OF THIS FILE.

The thing being replaced is this, from `_evaluate_observer`:

    coll_fields = {name: elem for (elem, name) in elem_field_re.findall(t.body)}

`t.body` is the whole text between a class's braces, method bodies and signatures included, so
that regex cannot tell a declaration from anything else shaped like one. Measured on the
corpus, it feeds `coll_fields` three kinds of entry it should not:

    RefactoredPOSCopilot/Receipt.java:35  List<SaleLineItem> items = ...   a LOCAL variable
    RefactoredPOSCopilot/Sale.java:20     public List<SaleLineItem> getSaleLineItem() {
    RefactoredPOSClaude/Sale.java:38      public List<SaleComponent> getComponents() {

The last two are METHOD NAMES read as if they were collection variables. They are inert today
only by luck: `foreach_re` wants a bare identifier after the colon, and a call site always has
`()`. A scope table built from the AST cannot make that mistake -- and `test_method_name_*`
below is what stops someone reintroducing it.

Positive cases alone could not fail this file. A table that returned every identifier in the
program would pass all of them.
"""

from __future__ import annotations

import os
import re
import sys

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from piqs.checker import PIQSChecker  # noqa: E402
from piqs.parser import extract_types  # noqa: E402


def scope_of(src: str, type_name: str, method_name: str) -> dict[str, str | None]:
    """The scope table for one method, via the supported accessor."""
    types = extract_types({"T.java": src})
    t = types[type_name]
    m = next(x for x in t.methods if x.name == method_name)
    return PIQSChecker()._scope(t, m, types)


def locals_of(src: str, type_name: str, method_name: str) -> dict[str, str | None]:
    """Only the body-declared part -- what the parser contributes."""
    types = extract_types({"T.java": src})
    t = types[type_name]
    return next(x for x in t.methods if x.name == method_name).locals


# --------------------------------------------------------------------------------------- #
# Positive cases: the seven sources a name can enter method scope from.
# --------------------------------------------------------------------------------------- #

FIELDS_AND_PARAMS = """
import java.util.List;
class Base {
    protected List<Observer> inherited;
}
class Store extends Base {
    private List<Observer> owned;
    void fire(Observer target, int count) {
        List<Observer> declared = null;
    }
}
interface Observer { void update(); }
"""


def test_class_field_is_in_scope():
    assert scope_of(FIELDS_AND_PARAMS, "Store", "fire")["owned"] == "List"


def test_inherited_field_is_in_scope():
    assert scope_of(FIELDS_AND_PARAMS, "Store", "fire")["inherited"] == "List"


def test_parameters_are_in_scope():
    s = scope_of(FIELDS_AND_PARAMS, "Store", "fire")
    assert s["target"] == "Observer"
    assert s["count"] == "int"


def test_local_variable_is_in_scope():
    assert scope_of(FIELDS_AND_PARAMS, "Store", "fire")["declared"] == "List"


def test_parameters_are_not_duplicated_into_locals():
    """Parameters live in `param_names`/`param_types`. `locals` is body declarations only --
    one source of truth each, assembled by `_scope`."""
    body = locals_of(FIELDS_AND_PARAMS, "Store", "fire")
    assert "declared" in body
    assert "target" not in body and "count" not in body


DECL_FORMS = """
import java.util.List;
class Sink {
    void run(List<Observer> obs) {
        for (Observer each : obs) { each.update(); }
        obs.forEach(untyped -> untyped.update());
        obs.forEach((Observer typed) -> typed.update());
        try (java.util.Scanner res = new java.util.Scanner(System.in)) {
            res.nextLine();
        } catch (java.io.IOException caught) {
            caught.printStackTrace();
        }
    }
}
interface Observer { void update(); }
"""


def test_enhanced_for_variable_is_in_scope():
    assert scope_of(DECL_FORMS, "Sink", "run")["each"] == "Observer"


def test_typed_lambda_parameter_keeps_its_type():
    assert scope_of(DECL_FORMS, "Sink", "run")["typed"] == "Observer"


def test_untyped_lambda_parameter_is_named_with_no_type():
    """`o -> o.update()` puts `o` in scope. Its type is not written, so it is None -- the name
    is recorded, no type is invented. Step 3 takes the element type from the iterated
    collection instead."""
    s = scope_of(DECL_FORMS, "Sink", "run")
    assert "untyped" in s
    assert s["untyped"] is None


def test_try_with_resources_is_in_scope():
    assert scope_of(DECL_FORMS, "Sink", "run")["res"] == "Scanner"


def test_catch_parameter_is_in_scope():
    assert scope_of(DECL_FORMS, "Sink", "run")["caught"] == "IOException"


# --------------------------------------------------------------------------------------- #
# Negative cases. These are what make the file able to fail.
# --------------------------------------------------------------------------------------- #

# Reproduced verbatim in shape from RefactoredPOSCopilot/Sale.java.
METHOD_SIGNATURE = """
import java.util.ArrayList;
class Sale {
    private ArrayList<SaleLineItem> slis = new ArrayList<>();
    public ArrayList<SaleLineItem> getSaleLineItem() {
        return slis;
    }
}
class SaleLineItem { }
"""

# The pattern being replaced, copied from `_evaluate_observer`.
_ELEM_FIELD_RE = re.compile(
    r"\b(?:List|Set|Collection|ArrayList|LinkedList|HashSet|CopyOnWriteArrayList|Vector)"
    r"\s*<\s*([A-Za-z_][A-Za-z0-9_]*)\s*>\s+([A-Za-z_][A-Za-z0-9_]*)"
)


def test_method_name_is_not_a_variable():
    """Finding 4, pinned. `getSaleLineItem` is a method, not a collection reference."""
    s = scope_of(METHOD_SIGNATURE, "Sale", "getSaleLineItem")
    assert "getSaleLineItem" not in s
    assert s["slis"] == "ArrayList"


def test_method_name_guard_is_not_vacuous():
    """Proves the guard above protects against something real rather than restating the
    obvious: the regex it replaces DOES harvest the method name from that same source."""
    types = extract_types({"T.java": METHOD_SIGNATURE})
    harvested = {name for (_elem, name) in _ELEM_FIELD_RE.findall(types["Sale"].body)}
    assert "getSaleLineItem" in harvested, "fixture no longer reproduces the defect"
    assert "slis" in harvested


NESTED = """
class Outer {
    private String outerField;
    void run() {
        class LocalClass {
            private String localClassField;
            void inner() { String insideLocalClass = "x"; }
        }
        Runnable anon = new Runnable() {
            private String anonField;
            public void run() { String insideAnon = "y"; }
        };
        String mine = "z";
    }
}
"""


def test_nested_class_field_is_not_in_enclosing_scope():
    s = scope_of(NESTED, "Outer", "run")
    assert "localClassField" not in s
    assert "anonField" not in s
    assert s["outerField"] == "String"


def test_variable_inside_nested_class_body_is_not_in_enclosing_scope():
    s = scope_of(NESTED, "Outer", "run")
    assert "insideLocalClass" not in s
    assert "insideAnon" not in s
    # the enclosing method's own declarations survive the boundary
    assert s["mine"] == "String"
    assert s["anon"] == "Runnable"


SHADOW = """
class Shadow {
    private int x;
    private int untouched;
    void go() {
        String x = "local wins";
    }
}
"""


def test_local_shadows_field_of_the_same_name():
    s = scope_of(SHADOW, "Shadow", "go")
    assert s["x"] == "String", "the local must win over the field, as in Java"
    assert s["untouched"] == "int"


PARAM_SHADOW = """
class ParamShadow {
    private int v;
    void go(String v) { }
}
"""


def test_parameter_shadows_field_of_the_same_name():
    assert scope_of(PARAM_SHADOW, "ParamShadow", "go")["v"] == "String"


def test_own_field_shadows_inherited_field_of_the_same_name():
    """A THIRD shadowing relationship, and the one the other two did not cover.

    The two tests above are LOCAL-vs-FIELD and PARAMETER-vs-FIELD. This is
    FIELD-vs-INHERITED-FIELD, and it was inverted: `_effective_fields` returns own fields first
    and ancestors after, so a plain dict comprehension let the ancestor win.

    Java hides a superclass field behind a subclass field of the same name. Inside `Sub.write`,
    the bare `held` is `Component`, not `Base`'s `Object`.

    Why it is not cosmetic: D3 asks whether a wrapper forwards to THE HELD REFERENCE, and step 3
    resolves that receiver's type through this table. No corpus file shadows an inherited field,
    so all four suites pass with the bug present -- see docs/PROPERTY_SPEC.md, "What a green
    suite does not prove".
    """
    path = os.path.join(ROOT, "tests", "fixtures_parser", "shadowed_inherited_field.java")
    with open(path, encoding="utf-8") as fh:
        src = fh.read()

    types = extract_types({"shadowed_inherited_field.java": src})
    sub = types["Sub"]
    write = next(m for m in sub.methods if m.name == "write")

    # Preconditions, asserted rather than assumed -- this case is easy to render vacuous.
    assert [(f.name, f.field_type) for f in sub.fields] == [("held", "Component")]
    assert [(f.name, f.field_type) for f in PIQSChecker()._effective_fields(sub, types)] == [
        ("held", "Component"),
        ("held", "Object"),
    ], "the fixture must actually shadow: own field first, inherited second"

    assert PIQSChecker()._scope(sub, write, types)["held"] == "Component"


# --------------------------------------------------------------------------------------- #
# The table must not change what the corpus sees. A bodyless method has no locals at all.
# --------------------------------------------------------------------------------------- #

ABSTRACT = """
interface Contract { void op(java.util.List<String> in); }
"""


def test_bodyless_method_has_an_empty_table():
    types = extract_types({"T.java": ABSTRACT})
    m = next(x for x in types["Contract"].methods if x.name == "op")
    assert m.has_body is False
    assert m.locals == {}


@pytest.mark.parametrize(
    "src,type_name,method_name",
    [
        (FIELDS_AND_PARAMS, "Store", "fire"),
        (DECL_FORMS, "Sink", "run"),
        (NESTED, "Outer", "run"),
    ],
)
def test_scope_values_are_base_names(src, type_name, method_name):
    """Every recorded type is `_base_name`-normalised -- no generics, no dotted package, no
    array brackets -- so `name in types` is a valid project-type test."""
    for name, declared in scope_of(src, type_name, method_name).items():
        if declared is None:
            continue
        assert not re.search(r"[<>\[\].]", declared), f"{name} -> {declared!r} is not a base name"
