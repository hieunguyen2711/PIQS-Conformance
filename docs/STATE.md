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

## 0. PLAN ORDER — reordered 2026-08-10, and why

**Generation is the schedule bottleneck, and generation needs PROMPTS, not a finished scorer.**
Prompts need the 12 pattern rule tables. The scorer only has to be right by the time results are
scored, which is *after* generation runs. So the four missing patterns outrank the remaining
checker stages.

| # | Work | Why here |
|---|---|---|
| 1 | **Adapter** | The separator is one type comparison. Cheapest of the four, and it proves the porting process before we commit to all four. **Corrected 2026-08-10:** this row used to add "and D4 already encodes it". D4 *stated* the comparison but is weight 2 and non-critical, so it never decided anything — a textbook object adapter was recognised as a Decorator with D4 = 0. Fixed by the same-component rule; see §5a. Adapter's own separator must be weight 3 or in the role derivation. |
| 2 | **State** | Separator is "the field is ASSIGNED from inside a method" — `_assigns_field` on the context's own field, which phase 2 just migrated. |
| 3 | **Abstract Factory** | — |
| 4 | **Proxy** | Blocked on a new property definition; see below. |
| 5 | Stage 3 (`O1` structural) | Without it the checker demonstrably reads names for `O1`, which is fatal to the paper's method claim. |
| 6 | Stage 4 (`C3` structural) | Same, for `C3`. |

**Stages 5 and 6 are DEFERRED, not dropped.**

| Stage | Reason for deferral |
|---|---|
| 5 — derived predicates read names | Its finding — *11 predicates changed, 0 verdicts changed* — is already recorded and IS the paper content. Fixing it adds nothing to the experiment. |
| 6 — obfuscator receiver-awareness | The 28 `update` collisions were already verified by hand. |

### The Proxy blocker — read before planning Proxy

`docs/PROPERTY_SPEC.md` already records that Decorator and Proxy are **structurally identical**
under static analysis, and `t3_decorator_lazy_proxy_KNOWN_LIMITATION` proves it: a real Proxy
scores as a Decorator at PIQS 100.

Conflict pair B is Decorator/Proxy. If both rule sets can be satisfied at once, every X output
scores "both" — and by the experiment design that means the separator is broken and **the pair is
invalid before a single prompt is written**.

The narrow fix, which IS decidable:

| | Where the wrapped object comes from |
|---|---|
| Decorator | arrives through the **constructor** (injected) |
| Proxy | is created **inside** the class |

This does not solve Decorator-vs-Proxy in general. It makes **pair B's separator** decidable. It is
a NEW property definition, not a pattern port, so it gets its own budget and its own prediction.
Do not start Proxy until Adapter and State have landed.

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
| 3 | Traversal detection, six loop forms | **DONE** — all six detected |

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

### When a purpose-built fixture is load-bearing: a within-helper pair

**The primary evidence is two wrong implementations of the SAME helper.** Same code, same suites,
same author, same week — only the error differs, which isolates the variable in a way the
across-helper comparison never quite did.

`_delegates_to_field` (helper 3) resolves a call's receiver. Two plausible ways to get it wrong:

| Wrong receiver rule | Kim | Battery | BDT | Its own fixture |
|---|---|---|---|---|
| first identifier **anywhere under** the object | green | green | **green** | **4 fail** |
| a `field_access`'s **object** instead of its **field** | green | green | **2 mismatches, exit 1** | fails |

One is caught by a pre-existing suite; the other is caught by nothing except the fixture written
for it. **Detection here is a property of the specific error, not of the helper.**

### Corroboration: the across-helper triple

| Helper | Deliberate error | Pre-existing suite? | Its fixture? |
|---|---|---|---|
| 2 — mentions | omit `this` / `super` | **yes** — BDT, 3 mismatches, exit 1 | yes (4 fail) |
| 3 — delegation | widen the receiver | **no** — all four green | **only** (4 fail) |
| 4 — assignment | drop the `operator == "="` filter | **no** — all four green | **only** (1 fail) |

Re-verified 2026-08-08 under controlled conditions (bytecode cleared, on-disk content checked
immediately before each run), because mutation runs are exactly what stale bytecode corrupts. All
three reproduce.

### How to state this, and how NOT to

**Wrong implementations actually tried: helper 2 → 1, helper 3 → 2, helper 4 → 1.** Four in total.
Helper 3's second one was written by accident while re-verifying, not as a designed probe.

The claim is an **existence proof**:

> At least one plausible wrong implementation of two of the three helpers escaped every validation
> suite, and was caught only by a purpose-built fixture.

**Never a rate.** Not "N of M errors escape", not a percentage. Four hand-written errors chosen by
the person who wrote the code is not a sample, and there is no denominator — the space of wrong
implementations is unbounded and unenumerated.

**Corpus size did not predict detection power.** Kim is 145 files and caught none of the four
errors. The BDT battery is 27 files and caught two. What matters is whether a corpus contains the
construct: Kim never scores Builder at all, so the properties helper 2 broke are ones Kim does not
evaluate.

**A MUTATION MUST CHANGE EXACTLY ONE THING — AND IT MUST BE THE RIGHT THING.**

*First half.* An early table patched both element-type checks at once and could not tell N1 from N3
apart, making one look redundant. A mutation that changes two things measures neither. This is "one
change at a time" applied to the test-the-test step.

*Second half.* MUT-4 v1 was written to break the iterator→collection map, and it cleared the map
before each insert. That **deleted** `it2` rather than making it resolve wrongly — so `loopN9` held,
and the fixture looked as if it guarded nothing. Rewritten as "the key is ignored, last value wins",
N9 flips. The mutation was single-purpose and still worthless, because it modelled a *different*
bug from the one the fixture exists to catch.

**A mutation that does not model the bug proves nothing, and it fails in the direction of a false
negative** — the fixture looks redundant and the natural next move is to delete a live guard. This
has now happened twice: `loopN1` (its body was `System.out.println(s)`, so the element was an
argument and the receiver rule rejected it before the element-type check was ever reached) and
MUT-4 v1. Both times the fixture was fine and the *probe* was wrong.

The check before trusting a negative result: **state which line of the real implementation the
mutation is standing in for, and confirm the mutated code still reaches the fixture's code path.**
A mutation that short-circuits earlier than the rule it targets tests nothing downstream of it.

**Mutation-testing method note.** Rapid successive in-place patches proved unreliable: stale
`__pycache__` survived rewrites and produced two contradictory readings of the same mutation. Runs
now clear bytecode and verify on-disk content immediately before evaluating.

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

## 5a. The same-component rule — found 2026-08-10, before Adapter started

**A textbook object adapter was recognised as a Decorator.** Found by review, not by a suite.

```java
interface Target { void run(); }
interface Source { void go(); }
class Adapt implements Target {
    private Source s;
    public Adapt(Source s) { this.s = s; }
    public void run() { s.go(); }
}
```

`D1 0  D2 1  D3 1  D4 0  D5 1  D6 0` → PIQS **53.33**, *Moderate*, **recognised** (critical set
`{D2, D3}` both held).

**The docstring and the code disagreed.** `isDecorator(W)` was documented as "conforms to a
component C **and** holds a field of type C" — the same C twice. The code built two independent
sets and never required them to intersect. The same-type requirement lived only in D1 and D4, both
weight 2 and non-critical, so they flagged the conversion without touching the verdict.

**Why this blocked the experiment, not just the checker.** Conflict pair F is Adapter/Decorator and
was scheduled first *because* its separator looked cheap. Every X output for pair F would have
satisfied both rule sets → the pair is invalid by the experiment's own design. Both pairs planned
as starting points were broken for the same underlying reason:

| pair | status |
|---|---|
| B — Decorator / Proxy | known, recorded in §0 |
| F — Adapter / Decorator | found 2026-08-10, fixed by this change |

In both, the distinguishing condition sat **outside the critical set**. That generalisation is now
a rule in `docs/PROPERTY_SPEC.md`: *a conflict-pair separator must be load-bearing for recognition.*

**Handled as a REDEFINITION, not a bug fix**, per the divergence rule — it changes which programs
satisfy D2, so it got its own branch, its own prediction, and its own measurement.

| Question asked before implementing | Predicted | Measured |
|---|---|---|
| D2 alone, or more? | all six — D1/D3 iterate the field list, D4/D6 take it as an argument, D5 is `... or d2` | all six went to 0 on the adapter |
| Which BDT cases move? | none | none — 28/28 |
| `t3_decorator_lazy_proxy_KNOWN_LIMITATION` still passes? | yes — a Proxy conforms to the type it holds | yes |
| Does Kim move? | cannot — Kim has **no Decorator scoring units** (10 factory, 10 strategy, 10 observer, 5 composite, 5 singleton) | 90.6% (145/160), 30/40 unchanged |
| Effect on the Decorator/Proxy limitation? | none — both hold the type they conform to | unchanged |

**Corpus exposure — remeasured 2026-08-10, one PROGRAM at a time.** `validation/decorator_rule_effect.py`
over 82 units (12 Kim programs with all their files together, 12 mutation battery, 28 BDT, 30
parser fixtures): 2 ADMISSION LOST, 1 FIELD LIST NARROWED, **all three are the fixtures e2acb66
added for this rule**, and **0 pre-existing corpus programs** are affected.

> **The original claim, "0 across 212 single-file programs", was right by accident.** Kim has no
> single-file programs — all 12 are multi-file. Scanning file by file, a class whose interface is
> in a sibling file gets `conformed = {}` and is skipped before the rule is reached, so that scan
> **could not** have found an affected Kim wrapper. The rewrite was wrong on its first run in the
> other direction: it dropped the `if not conformed: continue` gate that the loose rule **also**
> had, and reported 16. Both failures are the same shape — the comparison changed something other
> than the one thing under test. See §5b.

**The filter is on the FIELD LIST, not only on admission.** Gating admission alone leaves every
component-typed field in `wrapped_fields`, which D3/D4/D6 all read — so a class conforming to `C`,
holding both a `C` and an unrelated abstract `D`, and forwarding only to `D`, would still score
`D3 = 1`. `decorator_delegates_to_unrelated_component.java` is the only program in the repo where
the two forms of the rule disagree, because every corpus program holds exactly one component-typed
field.

**Open decision, deliberately not settled: D1 is now tautological.** `D1 == D2` for every program.
No number moved, but the Decorator set is **four** independent properties scored as six, which
inflates PSR for every recognised decorator. Removing D1 changes PSR's denominator for every
Decorator program — a second measured change, not this one. Pinned by `test_d1_is_now_implied_by_d2`.
*(This paragraph first said "five". The audit in §5c found D5 tautological too.)*

**A silent-skip hole was closed at the same time.** `tests/test_renaming_invariance.py` maps a
fixture filename to a pattern by substring and does `if pattern is None: continue`. A battery file
matching no marker was **dropped from the suite without a word** — green, and never tested.
`test_every_battery_file_is_covered` now compares the case list against the files on disk. It is
compared against the directory rather than a hardcoded count so it cannot go stale, and so the fix
is never "edit the number". Proven by dropping a marker-less file into the directory and watching
it fail.

## 5b. The measurement was wrong twice, in opposite directions

Both errors gave the *same kind* of wrong answer for the *same underlying reason*, and neither was
caught by a suite. The rule they teach is the mutation rule again, pointed at measurement rather
than at tests:

> **A script that compares two versions of a rule must hold everything except the one difference
> identical — otherwise it measures itself.**

| | What it did | What it reported | Why it was wrong |
|---|---|---|---|
| v0 — the file-by-file scan | one `.java` file at a time across the whole tree | "0 affected across 212 single-file programs" | **Kim has no single-file programs.** All 12 are multi-file (6–16 files). A class whose interface is declared in a sibling file gets `conformed = {}` and is skipped before the rule is reached, so the scan could not have found an affected Kim wrapper even if one existed. The answer was right; nothing about the method made it right. |
| v1 — `decorator_rule_effect.py`, first run | one program at a time, but modelled only the field list | **16** affected wrappers | It dropped `if not conformed: continue`, which the **loose rule had too**. Classes conforming to no abstract type were never candidates under either rule, so they had no admission to lose. Every `Context`-holds-a-`Strategy` and `Director`-holds-a-`Builder` in the corpus was counted as an effect of a change that never touched it. |
| v2 — corrected | one program at a time, both gates modelled | 2 + 1, all three planted | matches the prediction |

**The v1 failure is the more dangerous shape**, because it fails *loud*: a scary non-zero number
that invites a fix to the checker rather than to the script. v0 failed *quiet*, which is worse for
a reader and better for the code. Neither was a suite failure — no suite scores these programs as
Decorator, so no verdict ever moved and all four stayed green throughout. §2's rule applies
directly: **green suites mean the corpus lacks the case.**

**A measurement that returns zero must be shown capable of returning non-zero.**
`decorator_rule_effect.py` now carries a named positive control — the three fixtures `e2acb66`
added for this rule — and prints a warning if the control does not fire. Without it, "0 affected"
and "the script is broken" are the same output.

## 5c. Decorator tautology audit — measured 2026-08-10, NOTHING DELETED

**Four of the six Decorator properties carry information. Six are scored.**

Measured over 82 program units (12 Kim programs with all their files together, 12 mutation
battery, 28 BDT, 30 parser fixtures), every one evaluated as `decorator`:

| | measured |
|---|---|
| programs where `D1 != D2` | **0** |
| programs where `D5 != D2` | **0** |
| programs where `D2 == 1` | **13** |

| Property | Independent of D2? | Separating program |
|---|---|---|
| D1 | **NO** — identity by construction | none can exist |
| D3 | YES | `decorator_delegates_to_unrelated_component`, `decorator_no_delegation__FAIL`, `div5_chain_not_delegation` |
| D4 | **YES** — but the probe had to be built | `d4_abstract_base_partial_api.java` (new) |
| D5 | **NO** — identity by construction | none can exist |
| D6 | YES | `t1_decorator_partial_delegation_accepted` + 3 more |

### Why D1 and D5 cannot be separated by ANY program

An argument from the code, not from the corpus — a corpus can only ever say *"no case here"*.

**D1.** `wrapped_fields` is built by filtering on `f.field_type in conformed`, and `d1` then tests
`any(ctype in conformed ...)` over that same list. The quantifier ranges over a list built by
filtering on exactly the predicate it tests, and a candidate is appended only when the list is
non-empty. So `d1 == bool(decorators) == d2` for every input.

**D5.** `d5 = abstract_decorator_base or d2`, where `abstract_decorator_base` is an `any(...)` over
`decorators`. Two exhaustive cases: `decorators` empty → `d2` False and `any` over empty is False
→ `d5` False; `decorators` non-empty → `d2` True → `d5` True by the `or`. So `d5 == d2` always.
`abstract_decorator_base` is not dead — D5's description reads on it — but it can never change
D5's value.

### D4 survived, and only because a probe was constructed for it

**In the BDT battery `D4 == 1` in all 8 recognised decorators, which proves nothing.** `d4` is an
`any(...)` over every decorator in the program, and for a **concrete** class the Java compiler
already forces the implemented method set to cover the interface. One concrete decorator sets D4
for the whole program, and every battery case has one. This is trap-shaped: the corpus agrees with
"D4 is redundant" and with "D4 is independent" equally well.

`d4_abstract_base_partial_api.java` is an abstract decorator base implementing part of the
component API with **no concrete decorator present**. `_effective_methods` walks `extends` only,
never `implements` (checker.py:353), so the wrapper's effective method set is `{write}` while the
component's is `{write, flush}`.

    D1 1 · D2 1 · D3 1 · D4 0 · D5 1 · D6 1     PSR 83.33 · CPC 83.33 · PIQS 83.33 · Good

**Each guard proven against a deliberately broken checker**, one thing changed each time:

| Mutation | Flips |
|---|---|
| `d5 = abstract_decorator_base` (drop the `or d2`) | D5 tautology test **only** |
| `_transparent` uses `&` instead of `<=` | D4 independence test **only** |
| `wrapped_fields` back to `component_names` | D1 tautology test **and** the D3 separator |

The third flips two, correctly: reverting the same-component rule restores `Router`'s loose field
list, so its D3 becomes 1 and the separator disappears with it. One thing changed; two properties
depend on it.

**One wrong claim was written and caught by its own test.** The first version named
`abstract_decorator_base` as D6's separator. It is not — it scores `D6 = 1`. It is the fixture for
D6's `not m.has_body` clause, which is a different question from whether D6 disagrees with D2.

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
