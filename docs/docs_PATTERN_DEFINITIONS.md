# Pattern definitions — the rule authority for PIQS-Conformance

It is a working extract of the deep-research report *Static Detection of GoF Design Patterns:
Name-Independent Structural Rules and Repository Evidence*, which lives in the Claude Project folder
and **is not in this repository**. Claude Code cannot read that PDF; it can read this file.

Every clause below is restated in this project's own words. Where a rule statement is quoted from a
published source it is short and attributed. The PDF remains the fuller document; this file is the
part the checker needs.

## How to use this file

- **A checker rule must trace to a clause here or to GoF.** A predicate that cannot be traced to one
  does not go in.
- When proposing or reviewing a rule, **quote the clause number** it implements — for example
  "Adapter R2".
- Every clause below is name-independent by construction: it speaks of types, supertypes, fields,
  parameters, return types and calls. **None of them mentions an identifier.** If a proposed
  predicate needs a word to work, it is not implementing one of these clauses.

## Sources behind the clauses

| Short name | Full source |
|---|---|
| GoF | Gamma, Helm, Johnson & Vlissides (1994), *Design Patterns* |
| PINOT | Shi & Olsson (2006), ASE '06, DOI 10.1109/ASE.2006.57 |
| DPJF | Binun & Kniesel (2012), CSMR 2012 |
| DP-CORE | DP-CORE (2016), name-independent connection model |
| GEML | GEML (2021), *Journal of Systems and Software* |
| Patent | U.S. Patent 8,689,173 |
| P-MARt | Ptidej expert-annotated Java benchmark |

---

# 0. The decidability frame — read before anything else

Patterns split into two kinds:

| Kind | Patterns | What it means for us |
|---|---|---|
| **Structure-driven** | Adapter, Proxy, Composite, Template Method | Decidable from declarations alone |
| **Behaviour-driven** | the other eight | Needs method-body analysis |

Two pairs **cannot be separated by structure at all**:

- **State vs Strategy.** PINOT does not detect State. DePATOS, MLDA and SparT report the two merged.
- **Proxy vs Decorator.** GoF, PINOT and Refactoring.Guru all treat them as structurally
  overlapping.

**Do not build a rule that separates either pair.** Any rule that could do it reads intent, and
intent lives in names and comments — the one thing this instrument may not read. Give the
overlapping patterns rule sets that are honestly the same shape and record the overlap. It does not
corrupt the experiment: every generated program is scored against the pattern it was **asked** for.

Three separators **are** decisive and belong in the code:

| Separator | Rule |
|---|---|
| **Adapter vs Proxy/Decorator** | wrapped field's type ≠ the wrapper's own supertype → Adapter. Equal → Proxy or Decorator |
| **Abstract Factory vs Factory Method** | ≥2 abstract-product-returning methods on a factory **object** → Abstract Factory. One subclass-**overridden** product method → Factory Method |
| **Composite vs Observer** | the collection holder **is-a** the element type → Composite. **Is-not-a** → Observer |

The third is already implemented, in the Observer notification-site test.

---

# 1. The four patterns to build

## Adapter

**Intent (GoF).** Convert one class's interface into another that clients expect, so classes with
incompatible interfaces can work together. What varies is the interface presented, not the
behaviour.

**Object adapter — required clauses**

| # | Clause |
|---|---|
| **A1** | The Adapter implements or extends a **Target** supertype |
| **A2** | It holds a field whose type is the **Adaptee**, and that Adaptee type is **different from and unrelated to** the Target |
| **A3** | Adapter methods delegate to that adaptee field |

**Class adapter — required clauses**

| # | Clause |
|---|---|
| **A4** | The Adapter implements or extends the Target **and** extends the Adaptee |
| **A5** | Forwarded methods are inherited and called on `this`. There is no adaptee field and no delegation |

**Decisive signature.** GEML's `adapterMethod` operator and the Patent: the Adapter implements a
method **declared by the Target** that delegates to the adaptee field. DP-CORE states the same as a
triple: `inherits(adapter, target)` + `has(adapter, adaptee)` + `calls(adapter, adaptee)`. The Patent
distinguishes the object adapter's *directDelegationCall* on an adaptee field of multiplicity 1 from
the class adapter's *directLocalCall* to an inherited operation.

**Not required.** The word "Adapter".

**Styles.** Object adapter by delegation (`iluwatar/java-design-patterns/adapter`); class adapter by
inheritance (`DesignPatternsPHP`). Production: `java.io.InputStreamReader`,
`java.util.Arrays#asList`.

**Traps.** A wrapper that shares the target interface is Proxy or Decorator, not Adapter. A facade
hides two or more classes; PINOT's hiding rule is that Adapter and Proxy each hide exactly one.
"Wrapper" is an ambiguous alternative name — it also means Proxy and Decorator.

## Proxy

**Intent (GoF).** Stand in for another object to control access to it. Kinds: virtual, remote,
protection, smart-reference. What varies is access and lifecycle control, transparently.

| # | Clause |
|---|---|
| **P1** | A common **Subject** supertype exists |
| **P2** | The RealSubject implements or extends it |
| **P3** | The Proxy implements or extends the **same** supertype |
| **P4** | The Proxy holds a field typed as that supertype, or as the RealSubject |
| **P5** | A Proxy method forwards the **same-signature** call to that field |

**Decisive signature.** DPJF: the Proxy role has an association to the Subject role, and a method
declared in the Proxy invokes an abstract method **of the same signature** through that association.

**Not required.** The word "Proxy".

**Heuristics the report explicitly labels weak — use only as reported heuristics, never as rules.**
A Proxy often constructs its real subject itself, sometimes behind a null check (lazy init), and is
usually a single wrapper. A Decorator usually receives the wrapped object as a constructor
parameter, and is often stackable behind an abstract base.

**Styles.** Static virtual or protection proxy (`iluwatar/java-design-patterns/proxy`); dynamic
proxy via `java.lang.reflect.Proxy` and `InvocationHandler`, or Spring AOP.

## Abstract Factory

**Intent (GoF).** Provide an interface for creating families of related objects without naming their
concrete classes. What varies is the whole product family.

| # | Clause |
|---|---|
| **AF1** | An abstract factory supertype declares **≥2 methods, each returning a different abstract product type** |
| **AF2** | At least one — usually two or more — concrete factories implement it |
| **AF3** | There are **≥2 product hierarchies** |
| **AF4** | Each concrete factory method creates a concrete product while its **declared return type** is the abstract product |

**Decisive signature.** DP-CORE: `inherits(concreteFactory, abstractFactory)`,
`inherits(concreteProduct, abstractProduct)`, `creates(concreteFactory, concreteProduct)`, and
`uses(factory, abstractProduct)` where *uses* means a method's return type is the abstract product.

**Not required.** The word "Factory"; a Director.

**Separator from Factory Method.** Factory Method varies **one** product by a subclass that
**overrides** the creator's own product-returning method — inheritance, called on `this`. Abstract
Factory has **≥2** product-returning methods and varies by separate factory **objects** —
composition. Count the abstract-product-returning methods, and check whether variation comes from a
subclass override or from separate factory objects.

**Traps.** A single factory method returning one family member is Factory Method. A "factory of
factories" with only one product type is not Abstract Factory.

## State

**Intent (GoF).** Let an object change its behaviour when its internal state changes, so it appears
to change class.

| # | Clause |
|---|---|
| **ST1** | A Context holds a field of an abstract **State** type |
| **ST2** | Multiple concrete State classes implement it |
| **ST3** | The Context delegates behaviour to the current State object |

ST1–ST3 are **identical to Strategy's required clauses**. Two further signals are statically
checkable and are the only name-independent positive evidence for State:

| # | Signal |
|---|---|
| **ST4** | A concrete State holds a **back-reference to the Context** — a field, constructor parameter, or method parameter typed as the Context or its supertype |
| **ST5** | A concrete State **references a sibling** concrete State: it creates, returns or receives another implementer of the same State supertype. The report calls this the strongest name-independent State signal |

A third candidate — the Context's state field being written after construction — is checkable only
as *a write exists*. Where the write originates needs data-flow, so it cannot carry the distinction.

**Not decidable.** PINOT's "passively modified (State) versus actively modified (Strategy)"
distinction requires data-flow analysis. PINOT itself fails to detect State.

**Styles.** States trigger their own transitions and therefore know their siblings
(`iluwatar/java-design-patterns/state`); or the Context drives transitions from a state table. A
`switch` or `enum` finite-state machine with no state objects is related but is **not** the GoF
object State.

---

# 2. The eight implemented patterns — clauses for cross-checking

Short form. Use these when auditing an existing rule's published statement against the definition,
and when writing `nl_clause` sentences.

| Pattern | Required clauses | Explicitly not required |
|---|---|---|
| **Factory Method** | (1) product creation is behind a method returning an **abstract** type; (2) the client depends on the abstract product, not a concrete class; (3) which concrete product is produced can vary | specific names; an abstract Creator class; a dedicated creation method; the exact GoF UML |
| **Strategy** | (1) a Context holds a reference to an abstract behaviour type; (2) multiple interchangeable implementations exist; (3) the Context delegates work to the held object | the word "Strategy"; strategies knowing each other — they should **not** |
| **Composite** | (1) a common Component supertype; (2) a Composite holds a collection whose element type is that supertype; (3) Composite operations delegate to children by iterating and calling the same operation on each | the word "Composite"; leaves being childless. add/remove methods are common but **not** mandatory |
| **Observer** | (1) a Subject holds a collection of an abstract Observer type; (2) a **registration mechanism adds/removes observers at runtime**; (3) a notify loop iterates the collection and calls one operation on each | the words "Observer"/"listener"; a base Observer class — functional callbacks qualify |
| **Singleton** | (1) instantiation is restricted — **private or protected** constructor; (2) the class exposes its single instance via a static accessor **or** a static field | the word "Singleton"; laziness — eager init qualifies |
| **Builder** | (1) step-by-step configuration methods separate from the final build; (2) a terminal build method returns the product | the word "Builder"; a Director; fluent chaining |
| **Decorator** | (1) the decorator implements the **same** supertype as the wrapped object; (2) it holds a field of that same supertype; (3) it forwards calls, adding behaviour around them | the word "Decorator"; an abstract base; stacking |
| **Template Method** | (1) a concrete method in an abstract class calls one or more abstract or overridable steps; (2) subclasses supply the steps; (3) the skeleton method itself is not overridden | the word "Template"; a `final` template method; hook methods |

**Two clauses above disagree with the current implementation.** Both are recorded as open defects,
deliberately not fixed before generation:

- **Singleton** requires a private **or protected** constructor, and an accessor **or** a field. The
  code requires private, and an accessor **and** a field.
- **Composite** and **Observer** collections held in an array or a `Map` are invisible to the
  current field model.

---

# 3. Validation resources named by the report

| Resource | Status for this project |
|---|---|
| `iluwatar/java-design-patterns` — Java, MIT, one module per pattern | The style reference. **Read for styles; do not vendor the repository.** Write our own minimal fixtures |
| P-MARt — expert-annotated Java ground truth, 9 projects, 4,374 files | A genuine second oracle. **Not before the deadline.** Future work |
| PINOT | The 2006 tool is not worth chasing. Its decidability split is citable regardless |
| DP-CORE / GEML operator sets | They use the same primitives we extract — `inherits`, `has`, `calls`, `creates`, `uses`. A mapping would be citable evidence our rules are not ad hoc |
| Non-Java repositories — `faif/python-patterns`, `DesignPatternsPHP`, `tmrts/go-patterns` | **Style catalogue only, never test input.** The test for transfer is mechanism, not syntax: a Python callable strategy transfers as a Java lambda; a duck-typed factory does not transfer at all |
