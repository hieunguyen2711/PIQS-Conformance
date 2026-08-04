"""The checker's verdicts must not depend on identifier names.

For every fixture in `fixtures/`, evaluate the pattern on the original sources and on the
sources with every user-defined identifier machine-renamed, and require the
`(property_id, satisfaction)` list to be identical.

A failure here is a property that is keyed to a name rather than to structure.

Cases:
  * `fixtures/mutation_battery/`     -- 12 single-file cases, pattern from the filename prefix
  * `fixtures/mutation_battery_bdt/` -- 27 single-file cases, pattern from the filename
  * `fixtures/kim/`                  -- the 40 (program, pattern) scoring units in the manifest

`iter_cases()` and `compare()` are importable so the same case list can drive a report.
"""

from __future__ import annotations

import json
import os
import sys
from dataclasses import dataclass

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from piqs.checker import PIQSChecker  # noqa: E402
from piqs.obfuscator import build_rename_map, obfuscate  # noqa: E402

FIXTURES = os.path.join(ROOT, "fixtures")

# Battery filenames carry their pattern. Longest key first so "template" is not shadowed.
_PATTERN_BY_MARKER = [
    ("template", "template-method"),
    ("decorator", "decorator"),
    ("builder", "builder"),
    ("g1_", "singleton"),
    ("f4_", "factory-method"),
    ("s3_", "strategy"),
]


def _pattern_for(stem: str) -> str | None:
    for marker, pattern in _PATTERN_BY_MARKER:
        if marker in stem:
            return pattern
    return None


@dataclass(frozen=True)
class Case:
    """One (sources, pattern) pair to check for renaming invariance."""

    group: str
    name: str
    pattern: str
    files: tuple[tuple[str, str], ...]

    @property
    def id(self) -> str:
        return f"{self.group}:{self.name}:{self.pattern}"

    def sources(self) -> dict[str, str]:
        return dict(self.files)


def _battery_cases(subdir: str) -> list[Case]:
    d = os.path.join(FIXTURES, subdir)
    cases = []
    for fn in sorted(os.listdir(d)):
        if not fn.endswith(".java"):
            continue
        pattern = _pattern_for(fn[:-5])
        if pattern is None:
            continue
        with open(os.path.join(d, fn), encoding="utf-8", errors="ignore") as fh:
            src = fh.read()
        cases.append(Case(subdir, fn[:-5], pattern, ((fn, src),)))
    return cases


def _kim_cases() -> list[Case]:
    manifest_path = os.path.join(ROOT, "validation", "kim_file_manifest.json")
    if not os.path.isfile(manifest_path):
        return []
    with open(manifest_path) as fh:
        manifest = json.load(fh)

    by_program = {p["program"]: p for p in manifest["programs"]}
    cases = []
    for unit in manifest["scoring_units"]:
        prog = by_program[unit["program"]]
        root = os.path.join(FIXTURES, "kim", prog["program"])
        if not os.path.isdir(root):
            continue
        files = []
        for rel in prog["java_files"]:
            full = os.path.join(root, rel)
            with open(full, encoding="utf-8", errors="ignore") as fh:
                files.append((os.path.basename(rel), fh.read()))
        cases.append(
            Case("kim", f"{unit['case_study']}-{unit['llm']}", unit["pattern"], tuple(files))
        )
    return cases


def iter_cases() -> list[Case]:
    return _battery_cases("mutation_battery") + _battery_cases("mutation_battery_bdt") + _kim_cases()


def _verdicts(pattern: str, files: dict[str, str]) -> list[tuple[str, int]]:
    result = PIQSChecker().evaluate(pattern, files)
    return [(row["property_id"], row["satisfaction"]) for row in result["logical_assessment"]]


def compare(case: Case) -> tuple[list[tuple[str, int]], list[tuple[str, int]]]:
    """(verdicts on the original, verdicts on the renamed sources)."""
    original = case.sources()
    return _verdicts(case.pattern, original), _verdicts(case.pattern, obfuscate(original))


CASES = iter_cases()


@pytest.mark.parametrize("case", CASES, ids=[c.id for c in CASES])
def test_verdicts_survive_renaming(case: Case) -> None:
    before, after = compare(case)
    moved = [
        f"{pid}: {b} -> {a}"
        for (pid, b), (_, a) in zip(before, after)
        if b != a
    ]
    assert not moved, (
        f"{case.pattern} verdicts changed under renaming for {case.group}/{case.name}: "
        + ", ".join(moved)
    )


def test_obfuscator_preserves_structure() -> None:
    """The renamer must change identifiers and nothing else."""
    src = (
        "// keep me\n"
        "package com.example.app;\n"
        "import java.util.List;\n"
        "\n"
        "public interface Greeter {\n"
        "    String greet(String who);\n"
        "}\n"
        "class Loud implements Greeter {\n"
        "    private String prefix = \"Greeter says\";\n"
        "    @Override\n"
        "    public String greet(String who) {\n"
        "        int count = 1;\n"
        "        return prefix + who + count; /* Greeter */\n"
        "    }\n"
        "    public String toString() { return prefix; }\n"
        "}\n"
    )
    out = obfuscate({"Greeter.java": src}, rename_files=False)["Greeter.java"]

    assert "interface I1" in out and "class C1 implements I1" in out
    assert "String" in out and "List" in out                  # JDK types untouched
    assert "package com.example.app;" in out                  # package line untouched
    assert "import java.util.List;" in out                    # import untouched
    assert "// keep me" in out and "/* Greeter */" in out      # comments untouched
    assert '"Greeter says"' in out                            # string literal untouched
    assert "@Override" in out                                 # annotation untouched
    assert "public String toString()" in out                  # Object override preserved
    assert "greet" not in out.replace("// keep me", "")       # the method WAS renamed
    assert out.count("{") == src.count("{")                   # same structure
    assert out.count(";") == src.count(";")
    assert len(out.splitlines()) == len(src.splitlines())


def test_renaming_is_consistent_across_files() -> None:
    """One type gets one new name in every file that mentions it."""
    files = {
        "Shape.java": "interface Shape { double area(); }",
        "Circle.java": "class Circle implements Shape { public double area() { return 3.14; } }",
        "Registry.java": "class Registry { private Shape held; void keep(Shape s) { held = s; } }",
    }
    rmap = build_rename_map(files)
    new_shape = rmap.mapping["Shape"]
    out = obfuscate(files, rename_files=False)

    assert new_shape.startswith("I")
    for name, src in out.items():
        assert "Shape" not in src, f"{name} still mentions Shape"
    assert new_shape in out["Circle.java"] and new_shape in out["Registry.java"]
