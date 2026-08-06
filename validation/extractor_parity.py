"""Fact-level parity harness for the Java extraction migration (regex -> tree-sitter).

The four validation suites compare VERDICTS. Two extractors can produce identical verdicts
while disagreeing about the underlying facts -- a wrong return type that no predicate happens
to read, a method that exists in one model and not the other. This harness compares the FACTS.

For every .java file under fixtures/ it runs two extractors and dumps a normalised fact model:

    type   : name, kind, is_abstract, extends, implements (sorted),
             body_normalised, content_normalised
    field  : name, field_type, modifiers (sorted)
    method : name, owner, return_type, param_types, param_names, modifiers (sorted),
             is_constructor, has_body, body_normalised

Types, methods and fields are sorted by name so ordering is never reported as a difference,
and every body/content string is whitespace-collapsed to single spaces before comparison, so
formatting is never reported either. What remains is a real disagreement about the source.

Each file is extracted on its own (`{basename: content}`), so a difference is always
attributable to one file rather than to cross-file name collisions in the corpus.

Usage
    python validation/extractor_parity.py                     # regex vs parser
    python validation/extractor_parity.py --a regex --b regex # sanity: must be zero
    python validation/extractor_parity.py --json out.json     # full untruncated report
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from dataclasses import dataclass

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from piqs.checker import PIQSChecker  # noqa: E402

FIXTURES = os.path.join(ROOT, "fixtures")

_WS = re.compile(r"\s+")


def _norm(text: str) -> str:
    """Whitespace collapsed to single spaces. Formatting is not a difference."""
    return _WS.sub(" ", text or "").strip()


# --------------------------------------------------------------------------------------- #
# Extractors under comparison
# --------------------------------------------------------------------------------------- #

def _regex_extractor(files: dict[str, str]) -> dict:
    raise SystemExit(
        "The regex extractor was deleted after this harness reported parity.\n"
        "To re-run the regex-vs-parser comparison, check out the commit that added\n"
        "piqs/parser.py (the last one where PIQSChecker._extract_types_regex still exists)\n"
        "and run it there. `--a parser --b parser` still works as a self-check, and the\n"
        "harness is reusable for the phase-2 body-level migration."
    )


def _parser_extractor(files: dict[str, str]) -> dict:
    from piqs.parser import extract_types

    return extract_types(files)


EXTRACTORS = {"regex": _regex_extractor, "parser": _parser_extractor}


# --------------------------------------------------------------------------------------- #
# Fact model
# --------------------------------------------------------------------------------------- #

def method_facts(m) -> dict:
    return {
        "name": m.name,
        "owner": m.owner,
        "return_type": m.return_type,
        "param_types": list(m.param_types),
        "param_names": list(m.param_names),
        "modifiers": sorted(m.modifiers),
        "is_constructor": bool(m.is_constructor),
        "has_body": bool(m.has_body),
        "body_normalised": _norm(m.body),
    }


def field_facts(f) -> dict:
    return {
        "name": f.name,
        "field_type": f.field_type,
        "modifiers": sorted(f.modifiers),
    }


def _method_sort_key(d: dict) -> tuple:
    return (d["name"], tuple(d["param_types"]), d["return_type"] or "", d["has_body"])


def _field_sort_key(d: dict) -> tuple:
    return (d["name"], d["field_type"], tuple(d["modifiers"]))


def type_facts(t) -> dict:
    return {
        "name": t.name,
        "kind": t.kind,
        "is_abstract": bool(t.is_abstract),
        "extends": t.extends,
        "implements": sorted(t.implements),
        "body_normalised": _norm(t.body),
        "content_normalised": _norm(t.content),
        "methods": sorted((method_facts(m) for m in t.methods), key=_method_sort_key),
        "fields": sorted((field_facts(f) for f in t.fields), key=_field_sort_key),
    }


def dump(files: dict[str, str], extract) -> dict:
    """{type_name: type_facts}, types sorted by name."""
    types = extract(files)
    return {name: type_facts(types[name]) for name in sorted(types)}


# --------------------------------------------------------------------------------------- #
# Diff
# --------------------------------------------------------------------------------------- #

@dataclass
class Diff:
    file: str
    type: str
    member: str          # "" for a type-level attribute, else "method foo(...)" / "field bar"
    attribute: str
    a: object
    b: object

    def as_dict(self) -> dict:
        return {
            "file": self.file,
            "type": self.type,
            "member": self.member,
            "attribute": self.attribute,
            "a": self.a,
            "b": self.b,
        }


TYPE_ATTRS = ["kind", "is_abstract", "extends", "implements", "body_normalised", "content_normalised"]
METHOD_ATTRS = [
    "owner", "return_type", "param_types", "param_names", "modifiers",
    "is_constructor", "has_body", "body_normalised",
]
FIELD_ATTRS = ["field_type", "modifiers"]


def _sig(d: dict) -> str:
    return f"method {d['name']}({', '.join(d['param_types'])})"


def _pair_by_name(a_list: list[dict], b_list: list[dict], key) -> tuple[list, list, list]:
    """Align two member lists by name. Within a name group both sides are already sorted, so
    members pair positionally; leftovers are presence differences (only-in-A / only-in-B).

    Aligning on name rather than on the whole signature means a disagreement about, say, a
    parameter type surfaces as an attribute difference on ONE member instead of as a bogus
    add/remove pair -- which is what makes the report readable.
    """
    from collections import defaultdict

    a_by, b_by = defaultdict(list), defaultdict(list)
    for d in a_list:
        a_by[d["name"]].append(d)
    for d in b_list:
        b_by[d["name"]].append(d)

    paired, only_a, only_b = [], [], []
    for name in sorted(set(a_by) | set(b_by)):
        av, bv = a_by.get(name, []), b_by.get(name, [])
        n = min(len(av), len(bv))
        paired.extend(zip(av[:n], bv[:n]))
        only_a.extend(av[n:])
        only_b.extend(bv[n:])
    return paired, only_a, only_b


def diff_dumps(fname: str, a: dict, b: dict) -> list[Diff]:
    diffs: list[Diff] = []

    for tname in sorted(set(a) | set(b)):
        if tname not in a:
            diffs.append(Diff(fname, tname, "", "type-only-in-B", None, b[tname]["kind"]))
            continue
        if tname not in b:
            diffs.append(Diff(fname, tname, "", "type-only-in-A", a[tname]["kind"], None))
            continue

        at, bt = a[tname], b[tname]
        for attr in TYPE_ATTRS:
            if at[attr] != bt[attr]:
                diffs.append(Diff(fname, tname, "", attr, at[attr], bt[attr]))

        paired, only_a, only_b = _pair_by_name(at["methods"], bt["methods"], _method_sort_key)
        for am, bm in paired:
            for attr in METHOD_ATTRS:
                if am[attr] != bm[attr]:
                    diffs.append(Diff(fname, tname, _sig(am), attr, am[attr], bm[attr]))
        for am in only_a:
            diffs.append(Diff(fname, tname, _sig(am), "method-only-in-A", am, None))
        for bm in only_b:
            diffs.append(Diff(fname, tname, _sig(bm), "method-only-in-B", None, bm))

        paired, only_a, only_b = _pair_by_name(at["fields"], bt["fields"], _field_sort_key)
        for af, bf in paired:
            for attr in FIELD_ATTRS:
                if af[attr] != bf[attr]:
                    diffs.append(Diff(fname, tname, f"field {af['name']}", attr, af[attr], bf[attr]))
        for af in only_a:
            diffs.append(Diff(fname, tname, f"field {af['name']}", "field-only-in-A", af, None))
        for bf in only_b:
            diffs.append(Diff(fname, tname, f"field {bf['name']}", "field-only-in-B", None, bf))

    return diffs


# --------------------------------------------------------------------------------------- #
# Corpus
# --------------------------------------------------------------------------------------- #

def java_files() -> list[tuple[str, str]]:
    """(display_path, absolute_path) for every .java file under fixtures/, sorted."""
    out = []
    for dirpath, _dirnames, filenames in os.walk(FIXTURES):
        for fn in sorted(filenames):
            if fn.endswith(".java"):
                full = os.path.join(dirpath, fn)
                out.append((os.path.relpath(full, ROOT), full))
    return sorted(out)


def _is_phantom(m: dict) -> bool:
    """A pseudo-method the signature regex harvested from a call expression rather than from a
    declaration: it carries no body. A real bodyless declaration (an abstract method or an
    interface method) always declares a return type; a call expression cannot."""
    return not m["has_body"] and m["return_type"] is None and not m["is_constructor"]


def _short(v: object, width: int = 90) -> str:
    s = json.dumps(v) if not isinstance(v, str) else v
    s = _norm(s)
    return s if len(s) <= width else s[: width - 3] + "..."


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--a", default="regex", choices=sorted(EXTRACTORS))
    ap.add_argument("--b", default="parser", choices=sorted(EXTRACTORS))
    ap.add_argument("--json", default=None, help="write the full untruncated report here")
    ap.add_argument("--limit", type=int, default=60, help="max differences printed")
    args = ap.parse_args()

    extract_a, extract_b = EXTRACTORS[args.a], EXTRACTORS[args.b]

    all_diffs: list[Diff] = []
    phantoms: list[tuple[str, str, dict]] = []
    files = java_files()

    for display, full in files:
        with open(full, "r", encoding="utf-8", errors="ignore") as fh:
            content = fh.read()
        single = {os.path.basename(full): content}
        da = dump(single, extract_a)
        db = dump(single, extract_b)
        file_diffs = diff_dumps(display, da, db)
        all_diffs.extend(file_diffs)
        for d in file_diffs:
            if d.attribute == "method-only-in-A" and _is_phantom(d.a):
                phantoms.append((display, d.type, d.a))

    # ---------------- report ----------------
    print(f"Extractor parity: A={args.a}  B={args.b}")
    print(f"Files compared: {len(files)}")
    print(f"Differences:    {len(all_diffs)}")
    print()

    by_attr: dict[str, int] = {}
    for d in all_diffs:
        by_attr[d.attribute] = by_attr.get(d.attribute, 0) + 1
    if by_attr:
        print("By attribute:")
        for attr, n in sorted(by_attr.items(), key=lambda kv: (-kv[1], kv[0])):
            print(f"  {attr:22} {n}")
        print()

    if phantoms:
        print(f"Phantom methods present only in A ({len(phantoms)}):")
        seen: dict[str, int] = {}
        for display, tname, m in phantoms:
            seen[m["name"]] = seen.get(m["name"], 0) + 1
        for name, n in sorted(seen.items(), key=lambda kv: (-kv[1], kv[0])):
            print(f"  {name:32} x{n}")
        print()

    if all_diffs:
        print(f"Differences (first {min(args.limit, len(all_diffs))}):")
        for d in all_diffs[: args.limit]:
            where = f"{d.file} :: {d.type}" + (f" :: {d.member}" if d.member else "")
            print(f"  {where}")
            print(f"      {d.attribute}")
            print(f"      A: {_short(d.a)}")
            print(f"      B: {_short(d.b)}")
        if len(all_diffs) > args.limit:
            print(f"  ... {len(all_diffs) - args.limit} more (use --json for the full report)")
    else:
        print("ZERO DIFFERENCES -- the two extractors agree on every fact.")

    if args.json:
        with open(args.json, "w") as fh:
            json.dump(
                {
                    "a": args.a,
                    "b": args.b,
                    "files_compared": len(files),
                    "difference_count": len(all_diffs),
                    "by_attribute": by_attr,
                    "phantom_methods": [
                        {"file": f, "type": t, "method": m} for f, t, m in phantoms
                    ],
                    "differences": [d.as_dict() for d in all_diffs],
                },
                fh,
                indent=2,
            )
        print(f"\nWrote {args.json}")

    return 0 if not all_diffs else 1


if __name__ == "__main__":
    sys.exit(main())
