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

| Suite | Baseline |
|---|---|
| Kim property agreement | **90.6%** (145/160) |
| Kim units exact on all 3 metrics | 30/40 |
| Mutation battery | 12/12 |
| BDT battery | 27/27 + 5/5 D6 |
| Renaming invariance failures | **8** (5 × `C3`, 3 × `O1`) |
| pytest | **157 passed, 8 failed** (165 collected) |

pytest was 120 before the scope table (+20 `tests/test_scope_table.py`) and 140 before body
helper 1 (+17 `tests/test_body_helpers_divergences.py`). Collected by file: 81 invariance +
22 parity-harness + 20 method-extraction + 20 scope-table + 17 body-divergences +
3 parser-declarations + 2 D6 = 165.

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
| `piqs/checker.py` | **1516** | **1582** |
| `piqs/parser.py` | **302** | **451** |

**Parity harness limitation.** The regex side is deleted, so `validation/extractor_parity.py` can
only compare the parser against itself, which passes trivially. It therefore **cannot** verify a
tree-sitter version bump, despite what `requirements.txt` used to say — that instruction has been
corrected in place. A committed golden-fact snapshot would fix this. Queued as a Phase 2 Step 3
prerequisite, because Step 3 moves verdicts on purpose and a fact-level guard is the only way to
tell "new detection" from "accidental parser regression".

Current behaviour, verified: default invocation exits **1** with an explanation;
`--a parser --b parser` compares 184 files with 0 differences and exits 0.

## 5. Where we are — Parser Phase 2 (bodies + scope table)

Goal: move method **body** analysis from regex to tree-sitter, and build a scope table.

| Step | What | Status |
|---|---|---|
| 1 | Scope table: `{identifier → declared type}` per method | **DONE**, unmerged on `parser-phase2` |
| 2 | Body helpers as tree queries | **1 of 4 done** — `_calls_method` + `_calls_within` migrated |
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

Lambda parameters are stored as name-without-type (`dict[str, str | None]`). Locals shadow fields,
matching Java. Parameters are **not** duplicated into `locals` — they already live in
`param_names` / `param_types`; `_scope` is the only supported accessor.

Four guards, each proven by the mutation that makes it fail: drop the nested-type boundary → the
nested-variable test fails; also harvest nested `field_declaration`s → both nested tests fail;
invent a type for `o -> ...` → the untyped-lambda test fails; merge fields over locals → both
shadowing tests fail.

**Census — 184 files, 131 types, 233 methods.** The two quantities have different denominators;
stating them together without saying which was the original error.

| | A — body-declared names (`m.locals`) | B — full scope (fields + params + locals) |
|---|---:|---:|
| Total | **102** (2 untyped lambda params) | 506 |
| Mean over the **33 non-empty** methods | **3.09** | 5.67 |
| Mean over **all 233** methods | 0.44 | **2.17** |
| Max in one method | 11 | 12 |

`102 / 33 = 3.09` (A). `506 / 233 = 2.17` (B). The earlier report mixed A's totals with B's mean
and max, which is why it would not divide.

For the paper: *"Across 184 files / 131 types / 233 methods, the scope table records 102
body-declared names in 33 methods (mean 3.09 per non-empty method; 0.44 over all methods; max 11),
of which 2 are untyped lambda parameters. Full scope size, including fields and parameters,
averages 2.17 over all 233 methods (max 12)."*

Load-bearing check: `Receipt.toString` resolves `items → List` and `item → SaleLineItem`;
`Sale.getSaleLineItem` is correctly **absent** from its own scope.

### Step 2 — the eight divergences

Five helpers move, in this order — one at a time, four suites between each:

| # | Helper | Divergences it decides | Status |
|---|---|---|---|
| 1 | `_calls_method` **+ `_calls_within`** (a one-line delegate; cannot move separately) | 4, 6, 7, 8 | **DONE** |
| 2 | `_mentions_token` | 1, 4 | next — build the `this` fixture first |
| 3 | `_delegates_to_field` | 4, 5, 8 | not started |
| 4 | `_assigns_field` | 2, 3, 4 | not started |

Helper 1 landed with zero movement on all four suites, as predicted; pytest 140 → 157.
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
| 8 | Anonymous / local class bodies | **Descend** — no boundary for calls | 0 |

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

Corpus coverage of #8: of 185 methods with bodies, **1** contains a lambda
(`User.showAllBalances`) and **0** contain an anonymous class body. At the real call sites,
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

`checker.py` has changed size repeatedly (1516 on `main`, 1582 on `parser-phase2`). Older notes
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
| Golden-fact snapshot so a tree-sitter version bump can be verified | **before Step 3** |
| `Map<K,V>` element type invisible — `_base_name` strips it before the field model sees it | may fall out of Phase 2 |
| `run_scorer.py` calls `javac` and swallows the error — find out what it was for. Unrelated to the process exit code, which is correct (verified: exits 1 on failure). | before generation |
| Add `compiles` + `compile_errors` to result records | before generation |
| Rule: unknown supertypes analysed separately, not scored as failure | before generation |
| The 36 PIQS pattern tests were never committed and are still missing | before generation |
| `A-not-rebroken` case in `validation/synthetic_generality_tests.py` is vacuous — it repeats case A's assertion on case A's fixture. Needs a `ping` callback alongside a `pinger` local to become a real guard. That script is **not** one of the four suites. | any time |
| `w_ops.setdefault` keeps the first overload — pre-existing looseness in `D6` | low priority |

**Removed from this list, because it is done:** the stale-results guard. `compare.py` now refuses
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
