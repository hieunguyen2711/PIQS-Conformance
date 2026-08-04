# Migration record

From `hieunguyen2711/Java-Design-Patterns-Analyzer` to `piqs-conformance`, 2026-08-03.

The old repo was a FastAPI service that did pattern recognition *and* CK/Halstead/MI metrics,
LLM batch generation, HPC job submission, and dataset management. This repo does one thing:
decide whether Java source structurally conforms to a design pattern, and prove the decision
does not depend on identifier names. Everything not serving that job was left behind.

Nothing was pruned in place — the new tree was built by copying an explicit allow-list.

## What moved and what did not

| Old path | New path | Disposition | Why |
|---|---|---|---|
| `app/services/piqs_service.py` | `piqs/checker.py` | **copied**, class renamed | The checker. The whole reason the repo exists. `PIQSService` → `PIQSChecker`: it is a library, not a service. |
| `scripts/obfuscate.py` | `piqs/obfuscator.py` | **copied**, to be rewritten | Kept as the starting point. Old behaviour (class names only, zip-to-zip, package rewriting) is not what the invariance proof needs; rewritten in Stage 4 to rename *every* user-defined identifier in-memory. |
| — | `piqs/cli.py` | **new** | Command line front end. Thin wrapper over `PIQSChecker`; `--obfuscate` runs the same check on renamed sources. |
| — | `piqs/__init__.py` | **new** | Package exports. |
| `validation/mutation_battery/*.java` (12) | `fixtures/mutation_battery/` | **copied** | The oracle for the pass-4 `G1` / `F4` meaning changes. Expected verdict is encoded in each filename. |
| `validation/mutation_battery_bdt/*.java` (27) | `fixtures/mutation_battery_bdt/` | **copied** | The oracle for Builder / Decorator / Template Method, which Kim never covered. |
| `validation/run_mutation_battery.py` | `validation/` | **copied**, imports+paths fixed | Runs the 12-case battery. |
| `validation/run_mutation_battery_bdt.py` | `validation/` | **copied**, imports+paths fixed | Runs the 27-case battery plus the D6 diagnostics. |
| `validation/run_scorer.py` | `validation/` | **copied**, imports+paths fixed | Scores the Kim corpus into `results/kim_replication_raw.json`. |
| `validation/compare.py` | `validation/` | **copied**, paths fixed | Compares that against Kim's published ground truth → `results/kim_comparison.json`. |
| `validation/build_manifest.py` | `validation/` | **copied**, paths fixed | Provenance only: how the manifest was built. Not part of the normal flow; rerunning it rewrites `extracted_root`. |
| `validation/synthetic_generality_tests.py` | `validation/` | **copied**, imports+paths fixed | Structural-not-nominal regression guards for fix passes 2–3. |
| `validation/kim_file_manifest.json` | `validation/` | **copied byte-identical** | Maps the 145 corpus files to (case study, LLM, pattern). Left untouched so the migration cannot be accused of moving the goalposts; `run_scorer.py` rebases the stale `extracted_root` instead. |
| `validation/kim_comparison.json` | `results/` | **copied** | Committed baseline. The 91.2% agreement figure the migration must reproduce. |
| `validation/kim_replication_raw.json` | `results/` | **copied** | Committed baseline, per-property. |
| `validation/kim_replication_report_v5.md` | `docs/KIM_VALIDATION.md` | **copied** | The current report. v5 is the live one; v1–v4 are history. |
| `validation/bdt_property_spec.md` | `docs/PROPERTY_SPEC.md` | **copied** | The reviewable `Bn`/`Dn`/`Tn` property definitions, weights and critical sets. |
| `validation/*_v1.*`, `*_v2.*`, `*_v3.*`, `*_v4.*` (13 files) | `archive/fix-pass-diffs/` | **dropped from repo, kept on disk** | The history of four fix passes. Superseded by the v5 outputs. `archive/` is gitignored. Includes `kim_replication_report_v2_snapshot.md` and `kim_replication_report.md` (byte-identical to v1). |
| `validation/make_report*.py` (5 files) | `archive/fix-pass-diffs/` | **dropped from repo, kept on disk** | Report generators, one per pass. None kept — v5's *output* is now `docs/KIM_VALIDATION.md`, so the generator is dead weight. |
| `validation/piqs_service_*.diff` (5 files) | `archive/fix-pass-diffs/` | **dropped from repo, kept on disk** | The patches of the four fix passes plus the BDT pass. Already applied to the checker; the applied state is the truth. |
| `app/api/`, `app/core/`, `app/llm/`, `app/schemas/`, `app/utils/`, `main.py` | — | **dropped** | The FastAPI service: routes, settings, LLM clients, request/response models. This is not a web service. |
| `app/services/` — the other 10 files (CK metrics, Halstead, MI, analysis pipeline, analysis service, batch generation, batch metrics, prompt service, file service) | — | **dropped** | Code-quality metrics and LLM orchestration. Unrelated to structural conformance. |
| `generated_batches/` (3 528 files) | — | **dropped** | Generated LLM output. Regenerable, huge, not evidence of anything here. |
| `datasets_zipped/` (173), `datasets_obfuscated/` (83) | — | **dropped** | Inputs and outputs of the old zip-based obfuscator. The new obfuscator works in memory on source strings. |
| `data/` (35 files) | — | **dropped** | Working data for the metrics/generation pipelines. |
| `generation/` (5), `slurm/` (2), `configs/` (2) | — | **dropped** | Batch generation, HPC job scripts, pipeline configs. No HPC here. |
| `tests/` (5 files) | — | **dropped** | Tested generation, log-probs and Vertex smoke paths. **Contained no PIQS tests at all** — nothing to salvage. |
| `scripts/` — the other 14 files | — | **dropped** | Judge pairs, compression, batch runners, Mann-Whitney / sensitivity validators. Only `obfuscate.py` came across. |
| `shannon_entropy.py`, `spearman.py`, `validate_spearman.py`, `run_judge_evaluation.py` | — | **dropped** | Statistics for the LLM-judge study, a different piece of research. |
| `docs/how_to_run_on_slurm.md`, `docs/generation_pipeline_review.md` | — | **dropped** | Document the dropped HPC and generation pipelines. |
| `requirements.txt`, `requirements-generation.txt`, `requirements-hf.txt` | `requirements.txt` | **rewritten** | Old: FastAPI, uvicorn, pydantic, pydantic-settings, requests, python-multipart, plus generation/HF stacks. New: `pytest` alone — `piqs/` and `validation/` import only the standard library. |
| `README.txt`, `DATA_LAYOUT.md`, `SOURCE_LAYOUT.md` | `README.md` | **rewritten** | Described the service and the dataset layout, both gone. |

## Edits made while copying

Copied code was changed only in these ways. No predicate, threshold or weight was touched.

- `PIQSService` → `PIQSChecker` everywhere, and `from app.services.piqs_service import ...`
  → `from piqs.checker import ...`. `_PATTERN_WEIGHTS` and `_CRITICAL_PROPERTIES` stay exported;
  the validation scripts import them directly.
- Every script had `/Users/hieunguyen/Documents/Coding Projects/DP Recognition Backend`
  hardcoded. All now derive the project root from `__file__`, so the repo runs anywhere.
- Output paths follow the new layout: batteries materialise into `fixtures/…` instead of
  `validation/…`; `run_scorer.py` and `compare.py` write into `results/` instead of `validation/`.
- `run_scorer.py` resolves each program under `fixtures/kim/<program>/` rather than trusting
  the manifest's `extracted_root`, which points at a scratchpad directory that no longer exists.
- Doc-comment references were updated to the new paths and names.

One consequence worth recording: `run_scorer.py` stamps its output with
`"scorer": "piqs.checker.PIQSChecker (unmodified)"`, where the committed baseline in
`results/kim_replication_raw.json` says `"app.services.piqs_service.PIQSService (unmodified)"`.
That provenance string, and the recorded Python version, are the only fields expected to differ
between the baseline and a fresh run. Every verdict, predicate and score must be identical.

## Assets that were never in the old repo

Two things live on the user's machine and were never committed, so they could not be migrated
by cloning:

- **`fixtures/kim/`** — Kim's 145-file corpus across 12 programs, referenced throughout
  `validation/kim_file_manifest.json`. External research data: **never edited**.
- **PIQS pattern tests** — believed to exist locally, covering the five original patterns.
  The old `tests/` folder has none.

Both are handled in Stage 2.
