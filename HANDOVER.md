# Handover — state of the repo

**Note on this file.** It did not exist before 2026-08-06. Earlier instructions referred to a
`HANDOVER.md` containing stale line references ("line 886", "lines 904–906"); no such file is in
this repo's git history, so those references came from outside this tree. Do not go looking for
them. **Find code by name, never by line number** — `checker.py` has changed size three times
during the migration.

---

## How to run anything

`python3` on the development machine resolves to a pyenv install that has **no `tree_sitter_java`**.
Use the repo venv:

```bash
.venv/bin/python3 validation/run_scorer.py && .venv/bin/python3 validation/compare.py
.venv/bin/python3 validation/run_mutation_battery.py
.venv/bin/python3 validation/run_mutation_battery_bdt.py
.venv/bin/python3 -m pytest tests/ -q
```

Run **all four** after every change. Never fewer.

Do not pipe a suite through `head`/`tail` when you care about the exit code — in a shell pipeline
`$?` is the *last* command's status, so `run_scorer.py | tail` reports 0 even when the scorer
exits 1. Redirect instead: `... >/dev/null 2>&1; echo $?`.

`run_scorer.py` exits **1** correctly on failure; it does not swallow errors. (The separate
parked issue — "run_scorer.py swallows the javac error" — is about javac results being recorded
as data, not about the process exit code. Different thing, still open.)

## Baseline — current, and unchanged since before phase 2

| Suite | Expected |
|---|---|
| Kim property agreement | 90.6% (145/160) |
| Kim units exact on all 3 metrics | 30/40 |
| Mutation battery | 12/12 |
| BDT battery | 27/27 + 5/5 D6 |
| pytest | **140 passed, 8 failed** |

The 8 pytest failures are the **known and expected** renaming-invariance failures: 5 × C3
(composite) and 3 × O1 (observer). They still read hardcoded names. They are fixed in checker
stages 3 and 4. **Do not fix them during the parser migration.**

pytest was 120 passed before phase 2 step 1; the +20 are `tests/test_scope_table.py`.

## File sizes (for orientation only — never cite a line number)

| File | Lines |
|---|---|
| `piqs/checker.py` | 1564 |
| `piqs/parser.py` | 383 |

`checker.py` history: 1701 → 1510 (phase 1 deleted the declaration regexes) → 1564 (phase 2
step 1 added `_scope` and the `JavaMethod.locals` docs).

## Checker repair — 4 of 6 stages done

| Stage | Change | Kim result |
|---|---|---|
| 1 | Parser bug: `_METHOD_SIG_RE` had no left boundary | 91.2%, invariance 4 → 8 |
| 2A | Framework detector | 91.2% |
| 2B | Prediction recorded before the policy change | — |
| 2C | Framework policy applied | 91.2% → 90.6% (predicted exactly) |
| 2D | Removed `or ("Observer" in t.implements)` from O4 | 90.6% |

**Not done, not started:** stage 3 (O1 structural), stage 4 (C3 structural), stage 5 (derived
predicates), stage 6 (obfuscator).

## Parser migration

### Phase 1 — DONE (all 4 steps)

Parity harness built first, comparing regex vs tree-sitter fact by fact across 184 files, proven
with 18 deliberate breakages. Found 3 real regex bugs (`Map<String, Wallet>` fields vanished — 19
cases; nested-class methods leaked onto the parent — 6; `default` missing from modifiers — 1).
All declaration regexes deleted. Zero movement on all four suites.

### Phase 2 Step 1 — **DONE**

The scope table: `{identifier → declared base type}` per method. **Built, wired to nothing** — no
predicate reads it, so no verdict can move.

| Piece | Where |
|---|---|
| `JavaMethod.locals: dict[str, str \| None]` | `piqs/checker.py`, the `JavaMethod` dataclass |
| `_declared_in_body` — the AST walk | `piqs/parser.py` |
| `PIQSChecker._scope(t, m, types)` — the accessor | `piqs/checker.py`, next to `_effective_fields` |
| 20 tests | `tests/test_scope_table.py` |
| Resolution rule | `docs/PROPERTY_SPEC.md`, "Identifier resolution (parser phase 2)" |

Decisions made and recorded:

- `_scope` merges **fields → parameters → locals**, so a local shadows a field, as in Java.
- Parameters are **not** duplicated into `locals` — they already live in `param_names` /
  `param_types`. `_scope` is the only supported accessor.
- An untyped lambda parameter (`o -> o.update()`) records the **name with type `None`**. No type
  is invented. Step 3 takes the element type from the iterated collection.
- The walk **stops at a nested type body**: a field of a local or anonymous class, and a variable
  declared inside one, belong to that class.
- Block scope is not modelled (flat dict, last wins).

Corpus census, denominators explicit — 184 files, 131 types, 233 methods:

| | body-declared names only | full scope (fields + params + locals) |
|---|---|---|
| Total | 102 (2 untyped lambda params) | 506 |
| Mean over the 33 non-empty methods | 3.09 | 5.67 |
| Mean over all 233 methods | 0.44 | 2.17 |
| Max in one method | 11 | 12 |

### Phase 2 Step 2 — NEXT, not started

Migrate five body helpers from regex to tree queries: `_calls_method`, `_mentions_token`,
`_delegates_to_field`, `_assigns_field`, `_calls_within`.

**"Zero movement" is not safe here.** A tree query differs from the regex in at least five ways —
`this` is a keyword not an identifier; `x += 1` is an assignment in the tree but not to the regex;
`int x = 5;` matches the regex but is a declaration in the tree; the regex matches inside comments
and string literals and a tree does not; `_delegates_to_field` is deliberately narrow and a
`method_invocation` query is naturally wider. Each needs a decision recorded in
`docs/PROPERTY_SPEC.md`, a prediction, and one-helper-at-a-time measurement.

**Design constraint:** do **not** store `tree_sitter.Node` on `JavaMethod`. A node is only valid
while its `Tree` is alive; a collected tree gives a dangling reference and the failure is silent
or a crash a small test will not show. Extract eagerly at parse time into plain Python data
(`calls: list[tuple[str | None, str]]`, `assignments: set[str]`, `mentions: set[str]`), the shape
that worked in step 1. This also keeps `JavaMethod` serializable.

### Phase 2 Step 3 — loop forms. Verdicts WILL move.

`foreach_re` in `_evaluate_observer` catches one loop form of six. Missed: indexed, lambda
`forEach`, method reference, stream, iterator. Kim's corpus is old Java so this never shows;
generated 2026 Java will use the lambda and stream forms often, and the failure is silent — it
looks exactly like the model failing to write Observer.

Forms 2 (indexed) and 6 (iterator) have no named element variable. If they stall, ship 1 and 3,
record 2/4/5/6 as known limitations, move on.

## Parked

| Item | Why parked |
|---|---|
| **Golden-fact snapshot for the parser** — **prerequisite for phase 2 step 3** | `validation/extractor_parity.py` can no longer verify a tree-sitter version bump: the regex side was deleted in phase 1, and `--a parser --b parser` compares the parser against itself, so it passes trivially. `requirements.txt` said "do not relax these pins without re-running extractor_parity.py" — that instruction was false and has been corrected. **Step 3 moves verdicts on purpose**, so without a fact-level guard there is no way to tell "the new loop detection fired" from "the parser silently regressed" — they look identical at the verdict level. Steps 1 and 2 expect zero movement, so an unchanged suite is guard enough for them. Do not bump the pins until this exists. |
| `run_scorer.py` swallows the javac error | Compilation results recorded as data; unrelated to the process exit code, which is correct. |
| `Map<K,V>` element type is invisible — `_base_name` strips it | May be fixed by the scope table; re-check after phase 2. |

## Out of scope for the parser migration — do not change, do not break

| Item | Owner stage |
|---|---|
| `subject_candidates` uses the name set `{attach, detach, notifyObservers, register, remove, notify}` in `_evaluate_observer` | Stage 3 |
| `_has_verb_prefix(m.name, "add")` / `"remove"` decides C3 | Stage 4 |
| `is_register` / `is_unregister` / `is_notify` read names | Stage 5 |
| `reads` / `modifies` base predicates use `get[A-Z]` / `set[A-Z]` regexes | later |
| `_has_verb_prefix` is also used by Strategy (setter) and Builder B5 (immutability) | note for stage 4 |
| `notifies_loop` / `notifies_single` are booleans — the notifying type is discarded. Stage 3 (O1) needs that type. **Do not lift it during phase 2**; it is its own measured change. | Stage 3 |

## Working rules

1. One change at a time. All four suites before the next change starts.
2. **Predict before you change.** Write the expected numbers down first, then run, then compare.
3. Work on a branch. Never merge without review.
4. **Never edit an expected result to make a test pass.** If a test flips, that is information —
   report it and stop.
5. **Prove a guard is real.** Ship the mutation that makes it fail alongside it. See
   `docs/PROPERTY_SPEC.md`, "What a green suite does not prove" — a green suite tells you what the
   corpus and the tests contain, nothing more.
