"""Command line entry point for the conformance checker.

    piqs-check <pattern> <file-or-dir>...            structural conformance report
    piqs-check <pattern> <file-or-dir>... --json      the raw evaluation dict
    piqs-check <pattern> <file-or-dir>... --obfuscate check the renamed sources instead

Equivalently: `python -m piqs.cli ...`.

The --obfuscate flag is the point of the tool: it runs the same check over sources whose
identifiers have all been machine-renamed. A verdict that changes under --obfuscate was
keyed to a name, not to structure.
"""

from __future__ import annotations

import argparse
import json
import os
import sys

from piqs.checker import PIQSChecker, _CRITICAL_PROPERTIES, _PATTERN_WEIGHTS


def collect_java(paths: list[str]) -> dict[str, str]:
    """{basename: source} for every .java file named directly or found under a directory."""
    found: dict[str, str] = {}
    for p in paths:
        if os.path.isdir(p):
            for root, _, names in os.walk(p):
                for n in sorted(names):
                    if n.endswith(".java"):
                        full = os.path.join(root, n)
                        with open(full, encoding="utf-8", errors="ignore") as fh:
                            found[n] = fh.read()
        elif p.endswith(".java"):
            with open(p, encoding="utf-8", errors="ignore") as fh:
                found[os.path.basename(p)] = fh.read()
        else:
            raise SystemExit(f"not a .java file or directory: {p}")
    if not found:
        raise SystemExit("no .java files found")
    return found


def report(result: dict) -> str:
    pattern = result["pattern_name"]
    critical = _CRITICAL_PROPERTIES[pattern]
    rows = result["logical_assessment"]
    conforms = all(r["satisfaction"] == 1 for r in rows if r["property_id"] in critical)

    lines = [
        f"pattern:  {pattern}",
        f"files:    {len(result['files_analyzed'])} ({', '.join(result['files_analyzed'])})",
        "",
        f"{'prop':6} {'w':>2}  {'critical':8}  {'verdict':13}  justification",
        "-" * 100,
    ]
    for r in rows:
        pid = r["property_id"]
        lines.append(
            f"{pid:6} {r['weight']:>2}  {'yes' if pid in critical else '':8}  "
            f"{'satisfied' if r['satisfaction'] else 'NOT satisfied':13}  {r['justification']}"
        )
    lines += [
        "",
        f"PSR   {result['breadth_calculation_psr']['result_percent']:>6}%   "
        f"{result['breadth_calculation_psr']['formula']}",
        f"CPC   {result['depth_calculation_cpc']['result_percent']:>6}%   "
        f"{result['depth_calculation_cpc']['formula']}",
        f"PIQS  {result['final_quality_result_piqs']['result_percent']:>6}%   grade {result['grade']}",
        "",
        f"CONFORMS: {'yes' if conforms else 'no'}  "
        f"(all critical properties {sorted(critical)} satisfied)",
    ]
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(
        prog="piqs-check",
        description="Check whether Java source structurally conforms to a design pattern.",
    )
    ap.add_argument("pattern", choices=sorted(_PATTERN_WEIGHTS), help="design pattern to check")
    ap.add_argument("paths", nargs="+", help=".java files, or directories to search")
    ap.add_argument("--json", action="store_true", help="emit the raw evaluation dict")
    ap.add_argument(
        "--obfuscate",
        action="store_true",
        help="rename every user-defined identifier first, then check (name-independence probe)",
    )
    args = ap.parse_args(argv)

    files = collect_java(args.paths)
    if args.obfuscate:
        from piqs.obfuscator import obfuscate

        files = obfuscate(files)

    result = PIQSChecker().evaluate(args.pattern, files)
    print(json.dumps(result, indent=2) if args.json else report(result))

    critical = _CRITICAL_PROPERTIES[args.pattern]
    conforms = all(
        r["satisfaction"] == 1 for r in result["logical_assessment"] if r["property_id"] in critical
    )
    return 0 if conforms else 1


if __name__ == "__main__":
    sys.exit(main())
