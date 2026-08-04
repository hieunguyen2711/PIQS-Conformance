# piqs-conformance

Checks whether Java code **structurally** conforms to a design pattern — and proves the check
does not depend on identifier names.

A library plus a command line tool. Not a web service.

## The claim

Design-pattern detectors often cheat: a class called `PaymentStrategy` with a method called
`notifyObservers()` gets recognised because of what it is *called*, not because of what it *is*.
This project checks structure — return types, field types, call targets, abstract vs concrete,
`extends` / `implements` — and then demonstrates the independence by machine-renaming every
user-defined identifier and requiring the verdicts to be unchanged.

## Install

```sh
pip install -r requirements.txt   # pytest only; the library itself is stdlib-only
```

## Use

As a library:

```python
from piqs.checker import PIQSChecker

result = PIQSChecker().evaluate("observer", {"Bus.java": source, "Watcher.java": source2})
result["logical_assessment"]            # per-property verdicts + justifications
result["final_quality_result_piqs"]     # PSR/CPC/PIQS scores
```

As a command line tool:

```sh
python -m piqs.cli observer path/to/src/            # conformance report
python -m piqs.cli observer path/to/src/ --json     # raw evaluation dict
python -m piqs.cli observer path/to/src/ --obfuscate  # same check, all identifiers renamed
```

Exit code is 0 when every critical (weight-3) property is satisfied, 1 otherwise.

## Patterns

Five from Kim (2025) — `factory-method`, `strategy`, `composite`, `observer`, `singleton` —
plus three added here: `builder`, `decorator`, `template-method`.

A program *is* the pattern when all of its **critical** (weight-3) properties hold. Scores:

- **PSR** = satisfied / total × 100
- **CPC** = Σ(wᵢ·sᵢ) / Σ(wᵢ) × 100
- **PIQS** = PSR × 0.6 + CPC × 0.4

## Layout

| Path | What |
|---|---|
| `piqs/checker.py` | the checker — `PIQSChecker`, `_PATTERN_WEIGHTS`, `_CRITICAL_PROPERTIES` |
| `piqs/obfuscator.py` | renames every user-defined identifier across a set of sources |
| `piqs/cli.py` | command line entry point |
| `fixtures/mutation_battery/` | 12 labelled cases (the oracle for `G1` / `F4` meaning) |
| `fixtures/mutation_battery_bdt/` | 27 labelled cases (the oracle for Builder / Decorator / Template Method) |
| `fixtures/kim/` | Kim's 145-file corpus — **external research data, never edited** |
| `validation/` | the reproduction scripts |
| `results/` | committed baseline outputs the reproduction must reproduce |
| `docs/` | validation report, property spec, migration record |

## Validation

```sh
python validation/run_mutation_battery.py       # 12 cases, exit 0 iff all match their label
python validation/run_mutation_battery_bdt.py   # 27 cases, exit 0 iff all match their label
python validation/run_scorer.py && python validation/compare.py   # Kim corpus
python validation/synthetic_generality_tests.py # structural-not-nominal regression guards
pytest                                          # renaming invariance
```

Battery filenames carry their own expected verdict: a case ending `__FAIL` must not be
recognised as the pattern; every other case must be. The single exception is
`t3_decorator_lazy_proxy_KNOWN_LIMITATION.java`, a documented accepted limitation
(Decorator vs Proxy are structurally indistinguishable) — see [docs/PROPERTY_SPEC.md](docs/PROPERTY_SPEC.md).

Against Kim's published ground truth the checker agrees on **146/160 = 91.2%** of property
judgments, with 30/40 scoring units matching all three metrics exactly — see
[docs/KIM_VALIDATION.md](docs/KIM_VALIDATION.md).

## Credits and data provenance

**`fixtures/kim/` is not our data.** It is the corpus from Kim (2025), redistributed here
unmodified for reproducibility: 145 Java files across 12 programs — two case studies (POSS, a
Point of Sale System; SWS, a Smart Wallet System), each in an original form plus five
LLM-refactored versions (ChatGPT, Claude, Copilot, Gemini, Meta). Kim's published per-property
verdicts and PSR/CPC/PIQS tables are the ground truth that `validation/compare.py` scores
against, and the PSR/CPC/PIQS formulas and the Table 9 weighting philosophy are Kim's.

Those files are treated as read-only research data and are never edited. The ZIP distribution
they were extracted from is recorded per program in `validation/kim_file_manifest.json` under
`source_zip`. Credit for the corpus and the metric belongs to Kim; the structural checker, the
39-case mutation battery, the three added patterns (Builder, Decorator, Template Method) and
the renaming-invariance work are ours.

## Repo provenance

Migrated from `Java-Design-Patterns-Analyzer`, which was a FastAPI service carrying LLM
clients, HPC job scripts and generated datasets. What came across and what did not is recorded
in [docs/MIGRATION.md](docs/MIGRATION.md).
