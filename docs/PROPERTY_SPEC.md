# Builder / Decorator / Template Method — final property spec

This is the reviewable record of what was implemented in
`app.services.piqs_service.PIQSService` for the three new GoF patterns. It records the final
`Bn / Dn / Tn` statements, their structural/behavioral tag, the final weight, the critical set,
and the Decorator-vs-Proxy limitation.

The metric formulas are **unchanged** from Kim's five existing patterns:

- **PSR** = satisfied / total × 100
- **CPC** = Σ(wᵢ·sᵢ) / Σ(wᵢ) × 100 — weighted average over **all** properties
- **PIQS** = PSR × 0.6 + CPC × 0.4

Weighting follows Kim's Table 9 philosophy (RULE 2), which overrides the draft's provisional
weights where they conflicted:

- **weight 3** — the relationship/behaviour that makes the pattern actually work (also the
  **critical set**: a program is recognised AS the pattern only when *all* its weight-3
  properties hold).
- **weight 2** — existence-of-a-role, and properties governing component interaction.
- **weight 1** — supporting / peripheral.

All detection is **structural** — return types, field types, call targets, abstract/concrete,
`extends`/`implements`. **Nothing is keyed to a class name, method name, or file path.** Roles
are detected by shape.

## Reused scaffolding

Base predicates reused verbatim from the five existing patterns: `isAbstract`, `isConcrete`,
`hasMethod`, `returns`, `implements`, `extends`, `overrides`, `accepts`, `calls`, `reads`,
`modifies`. Pass-3 precision work reused: whole-token identifier matching (`_calls_within`,
`_mentions_within`, `_has_verb_prefix`) and class-scope-only field extraction. Substring name
matching and method-local-variable-as-field are **not** reintroduced.

> **Parser migration, phase 1.** Class-scope-only field extraction was originally `_class_scope_only`,
> which stripped every brace-delimited block from the class body text before applying a field
> regex. Declaration extraction is now a tree-sitter parse (`piqs/parser.py`), so class scope is
> read off the syntax tree — fields are the `field_declaration` children of the type's own body
> node — and `_class_scope_only`, the field regex and the declaration/signature regexes are
> deleted. The guarantee is unchanged and stronger: a method-local variable is not a field
> because it is not in the type's body, not because a brace-stripping pass removed it.

Two new AST helpers were added (the only ones the codebase lacked):

- **`callsWithin(method, target)`** — does `method`'s body invoke a method named exactly
  `target`? (whole-token; reused by D3 and T3). Implemented as `_calls_within`.
- **`fieldOfType(class, type)`** — does `class` hold a class-scope field of the given type?
  (reused by D2). Implemented as `_field_of_type`.

One infrastructure change: `JavaMethod.has_body` distinguishes a `;`-terminated declaration (an
abstract-class abstract method / bodyless interface method) from an empty-bodied concrete method
(`{}`). Both previously left `body == ""`; Template Method needs to tell them apart. The five
existing patterns never read this field.

Interface-vs-abstract handling follows the codebase rule: a Java **interface counts as an
abstract type** for any role that may be abstract; `isAbstract` is required only where a pattern
genuinely demands it.

---

## Builder — critical set {B1, B2}

Derived roles: `isBuilder`, `isProduct`, `isTerminalMethod`, `isStepMethod`, computed over each
candidate's **effective** (inherited) method/field set so a classic GoF builder split across an
abstract `Builder` (declares `getResult()`) and a `ConcreteBuilder` (defines void build-parts) is
seen as one builder family.

| ID | Statement | Tag | Weight |
|----|-----------|-----|--------|
| **B1** | `build()` returns a product distinct from the builder (a builder has step methods **and** a terminal method whose return type ≠ the builder type). | behavioral | **3** (critical) |
| **B2** | Step/configuration methods assemble the product: fluent-return-`this` **XOR** void-buildPart + `getResult()`. | behavioral | **3** (critical) |
| B3 | Builder type and product type are distinct. | structural | 2 |
| B4 | Telescoping-constructor avoidance / staged construction (a fluent chain, or ≥ 2 discrete step methods). | structural | 2 |
| B5 | Product effectively immutable — no public mutator for a built field (a non-project product, e.g. `String`, is treated as immutable). | structural | 1 |
| B6 | Director orchestrates **XOR** client drives the fluent chain (fluent steps ⇒ client-driven; else a non-builder/non-product type invokes a builder step method). | behavioral | 1 |

**Accepted variants (RULE 3):** interface / abstract-class / concrete static-nested builder;
`builder()` static factory or public constructor; builder reuse; mutable or immutable product
(B5 weight handles the difference). **Rejected:** a plain class with setters and no terminal
product-returning method (B1 fails); a "builder" whose `build()` returns the builder/`void`
(B1 fails).

---

## Decorator — critical set {D2, D3}

Derived roles: `isComponent` (an abstract type — interface or abstract class), `isDecorator`
(a class that conforms to a component **and** holds a field of that component type), `wraps`,
`delegatesTo`.

| ID | Statement | Tag | Weight |
|----|-----------|-----|--------|
| D1 | Decorator conforms to the **same** component type as what it wraps (is-a matches has-a). | structural | 2 |
| **D2** | Decorator holds a component-typed reference (composition). | structural | **3** (critical) |
| **D3** | Decorator delegates to the wrapped reference in its component methods (see the *any-vs-all* judgment call below). | behavioral | **3** (critical) |
| D4 | Transparent enhancement — no interface conversion: the decorator exposes the wrapped component's whole operation set (distinguishes from **Adapter**). | structural | 2 |
| D5 | Abstract decorator base / recursive composability — a collapsed single decorator is accepted (it wraps the component type, so it can wrap another decorator). | structural | 1 |
| D6 | **Full delegation (non-critical diagnostic)** — every implemented component operation forwards to the wrapped reference. Flags partial delegation *without* changing recognition. | behavioral | 1 |

**Accepted variants (RULE 3):** interface or abstract-class component; a collapsed single
decorator with no abstract base (D5 low-weight); constructor or setter injection of the wrapped
reference. **Rejected:** a subclass that extends the concrete component with no wrapped reference
(D2 fails); a wrapper that delegates to nothing (D3 fails).

### D3 semantics — the *any-vs-all* decision (RESOLVED)

D3 reads **"at least one component method delegates to the wrapped reference"** (existential). A
wrapper that delegates in some methods but hard-codes/ignores the delegate in others (*partial
delegation*) therefore **passes** D3. The stricter reading — "*all/most* component operations
forward" — would reject partial delegation, but it would **also** reject legitimate
method-suppressing decorators (read-only views, capability-reducing wrappers) that intentionally
short-circuit some operations.

**Decision (approved):** keep the critical D3 = existential "any", and add a **non-critical D6**
diagnostic that is satisfied only when *every* implemented component operation forwards. This gives
visibility into partial delegation without changing recognition (the critical set stays {D2, D3}).
The `t1_decorator_partial_delegation_accepted` case demonstrates it: recognised (D2=1, D3=1) with
**D6=0** flagging the incomplete forwarding; the five full-delegation decorators all score D6=1.
This mirrors the checker's accept-any-conforming-wrapper philosophy (it already accepts Proxy).

### Known limitation — Decorator vs Proxy (RULE 4, encoded not fixed)

Decorator and Proxy are **structurally identical** under static analysis: both conform to the
component interface, hold a component-typed reference, and delegate to it. "Adds behaviour"
(Decorator) vs "controls access" (Proxy) is a semantic intent that is **not statically
decidable**. This checker does **not** attempt to distinguish them — any structurally-conforming
wrapper is accepted as Decorator. This is stated in a code comment on `_evaluate_decorator` and
will be disclosed in the paper's threats to validity. (D4 distinguishes Decorator from *Adapter*,
which is decidable — an Adapter converts to a different interface — but makes **no** claim about
Proxy.)

This limitation is now **demonstrated**, not merely asserted: the battery case
`t3_decorator_lazy_proxy_KNOWN_LIMITATION` is a genuine lazy-init/virtual **Proxy** (holds the
component, delegates, but its added logic *controls access* — it creates the real subject on
first use). The checker recognises it as a Decorator (D2=1, D3=1, PIQS 100). The case carries an
in-source `// KNOWN LIMITATION` comment so reviewers see the accepted-Proxy fact directly.

### Known limitation — `this` inside an anonymous class (recorded, not fixed)

In Java, `this` inside an anonymous class refers to the **anonymous class**, not the enclosing
one. Under divergence #8 the call walk descends into anonymous class bodies, so

```java
class Logger implements Sink {
    private Sink inner;
    public void write(String s) {
        Runnable r = new Runnable() { public void run() { this.inner.op(); } };
        r.run();
    }
}
```

credits **`Logger`** with delegating to `inner`, when `this.inner` inside the anonymous class does
not name `Logger`'s field at all. (Written without `this`, `inner.op()` *would* correctly resolve
to the enclosing instance's field — it is the explicit `this` qualifier that is misread.)

**Not fixed in phase 2, on purpose.** The retired regex behaved the same way, so this is exact
parity: fixing it would be a meaning change smuggled inside a mechanism change, and any resulting
movement would be unattributable. Fixing it properly needs the receiver's *enclosing type*, which
the flat `(receiver, method_name)` shape does not carry.

**Coverage: zero.** The corpus contains 0 anonymous class bodies in 422 method bodies, so nothing
scores differently today. This is a generated-code risk, not a current one — 2026 Java uses
anonymous classes and lambdas far more than Kim's corpus does.

### Known limitation — assignment to a local that shadows a field (recorded, not fixed)

```java
void shadowedWrite(Object other, Object another) {
    Object held = other;   // declares a LOCAL that shadows the field `held`
    held = another;        // assigns the LOCAL -- the field is never touched
}
```

`_assigns_field(method, "held")` reports **True**. The declaration is correctly excluded
(divergence #3 — it is a `local_variable_declaration`), but the second line is a genuine
`assignment_expression` whose target is the bare name `held`, and nothing at that point knows the
name has been rebound to a local.

**Not fixed in phase 2, on purpose.** The retired regex behaved identically, so this is exact
parity. `JavaMethod.locals` now exists and could resolve it — a name declared in the body shadows
the field for the rest of the method — but using it here would turn a mechanism change into a
meaning change, and any resulting movement would be unattributable. It is a **Step 3** question
with its own prediction.

The same reasoning distinguishes the two assignment divergences. **#2** (compound operators)
preserves the regex even though the regex is arguably wrong, because fixing it changes which
programs satisfy a property. **#3** (declarations) takes the tree's answer, because the regex's
answer was never correct for any program — it removes a false positive rather than redefining the
predicate.

**Coverage: zero.** No `_assigns_field` call site in either corpus has a local shadowing the
queried field name. Pinned by `tests/fixtures_parser/div3_declaration_not_assignment.java`, whose
final case asserts the limitation rather than the correct answer, and says so.

---

## Template Method — critical set {T3}

Derived roles: `isAbstractClassType` (abstract class or interface), `isTemplateMethod` (a
concrete method that invokes ≥ 1 deferred operation), `isPrimitiveOp` (a bodyless abstract method
implemented by subclasses), `isHook` (a concrete overridable method the template invokes and a
subclass overrides — a default-body extension point).

| ID | Statement | Tag | Weight |
|----|-----------|-----|--------|
| T1 | A concrete template method exists in an abstract type (a fixed skeleton). | structural | 2 |
| T2 | ≥ 1 abstract primitive and/or hook deferred to subclasses. | structural | 2 |
| **T3** | The template body invokes the primitive/hook operations (inversion of control). | behavioral | **3** (critical) |
| T4 | Template method is `final` / non-overridable (non-`final` accepted, lower-scoring). | structural | 2 |
| T5 | Subclass overrides the primitives, **not** the template method. | behavioral | 2 |

**Accepted variants (RULE 3):** `final` or non-`final` template (T4 weight handles it); abstract
primitives or default-body hooks (T2). **Rejected:** an abstract "template" method (T1 fails — no
fixed skeleton); an abstract class with a concrete method but zero deferred steps (T2 fails); a
concrete method whose abstract siblings are never called from it (T3 fails).

A genuine primitive must declare a return type — this rejects pseudo-methods the signature regex
harvests from call expressions inside method bodies (e.g. `System.out.println(...)`), which would
otherwise fake inversion of control.

---

## Definitional decisions

These are explicit, recorded choices of the same kind as two decisions already made and documented
for the original five patterns:

- **F4 — concrete single product** is accepted as Factory Method when there is no abstract product
  hierarchy the factory bypasses (see the `_evaluate_factory_method` "Change 2" comment and the
  `f4_concrete_single_product` mutation case).
- **S3 — a strategy passed only as a method parameter** (not held as context state) is *rejected*
  as the Context role (see the `s3_parameter_only` mutation case).

New decision recorded in this work:

- **Template Method in an interface (Java-8 default method): ACCEPTED.** `isAbstractClassType`
  treats a Java interface as an abstract type, so an interface with a **default-method template**
  that calls **abstract interface primitives** is recognised as Template Method (T3 holds).
  *Justification:* a default method is a genuine concrete skeleton, the abstract interface methods
  are genuinely deferred to implementors, and this is a real, common modern idiom (e.g.
  `Comparator`, `Collector`-style helpers); accepting it is also consistent with the codebase's
  interface-as-abstract-role rule already applied to the other roles. Demonstrated by the MUST-PASS
  case `t4_template_interface_default_method` (an `interface Report` whose `default render()` calls
  abstract `header()`/`body()`), verified recognised (T3=1). The classic abstract-*class* form
  remains fully supported; this decision only *adds* the interface form, it does not replace it.

  **Implementation note (parser migration, phase 1).** When this decision was taken the extractor
  could not actually see the `default` modifier: `_METHOD_SIG_RE`'s modifier alternation listed
  `public|protected|private|static|final|abstract|synchronized` and nothing else, so a default
  method was extracted with an **empty** modifier set. The decision was still implemented
  correctly, because what T1/T2/T3 read is `has_body` — a default method has a brace body, an
  abstract interface method does not — and `has_body` was always right. But the modifier that
  *names* the idiom was unobservable, so the accepted variant could not have been distinguished
  from a hypothetical bodied interface method by any other route. As of the tree-sitter extractor
  (`piqs/parser.py`) the modifier is recorded: `render()` now carries `modifiers == {"default"}`.
  No property reads it today and no verdict moved; it is recorded here because the design decision
  was documented while the implementation could not observe the thing it decided about. Pinned by
  `tests/fixtures_parser/interface_default_method.java`.

## Framework inheritance

**The rule.** A type that obtains its pattern structure by extending or implementing a type the
project does not declare is scored as **not conforming**, unless the source still declares the
roles the pattern requires of it. Framework inheritance by itself never satisfies a property.

Detection is recorded, not acted on. Every evaluation reports:

```json
"framework_inheritance": [
  {"type": "AuditLog", "supertype": "Observable", "pattern_roles_supplied": []}
]
```

A supertype counts as framework only when it is **both** absent from the project's own
declarations **and** on `_FRAMEWORK_SUPERTYPES` (`Observable`, `Observer`, `AbstractList`,
`AbstractMap`, `AbstractSet`, `FilterInputStream`, `FilterOutputStream`, `HttpServlet`, `Thread`,
`TimerTask`), matched on the simple name by exact comparison, never by substring. A project that
declares its own `Observer.java` is *not* a framework user, and its local interface is seen by the
ordinary structural predicates like any other type. A referenced supertype that is neither
declared locally nor on the list is neither — it is reported separately as
`unknown_supertypes`, so a missing file or a third-party dependency can never be silently read as
either local structure or framework structure.

**Why.** The study measures **structure the model produced, not structure it inherited.** In the
SWS case study, `AuditLog extends java.util.Observable` and its whole body is:

```java
public void logAction(String logEntry) {
    setChanged();
    notifyObservers(logEntry);
}
```

There is no observer collection, no registration method, no callback interface and no traversal in
the source. All of it lives in `java.util.Observable`. Four of the five models wrote that structure
themselves; one reached for the framework. Crediting the fifth with an Observer implementation
would be crediting `java.util.Observable`, and would make the fifth model indistinguishable from
the four that did the work.

Note what the rule does *not* say. It is not "framework inheritance disqualifies you." A class
extending `AbstractList` inherits the algorithm skeleton but must still supply `get()` and
`size()`; those primitives are its participation in Template Method, they are declared in the
source, and the ordinary predicates find them. The rule is enforced simply by removing the
shortcuts that granted a role for a supertype's *name* — after which a type is credited only for
structure the checker can actually see. `pattern_roles_supplied` describes what that structure is;
it is descriptive and never decides anything, because deciding what a framework supertype
*requires* would need a model of the framework, and the policy does not depend on having one.

**Alternatives rejected.**

- *Accept framework inheritance as conforming.* This would require modelling the JDK — knowing
  that `Observable` supplies registration, a collection and notification — and would credit a model
  for structure it did not produce. It also does not scale: every framework a generated program
  reaches for would need a hand-written model before the program could be scored.
- *Exclude such files from the corpus.* This would hide a real and interesting model behaviour.
  That one of five models delegated the pattern to `java.util.Observable` while the other four
  implemented it is a finding, not noise, and dropping the file would erase it.

**Effect on the replication.** Applying this policy moved exactly one of 160 property judgments:
`SWS/Meta/observer/O1`, satisfied → not satisfied, and with it that unit's PSR/CPC/PIQS from
25.0/18.18/22.27 to 0/0/0. Headline agreement with Kim goes from 91.2% to **90.6%**; O1 per-property
agreement from 9/10 to 8/10, still above the 80% reliability threshold. Kim marked that cell
satisfied. We now disagree, for the same reason we already disagreed with Kim on O2 of the same
cell — recorded in `KIM_VALIDATION.md` as Kim-side leniency.

## Identifier resolution (parser phase 2)

**The rule.** An identifier resolves to a project type when its declared type's simple name
appears in the project's type table. Types not declared in the project are external. This is
sound for single-package projects; cross-package name collisions are not resolved and did not
occur in either corpus.

**The scope table.** `PIQSChecker._scope(type, method, types)` returns `{identifier: declared
base type}` for one method. Three sources, merged in Java shadowing order — a later source
overwrites an earlier one:

| # | Source | Where it comes from |
|---|---|---|
| 1 | fields of the type and of its project-defined ancestors | `_effective_fields` |
| 2 | the method's parameters | `JavaMethod.param_names` / `param_types` |
| 3 | names declared in the method body | `JavaMethod.locals`, built by `piqs.parser` |

Source 3 covers local variables, enhanced-for variables, try-with-resources resources, catch
parameters and lambda parameters. A lambda parameter written without a type (`o -> o.update()`)
records the **name with type `None`** — the name is in scope, and no type is invented. A consumer
that needs the element type takes it from the iterated collection.

**What the table deliberately excludes.** The walk stops at a nested type body, so a field of a
local or anonymous class, and a variable declared inside one, belong to that class rather than to
the enclosing method. Block scope is not modelled: the dict is flat, so two sibling blocks each
declaring `i` collapse to one entry.

**Why this replaces text matching.** The pattern being retired is
`elem_field_re.findall(t.body)` in `_evaluate_observer` (and its twins in `_evaluate_composite`
and `_framework_roles_supplied`). `t.body` is the whole text between a class's braces, method
bodies and signatures included, so the regex cannot tell a declaration from anything shaped like
one. Measured across the 184 corpus files, five types feed it a name that is not a class field:

| File | Harvested | Actually a |
|---|---|---|
| `RefactoredPOSCopilot/Receipt.java:35` | `items` | local variable |
| `POS/Receipt.java:35` | `items` | local variable (unscored, `original_base`) |
| `RefactoredPOSCopilot/Sale.java:20` | `getSaleLineItem` | **method name** |
| `POS/Sale.java:27` | `getSaleLineItem` | **method name** (unscored) |
| `RefactoredPOSClaude/Sale.java:38` | `getComponents` | **method name** |

The method-name entries are inert today only by luck: `foreach_re` wants a bare identifier after
the colon, and a call site always carries `()`. The local-variable entries are **load-bearing** —
they are why a method-local collection of observers is detected at all today. Any scope table that
held fields only would therefore be a silent regression, not a no-op; see
`tests/test_scope_table.py`.

## Body predicates: text matching vs the AST (parser phase 2, step 2)

The body helpers were regexes over method-body **text**. A query over the AST is not equivalent
to one. Each difference below is a **recorded decision**, not an implementation accident.

`_calls_method(body, name)` is retired. The call predicate is `_calls_within(method, target)`,
reading `JavaMethod.calls` — `[(receiver, method_name)]`, precomputed at parse time. Exact-name
matching is unchanged: `read` still never matches inside `readLine`, but that now falls out of the
tree rather than from a look-behind assertion.

| # | Construct | Decision | Why |
|---|---|---|---|
| 1 | `this` / `super` are KEYWORD nodes, not identifiers | **Include them** in the mentions set | The retired regex was a whole-word text match and found them like any word. Builder B1 accepts a terminal only if its body consumes configured state, one route being passing `this` to the product constructor. **The only divergence in the set with a live verdict** |
| 4 | Comments and string literals | **Not code.** `// observers.add(o)` is not a call | A model must not earn a property for a commented-out call. The one divergence the corpus exercises in bulk: 34,190 masked characters across the 10 scored programs, 0 of 40 units moved |
| 6 | `new Wallet()` | **Not a method call** | `callsWithin(method, target)` takes a *method* as its target. The regex matched a bare identifier followed by `(`, which a constructor also is |
| 7 | A method **declared** in the body | **Not an invocation** | The phantom-method problem phase 1 removed at the type level, reappearing at the body level. Collecting only `method_invocation` excludes it with no special case |
| 8 | Anonymous / local class bodies | **Descend** | A call written inside an anonymous class still runs against the *enclosing* instance's fields, so it really is the enclosing class delegating. This is the one place the call walk differs from the scope walk |

**Divergence 8 is the subtle one.** `_declared_in_body` (the scope table) *stops* at a nested type
body: a field of an anonymous class belongs to that class. `_invocations` *descends*: a call there
belongs to the enclosing method. Reusing one walker for both would silently drop D3 for

```java
public void write(String s) {
    Runnable r = new Runnable() { public void run() { inner.write(s); } };
    r.run();
}
```

A **lambda** body is not affected either way — it is a `block`, not a `class_body`, so the scope
walk already descends into it. Only anonymous and local *classes* differ.

**Receiver normalisation.** One rule reproduces the retired regexes on every shape they accept or
reject, for call receivers and assignment targets alike:

> `identifier` → its own text. `field_access` → its **field**'s text. Anything else → `None`.

| Expression | Retired regex | Stored |
|---|---|---|
| `f.op()` | `f` delegates | `"f"` |
| `this.f.op()` | `f` delegates | `"f"` |
| `f.g.op()` | `g` delegates, `f` does **not** | `"g"` |
| `getX().op()` | nothing delegates | `None` |
| `op()` | nothing delegates | `None` |
| `f = x` / `this.f = x` | `f` assigned | `"f"` |
| `f.g = x` | `g` assigned, `f` not | `"g"` |
| `arr[0] = x` | `arr` not assigned | `None` |

`f.g.op()` stores `"g"`, **not** `None`: the regex needs `<name> . <ident> (`, which `g.op(`
satisfies, so `_delegates_to_field("f.g.op();", "g")` was already True. `None` would drop it.
Because `None` can never equal a field name, chains and unqualified calls are rejected by
comparison alone.

**No tree-sitter `Node` is stored on `JavaMethod`.** A `Node` is valid only while its `Tree` is
alive; holding one past parse time gives a dangling reference that fails silently or crashes in a
way a small test will not surface. Everything is extracted eagerly into plain Python data, which
also keeps `JavaMethod` serializable for the result records.

**Divergence 1 is the exception to everything below.** Omitting `this`/`super` fails 4 fixtures
AND breaks the BDT battery: `builder_bloch_fluent_static_nested` and `t5_builder_immutable_product`
flip `B1=1 → 0`, PIQS 100 → 20, 3 mismatches, exit 1. Kim does not move, because Kim never scores
Builder. Measured: 43 call sites pass `"this"`, 3 are True, all in BDT. The fixture covers two
distinct node positions — `new Loaf(this)` (constructor argument) and `synchronized (this)`
(statement lock) — because a fix for one is not a fix for the other.

**Coverage warning.** Of the other four divergences, three occur **zero** times in either corpus (#6,
#7, #8 — and #8's near-miss, 7 lambdas in 422 method bodies, is not even the affected shape). All four
suites stay green whichever behaviour is chosen. `tests/test_body_helpers_divergences.py` is the
only thing that distinguishes a correct migration from a wrong one, and each of its guards ships
with the mutation that makes it fail. See the next section.

## Rule: does a divergence REDEFINE the predicate, or REMOVE A FALSE POSITIVE?

Every migration divergence is decided by this question, and it is the reason two divergences that
look alike are decided oppositely.

| | Redefines the predicate | Removes a false positive |
|---|---|---|
| Test | changes **which programs satisfy a property** | removes an answer that was **never correct for any program** |
| Handling | needs its **own separately-measured change**, with its own prediction | may **ride along** with a mechanism migration |
| Why | a movement caused by new meaning is indistinguishable from one caused by the new mechanism, so the migration stops being measurable | there is no reading under which the old answer was right, so nothing is being traded away |

Worked pair, from phase 2 step 2:

* **Divergence #2 — compound assignment.** `total += x` does populate state, and `_assigns_field`
  is documented as signalling a step that populates state, so the regex is arguably wrong. It was
  **preserved anyway**: correcting it would change which builders satisfy B1/B2. Parked as a
  candidate meaning change with its own prediction.
* **Divergence #3 — local declaration.** `int count = 5;` declares a local that shadows the field
  and leaves the field untouched. The regex called that an assignment to the field. **The tree's
  answer was taken**, because no program was ever served by the old one.

Applied across step 2: #3, #4, #6 and #7 removed false positives and rode along; #2 preserved
regex behaviour; #1, #5 and #8 were parity requirements rather than either.

## What a green suite does not prove

A recurring failure mode in this repo, recorded because it has now cost real work twice. "No
test breaks" tells you what the corpus and the test suite **contain**. It does not tell you the
code is dead, nor that a test is doing its job.

**Case 1 — the D6 guard (`_fully_delegates`, `not m.has_body`).** One line looked like dead code
left over from the retired signature regex. Deleting it passes all four suites. It is still
load-bearing for a different reason: an abstract decorator base may forward part of the component
API and leave the rest abstract, and a bodyless declaration is not implemented. Without the skip
a correct abstract base scores D6=0, moving PIQS from 100 to 86.67. No corpus file exercises it.
`tests/test_decorator_d6_abstract_base.py` and its fixture are the only thing standing between
that line and a deletion that looks safe.

**Case 2 — the nested-class-field test (`tests/test_scope_table.py`).** The scope table walk stops
at a nested type body, and two tests assert nothing from inside a local or anonymous class leaks
into the enclosing method's scope. Removing the boundary was expected to fail both. It failed only
`test_variable_inside_nested_class_body_is_not_in_enclosing_scope`.

Reason: a nested class's field is a `field_declaration` node, and the walk reads
`local_variable_declaration` and four other forms — never `field_declaration`. So
`test_nested_class_field_is_not_in_enclosing_scope` could not fail from removing the boundary,
because the boundary was not what stopped it. The test was passing for a reason other than the one
it advertised.

It was **kept**, not deleted, because a second mutation shows what it does catch: adding
`field_declaration` to the walk — a plausible future "completeness" edit — fails both tests. The
guard is real; it protects a different mutation from the one its name suggests.

The lesson generalises: **a passing test is evidence only against the mutations you have actually
tried.** Every guard added in this repo should come with the mutation that makes it fail, recorded
alongside it. All four scope-table guards were verified this way (nested boundary, nested field
harvesting, invented lambda type, reversed shadowing order).

## Oracle

There is no Kim ground truth for these three patterns (Kim 2025 never covered them). The oracle is
`validation/mutation_battery_bdt/` + `validation/run_mutation_battery_bdt.py`:

- **CONFIRMED cases (27)** — 18 MUST-PASS (JDK-exemplar analogues + idiomatic variants, including
  the "discriminating middle" cases: genuine-enhance decorator, primitive+hook template, fluent
  interface builder, Java-8 default-method template, Proxy-as-Decorator) and 9 MUST-FAIL (degenerate
  forms: hollow builder, fluent-no-terminal builder, no-IoC / private-helper templates, no-delegation
  wrapper, plain inheritance). A case's verdict is "is the pattern" iff **all** critical (weight-3)
  properties hold. Every case matches its label and compiles under `javac`; these gate the exit code.
- **D6 diagnostics (5)** — demonstrate that the non-critical Decorator D6 flag separates partial
  (D6=0) from full (D6=1) delegation *without* changing recognition (every case stays recognised via
  the critical {D2,D3} set).

The three pass-5 probe cases that began as *open findings* were resolved after review (two Builder
gaps fixed, the Decorator D3 semantics decided) — see *Resolved findings* below. Per the
coverage-pass golden rule, no probe was forced green by a predicate change **before** approval.

## Resolved findings (pass-5 coverage probes → approved changes)

Three probe cases surfaced the "discriminating middle" and were **independently re-verified** (each
traced against the code and re-run through the scorer by a separate agent). All three are now
**resolved** with approval; the changes touch only `_evaluate_builder` / `_evaluate_decorator`
(new patterns) — the five original patterns are byte-identical (Kim 91.2% unchanged).

1. **Builder B2 — hollow steps (discrimination gap) → FIXED.**
   `t1_builder_hollow_steps_ignored`: a fluent step sets a builder field that `build()` ignores
   (product built with defaults) was wrongly recognised. **Fix applied:** a terminal now qualifies
   only if its body references a builder effective-field (whole token) **or** mentions `this` — so
   `return new Gadget();` is no longer a terminal (B1→0), while `new Pizza(this)`, `return product;`,
   `return value;`, `new Car(color, wheels)` are kept. Verified non-regressing across the whole
   builder battery and extra edge cases (abstract-class fluent, `this.field`-consuming terminal).
   *Documented caveat:* the `this` clause is a structural proxy — a pathological `new Gadget(this)`
   that ignores the arg still passes; full detection needs deeper dataflow. This is an accepted
   residual limitation, not a bug.

2. **Decorator D3 — partial delegation (judgment call) → DECIDED (keep "any" + add D6).**
   See *D3 semantics* above. Recognition stays existential ("any method delegates"); a **non-critical
   D6** diagnostic (weight 1) flags when not every operation forwards. `t1_decorator_partial_delegation_accepted`
   is recognised (D2=1, D3=1) with D6=0; the five full-delegation decorators score D6=1. Rationale
   for keeping "any": an "all/most" rule would wrongly reject canonical method-suppressing decorators
   (`Collections.unmodifiableList`, whose mutators throw instead of forwarding).

3. **Builder B1/B2 — fluent *interface* builder missed (discrimination gap) → FIXED.**
   `t2_builder_interface_fluent`: an idiomatic fluent builder whose steps return the **interface**
   type (`return this` typed as the abstraction) was not recognised. **Fix applied:** fluent-step
   detection broadened from `m.return_type == t.name` to also accept a return type the builder
   `_conforms_to` — so a step returning an interface/superclass the builder implements/extends counts.
   Verified non-regressing: the MUST-FAIL `builder_build_returns_this` and
   `t1_builder_fluent_setters_no_terminal` stay failing (no distinct-product terminal); the fix also
   generalises to abstract-class fluent builders. *Theoretical edge (absent from the battery):* a
   builder conforming to its own product type could lose its terminal under the broadened rule.

*(Parser note, benign — no action needed:* the interface default-method template's `render()` body
harvests a spurious `body` pseudo-method from the `body()` call expression; it is correctly filtered
by the `return_type is not None` guard and has zero effect on T3. The D6 helper applies the same
guard — it skips bodyless pseudo-methods so a call-harvested duplicate cannot mask a real method's
delegation.)*
