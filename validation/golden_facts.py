"""Fact-level regression guard for the tree-sitter parser.

WHAT THIS IS FOR.

Phase 2 step 3 moves verdicts ON PURPOSE -- it teaches the checker five loop forms it cannot
currently see. Once that starts, a moved number has two possible causes and they are
indistinguishable at the verdict level:

    (a) the new loop detection fired          -- correct, expected
    (b) the parser silently regressed          -- a defect

The four suites report verdicts, so they cannot separate these. This records the FACTS the
parser extracts -- every type, field, method, and the four body-level maps -- so a change to the
parser shows up as a fact diff regardless of whether any verdict moved.

It is a FIFTH command, not a replacement:

    python3 validation/golden_facts.py --write     regenerate results/parser_golden.json
    python3 validation/golden_facts.py --check     diff a fresh dump against it; exit 1 on any
                                                   difference, or on any failure to produce one

It also finally makes the pinned tree-sitter versions verifiable. `extractor_parity.py` compares
the parser against ITSELF, so after a version bump both sides are the new version and it passes
trivially. This does not: the golden file was written by the pinned version and committed.

TWO DESIGN DECISIONS THAT ARE NOT INCIDENTAL.

* **One file at a time.** `extract_types` keys its result by SIMPLE NAME, so extracting many
  files in one call collapses same-named classes across programs, last one wins. That bug
  already cost this project a census and would have deleted a published finding (see
  docs/STATE.md). A snapshot built that way would bake the collapse in and guard the wrong
  thing. Each file gets `{basename: content}` of its own, exactly as `extractor_parity.py` does.

* **Every failure is a FAILURE, never zero differences.** An empty dump, a file that will not
  parse, a missing golden file, zero files discovered -- each exits non-zero with a message. A
  guard whose broken state is indistinguishable from its passing state is the `cmd | tail`
  problem again: silence read as success.
"""

from __future__ import annotations

import argparse
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from piqs.parser import extract_types  # noqa: E402

GOLDEN = os.path.join(ROOT, "results", "parser_golden.json")

# Both corpora, plus the parser's own regression fixtures. The fixtures are deliberately
# included: they hold the edge cases most likely to regress -- nested types, generic fields,
# interface default methods, and one file per migration divergence. Adding a fixture therefore
# requires a --write, which is correct: it is a deliberate act, and it should be visible.
SOURCE_DIRS = ("fixtures", "tests/fixtures_parser")


def discover() -> list[str]:
    """Every .java file under SOURCE_DIRS, as repo-relative paths, sorted."""
    out = []
    for sub in SOURCE_DIRS:
        base = os.path.join(ROOT, sub)
        for dirpath, _dirs, names in os.walk(base):
            for nm in sorted(names):
                if nm.endswith(".java"):
                    out.append(os.path.relpath(os.path.join(dirpath, nm), ROOT))
    return sorted(out)


def facts_for(rel_path: str) -> dict:
    """The parser's facts for ONE file. Sets become sorted lists so the JSON is canonical."""
    with open(os.path.join(ROOT, rel_path), encoding="utf-8", errors="ignore") as fh:
        content = fh.read()

    # One file at a time -- see the module docstring.
    types = extract_types({os.path.basename(rel_path): content})

    out = {}
    for name, t in sorted(types.items()):
        out[name] = {
            "kind": t.kind,
            "is_abstract": t.is_abstract,
            "extends": t.extends,
            "implements": list(t.implements),
            "fields": [
                {"name": f.name, "type": f.field_type, "modifiers": sorted(f.modifiers)}
                for f in t.fields
            ],
            # Source order is preserved: it is stable and it is part of the contract.
            "methods": [
                {
                    "name": m.name,
                    "owner": m.owner,
                    "return_type": m.return_type,
                    "param_types": list(m.param_types),
                    "param_names": list(m.param_names),
                    "modifiers": sorted(m.modifiers),
                    "is_constructor": m.is_constructor,
                    "has_body": m.has_body,
                    # The four phase-2 body maps.
                    "locals": {k: m.locals[k] for k in sorted(m.locals)},
                    "calls": [list(c) for c in m.calls],
                    "mentions": sorted(m.mentions),
                    "assignments": sorted(m.assignments),
                }
                for m in t.methods
            ],
        }
    return out


def build() -> dict:
    files = discover()
    if not files:
        raise SystemExit(
            "FAILED: no .java files discovered under " + ", ".join(SOURCE_DIRS) + ".\n"
            "An empty corpus would produce an empty snapshot that matches nothing and reports "
            "zero differences. Refusing."
        )

    snapshot = {}
    for rel in files:
        try:
            snapshot[rel] = facts_for(rel)
        except Exception as exc:  # noqa: BLE001
            raise SystemExit(
                f"FAILED: {rel} could not be parsed into facts: "
                f"{type(exc).__name__}: {exc}\n"
                "A file that will not parse is a defect, not an absence of differences."
            ) from exc

    total_types = sum(len(v) for v in snapshot.values())
    if total_types == 0:
        raise SystemExit(
            f"FAILED: parsed {len(files)} files and extracted 0 types. "
            "That is a broken parser, not a clean run."
        )
    return snapshot


# ------------------------------------------------------------------ diffing


def _walk_diff(path: str, old, new, out: list[str]) -> None:
    """Report leaf-level differences with a readable path."""
    if type(old) is not type(new):
        out.append(f"{path}: type {type(old).__name__} -> {type(new).__name__}  {old!r} -> {new!r}")
        return
    if isinstance(old, dict):
        for k in sorted(set(old) | set(new)):
            if k not in old:
                out.append(f"{path}.{k}: ADDED  {new[k]!r}")
            elif k not in new:
                out.append(f"{path}.{k}: REMOVED  {old[k]!r}")
            else:
                _walk_diff(f"{path}.{k}", old[k], new[k], out)
    elif isinstance(old, list):
        if len(old) != len(new):
            out.append(f"{path}: length {len(old)} -> {len(new)}  {old!r} -> {new!r}")
            return
        for i, (a, b) in enumerate(zip(old, new)):
            _walk_diff(f"{path}[{i}]", a, b, out)
    elif old != new:
        out.append(f"{path}: {old!r} -> {new!r}")


def check() -> int:
    if not os.path.exists(GOLDEN):
        print(
            f"FAILED: {os.path.relpath(GOLDEN, ROOT)} does not exist.\n"
            "Run `python3 validation/golden_facts.py --write` first, and commit the result.",
            file=sys.stderr,
        )
        return 1

    with open(GOLDEN, encoding="utf-8") as fh:
        golden = json.load(fh)

    if not golden:
        print("FAILED: the committed snapshot is empty. It would match nothing.", file=sys.stderr)
        return 1

    fresh = build()

    diffs: list[str] = []
    for rel in sorted(set(golden) | set(fresh)):
        if rel not in golden:
            diffs.append(f"{rel}: FILE ADDED (not in the snapshot -- regenerate with --write)")
        elif rel not in fresh:
            diffs.append(f"{rel}: FILE MISSING (in the snapshot, not on disk)")
        else:
            _walk_diff(rel, golden[rel], fresh[rel], diffs)

    n_files = len(fresh)
    n_types = sum(len(v) for v in fresh.values())
    n_methods = sum(len(t["methods"]) for v in fresh.values() for t in v.values())

    if diffs:
        print(f"PARSER FACTS CHANGED: {len(diffs)} difference(s)\n")
        for d in diffs[:60]:
            print("  " + d)
        if len(diffs) > 60:
            print(f"  ... and {len(diffs) - 60} more")
        print(
            "\nIf this was intended -- a parser change you meant to make, or a new fixture --\n"
            "re-run with --write and commit the snapshot in the SAME commit as the change,\n"
            "so a reviewer sees the facts move alongside the code."
        )
        return 1

    print(f"parser facts unchanged: {n_files} files, {n_types} types, {n_methods} methods")
    return 0


def write() -> int:
    snapshot = build()
    os.makedirs(os.path.dirname(GOLDEN), exist_ok=True)
    with open(GOLDEN, "w", encoding="utf-8") as fh:
        json.dump(snapshot, fh, indent=1, sort_keys=True)
        fh.write("\n")
    n_types = sum(len(v) for v in snapshot.values())
    n_methods = sum(len(t["methods"]) for v in snapshot.values() for t in v.values())
    print(
        f"wrote {os.path.relpath(GOLDEN, ROOT)}: "
        f"{len(snapshot)} files, {n_types} types, {n_methods} methods"
    )
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--write", action="store_true", help="regenerate the committed snapshot")
    g.add_argument("--check", action="store_true", help="diff against it; exit 1 on any difference")
    args = ap.parse_args()
    return write() if args.write else check()


if __name__ == "__main__":
    sys.exit(main())
