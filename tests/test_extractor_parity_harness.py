"""The parity harness must actually catch a difference.

`--a regex --b regex` reporting zero differences proves nothing on its own: an empty diff
function scores the same. This is the negative control. Each case perturbs exactly one fact
in the model and asserts the harness reports it, so a clean parity run means the extractors
agree rather than that the comparison is blind.

The last two cases pin the two normalisations that must NOT be reported: whitespace in body
strings, and member/type ordering.
"""

from __future__ import annotations

import copy
import os
import sys

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from piqs.checker import PIQSChecker  # noqa: E402
from validation.extractor_parity import diff_dumps, dump  # noqa: E402

SOURCE = {
    "Sample.java": (
        "abstract class Sample extends Base implements Alpha, Beta {\n"
        "    private static final Registry registry = new Registry();\n"
        "    protected int count;\n"
        "    Sample(String name) { this.count = 0; }\n"
        "    public final Widget build(String key, int size) { return new Widget(key); }\n"
        "    protected abstract void step();\n"
        "}\n"
    )
}


def _regex(files):
    return PIQSChecker()._extract_types_regex(files)


def _base_dump() -> dict:
    return dump(SOURCE, _regex)


def test_the_model_is_populated() -> None:
    """Guards the perturbations below: they are only meaningful on a non-empty model."""
    d = _base_dump()
    assert set(d) == {"Sample"}
    t = d["Sample"]
    assert t["kind"] == "class" and t["is_abstract"] is True
    assert t["extends"] == "Base" and t["implements"] == ["Alpha", "Beta"]
    assert {m["name"] for m in t["methods"]} == {"Sample", "build", "step"}
    assert {f["name"] for f in t["fields"]} == {"registry", "count"}


def _method(d: dict, name: str) -> dict:
    return next(m for m in d["Sample"]["methods"] if m["name"] == name)


def _field(d: dict, name: str) -> dict:
    return next(f for f in d["Sample"]["fields"] if f["name"] == name)


def _drop_method(d, name):
    d["Sample"]["methods"] = [m for m in d["Sample"]["methods"] if m["name"] != name]


def _drop_type(d, name):
    del d[name]


PERTURBATIONS = [
    ("type_kind", lambda d: d["Sample"].__setitem__("kind", "interface"), "kind"),
    ("type_is_abstract", lambda d: d["Sample"].__setitem__("is_abstract", False), "is_abstract"),
    ("type_extends", lambda d: d["Sample"].__setitem__("extends", "Other"), "extends"),
    ("type_implements", lambda d: d["Sample"].__setitem__("implements", ["Alpha"]), "implements"),
    ("type_body", lambda d: d["Sample"].__setitem__("body_normalised", "changed"), "body_normalised"),
    ("type_content", lambda d: d["Sample"].__setitem__("content_normalised", "changed"), "content_normalised"),
    ("method_missing", lambda d: _drop_method(d, "step"), "method-only-in-A"),
    ("method_return_type", lambda d: _method(d, "build").__setitem__("return_type", "Object"), "return_type"),
    ("method_param_types", lambda d: _method(d, "build").__setitem__("param_types", ["String"]), "param_types"),
    ("method_param_names", lambda d: _method(d, "build").__setitem__("param_names", ["k", "s"]), "param_names"),
    ("method_modifiers", lambda d: _method(d, "build").__setitem__("modifiers", ["public"]), "modifiers"),
    ("method_has_body", lambda d: _method(d, "step").__setitem__("has_body", True), "has_body"),
    ("method_is_constructor", lambda d: _method(d, "Sample").__setitem__("is_constructor", False), "is_constructor"),
    ("method_body", lambda d: _method(d, "build").__setitem__("body_normalised", "return null;"), "body_normalised"),
    ("method_owner", lambda d: _method(d, "build").__setitem__("owner", "Elsewhere"), "owner"),
    ("field_type", lambda d: _field(d, "count").__setitem__("field_type", "long"), "field_type"),
    ("field_modifiers", lambda d: _field(d, "registry").__setitem__("modifiers", ["private"]), "modifiers"),
    ("type_missing", lambda d: _drop_type(d, "Sample"), "type-only-in-A"),
]


@pytest.mark.parametrize(
    "label,perturb,expected_attribute",
    PERTURBATIONS,
    ids=[c[0] for c in PERTURBATIONS],
)
def test_perturbation_is_reported(label, perturb, expected_attribute) -> None:
    a = _base_dump()
    b = _base_dump()
    perturb(b)
    diffs = diff_dumps("Sample.java", a, b)
    assert diffs, f"{label}: the harness reported NO difference -- the comparison is blind"
    assert expected_attribute in {d.attribute for d in diffs}, (
        f"{label}: expected attribute {expected_attribute!r}, got {sorted({d.attribute for d in diffs})}"
    )


def test_identical_dumps_are_clean() -> None:
    assert diff_dumps("Sample.java", _base_dump(), _base_dump()) == []


def test_whitespace_is_not_a_difference() -> None:
    """Reformatting a body must not be reported -- only its content may be."""
    reflowed = {"Sample.java": SOURCE["Sample.java"].replace("    ", "\t\t").replace(" { ", "\n{\n")}
    a = dump(SOURCE, _regex)
    b = dump(reflowed, _regex)
    assert diff_dumps("Sample.java", a, b) == []


def test_ordering_is_not_a_difference() -> None:
    """Members are sorted by name before comparison, so declaration order is invisible."""
    a = _base_dump()
    b = copy.deepcopy(a)
    b["Sample"]["methods"].reverse()
    b["Sample"]["fields"].reverse()
    assert diff_dumps("Sample.java", a, b) == []
