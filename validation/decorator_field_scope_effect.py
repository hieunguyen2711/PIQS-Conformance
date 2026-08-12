"""How many classes are invisible to the Decorator role derivation because it reads OWN fields?

THE DEFECT, MEASURED NOT ARGUED.

The candidate loop in `_evaluate_decorator` reads `w.fields` -- own fields only, never
`_effective_fields`. A concrete decorator that extends an abstract decorator base inherits the
component reference and declares no field of its own, so `w.fields` is empty for it and it is
**never a decorator candidate at all**.

That is the canonical GoF Decorator shape. Only the base is ever judged. And D2, D3, D4 and D6 are
each an `any(...)` over the candidate list, so one compliant class carries the whole program --
see tests/fixtures_parser/decorator_subclass_forwards_nothing.java, which forwards nothing and
scores 100.

THIS SCRIPT MEASURES ONLY. It changes no predicate and decides nothing. Two design questions are
open and belong to the project owner:

  1. own fields versus effective fields for candidate admission;
  2. `any(...)` versus `all(...)` for D3, D4 and D6.

Fixing (1) without (2) leaves the fixture above at 100, because the compliant base still satisfies
every `any(...)` on the subclass's behalf. Measured, not predicted: see the four-way table in
docs/STATE.md.

METHOD. One PROGRAM at a time, exactly as validation/decorator_rule_effect.py does -- a Kim
program is all of its files together. Scanning file by file would be meaningless here for the same
reason it was there: a subclass whose base is declared in a sibling file has no visible ancestor,
so `_effective_fields` would return its own fields and the difference under test would vanish.

    python3 validation/decorator_field_scope_effect.py

Exit 0 for any corpus result; exit 1 ONLY if the positive control fails, which means the script's
own numbers cannot be trusted.
"""

from __future__ import annotations

import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "validation"))

from decorator_rule_effect import programs  # noqa: E402
from piqs.checker import PIQSChecker  # noqa: E402

# Fixtures that MUST appear, checked by COUNT and named individually. Each holds a concrete
# decorator extending an abstract decorator base -- the exact shape under test. A run that finds
# neither is broken, not clean.
CONTROL = {
    "tests/fixtures_parser/abstract_decorator_base.java",
    "tests/fixtures_parser/decorator_subclass_forwards_nothing.java",
}


def invisible_classes(files: dict[str, str]) -> list[tuple[str, list[str]]]:
    """Classes that WOULD be decorator candidates under `_effective_fields` and are not now.

    The condition is precise: conforms to a component, holds NO own field of a conformed type,
    but DOES hold an inherited one. Anything else is unaffected by the admission rule.
    """
    svc = PIQSChecker()
    types = svc._extract_types(files)
    component_names = svc._component_type_names(types)
    out = []
    for w in (t for t in types.values() if t.kind == "class"):
        conformed = {c for c in component_names if svc._conforms_to(w, c, types)}
        if not conformed:
            continue
        own = [f.field_type for f in w.fields if f.field_type in conformed]
        effective = [
            f.field_type for f in svc._effective_fields(w, types) if f.field_type in conformed
        ]
        if not own and effective:
            out.append((w.name, sorted(set(effective))))
    return out


def main() -> int:
    hits, n_units = [], 0
    for label, files in programs():
        n_units += 1
        for name, inherited in invisible_classes(files):
            hits.append((label, name, inherited))

    affected = {label for label, _n, _i in hits}
    print(f"units evaluated: {n_units}")
    print()
    print(f"classes invisible to the Decorator role derivation: {len(hits)} "
          f"in {len(affected)} program(s)")
    for label, name, inherited in hits:
        print(f"    {label}")
        print(f"        class {name}  inherits a component-typed field {inherited}, declares none")
    print()

    missing = CONTROL - affected
    print(f"positive control: {len(CONTROL) - len(missing)}/{len(CONTROL)}")
    if missing:
        print("\n  BROKEN: the numbers above are UNPROVEN -- a measurement that cannot return "
              "non-zero\n  says nothing when it returns zero.")
        for m in sorted(missing):
            print(f"      MISSING  {m}")
        return 1
    other = sorted(affected - CONTROL)
    print(f"programs affected BEYOND the two control fixtures: {len(other)}")
    for o in other:
        print(f"      {o}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
