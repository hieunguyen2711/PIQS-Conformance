"""How many wrappers does the Decorator same-component rule actually change? Measured per PROGRAM.

WHY THIS SCRIPT EXISTS, AND WHY THE ANSWER IT REPLACES WAS UNSUPPORTED.

Commit e2acb66 changed `isDecorator` to require that the wrapped field's type is one of the
components the class conforms to. The effect was reported as "0 affected across 212 single-file
programs". The conclusion was right. The METHOD was not, and the flaw is worth stating because it
is easy to repeat:

    KIM HAS NO SINGLE-FILE PROGRAMS. All 12 are multi-file, 6 to 16 files each.

`_component_type_names` only sees the types in the dict it is handed. Scanning a corpus file by
file, a class whose interface is declared in a SIBLING file has that interface absent from
`types`, so `conformed` comes back empty and the candidate loop `continue`s before the rule is
ever reached -- and `field_type in component_names` fails for the same reason. The class is
invisible from both directions. A file-by-file scan therefore CANNOT find an affected Kim wrapper,
whether or not one exists. Reporting zero from it is reporting the method, not the corpus.

So: one PROGRAM at a time. A Kim program is all of its files together, exactly as
`run_scorer.py` evaluates it. A battery or parser fixture is one self-contained file, which is
what those are.

WHAT IT REPORTS, AND WHY THE ANSWER IS NOT ZERO.

For every class in every program it computes the two field lists the two versions of the rule
produce:

    loose   fields whose type is any abstract type in the program   (before e2acb66)
    strict  fields whose type is one this class CONFORMS TO         (after)

and reports every class where they differ, in two kinds:

    ADMISSION LOST        loose is non-empty, strict is empty. The class WAS a decorator
                          candidate and is not one now. This is the object-adapter case.
    FIELD LIST NARROWED   both non-empty, but strict is smaller. The class is still a candidate,
                          but D3/D4/D6 now ask about fewer fields -- which is the difference
                          between filtering admission and filtering the field list.

**The expected output is 3, not 0.** e2acb66 added three fixtures whose whole purpose is to be
affected by this rule. A run that reports zero means the script is broken, not that the corpus is
clean: a measurement that can only ever return zero proves nothing about the corpus. Those three
are this script's positive control, and they are what makes the zero for everything ELSE mean
something.

    python3 validation/decorator_rule_effect.py

Exit code is 0 whatever it finds -- this is a measurement, not a guard. The guard for the rule
itself is the battery case `t5_object_adapter_rejected_as_decorator__FAIL`.
"""

from __future__ import annotations

import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from piqs.checker import PIQSChecker  # noqa: E402

MANIFEST = os.path.join(ROOT, "validation", "kim_file_manifest.json")

# Single-file groups. Each .java file in these is a self-contained program.
SINGLE_FILE_DIRS = ("fixtures/mutation_battery", "fixtures/mutation_battery_bdt",
                    "tests/fixtures_parser")

# Fixtures added by e2acb66 for this exact rule. They are the POSITIVE CONTROL: the script must
# find them, and they are excluded when reporting the effect on the pre-existing corpus.
INTRODUCED_BY_THE_RULE = {
    "tests/fixtures_parser/object_adapter_not_a_decorator.java",
    "tests/fixtures_parser/decorator_delegates_to_unrelated_component.java",
    "fixtures/mutation_battery_bdt/t5_object_adapter_rejected_as_decorator__FAIL.java",
}


def programs() -> list[tuple[str, dict[str, str]]]:
    """Every unit as (label, {basename: source}). A Kim program is ALL its files together."""
    out: list[tuple[str, dict[str, str]]] = []

    with open(MANIFEST) as fh:
        manifest = json.load(fh)
    for prog in manifest["programs"]:
        root = os.path.join(ROOT, "fixtures", "kim", prog["program"])
        if not os.path.isdir(root):
            continue
        files = {}
        for rel in prog["java_files"]:
            with open(os.path.join(root, rel), encoding="utf-8", errors="ignore") as fh:
                files[os.path.basename(rel)] = fh.read()
        out.append((f"kim/{prog['program']} ({len(files)} files)", files))

    for sub in SINGLE_FILE_DIRS:
        d = os.path.join(ROOT, sub)
        for fn in sorted(os.listdir(d)):
            if not fn.endswith(".java"):
                continue
            with open(os.path.join(d, fn), encoding="utf-8", errors="ignore") as fh:
                out.append((f"{sub}/{fn}", {fn: fh.read()}))
    return out


def wrappers(files: dict[str, str]) -> list[tuple[str, list[str], list[str]]]:
    """(class name, loose field types, strict field types) for every class with a loose match.

    THE `conformed` GATE IS PART OF BOTH RULES AND MUST BE MODELLED. The first version of this
    script left it out, and reported 16 affected wrappers instead of 3. The pre-e2acb66 code was:

        conformed = {c for c in component_names if self._conforms_to(w, c, types)}
        if not conformed:
            continue                        # <-- present BEFORE the change too
        wrapped_fields = [... if f.field_type in component_names]

    A class that conforms to no abstract type was never a decorator candidate under EITHER rule,
    so it has no admission to lose. Dropping the gate counted every `Context`-holds-a-`Strategy`
    and `Director`-holds-a-`Builder` in the corpus as an effect of a change that did not touch
    them. The difference between the two rules is ONLY in the field list -- `component_names`
    versus `conformed` -- and a script measuring that difference has to hold everything else
    identical, or it measures itself.
    """
    svc = PIQSChecker()
    types = svc._extract_types(files)
    component_names = svc._component_type_names(types)
    rows = []
    for w in (t for t in types.values() if t.kind == "class"):
        conformed = {c for c in component_names if svc._conforms_to(w, c, types)}
        if not conformed:
            continue
        loose = [f.field_type for f in w.fields if f.field_type in component_names]
        strict = [f.field_type for f in w.fields if f.field_type in conformed]
        if loose:
            rows.append((w.name, loose, strict))
    return rows


def main() -> int:
    admission_lost, narrowed = [], []
    n_units = 0
    n_kim = 0

    for label, files in programs():
        n_units += 1
        if label.startswith("kim/"):
            n_kim += 1
        for name, loose, strict in wrappers(files):
            if not strict:
                admission_lost.append((label, name, loose))
            elif len(strict) < len(loose):
                dropped = sorted(set(loose) - set(strict))
                narrowed.append((label, name, loose, strict, dropped))

    print(f"units evaluated: {n_units}  ({n_kim} Kim programs, all multi-file, "
          f"+ {n_units - n_kim} single-file programs)")
    print()

    print(f"ADMISSION LOST -- was a decorator candidate, is not one now: {len(admission_lost)}")
    for label, name, loose in admission_lost:
        print(f"    {label}  class {name}  held component types {loose}, none conformed to")
    print()

    print(f"FIELD LIST NARROWED -- still a candidate, D3/D4/D6 see fewer fields: {len(narrowed)}")
    for label, name, loose, strict, dropped in narrowed:
        print(f"    {label}  class {name}  {loose} -> {strict}  (dropped {dropped})")
    print()

    affected = {label for label, *_ in admission_lost} | {label for label, *_ in narrowed}
    control = {a for a in affected if any(a.endswith(c.split("/")[-1]) for c in INTRODUCED_BY_THE_RULE)}
    pre_existing = affected - control

    print(f"affected programs: {len(affected)}")
    print(f"  of which fixtures ADDED BY e2acb66 for this rule (the positive control): "
          f"{len(control)}")
    for a in sorted(control):
        print(f"      {a}")
    print(f"  PRE-EXISTING corpus programs affected: {len(pre_existing)}")
    for a in sorted(pre_existing):
        print(f"      {a}")
    if not control:
        print("\n  WARNING: the positive control did not fire. This script found none of the "
              "three fixtures\n  that exist to be affected by this rule -- treat any zero above "
              "as unproven.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
