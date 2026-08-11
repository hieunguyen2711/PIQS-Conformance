"""Run the PIQS scorer (piqs.checker.PIQSChecker, UNMODIFIED) on Kim's
refactored programs and record, per (case study, LLM, pattern):
  - per-property satisfied/not verdicts
  - PSR, CPC, PIQS
  - base/derived predicates (for disagreement analysis)
Also record javac compilation per program.

Writes results/kim_replication_raw.json. Read-only on Kim's code and on the scorer.
"""

import json
import os
import shutil
import subprocess
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from piqs.checker import PIQSChecker, _PATTERN_WEIGHTS  # noqa: E402

MANIFEST = os.path.join(ROOT, "validation/kim_file_manifest.json")
OUT = os.path.join(ROOT, "results/kim_replication_raw.json")

# The corpus now lives in-repo under fixtures/kim/<program>/. The manifest is kept
# byte-identical to the old repo's, so its `extracted_root` still points at the
# throwaway scratchpad the ZIPs were originally unpacked into; rebase off the
# program name instead. Read-only -- nothing here writes under fixtures/kim/.
KIM_ROOT = os.path.join(ROOT, "fixtures", "kim")


def program_root(prog):
    return os.path.join(KIM_ROOT, prog["program"])


def load_files(program_root, rel_files):
    """basename -> content for every .java file in the program."""
    out = {}
    for rel in rel_files:
        full = os.path.join(program_root, rel)
        with open(full, "r", encoding="utf-8", errors="ignore") as fh:
            out[os.path.basename(rel)] = fh.read()
    return out


def javac_available():
    """Is a JDK on PATH? Checked once, so the answer is the same for every program in a run."""
    return shutil.which("javac") is not None


def compile_program(program_root, rel_files):
    """javac all program sources together into a temp dir. Returns (ok, returncode, stderr).

    Returns `(None, None, None)` when javac is not on PATH -- javac is an OPTIONAL external
    tool, not a Python dependency (see requirements.txt), and compilation is recorded ALONGSIDE
    the scores, never used to produce them. Without the guard `subprocess.run` raises
    FileNotFoundError and the entire Kim run dies before scoring anything, so anyone reproducing
    the 90.6% figure on a machine without a JDK got a traceback instead of a number.

    WHY `None` AND NOT THE STRING "n/a". The only reader of this field is the compilation summary
    at the bottom of main(), and it was written as `'OK ' if p['compiles'] else 'FAIL'`. A truthy
    string would print OK for a program that was never compiled -- silence read as success, which
    is the failure mode this repo keeps meeting. `None` is falsy, so it would have printed FAIL,
    which is a different lie; the summary is therefore updated in the same commit to distinguish
    three states rather than two. `None` also keeps `compiles` a plain bool whenever a JDK IS
    present, so the committed results/kim_replication_raw.json is unchanged in the normal case.
    """
    if not javac_available():
        return None, None, None
    java_paths = [os.path.join(program_root, rel) for rel in rel_files]
    with tempfile.TemporaryDirectory() as tmp:
        proc = subprocess.run(
            ["javac", "-d", tmp, *java_paths],
            capture_output=True,
            text=True,
        )
        return proc.returncode == 0, proc.returncode, _anonymise(proc.stderr.strip(), tmp)


def _anonymise(text, tmpdir=None):
    """Replace machine-specific absolute paths with placeholders before anything is written.

    javac prints the ABSOLUTE path of every file it complains about, and this stderr is stored
    verbatim in results/kim_replication_raw.json. Six programs fail to compile, so six copies of
    the author's home directory and full project path were committed as DATA.

    (This docstring cannot quote the offending prefix as an example: the guard below scans every
    tracked file, and an illustrative path is indistinguishable from a real one. It caught this
    very docstring on the first run, which is the behaviour wanted.)

    Two problems, and the second is the serious one:

      * a correct run on another machine differs from the committed baseline in every one of
        those strings, so a whole-file diff cannot be used as a regression check;
      * the paper is double-blind, and anonymising a repository URL does not anonymise a string
        inside a committed data file. docs/MIGRATION.md records that every SCRIPT had this exact
        prefix removed so the repo runs anywhere. The data files put it back as content.

    Normalising at the point of writing, rather than cleaning the file afterwards, is what makes
    it stay fixed: the next tool whose output gets captured is covered too. The error text itself
    is kept -- the diagnostic value is in the message, not in the path.

    Pinned by tests/test_no_absolute_paths.py, which scans every git-tracked file.
    """
    if not text:
        return text
    if tmpdir:
        text = text.replace(tmpdir, "<tmpdir>")
    return text.replace(ROOT, "<repo>")


def main():
    with open(MANIFEST) as fh:
        manifest = json.load(fh)

    svc = PIQSChecker()
    prog_by_name = {p["program"]: p for p in manifest["programs"]}

    programs_out = {}
    results = []

    # Compile every program (originals + refactored) for the record.
    for prog in manifest["programs"]:
        name = prog["program"]
        root = program_root(prog)
        ok, rc, stderr = compile_program(root, prog["java_files"])
        programs_out[name] = {
            "case_study": prog["case_study"],
            "llm": prog["llm"],
            "role": prog["role"],
            "num_java_files": prog["num_java_files"],
            "java_files": prog["java_files"],
            "compiles": ok,
            "javac_returncode": rc,
            "javac_stderr": stderr,
        }

    # Score each (case study, LLM, pattern) unit on the refactored programs.
    for unit in manifest["scoring_units"]:
        prog = prog_by_name[unit["program"]]
        files = load_files(program_root(prog), prog["java_files"])
        res = svc.evaluate(pattern_name=unit["pattern"], java_files=files)

        props = {
            row["property_id"]: {
                "weight": row["weight"],
                "satisfaction": row["satisfaction"],
                "satisfied": bool(row["satisfaction"]),
                "justification": row["justification"],
            }
            for row in res["logical_assessment"]
        }
        results.append(
            {
                "case_study": unit["case_study"],
                "llm": unit["llm"],
                "pattern": unit["pattern"],
                "program": unit["program"],
                "properties": props,
                "psr": res["breadth_calculation_psr"]["result_percent"],
                "cpc": res["depth_calculation_cpc"]["result_percent"],
                "piqs": res["final_quality_result_piqs"]["result_percent"],
                "psr_formula": res["breadth_calculation_psr"]["formula"],
                "cpc_formula": res["depth_calculation_cpc"]["formula"],
                "piqs_formula": res["final_quality_result_piqs"]["formula"],
                "base_predicates": res["base_predicates"],
                "derived_predicates": res["derived_predicates"],
                "grade": res["grade"],
            }
        )

    # Availability is a property of the machine, not of each program: recorded once at the top
    # level so a reader of the raw JSON does not have to infer it from twelve nulls.
    out = {
        "generated_by": "validation/run_scorer.py",
        "scorer": "piqs.checker.PIQSChecker (unmodified)",
        "python": sys.version.split()[0],
        "javac_available": javac_available(),
        "weights": _PATTERN_WEIGHTS,
        "programs": programs_out,
        "results": results,
    }
    with open(OUT, "w") as fh:
        json.dump(out, fh, indent=2)

    print(f"Wrote {OUT}")
    print(f"  programs compiled/checked: {len(programs_out)}")
    print(f"  scoring units evaluated: {len(results)}")
    # Three states, not two. `compiles is None` means NOT MEASURED, which is neither OK nor FAIL;
    # printing either of those for an unmeasured program is a false report, and the falsy-None
    # version of this line would have printed FAIL for all twelve.
    if not out["javac_available"]:
        print("\nCompilation summary: NOT MEASURED -- javac is not on PATH.")
        print("  javac is an optional external tool. Every score above is unaffected: the "
              "checker never reads\n  the compile result. Install a JDK to record compilation.")
    else:
        print("\nCompilation summary:")
        for name, p in programs_out.items():
            if p["role"] == "refactored":
                print(f"  {'OK ' if p['compiles'] else 'FAIL'}  "
                      f"{p['case_study']:4} {p['llm']:8} {name}")


if __name__ == "__main__":
    main()
