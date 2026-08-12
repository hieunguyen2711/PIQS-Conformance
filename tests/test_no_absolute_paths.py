"""No committed file may contain an absolute path from the machine that produced it.

TWO REASONS, AND THE SECOND IS THE SERIOUS ONE.

**Reproducibility.** A correct run on another machine differs from the committed baseline in
every embedded path, so a whole-file diff cannot be used as a regression check. The paths are
recorded as *data*, so no amount of care in the scripts removes them.

**Double-blind review.** Anonymising a repository URL does not anonymise a string inside a
committed data file. `docs/MIGRATION.md` records that every script had its hardcoded
`/Users/<name>/…` prefix removed so the repo runs anywhere — and then the data files
reintroduced the same prefix as content. A reviewer greps, not reads.

WHY A TEST AND NOT A ONE-OFF CLEANUP. Six of these arrived from a single `javac` invocation whose
stderr was stored verbatim. Any future tool whose output is captured into a result file brings
them back, and nothing about the four suites would notice: paths in a stderr string change no
verdict. This is the standing check.

THE EXEMPTIONS ARE UNRESOLVED, NOT APPROVED. Each entry below is a file where absolute paths are
still present and a decision is owed. They are listed rather than suppressed silently so the
count is visible and someone has to look at them. An exemption is not a judgment that the file is
fine.
"""

from __future__ import annotations

import os
import re
import subprocess
import sys

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

# Absolute paths that belong to a machine rather than to the repository. `/private/tmp/...` and
# `/tmp/...` are included because scratchpad paths carry the same identifying information as a
# home directory -- the session directories in this project embed the full home path in their
# name.
_ABSOLUTE = re.compile(r"(/Users/|/home/[a-z]|/private/tmp/|/var/folders/|[A-Z]:\\\\Users\\\\)")

# Files with unresolved hits. Reason recorded for each; NONE of these is approved.
_UNRESOLVED = {
    "validation/kim_file_manifest.json":
        "24 hits (source_zip, extracted_root). MIGRATION.md:28 states it was copied "
        "BYTE-IDENTICAL and left untouched 'so the migration cannot be accused of moving the "
        "goalposts'. Rewriting it is a decision about a measured artifact, not a cleanup.",
    # validation/build_manifest.py WAS listed here. It is not any more: KIM_ZIP_DIR is now a
    # REQUIRED environment variable with no default, so there is no path left to anonymise. That
    # is the preferred way off this list -- remove the path, do not permit it.
    "docs/MIGRATION.md":
        "2 hits: a GitHub username, and the old absolute path quoted as documentation of its own "
        "removal. The username is the sharper double-blind risk of the two.",
}


def _tracked_text_files() -> list[str]:
    out = subprocess.run(["git", "ls-files"], cwd=ROOT, capture_output=True, text=True, check=True)
    files = []
    for rel in out.stdout.splitlines():
        if not rel or rel.endswith((".png", ".jpg", ".zip", ".class", ".jar")):
            continue
        files.append(rel)
    return files


def _hits(rel: str) -> list[str]:
    try:
        with open(os.path.join(ROOT, rel), encoding="utf-8", errors="ignore") as fh:
            lines = fh.read().splitlines()
    except OSError:
        return []
    return [f"{rel}:{i}" for i, line in enumerate(lines, 1) if _ABSOLUTE.search(line)]


def test_no_absolute_paths_in_committed_files():
    """The guard. A new file with a machine path fails here and nowhere else."""
    offenders: dict[str, list[str]] = {}
    for rel in _tracked_text_files():
        if rel in _UNRESOLVED or rel == "tests/test_no_absolute_paths.py":
            continue
        found = _hits(rel)
        if found:
            offenders[rel] = found

    assert not offenders, (
        "absolute machine paths in committed files:\n"
        + "\n".join(f"  {rel}: {len(v)} line(s) -- {v[:3]}" for rel, v in sorted(offenders.items()))
        + "\n\nThese are a reproducibility problem and a double-blind risk. Normalise the path to "
        "a placeholder\nat the point it is written, or add the file to _UNRESOLVED with a reason "
        "if it needs a decision."
    )


@pytest.mark.parametrize("rel", sorted(_UNRESOLVED))
def test_unresolved_exemptions_still_have_hits(rel: str):
    """An exemption that no longer applies must be deleted, not left as permanent permission.

    Without this, a file cleaned up later keeps its entry forever and the exemption list grows
    into a place where new offenders can hide.
    """
    assert _hits(rel), (
        f"{rel} is listed in _UNRESOLVED but no longer contains an absolute path. "
        "Remove the entry -- the exemption list must shrink, never accumulate."
    )
