"""Run both obfuscators over the whole corpus and report every difference in the rename map.

    python3 validation/obfuscator_diff.py

`piqs.obfuscator` is regex-based; `piqs.obfuscator_ts` is a parser. They are meant to implement
the SAME POLICY by DIFFERENT MECHANISMS, so a difference is always one of two things, and the
two carry opposite weight:

    names only tree-sitter renames   expected -- the regex module's `_LOCAL_RE` consumes the
                                     `;` that ends the previous statement, so every second
                                     declaration in a run is skipped
    names only the regex renames     A DEFECT IN THE NEW MODULE until proven otherwise. The
                                     only acceptable entries are JDK class names the regex
                                     reaches through its `new X(` misread -- `_METHOD_SIG_RE`
                                     matches *word word `(`*, so `new DecimalFormat("$0.00")`
                                     reads as a declaration named `DecimalFormat` with return
                                     type `new`. Each one is named with its reason below.

The `values differ` column is numbering only. `m1` versus `m7` says nothing: the counters are
assigned over a sorted name list, so discovering one extra name shifts everything after it.
What matters is the SET of renamed names, which is the first two columns.

Corpus: every leaf package directory under `fixtures/kim/` as one set, plus every `.java` file
in `fixtures/mutation_battery/`, `fixtures/mutation_battery_bdt/` and `tests/fixtures_parser/`
as its own single-file set.
"""

from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
import tempfile
from collections import Counter

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from piqs import obfuscator as regex_mod  # noqa: E402
from piqs import obfuscator_ts as ts_mod  # noqa: E402

# JDK class names the regex module renames only because `new X(...)` looks like a method
# declaration to `_METHOD_SIG_RE`. Renaming one of these produces code that does not compile,
# so tree-sitter leaving it alone is the FIX, not a miss.
_KNOWN_REGEX_ARTEFACTS = {
    "DecimalFormat": "reached through `new DecimalFormat(...)`, which `_METHOD_SIG_RE` reads "
                     "as a declaration named DecimalFormat with return type `new`; the class "
                     "is not in `_JDK_NAMES`, so the regex renames a JDK type",
    "in": "the SAME `new X(` misread, arriving through the parameter list instead of the "
          "method name: `new Scanner(System.in);` matches `_METHOD_SIG_RE` with ret=`new`, "
          "name=`Scanner`, params=`System.in`, and `_split_params` reads that as one "
          "parameter named `in` of type `System`. `Scanner` is in `_JDK_NAMES` so the method "
          "name is dropped, but the phantom PARAMETER survives into the map. Every real "
          "occurrence is `System.in`, a JDK member access, so the regex renames it nowhere -- "
          "it only inflates `jdk_member_sites` by 4 across the corpus. Verified: the sole "
          "occurrence in each set is `new Scanner(System.in)`, and the regex's own output "
          "still contains `System.in` unchanged.",
}


def _read(path: str) -> str:
    with open(path, encoding="utf-8", errors="ignore") as fh:
        return fh.read()


def corpus() -> list[tuple[str, dict[str, str]]]:
    """`[(label, {filename: source})]` -- one entry per source set."""
    sets: list[tuple[str, dict[str, str]]] = []

    kim = os.path.join(ROOT, "fixtures", "kim")
    leaf_dirs = set()
    for dirpath, _, filenames in os.walk(kim):
        if any(f.endswith(".java") for f in filenames):
            leaf_dirs.add(dirpath)
    for d in sorted(leaf_dirs):
        files = {
            f: _read(os.path.join(d, f))
            for f in sorted(os.listdir(d))
            if f.endswith(".java")
        }
        sets.append((os.path.relpath(d, ROOT), files))

    for sub in ("fixtures/mutation_battery", "fixtures/mutation_battery_bdt",
                "tests/fixtures_parser"):
        path = os.path.join(ROOT, sub)
        if not os.path.isdir(path):
            continue
        for f in sorted(os.listdir(path)):
            if f.endswith(".java"):
                sets.append((f"{sub}/{f}", {f: _read(os.path.join(path, f))}))

    return sets


def compare_set(files: dict[str, str]):
    """`(regex map, tree-sitter map)` for one source set, or an error string."""
    a = regex_mod.build_rename_map_regex(files)
    b = ts_mod.build_rename_map(files)
    return a, b


def javac(files: dict[str, str]) -> tuple[bool, str]:
    """`(compiled, stderr)` for one source set, written flat into a temp directory.

    Filenames come from `file_mapping`, so `public class C8` lands in `C8.java` -- writing the
    obfuscated text under the ORIGINAL filename produces a spurious "class C8 is public, should
    be declared in a file named C8.java" that has nothing to do with the renaming.
    """
    if shutil.which("javac") is None:
        return False, "javac not on PATH"
    d = tempfile.mkdtemp(prefix="piqs-javac-")
    try:
        paths = []
        for fname, src in files.items():
            path = os.path.join(d, os.path.basename(fname))
            with open(path, "w", encoding="utf-8") as fh:
                fh.write(src)
            paths.append(path)
        proc = subprocess.run(
            ["javac", "-nowarn", "-d", os.path.join(d, "out"), *paths],
            capture_output=True, text=True, timeout=300,
        )
        return proc.returncode == 0, proc.stderr
    finally:
        shutil.rmtree(d, ignore_errors=True)


def compile_report(sets) -> None:
    """javac each set three ways -- original, regex output, tree-sitter output.

    A renaming tool that changes which method gets called cannot be used to argue that
    verdicts are name-independent, so "the output still compiles" is not a nicety here; it is
    the precondition for the invariance suite meaning anything. Sets whose ORIGINAL does not
    compile are reported separately and prove nothing either way.
    """
    print("=" * 78)
    print("COMPILE CHECK (javac)")
    print("=" * 78)
    good = 0
    broke_regex: list[tuple[str, str]] = []
    broke_ts: list[tuple[str, str]] = []
    bad_original: list[str] = []

    for label, files in sets:
        ok0, _ = javac(files)
        if not ok0:
            bad_original.append(label)
            continue
        good += 1
        for fn, bucket in ((regex_mod.obfuscate_regex, broke_regex),
                           (ts_mod.obfuscate, broke_ts)):
            try:
                out = fn(files)
                ok, err = javac(out)
            except Exception as exc:  # noqa: BLE001
                ok, err = False, f"{type(exc).__name__}: {exc}"
            if not ok:
                first = next((ln for ln in err.splitlines() if "error:" in ln), err[:120])
                bucket.append((label, first.split("error:", 1)[-1].strip()))

    print(f"sets whose ORIGINAL compiles          : {good}/{len(sets)}")
    print(f"sets whose original does NOT compile  : {len(bad_original)} "
          "(prove nothing either way)")
    for label in bad_original:
        print(f"    {label}")
    print()
    for name, bucket in (("REGEX", broke_regex), ("TREE-SITTER", broke_ts)):
        print(f"{name} output fails javac on {len(bucket)}/{good} good sets:")
        for label, err in bucket:
            print(f"    {label}")
            print(f"        {err}")
        if not bucket:
            print("    (none)")
        print()


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--quiet", action="store_true",
                    help="summary only; do not list per-set differences")
    ap.add_argument("--javac", action="store_true",
                    help="also compile every set three ways (original, regex, tree-sitter)")
    args = ap.parse_args()

    sets = corpus()
    regex_only_total: Counter = Counter()
    ts_only_total: Counter = Counter()
    withheld_added: Counter = Counter()
    withheld_removed: Counter = Counter()
    jdk_delta: Counter = Counter()
    renamed_regex = renamed_ts = 0
    value_diff_sets = 0
    failures: list[tuple[str, str]] = []
    differing_sets = 0

    print(f"corpus: {len(sets)} source sets\n")

    for label, files in sets:
        try:
            a, b = compare_set(files)
        except Exception as exc:  # noqa: BLE001 -- report, do not hide
            failures.append((label, f"{type(exc).__name__}: {exc}"))
            continue

        renamed_regex += len(a.mapping)
        renamed_ts += len(b.mapping)

        regex_only = sorted(set(a.mapping) - set(b.mapping))
        ts_only = sorted(set(b.mapping) - set(a.mapping))
        shared = set(a.mapping) & set(b.mapping)
        values_differ = sorted(n for n in shared if a.mapping[n] != b.mapping[n])
        w_add = sorted(set(b.withheld_names) - set(a.withheld_names))
        w_rem = sorted(set(a.withheld_names) - set(b.withheld_names))

        for n in regex_only:
            regex_only_total[n] += 1
        for n in ts_only:
            ts_only_total[n] += 1
        for n in w_add:
            withheld_added[n] += 1
        for n in w_rem:
            withheld_removed[n] += 1
        for n in set(a.jdk_member_sites) | set(b.jdk_member_sites):
            jdk_delta[n] += b.jdk_member_sites.get(n, 0) - a.jdk_member_sites.get(n, 0)
        if values_differ:
            value_diff_sets += 1

        if regex_only or ts_only or w_add or w_rem:
            differing_sets += 1
            if not args.quiet:
                print(f"--- {label}")
                if regex_only:
                    print(f"    regex only ({len(regex_only)}): {regex_only}")
                if ts_only:
                    print(f"    ts only    ({len(ts_only)}): {ts_only}")
                if w_add:
                    print(f"    withheld + : {[(n, b.withheld_names[n]) for n in w_add]}")
                if w_rem:
                    print(f"    withheld - : {[(n, a.withheld_names[n]) for n in w_rem]}")

    print()
    print("=" * 78)
    print("SUMMARY")
    print("=" * 78)
    print(f"source sets                    : {len(sets)}")
    print(f"sets with a name-set difference: {differing_sets}")
    print(f"sets with numbering-only diffs : {value_diff_sets}")
    print(f"identifiers renamed, regex     : {renamed_regex}")
    print(f"identifiers renamed, ts        : {renamed_ts}")
    print(f"                         delta : {renamed_ts - renamed_regex:+d}")
    print()

    print(f"names only the REGEX renames ({len(regex_only_total)} distinct):")
    unexplained = []
    if not regex_only_total:
        print("    (none)")
    for name, count in sorted(regex_only_total.items()):
        why = _KNOWN_REGEX_ARTEFACTS.get(name)
        if why is None:
            unexplained.append(name)
            print(f"    {name:24} x{count:<4} *** UNEXPLAINED -- investigate ***")
        else:
            print(f"    {name:24} x{count:<4} {why}")
    print()

    print(f"names only TREE-SITTER renames ({len(ts_only_total)} distinct):")
    if not ts_only_total:
        print("    (none)")
    for name, count in sorted(ts_only_total.items()):
        print(f"    {name:24} x{count}")
    print()

    print(f"withheld_names ADDED by tree-sitter ({len(withheld_added)} distinct):")
    for name, count in sorted(withheld_added.items()) or [("(none)", 0)]:
        print(f"    {name:24} x{count}" if count else "    (none)")
    print()
    print(f"withheld_names REMOVED by tree-sitter ({len(withheld_removed)} distinct):")
    for name, count in sorted(withheld_removed.items()) or [("(none)", 0)]:
        print(f"    {name:24} x{count}" if count else "    (none)")
    print()

    nonzero = {n: v for n, v in jdk_delta.items() if v}
    print(f"jdk_member_sites delta (ts - regex), {len(nonzero)} names moved:")
    for name, delta in sorted(nonzero.items()) or [("(none)", 0)]:
        print(f"    {name:24} {delta:+d}" if delta else "    (none)")
    print()

    if failures:
        print(f"SETS THAT RAISED ({len(failures)}):")
        for label, msg in failures:
            print(f"    {label}: {msg}")
        print()

    if args.javac:
        compile_report(sets)

    if unexplained:
        print(f"RESULT: {len(unexplained)} unexplained regex-only name(s): {unexplained}")
        return 1
    print("RESULT: every regex-only name is a known `new X(` artefact.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
