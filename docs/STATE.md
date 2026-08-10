# PROJECT STATE

Working notes for whoever (human or agent) picks this repo up next.

**Scope of this file:** engineering state only. Paper strategy, venue and schedule live outside
the repo on purpose — see "What does not go in this file" at the end.

Last updated: **2026-08-07**, branch `parser-phase2`. The commit that carries this revision
is the one that migrates body helper 1; `git log --oneline -1` is authoritative.

**This file supersedes `HANDOVER.md`**, which was created on this branch on 2026-08-06 and has
been deleted. Two state files is the drift that made this one necessary. "Park it" and "update the
state file" both mean this file.

---

## 1. What this repo does

One job: decide whether Java source **structurally** conforms to a GoF design pattern, and prove
the verdict does **not** depend on identifier names.

Why name-independence matters: the checker will be run on LLM-generated Java. Generated code uses
unusual identifier names. A checker that reads names would report its own bug as a model result.

The proof is `tests/test_renaming_invariance.py`: rename every user identifier to nonsense, and
the verdicts must not move.

## 2. The four suites — the measurement

Run all four after **every** change. Never fewer.

```bash
.venv/bin/python3 validation/run_scorer.py && .venv/bin/python3 validation/compare.py
.venv/bin/python3 validation/run_mutation_battery.py                 # 12 cases
.venv/bin/python3 validation/run_mutation_battery_bdt.py             # 27 cases + 5 D6
.venv/bin/python3 -m pytest tests/ -q                                # incl. invariance
```

**A fifth command, answering a different question.** The four suites report VERDICTS. This
reports the FACTS the parser extracts, so a parser regression is visible even when no verdict
moves — which is exactly the situation Step 3 creates:

```bash
.venv/bin/python3 validation/golden_facts.py --check    # 197 files, 267 types, 552 methods
```

| Suite | Baseline |
|---|---|
| Kim property agreement | **90.6%** (145/160) |
| Kim units exact on all 3 metrics | 30/40 |
| Mutation battery | 12/12 |
| BDT battery | 27/27 + 5/5 D6 |
| Renaming invariance failures | **8** (5 × `C3`, 3 × `O1`) |
| pytest | **179 passed, 8 failed** (187 collected), **0 warnings** |
| Golden facts (`--check`) | 197 files, 267 types, 552 methods, 0 differences |

pytest was 120 before the scope table (+20 `tests/test_scope_table.py`) and 140 before body
helper 1 (+17 `tests/test_body_helpers_divergences.py`). Collected by file: 81 invariance +
22 parity-harness + 20 method-extraction + 20 scope-table + 17 body-divergences +
3 parser-declarations + 2 D6 = 165.

**The pytest warning count is 0, and that is load-bearing.** A `SyntaxWarning` from `\\s` in a
docstring was caught during step 2 only because the run reported `1 warning` where there had
been none. Every `.py` in the repo now compiles clean under `-W error::SyntaxWarning`. If the
count is ever non-zero, something new is wrong.

The 8 invariance failures are **known and expected**. `C3` and `O1` still read hardcoded names.
They are fixed in Stage 3 and Stage 4, not before.

**Environment note — this is not optional on the dev machine.** Bare `python3` resolves to a pyenv
build with **no `tree_sitter_java`**; `run_scorer.py` then exits 1, correctly. Use
`.venv/bin/python3`. Do **not** mask an exit code with a pipe — `cmd | tail` makes `$?` the exit
code of `tail`, not of `cmd`. Redirect instead: `cmd >/dev/null 2>&1; echo $?`.

`compare.py` refuses to run when `results/kim_replication_raw.json` is older than `checker.py` or
`parser.py`, so a stale snapshot cannot be reported as a fresh result.

## 3. Rules of work

1. **One change at a time.** All four suites before the next change starts.
2. **Predict before you change.** Write the expected numbers down first, then run, then compare.
3. **Branch. Never merge without review.**
4. **Never edit an expected result to make a test pass.** A flipped test is information. Report and stop.
5. **Prove a guard is real.** Show the test failing against a deliberately broken implementation
   before showing it passing against the real one.
6. **Stop at checkpoints and wait.**

**The lesson this repo keeps re-learning.** "No test breaks when I remove this" only tells you the
corpus and the test suite do not contain the case. It does not tell you the code is dead.
Before deleting anything: build the case, prove the branch fires, run it both ways, decide from
the specification.

Two recorded instances (full write-up in `docs/PROPERTY_SPEC.md`, "What a green suite does not
prove"):

| Instance | What happened |
|---|---|
| The `D6` guard | One line (`not m.has_body`) was nearly deleted as dead code. It changes `PIQS` 100 → 86.67 on an abstract decorator base. No corpus file exercises it. Pinned by `tests/test_decorator_d6_abstract_base.py`. |
| The nested-class scope test | The test looked like it guarded the nested-type boundary. Mutation proved it did not — the walk never reads `field_declaration` at all, so removing the boundary failed only the sibling *variable* test. It guards a *different* future mutation: adding `field_declaration` to the walk, which fails both. Kept, for the corrected reason. |

## 4. What is done

### Checker repair — 4 of 6 stages

| Stage | Change | Kim result |
|---|---|---|
| 1 | Parser bug: `_METHOD_SIG_RE` had no left boundary, so method **calls** were read as **declarations** | 91.2% (no change), invariance 4 → 8 |
| 2A | Framework detector: a supertype is "framework" only if **not declared in the project** and on a known list | 91.2% |
| 2B | Prediction put on record before the policy change | — |
| 2C | Framework policy applied: inherited structure does not count | 91.2% → **90.6%** (predicted exactly) |
| 2D | Removed `or ("Observer" in t.implements)` from `O4` | 90.6% |

### Parser migration — Phase 1 (declarations), all 4 steps

- Parity harness built **first**: compares both readers fact by fact across the corpus, not just
  verdicts.
- Real regex bugs found and fixed: `Map<String, Wallet>` fields vanished, nested class methods
  leaked onto the parent, `default` missing from the modifier list.
- All declaration regexes deleted. Zero movement on all four suites.

> **Unverified from inside the repo.** The counts often quoted for this phase — 18 deliberate
> breakages, 19 / 6 / 1 affected cases, `checker.py` 1701 lines before — appear in no committed
> document. They are carried forward from working reports. The line counts that *can* be checked
> are below. Treat the rest as history, not as evidence.

| File | `main` | `parser-phase2` |
|---|---:|---:|
| `piqs/checker.py` | **1516** | **1621** |
| `piqs/parser.py` | **302** | **583** |

**Parity harness limitation — now solved by a different tool.** The regex side is deleted, so
`validation/extractor_parity.py` can only compare the parser against itself, which passes
trivially, and it can never verify a version bump. `validation/golden_facts.py --check` does: the
snapshot was written by the pinned versions and committed, so a bumped parser is compared against
recorded facts rather than against itself. `requirements.txt` carries the procedure.

Current behaviour, verified: default invocation exits **1** with an explanation;
`--a parser --b parser` compares 184 files with 0 differences and exits 0.

## 5. Where we are — Parser Phase 2 (bodies + scope table)

Goal: move method **body** analysis from regex to tree-sitter, and build a scope table.

| Step | What | Status |
|---|---|---|
| 1 | Scope table: `{identifier → declared type}` per method | **DONE**, unmerged on `parser-phase2` |
| 2 | Body helpers as tree queries | **DONE** — all five helpers migrated |
| 3 | Traversal detection, six loop forms | not started — the payoff |

### Step 1 — what was built

| Piece | Where |
|---|---|
| `JavaMethod.locals` | `checker.py` |
| `_declared_in_body` (the AST walk) | `parser.py` |
| `PIQSChecker._scope(t, m, types)` | `checker.py` |
| 20 tests | `tests/test_scope_table.py` |
| Resolution rule | `docs/PROPERTY_SPEC.md`, "Identifier resolution" |

Design: **build the table, wire nothing.** Zero call sites changed, so zero movement is true by
construction. All verdict risk is pushed into Step 3 where it can be measured alone.

Lambda parameters are stored as name-without-type (`dict[str, str | None]`). Parameters are
**not** duplicated into `locals` — they already live in `param_names` / `param_types`; `_scope`
is the only supported accessor.

**Three shadowing relationships, not one.** `_scope` merges fields → parameters → locals, so:

| Relationship | Nearest declaration wins | Guard |
|---|---|---|
| local vs field | the local | `test_local_shadows_field_of_the_same_name` |
| parameter vs field | the parameter | `test_parameter_shadows_field_of_the_same_name` |
| **own field vs inherited field** | **the own field** | `test_own_field_shadows_inherited_field_of_the_same_name` |

The third was **inverted until 2026-08-07**. `_effective_fields` returns own fields first and
ancestors after, so a plain dict comprehension let the ancestor win: a `Sub` declaring
`Component held` over a `Base` declaring `Object held` resolved `held` to `Object`. Fixed by
`reversed(...)` **inside `_scope` only** — `_effective_fields` is not reordered, because its other
caller (`_evaluate_builder`) collapses the result into a set, where order is invisible, and
reordering it would be an unmeasured change elsewhere.

Not cosmetic: D3 asks whether a wrapper forwards to *the held reference*, and Step 3 resolves that
receiver's type through this table. **No corpus file shadows an inherited field**, so all four
suites passed with the bug present. Pinned by `tests/fixtures_parser/shadowed_inherited_field.java`.

Five guards, each proven by the mutation that makes it fail:

| Mutation | Tests that fail |
|---|---|
| drop the nested-type boundary | the nested-*variable* test |
| also harvest nested `field_declaration`s | both nested tests |
| invent a type for `o -> ...` | the untyped-lambda test |
| merge fields over locals | both *local/parameter* shadowing tests |
| **drop `reversed()` in `_scope`** | **only the inherited-field test** — the other two shadowing guards still pass, which is exactly why this bug survived |

**Census — measured PER PROGRAM, which is how the checker evaluates.** 51 units (12 Kim programs
+ 12 mutation-battery + 27 BDT cases), 184 files, 237 types, 492 methods.

| | A — body-declared names (`m.locals`) | B — full scope (fields + params + locals) |
|---|---:|---:|
| Total | **170** (14 untyped lambda params) | **1332** |
| Mean over the **88 non-empty** methods | **1.93** | — |
| Mean over **all 492** methods | 0.35 | **2.71** |
| Max in one method | 11 | 12 |

`170 / 88 = 1.93` (A). `1332 / 492 = 2.71` (B). Both divide.

> **An earlier version of this census was wrong** and the figures are in the git history: 131
> types / 233 methods / 102 names / 2 untyped lambda params / mean 3.09 / 506 entries. It called
> `extract_types` **once over all 184 files at once**. That function keys its result by SIMPLE
> NAME, so a class appearing in several programs — `Sale` is in five — collapses to a single
> entry, last one wins. Every figure was understated. The checker never does this: it evaluates
> one program at a time. Census the same way, or the denominator is not the population.

For the paper: *"Across 51 programs / 184 files / 237 types / 492 methods, the scope table records
170 body-declared names in 88 methods (mean 1.93 per non-empty method; 0.35 over all methods; max
11), of which 14 are untyped lambda parameters. Full scope size, including fields and parameters,
averages 2.71 over all 492 methods (max 12)."*


### A finding that whole-corpus extraction DELETES

`extract_types` keys its result by simple name, so extracting many programs in one call makes a
class present in several of them collapse to a single entry, last one wins. Applied to the
framework-inheritance detector, `AuditLog` — the one type in the corpus that obtains its Observer
structure from `java.util.Observable` — collapses with a same-named class from another program,
and the survivor does not extend `Observable`.

The count therefore reads **0 framework-inheriting types instead of 1**, with nothing to indicate
a type was dropped: the corpus simply looks uniform.

What would have been lost is a result, not a statistic — that one of five models delegated Observer
to the JDK while the other four wrote the structure themselves. This belongs with "11 predicates
changed and 0 verdicts changed" as a property of the tool rather than of the data: an aggregate
computed at the wrong granularity can erase the very case it was built to detect.

### The controlled pair: when a purpose-built fixture is load-bearing

Two deliberate errors of comparable severity were introduced during step 2, one per helper, and
measured before correction. What caught them differed:

**Step 3 negative controls — independence proven by disjoint mutation sets.** N1 and N3 both guard
the element-type check, but on *different code paths*, so a mutation of one leaves the other
untouched:

| Mutation | N1 | N2 | N3 |
|---|---|---|---|
| element-type check dropped on the **form-1** branch | **flips** | held | held |
| element-type check dropped on the **form-3** branch | held | held | **flips** |
| element MENTIONED rather than the receiver | held | **flips** | held |
| element type taken from any observer-typed field | held | held | **flips** |

N1 = {A1}, N2 = {B}, N3 = {A3, C} — disjoint. An earlier table patched both branches at once,
which made N1's set look like a subset of N3's and the two look redundant.

**N4 is UNPROVEN and must not be counted as a guard yet.** It guards the enclosing-loop rule for
forms 2 and 6, and nothing implements those, so there is no code to widen and no mutation that can
flip it. It is proven when form 2 lands. **If the stopping rule drops forms 2 and 6, delete N4**
rather than leaving a guard for shipped-nothing.

**A MUTATION MUST CHANGE EXACTLY ONE THING.** The first attempt at the table above patched both
element-type checks at once, so it could not tell N1 from N3 and made one look redundant. A
mutation that changes two things measures neither. This is "one change at a time" applied to the
test-the-test step, and it is as easy to get wrong there as anywhere else.

**Mutation-testing method note.** Results from rapid successive in-place patches proved
unreliable: stale `__pycache__` survived rewrites and produced two contradictory readings of the
same mutation. Mutation runs now clear bytecode and verify the on-disk content immediately before
evaluating. Earlier single-mutation runs in this project were separated by full suite runs and are
not affected.

| Helper | Deliberate error | Caught by a PRE-EXISTING suite? | Caught by its new fixture? |
|---|---|---|---|
| 2 — mentions | omit the `this` / `super` keyword nodes | **Yes** — BDT battery, 3 mismatches, exit 1 | yes (4 fail) |
| 3 — delegation | widen the receiver to the first identifier under the object | **No** — Kim, the mutation battery and BDT all stayed green | **yes, only** (4 fail) |
| 4 — assignment | drop the `operator == "="` filter, so all ten compound forms count | **No** — all four suites green, BDT exit 0 | **yes, only** (1 fail) |

**Re-verified 2026-08-08 under controlled conditions** (bytecode cleared, on-disk content checked
immediately before each run), because these results are a paper claim and mutation runs are
exactly what stale bytecode corrupted. All three reproduce: helper 2 -> BDT 3 mismatches exit 1;
helper 3 -> all four suites green, 4 divergence fixtures fail; helper 4 -> all four suites green,
1 divergence fixture fails.

**A refinement the re-run produced, and the claim should carry it.** A *different* too-wide
receiver rule for helper 3 -- taking a `field_access`'s OBJECT rather than its FIELD -- **is**
caught, by 2 BDT mismatches. So the finding is not "any wrong implementation of helper 3 escapes
the suites". It is that **a plausible wrong implementation did**. Detection here is a property of
the specific error, not of the helper, and the paper sentence should say so.

Two of the three deliberate errors would have shipped with every validation suite green. The
fixture was **load-bearing** for helpers 3 and 4, and merely **confirmatory** for helper 2 — and
nothing tells you which case you are in except running the error and looking.

The distinguishing variable is corpus coverage, not care: divergence #1 has 43 live call sites,
divergence #5 has 0 of 41 (`).op(` appears in no `_delegates_to_field` body).

**Corpus size did not predict detection power.** Kim is 145 files and caught neither error. The BDT
battery is 27 files and caught helper 2's. What matters is whether a corpus contains the construct
— Kim is 2015-era Java that never scores Builder at all, so the properties helper 2 broke are ones
Kim does not evaluate.




### Correction: "Kim's corpus is old Java, so the other loop forms never occur"

That sentence appeared in the handover and was repeated several times, including in this file. It
was **never measured**. Measured across the 145 Kim files:

| Form | Kim | Batteries |
|---|---:|---:|
| 1 enhanced-for | 27 | — |
| 2 indexed `for` | **0** | 1 (`template_abstractlist_analogue`, a Template Method case) |
| 3 `forEach` lambda | **6** | 0 |
| 4 method reference | **1** | 0 |
| 5 `stream().forEach` | **0** | 0 |
| 6 iterator + `while` | **0** | 0 |

Right about forms 2, 5 and 6; wrong about 3 and 4. Kim's corpus does contain Java-8 constructs.

Same failure as the census: a number carried forward from a report, restated until it sounded
established, and never divided. The 6 form-3 sites and the 1 form-4 site both turn out not to move
any verdict — but for reasons that had to be traced, not assumed.

### Step 3 — decisions made BEFORE the work, so they are not made under sunk cost

**The success signal inverts.** Steps 1 and 2 were parity work: predict zero movement, measure
zero, any movement is a defect. Step 3 moves verdicts **on purpose**, so:

| | Steps 1–2 | Step 3 |
|---|---|---|
| Movement | a defect | expected — but every movement needs a **named construct and a fixture** |
| No movement | success | **a warning sign** — either the detection never fired, or it fired and nothing depended on it |

Unexplained movement is still a defect. So is a suspiciously quiet run.

**The stopping rule.** If forms 2 (indexed) and 6 (iterator) stall, ship forms 1, 3, 4 and 5,
record 2 and 6 as known limitations in `docs/PROPERTY_SPEC.md` with the reason, and move on.
Enhanced-for plus `forEach`-lambda covers most real Java. **Do not spend a second session on the
indexed and iterator forms.**

**Out of scope for Step 3's loop work.** `_evaluate_observer`'s `coll_fields` text matching must
NOT change in the same commit as the loop forms. It is the `t.body` trap, and through `elem_re`
(lines 855/868) it moves **Composite** as well as Observer. If loop detection needs the collection
identified differently, that is a separate change with its own prediction — and by the rule in
PROPERTY_SPEC.md it **redefines the predicate** rather than removing a false positive.

**After every form: run the four suites AND `golden_facts.py --check`, and report both.** The
snapshot is load-bearing from here on:

| Verdict moved | `--check` | Reading |
|---|---|---|
| yes | clean | the new detection fired — what we want |
| yes | dirty | **the parser changed underneath you**; the movement is not what you think it is |
| no | clean | detection did not fire, or nothing depended on it — investigate |

### Body-regex inventory — what Step 2 did NOT migrate

Step 2 migrated the five general-purpose body helpers. **25 regexes still read `m.body` or
`t.body` directly**, inside the evaluators. They are not helpers; each is a one-off pattern
inlined into a property. Listed here because Step 3 and Stages 3–4 will touch several, and the
inventory should exist before Step 2 closes. **None is in scope now.**

| Line | Function | Reads | What it matches | Feeds |
|---:|---|---|---|---|
| 422, 428 | `_framework_roles_supplied` | `t.body` | collection-of-project-type | descriptive flag only, never a verdict |
| 436, 437 | `_framework_roles_supplied` | `m.body` | a for-loop + any call | descriptive flag only |
| 550, 565 | `_declared_parents` | `m.body` | `new X(` | Factory `F2`/`F3` creator detection |
| 655, 673, 680 | `_returns_in_hierarchy` | `m.body` | `new X(` capture | Factory `F4` product detection |
| 728 | `_evaluate_strategy` | `m.body` | any `.method(` | Strategy base predicate `calls` |
| 820 | `_evaluate_composite` | `t.body` | `List<`/`Set<`/`Collection<` | `hasChildren(x)` derived |
| 855, 868 | `_evaluate_composite` | `t.body` | collection element type | `C1`, `C4`, `C5` — **the loose `t.body` trap** |
| 913, 928 | `_evaluate_observer` | `t.body` | collection element type | `O2`, `O3`, `O4` — **the loose `t.body` trap** |
| 917, 937 | `_evaluate_observer` | `m.body` | enhanced-for only | `O3` — **the one loop form of six; Step 3's target** |
| 941, 955 | `_evaluate_observer` | `m.body` | `<var>.<callback>(` | `O3`/`O4` callback harvesting |
| 980, 981 | `_evaluate_observer` | `m.body` | `get[A-Z]` / `set[A-Z]` | base `reads` / `modifies` — **name-reading** |
| 983, 988, 989 | `_evaluate_observer` | `m.body` | `.add(` / `.remove(` / `.clear(` | base `modifiesCollection`, `increases`, `decreases` |
| 991 | `_evaluate_observer` | `m.body` | any `.method(` | base `calls` |
| 1124 | `static_instance_of` | `m.body` | `new <Singleton>(` | `G1` |

Three groups matter later:

1. **The loose `t.body` element-type match** (855/868, 913/928) is the trap described above — it
   cannot tell a field from a local or from a method signature. Replacing it is what Step 3 does,
   and it moves Composite as well as Observer.
2. **`foreach_re`** (917/937) matches one loop form of six. Step 3's payoff.
3. **`get[A-Z]` / `set[A-Z]`** (980/981) read names, like `C3` and `O1`. Stage-4 territory. No
   verdict depends on them alone — they are base predicates in the published evidence trace.

### Figure provenance — every number audited after the collapse bug

`extract_types` keys its result by **simple name**. Calling it once over many files collapses
same-named classes across programs, last one wins. Every published figure was re-derived to find
out which ones were computed that way.

| Figure | How it was computed | Verdict |
|---|---|---|
| Scope-table census | one whole-corpus call | **CORRECTED** — see above |
| Divergence #8 coverage | one whole-corpus call | **CORRECTED** — 422 bodies, 7 lambdas, 0 anonymous classes |
| "185 methods with bodies" | one whole-corpus call | **CORRECTED** — the corpus has **422** |
| Framework-inheriting types = **1** (`AuditLog` → `Observable`) | per-program `evaluate()` | **VERIFIED, holds** |
| Unknown supertypes = **0** | per-program `evaluate()` | **VERIFIED, holds** |
| "5 sites feed `coll_fields` a non-field name" | per file | **VERIFIED, holds** |
| 34,190 masked comment/string characters | per program | **VERIFIED**, but the denominator was unstated — it is the **10 scored** programs. All 12 (including the two unscored `original_base`) give 38,729 |
| Body-helper call counts (765 / 78 / 52 / 42) | drove the real checker per scoring unit | **VERIFIED, holds** |
| Divergence #1: 43 `this` sites, 3 True | same | **VERIFIED, holds** |
| ERROR/MISSING nodes = 0 | per file | **VERIFIED**, denominator now stated: 0 of **422** corpus bodies, 0 of **448** including test fixtures |
| Phase 1 parity: 184 files, 0 differences | `extractor_parity.py` parses **one file at a time** (`single = {basename: content}`) | **VERIFIED, holds** |

**Phase 1 is not affected.** `validation/extractor_parity.py` builds a fresh single-entry dict per
file, so its 26 differences and its "phantom methods: 0" result were never measured on a collapsed
table. Do not re-open that work.

**The collapse does not merely understate — it can erase a finding.** Recomputing framework
inheritance over a whole-corpus `extract_types` gives **0** framework-inheriting types, because
`AuditLog` collapses with a same-named class from another program and the survivor does not extend
`Observable`. The per-program figure is 1. A finding that exists per program can vanish entirely
when the corpus is flattened.

### Method counts, with denominators stated

| Basis | Files | Methods | With body | Bodyless |
|---|---:|---:|---:|---:|
| 184 corpus files | 184 | 492 | **422** | 70 |
| 51 units, per program | — | 492 | 422 | 70 |
| Corpus + `tests/fixtures_parser` | 193 | 526 | 448 | 78 |

Per-file and per-program are identical: a file belongs to exactly one program, so grouping cannot
change per-file extraction. The census differed only because it extracted every file in **one**
call. An earlier report gave "434 method bodies" for the ERROR scan and "422" for divergence #8
without saying so — 434 was corpus **plus the five test fixtures existing at that moment**.

Load-bearing check: `Receipt.toString` resolves `items → List` and `item → SaleLineItem`;
`Sale.getSaleLineItem` is correctly **absent** from its own scope.

### Step 2 — the eight divergences

Five helpers move, in this order — one at a time, four suites between each:

| # | Helper | Divergences it decides | Status |
|---|---|---|---|
| 1 | `_calls_method` **+ `_calls_within`** (a one-line delegate; cannot move separately) | 4, 6, 7, 8 | **DONE** |
| 2 | `_mentions_token` → `_mentions_within` | 1, 4 | **DONE** |
| 3 | `_delegates_to_field` | 4, 5, 8 | **DONE** |
| 4 | `_assigns_field` | 2, 3, 4 | **DONE** |

Helper 1 landed with zero movement on all four suites, as predicted; pytest 140 → 157.
Attribution measured directly at both commits: `8b49bc4` (parent) 140 passed, `5ae1640` 157
passed, every other suite figure identical.

**Helper 2 is the one that proved a divergence live.** `_mentions_token` → `_mentions_within`,
reading `JavaMethod.mentions`. Built NAIVELY first — `{identifier, type_identifier}` — and
measured before correcting:

| | naive | correct (`+ this, super`) |
|---|---|---|
| divergence fixtures | **4 fail** | 24 pass |
| BDT battery | **3 mismatches, exit 1** | 27/27 + 5/5, exit 0 |
| Kim | 90.6% — **unmoved** | 90.6% |

`builder_bloch_fluent_static_nested` and `t5_builder_immutable_product` both go from
`(1,1,1,1,1,1)` to `(0,1,0,0,0,0)` — **five** properties move, not one. PSR 100 → 16.67,
CPC 100 → 25.0, PIQS 100 → 20.0.

The cascade: a terminal is accepted only if its body consumes configured state, one route being
`this` passed to the product constructor. Lose `this`, and `terminals` is empty, so `real_builders`
is empty — and **B1, B3, B4, B5 and B6 all route through `real_builders`**. Only B2 reads
`builder_infos` directly, where `fluent_steps` is still non-empty, which is why B2 alone survives.

**Kim never scores Builder**, so only the BDT battery could ever have caught this — the corpus that
matters is not always the big one.

**Helper 3** (`_delegates_to_field`, signature now `(method, field_name)`) is the mirror image of
helper 2, and just as instructive. Built with a deliberately WIDE qualifier — the first identifier
anywhere under the call's object — and measured:

| | wide | correct (uniform rule) |
|---|---|---|
| divergence fixtures | **4 fail** | 29 pass |
| Kim | 90.6% | 90.6% |
| Mutation battery | 12/12 | 12/12 |
| BDT battery | 27/27 + 5/5 | 27/27 + 5/5 |

**Every suite stayed green while the implementation was wrong.** Divergence #5 has zero corpus
coverage, so the fixtures are the only thing that distinguishes a correct migration from a broken
one. Compare helper 2, where the BDT battery caught it immediately — the difference is coverage,
not care.

Nothing re-narrows the query: `_qualifier` stores `None` for any receiver that is not a simple
reference, and `None` never equals a field name. There is no chain-detection branch.
`_calls_method` is **deleted** — `_calls_within` reading `JavaMethod.calls` is the single API.
`validation/synthetic_generality_tests.py` was the only consumer outside the four suites and now
goes through a real parse rather than a bare string; it still reports 10/10.

Its five guards, each proven by the mutation that makes it fail: revert to the old regex → the
three comment/string tests plus both declaration tests fail (6 total); collect
`object_creation_expression` → the constructor test fails; collect `method_declaration` → both
declaration tests fail; reuse the scope walk's nested-type boundary → all three descent tests
fail; take a `field_access`'s *object* instead of its *field* → the normalisation test fails.

A tree query is not equivalent to a regex over body text. Each difference is a **decision**, not
an accident.

| # | Construct | Decision | Corpus sites |
|---|---|---|---|
| 1 | `this` is a keyword node, not an identifier | Include `this`/`super` in `mentions` | 43 (3 True) |
| 2 | `x += 1` is an `assignment_expression`; the regex misses it | **Exclude** — exact parity | 0 |
| 3 | `int x = 5;` matches the regex, is a declaration in the tree | Exclude — tree wins | 0 |
| 4 | Comments and string literals | Exclude — tree wins | 34,190 chars, 0 verdict effect |
| 5 | `getX().op()` chains | Reject via `None` qualifier | 0 |
| 6 | `new Wallet()` matches `_calls_method(body, "Wallet")` | Exclude — a constructor is not a method | 0 |
| 7 | A method **declared** in a body | Exclude — a declaration is not an invocation | 0 |
| 8 | Anonymous / local class bodies | **Descend** — no boundary for calls | 0 of 422 bodies (7 have a lambda, not the affected shape) |

Seven of eight have **zero corpus coverage**. The suites are not evidence. Each ships with its own
fixture, in the same commit as the helper that decides it.

**Divergence #1 is the only one with a live verdict.** Dropping `this` from the node set produces
exactly 3 disagreements, all real: `return new Pizza(this);`, `synchronized (this) { ... }`,
`return new Point(this);`. Builder `B1` reads it. Its fixture is built **before** the helper.

**Divergence #8, precisely.** The Step 1 boundary is `{class_body, interface_body, enum_body}`. A
**lambda body is none of those** — it is a `block` or a bare expression — so the Step 1 walker
already descends into lambdas. Only an **anonymous or local class body** is stopped. Measured:

| Case | regex | descend | stop at nested |
|---|---|---|---|
| `() -> inner.write(s)` → `delegates(inner)` | True | True | **True** — no divergence |
| `new Runnable(){ … inner.write(s) … }` → `delegates(inner)` | True | True | **False** — the real one |
| `new Runnable(){ public void write(…){} }` → `calls(write)` | True | **False** | False |

The last row is #7 surviving inside a descended body: collecting only `method_invocation` nodes
excludes a `method_declaration` automatically, no special case. Descending does not resurrect
declarations, and there the tree is right and the regex is wrong.

Corpus coverage of #8: of **422** method bodies in the 184 corpus files, **7** contain a lambda
and **0** contain an anonymous class body. At the real call sites,
descend and stop both agree with the regex on all 943 calls.

**Uniform normalisation rule** (reproduces the regex on all 13 cases, for receivers and assignment
targets alike):

> `identifier` → its text. `field_access` → its **field** text. Anything else → `None`.

| Expression | Regex | Stored |
|---|---|---|
| `f.op()` | `f` delegates | `"f"` |
| `this.f.op()` | `f` delegates | `"f"` |
| `f.g.op()` | `g` delegates, `f` does **not** | `"g"` |
| `getX().op()` | nothing | `None` |
| `op()` | nothing | `None` |
| `f = x` / `this.f = x` | `f` assigned | `"f"` |
| `f.g = x` | `g` assigned, `f` not | `"g"` |
| `arr[0] = x` | `arr` not assigned | `None` (skipped) |

Note `f.g.op()` stores **`"g"`, not `None`** — `_delegates_to_field("f.g.op();", "g")` is True, so
storing `None` would lose a real match.

**Data shape.** No tree-sitter nodes are stored on `JavaMethod`. A node is only valid while its
`Tree` is alive. Everything is precomputed at parse time in `_build_method`, from the **real
method node**, into plain Python data:

```python
calls:       list[tuple[str | None, str]]   # (receiver, method_name)
assignments: set[str]                       # simple `=` targets
mentions:    set[str]                       # identifiers AND keywords
```

**The `class __P{void __m(){…}}` wrapper is probe-only and must never reach production.** It exists
only because the measurement scripts receive `m.body` as a *text string* — the shape the current
helpers take — and so have to re-parse. Production has the node already. Re-parsing body text is
also unsound in its own right: a body containing `super(...)` or referring to enclosing scope can
parse with `ERROR` nodes when lifted out of context. One probe run was invalidated by exactly this
wrapper — its own `class_body` tripped the nested-type boundary, so the "stop" walk collected
nothing and reported 28/41/23/31 false disagreements. Fixed by starting the walk at the method's
`block`.

**Step 2 must not read `JavaMethod.locals`.** Shadowing-aware resolution is a meaning change, not
a mechanism change. Parked for Step 3 with its own prediction.

### Step 3 — six loop forms (not started)

`foreach_re` matches **one** loop form. Five are missed:

```java
for (Observer o : observers) o.update();                     // 1. enhanced-for  CAUGHT
for (int i = 0; i < obs.size(); i++) obs.get(i).update();    // 2. indexed       MISSED
observers.forEach(o -> o.update());                          // 3. lambda        MISSED
observers.forEach(Observer::update);                         // 4. method ref    MISSED
observers.stream().forEach(o -> o.update());                 // 5. stream        MISSED
Iterator<Observer> it = observers.iterator();
while (it.hasNext()) it.next().update();                     // 6. iterator      MISSED
```

Kim's corpus is old Java, so this never shows. Generated 2026 Java will use forms 3 and 5.
**The failure is silent** — it looks exactly like a model failing to write Observer.

Verdicts **will** move in Step 3, and that is correct. Every movement needs a named construct and a
fixture. Unexplained movement is a defect.

Forms 2 and 6 have no named element variable — the call sits on `observers.get(i)` or `it.next()`.
If that stalls, ship forms 1 and 3, record the rest as known limitations, move on.

## 6. Traps in the current code

### `t.body` includes method bodies

`_evaluate_observer` builds `coll_fields` from `elem_field_re.findall(t.body)`. `t.body` is the
whole text between the class braces, **method bodies included**. So a local
`List<Observer> snapshot = ...` is already matched — by accident, through text matching.

Confirmed empirically: a program with a local collection and **no fields at all** scores `O3`
satisfied, `PIQS` 77.73 — identical to the field-holding control.

**A fields-only scope table is therefore a regression, not a no-op.**

The same loose pattern is in three places: `_evaluate_observer`, `_evaluate_composite`
(`elem_re.findall(t.body)`, `has_children`), and `_framework_roles_supplied`. Changing collection
element detection can move Composite (`C1`, `C4`, `C5`), not just Observer.

`elem_field_re` also cannot tell a declaration from a method signature: `public List<X> getX() {`
lands in `coll_fields` as a key named `getX`. Currently inert — `foreach_re` needs a bare
identifier after `:`, and a call site always has `()`. The scope table must not reproduce it.
Five such sites in the corpus, listed in `docs/PROPERTY_SPEC.md`.

### Two different meanings of "field" coexist

| Notion | Source | Correctness |
|---|---|---|
| `t.fields` | the tree, class-scope only | correct |
| `coll_fields` / `elem_re` | text regex on `t.body` | loose; locals included |

`_evaluate_observer` uses **both**. So a locally-held **collection** of observers is found, and a
locally-held **single** observer is not. Confirmed empirically. Unifying them is right, but it is a
behaviour change: name it, predict it, fixture it.

### `notifies_loop` is a boolean

`notifies_loop` and `notifies_single` are `True`/`False`. The notifying **type** is discarded.
Stage 3 (`O1`) needs that type. Do not lift it inside Phase 2 — it becomes its own measured change.

### Do not use line numbers

`checker.py` has changed size repeatedly (1516 on `main`, 1621 on `parser-phase2`). Older notes
cite lines 886 and 904–906. Find things by name instead:

| Old reference | Find this |
|---|---|
| line 886 | the `subject_candidates` list comprehension in `_evaluate_observer` |
| lines 904–906 | `is_register` / `is_unregister` / `is_notify` in `_evaluate_observer` |

## 7. Not done — later stages

| Stage | Work | Notes |
|---|---|---|
| 3 | `O1` structural | `subject_candidates` uses `{"attach","detach","notifyObservers","register","remove","notify"}`. Lift the notifying type from the boolean. Look **upward** for the abstract subject via `_conforms_to`. Six derived predicates read `subject_candidates`, so expect Kim to move by more than one cell, in either direction. Finish rule: one construction site, no string literals. |
| 4 | `C3` structural | Uses `_has_verb_prefix(m.name, "add")` / `"remove"`. Structural form: a method whose parameter type is the component type and whose body writes to the component-typed collection field. **Note:** `_has_verb_prefix` is also used by Strategy (setter) and Builder `B5` (immutability) — changing it moves more than `C3`. |
| 5 | Derived predicates | `is_register` / `is_unregister` / `is_notify` read names. No verdict depends on them, but they are the published evidence trace. In Stage 1, **11 predicates changed and 0 verdicts changed** — direct evidence the trace is decoration. Extend the invariance test to cover derived predicates, matched by position not by name. |
| later | `reads` / `modifies` base predicates | They match `get[A-Z]` / `set[A-Z]` regexes over method bodies — name-reading, like `C3` and `O1`, but no verdict currently turns on them alone. Phase 2 must not change them; they are not among the five body helpers. |
| 6 | Obfuscator receiver-aware | Renaming a user method called `add` also renames `list.add(...)`. Fix by tracking declarations, then skipping calls whose receiver is a JDK type. **Do not** fix it by refusing to rename `update` — `update` was renamed in 28 cases and `O4` held 9/9, which is the strongest evidence in the report. |

## 8. Parked

| Item | When |
|---|---|
| `_assigns_field` is documented as signalling a step that **populates state**. `total += x` populates state and is not matched (the regex is `name\s*=(?!=)`; the `+` blocks it). Phase 2 preserves this deliberately — a mechanism change that also changes meaning makes any movement ambiguous. Candidate meaning change, own prediction. Corpus coverage: 0 sites. | after Step 2 |
| Shadowing-aware resolution (a local shadowing a field should arguably fail `D3`) | Step 3 |

| **`Map<K,V>` element type — LOWER priority, and the BiConsumer risk turned out NOT to apply.** Measured after form 3 landed: all six Kim sites are rejected at the **arity check** (a `BiConsumer` has two parameters; `Collection.forEach` takes a one-parameter `Consumer`), *before* `coll_fields` is ever consulted. So the false-positive risk — that adding `Map` to `elem_field_re` would silently resolve the element to the FIRST lambda parameter, `String` rather than `Wallet` — is **not reachable through form 3 at all**. That is a better outcome than being blocked by the accident of `elem_field_re` not listing `Map`: one is a rule correct on its own terms, the other would have evaporated the moment someone edited that regex. What remains genuinely blocked is `values().forEach(...)` and `entrySet().forEach(...)`; see PROPERTY_SPEC.md. Original note follows.** `_base_name` strips the type argument, and `elem_field_re` does not list `Map` at all, so the 6 Kim `forEach` sites (`wallets.forEach((currency, wallet) -> ...)`) cannot resolve an element type. Unblocking it is **not** simply recovering missed positives: **(a)** `Map.forEach` takes a `BiConsumer`, so the element is the **second** lambda parameter — adding `Map` to `elem_field_re` naively would resolve the element type to `String`, not `Wallet`, silently wrong; **(b)** iterating a wallet map is very likely not observer notification at all, so unblocking it may **create a false positive on Kim** rather than recover a missed one. Do not touch in Step 3. | deprioritised |
| `run_scorer.py` calls `javac` and swallows the error — find out what it was for. Unrelated to the process exit code, which is correct (verified: exits 1 on failure). | before generation |
| Add `compiles` + `compile_errors` to result records | before generation |
| Rule: unknown supertypes analysed separately, not scored as failure | before generation |
| The 36 PIQS pattern tests were never committed and are still missing | before generation |
| `A-not-rebroken` case in `validation/synthetic_generality_tests.py` is vacuous — it repeats case A's assertion on case A's fixture. Needs a `ping` callback alongside a `pinger` local to become a real guard. That script is **not** one of the four suites. | any time |
| `w_ops.setdefault` keeps the first overload — pre-existing looseness in `D6` | low priority |

**Snapshot scope decision (settled, do not narrow).** `golden_facts.py` covers
`tests/fixtures_parser/` as well as the 184-file corpus — 197 files in total. Those 13
fixtures are the ONLY place several constructs exist at all: interface default methods, the
shadowed inherited field, and one file per migration divergence. Leaving them out would make
the guard blind to exactly the cases it was built for. "Adding a fixture requires a
`--write`" is a feature, not a cost: a fixture change appearing in a diff is what makes it
reviewable.

**Removed from this list, because it is done:** the golden-fact snapshot — `validation/golden_facts.py` + `results/parser_golden.json`, 197 files / 267 types / 552 methods, proven to go red on six deliberate faults (field type, dropped method, a `calls` entry, an `assignments` entry, an empty corpus, an unparseable file) and green unmodified. `requirements.txt` now carries the version-bump procedure instead of a note saying none exists.

**Also removed, because it is done:** the stale-results guard. `compare.py` now refuses
to run when `results/kim_replication_raw.json` is older than `checker.py` or `parser.py`. Built,
committed, and proven to fire in all four branches (fresh → 0; touch `checker.py` → 1; touch
`parser.py` → 1; results absent → 1).

**Located, not removed:** the "`A-not-rebroken` test is vacuous" item. It is **not** in `tests/` —
it is the last case in `validation/synthetic_generality_tests.py`, which is a standalone script
and **not one of the four suites**. The file flags the defect itself, in a comment: the case
re-runs `props("observer", obs_named)` on the same fixture with the same assertion as case A, so
it cannot fail unless case A also fails. To become a real guard it needs a fixture where the
callback name is a **substring** of another identifier in the same body — a `ping` callback
alongside a `pinger` local — which is the case whole-token matching could plausibly break.
Still open; see section 8.

## 9. What does not go in this file

**This repository is public.** Anything committed here is readable by anyone, under the owner's
real account name.

Keep out of the repo:

- the paper's claim, framing and novelty analysis
- venue, deadline, submission strategy
- anything that would identify the author during double-blind review
- personal or budget notes

Those live in the private working notes, not here. This file carries engineering state only.
