"""Structural design-pattern conformance checker.

Evaluates whether Java source structurally conforms to a GoF design pattern, using
explicit base and derived predicates. Detection is structural -- return types, field
types, call targets, abstract/concrete, extends/implements. Exports `PIQSChecker`
plus `_PATTERN_WEIGHTS` and `_CRITICAL_PROPERTIES` (read by the validation scripts).
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field


_PATTERN_WEIGHTS = {
    "factory-method": {"F1": 2, "F2": 3, "F3": 3, "F4": 3, "F5": 2},
    "strategy": {"S1": 3, "S2": 3, "S3": 2, "S4": 3},
    "composite": {"C1": 3, "C2": 2, "C3": 3, "C4": 3, "C5": 3},
    "observer": {"O1": 2, "O2": 3, "O3": 3, "O4": 3},
    "singleton": {"G1": 3},
    # --- New patterns (Builder / Decorator / Template Method). Weights follow Kim's Table 9
    # philosophy (RULE 2): weight 3 = the enabling relationship/behaviour that makes the
    # pattern work (also the CRITICAL set); weight 2 = existence-of-a-role / interaction;
    # weight 1 = supporting/peripheral. See validation/bdt_property_spec.md.
    "builder": {"B1": 3, "B2": 3, "B3": 2, "B4": 2, "B5": 1, "B6": 1},
    # D1 and D5 were removed 2026-08-10: both proven tautologies, `== D2` for every program by
    # construction. See PROPERTY_SPEC.md -- the reason is prompt generation, not PSR.
    "decorator": {"D2": 3, "D3": 3, "D4": 2, "D6": 1},
    "template-method": {"T1": 2, "T2": 2, "T3": 3, "T4": 2, "T5": 2},
}

# The critical property set per pattern -- the weight-3 relationship/behaviour properties.
# A program is recognised AS the pattern only when ALL of its critical properties hold; the
# BDT mutation battery keys its MUST-PASS / MUST-FAIL verdicts off exactly this set.
# The receiver recorded for `super.m()` and `Outer.super.m()`.
#
# WHY NOT THE BARE TEXT "super". The first version of this used it, on the reasoning that `super`
# is a reserved keyword so no field could be named it. Java forbids it -- but THIS CHECKER IS NOT
# javac, and the code it scores is generated code that frequently does not compile:
#
#     javac                 error: <identifier> expected
#     tree-sitter           has_error == False
#     extract_types         fields == [('super', 'Duct')]
#
# So `class Weird { private Duct super; void write(String s){ super.write(s); } }` is reachable,
# and with the bare text `_delegates_to_field` compared the receiver of a PARENT-CLASS call equal
# to a field named `super` and credited delegation to a field that is never touched -- scoring
# that program D2 1 D3 1 D4 1 D6 1, PIQS 100. That was a regression INTRODUCED by the bare-text
# version, not a pre-existing hole: before any super handling the receiver was None.
#
# `<super>` cannot be any identifier, because `<` and `>` are not JavaLetters (JLS 3.8). Verified
# against this parser rather than argued: `private Duct <super>;` yields a field whose name is the
# empty string, never "<super>". A string (rather than a sentinel object) also survives the JSON
# round-trip in results/parser_golden.json, and `calls` IS snapshotted there.
#
# Pinned by tests/fixtures_parser/field_named_super.java.
#
# IT LIVES HERE, NOT IN parser.py, FOR AN IMPORT REASON: `parser` imports `checker` at module
# level, while `checker` imports `parser` only inside a function to break the cycle. A constant
# that both need therefore has to sit on the `checker` side. `parser` re-exports it, so
# `from piqs.parser import SUPER_RECEIVER` still works.
SUPER_RECEIVER = "<super>"


_CRITICAL_PROPERTIES = {
    "factory-method": {"F2", "F3", "F4"},
    "strategy": {"S1", "S2", "S4"},
    "composite": {"C1", "C3", "C4", "C5"},
    "observer": {"O2", "O3", "O4"},
    "singleton": {"G1"},
    "builder": {"B1", "B2"},
    "decorator": {"D2", "D3"},
    "template-method": {"T3"},
}

# Framework supertypes that supply pattern structure from outside the project source.
# A supertype counts as framework only when it is BOTH on this list AND absent from the
# project's own declarations -- a project that declares its own `Observer` is not using the
# JDK one. Matched on the simple name by exact comparison, never by substring: the corpora
# are single-package and may or may not carry imports. Extend freely.
_FRAMEWORK_SUPERTYPES = {
    "Observable",
    "Observer",
    "AbstractList",
    "AbstractMap",
    "AbstractSet",
    "FilterInputStream",
    "FilterOutputStream",
    "HttpServlet",
    "Thread",
    "TimerTask",
}

@dataclass
class JavaField:
    name: str
    field_type: str
    modifiers: set[str] = field(default_factory=set)


@dataclass
class JavaMethod:
    name: str
    owner: str
    return_type: str | None
    param_types: list[str]
    param_names: list[str]
    modifiers: set[str]
    body: str
    is_constructor: bool
    # True when the declaration carried a brace body ("{ ... }"); False for a `;`-terminated
    # declaration (an abstract-class abstract method or a bodyless interface method). This is
    # the ONLY reliable way to tell an abstract primitive (`void step();`) from an
    # empty-bodied concrete method (`void step() {}`) -- both leave `body == ""`. Template
    # Method (T1/T2/T3) needs this distinction; the five original patterns never read it.
    has_body: bool = True
    # {identifier: declared base type} for every name declared INSIDE this method's body --
    # local variables, enhanced-for variables, try-with-resources resources, catch parameters
    # and lambda parameters. Built by piqs.parser from the AST.
    #
    # Parameters are deliberately NOT duplicated here: they already live in `param_names` /
    # `param_types`, and a second copy is a second thing to keep in step. Assemble the full
    # scope with `PIQSChecker._scope(type, method, types)`, which is the only supported way to
    # read it -- that merges fields, then parameters, then these, in Java shadowing order.
    #
    # The value is None when a name is declared without a type the parser can see: an
    # untyped lambda parameter (`o -> o.update()`). The NAME is still recorded, because a
    # consumer that needs the type gets it from the iterated collection, not from the lambda.
    #
    # Block scope is not modelled -- the dict is flat, so two sibling blocks each declaring
    # `i` collapse to one entry (last wins). No predicate distinguishes them.
    locals: dict[str, str | None] = field(default_factory=dict)
    # [(receiver, method_name)] for every call in this method's body, in source order. Built by
    # piqs.parser from the AST; read through `PIQSChecker._calls_within`.
    #
    # `receiver` is the reference the call is written against -- "f" for `f.op()` and for
    # `this.f.op()`, "g" for `f.g.op()`, None for `op()` and for a chain like `getX().op()`.
    # None can never equal a field name, so chains and unqualified calls are rejected by
    # comparison alone.
    #
    # Tree-sitter Nodes are deliberately NOT stored: a Node is only valid while its Tree is
    # alive, so holding one past parse time gives a dangling reference that fails silently.
    # Everything is extracted eagerly into plain data, which also keeps JavaMethod serializable.
    calls: list[tuple[str | None, str]] = field(default_factory=list)
    # Every whole token named in the body -- identifiers AND the `this` / `super`
    # keywords. Built by piqs.parser; read through `PIQSChecker._mentions_within`.
    mentions: set[str] = field(default_factory=set)
    # Names assigned in the body via a simple `=`. Built by piqs.parser; read through
    # `PIQSChecker._assigns_field`.
    assignments: set[str] = field(default_factory=set)
    # [(collection identifier, callback name)] for each notification loop the parser
    # recognises in this body. The ELEMENT TYPE is not resolved here -- the checker does
    # that from `coll_fields`, unchanged, so loop shapes can be added without touching
    # the `t.body` text matching that also feeds Composite.
    traversals: list[tuple[str, str, str | None]] = field(default_factory=list)


@dataclass
class JavaType:
    name: str
    kind: str
    is_abstract: bool
    extends: str | None
    implements: list[str] = field(default_factory=list)
    content: str = ""
    body: str = ""
    methods: list[JavaMethod] = field(default_factory=list)
    fields: list[JavaField] = field(default_factory=list)


class PIQSChecker:
    def evaluate(self, pattern_name: str, java_files: dict[str, str]) -> dict:
        normalized = pattern_name.strip().lower()
        if normalized not in _PATTERN_WEIGHTS:
            raise ValueError(
                "Unsupported pattern_name. Use one of: factory-method, strategy, "
                "composite, observer, singleton, builder, decorator, template-method."
            )

        types = self._extract_types(java_files)

        if normalized == "factory-method":
            base, derived, assessments = self._evaluate_factory_method(types)
        elif normalized == "strategy":
            base, derived, assessments = self._evaluate_strategy(types)
        elif normalized == "composite":
            base, derived, assessments = self._evaluate_composite(types)
        elif normalized == "observer":
            base, derived, assessments = self._evaluate_observer(types)
        elif normalized == "singleton":
            base, derived, assessments = self._evaluate_singleton(types)
        elif normalized == "builder":
            base, derived, assessments = self._evaluate_builder(types)
        elif normalized == "decorator":
            base, derived, assessments = self._evaluate_decorator(types)
        else:
            base, derived, assessments = self._evaluate_template_method(types)

        weights = _PATTERN_WEIGHTS[normalized]
        total_properties = len(assessments)
        satisfied = sum(1 for row in assessments if row["satisfaction"] == 1)
        weighted_earned = sum(row["weight"] * row["satisfaction"] for row in assessments)
        weighted_total = sum(weights.values())

        psr = (satisfied / total_properties) * 100 if total_properties else 0.0
        cpc = (weighted_earned / weighted_total) * 100 if weighted_total else 0.0
        piqs = (psr * 0.6) + (cpc * 0.4)

        # Framework inheritance: structure supplied from outside the source. Reported as a
        # flag so a reader can see it; it never satisfies a property. See PROPERTY_SPEC.md.
        framework_supers, unknown_supers = self._classify_supertypes(types)

        return {
            "pattern_name": normalized,
            "files_analyzed": sorted(java_files.keys()),
            "base_predicates": base,
            "derived_predicates": derived,
            "logical_assessment": assessments,
            "framework_inheritance": [
                {
                    "type": type_name,
                    "supertype": supertype,
                    "pattern_roles_supplied": self._framework_roles_supplied(
                        types[type_name], types
                    ),
                }
                for type_name, supertype in framework_supers
            ],
            "unknown_supertypes": [
                {"type": type_name, "supertype": supertype}
                for type_name, supertype in unknown_supers
            ],
            "breadth_calculation_psr": {
                "formula": f"({satisfied}/{total_properties})*100",
                "result_percent": round(psr, 2),
            },
            "depth_calculation_cpc": {
                "formula": f"({weighted_earned}/{weighted_total})*100",
                "result_percent": round(cpc, 2),
            },
            "final_quality_result_piqs": {
                "formula": f"({round(psr, 2)}*0.6)+({round(cpc, 2)}*0.4)",
                "result_percent": round(piqs, 2),
            },
            "grade": self._grade(piqs),
        }

    def _extract_types(self, java_files: dict[str, str]) -> dict[str, JavaType]:
        """The extractor the checker runs on: a tree-sitter parse of each file (piqs/parser.py).

        Every predicate reads the JavaType / JavaMethod / JavaField model below and is
        indifferent to how it was built. The regex declaration scanner this replaced was
        removed once validation/extractor_parity.py compared both extractors fact by fact
        across all 184 corpus files and every remaining difference was traced to a regex bug
        (see tests/fixtures_parser/ for one regression test per bug class).

        The import is function-local because piqs.parser imports the dataclasses and
        _base_name from this module.
        """
        from piqs.parser import extract_types

        return extract_types(java_files)

    @staticmethod
    def _mentions_within(method: "JavaMethod", token: str) -> bool:
        """mentionsWithin(method, token): does `method`'s body name `token` as a whole token?

        Phase 2, step 2. Reads `method.mentions`, precomputed from the AST; the
        `_mentions_token(body, name)` regex it replaces is gone. Whole-token matching is
        unchanged -- `siz` still does not match inside `size` -- but it now comes from the tree
        rather than a look-behind.

        `this` and `super` are included: they are keyword nodes, and Builder B1 reads
        `this` to accept a terminal. Comments and string literals are not (divergence #4).
        """
        return token in method.mentions

    @staticmethod
    def _has_verb_prefix(name: str, verb: str) -> bool:
        """Fix G: True if `name` is exactly `verb`, or a camelCase method that begins with
        it (add -> add, addChild, addObserver, add_child) -- but NOT a word that merely
        starts with those letters (add -> address is False)."""
        if name == verb:
            return True
        if name.startswith(verb):
            rest = name[len(verb):]
            return bool(rest) and (rest[0].isupper() or rest[0].isdigit() or rest[0] == "_")
        return False

    @staticmethod
    def _enum_constant_count(body: str) -> int:
        """Count an enum's constants -- the comma-separated identifiers before the first
        top-level ';' (or the whole body if there is none). Nested parens/braces
        (constant arguments or bodies) are flattened so they don't inflate the count.
        A single-constant enum is the canonical enum-singleton (one instance)."""
        depth = 0
        seg: list[str] = []
        for ch in body:
            if ch in "{(":
                depth += 1
            elif ch in "})":
                if depth > 0:
                    depth -= 1
            elif ch == ";" and depth == 0:
                break
            else:
                seg.append(ch if depth == 0 else " ")
        count = 0
        for part in "".join(seg).split(","):
            part = part.strip()
            if not part:
                continue
            first = part.split()[0]
            if re.match(r"[A-Za-z_][A-Za-z0-9_]*$", first):
                count += 1
        return count

    # ------------------------------------------------------------------ #
    # New AST helpers (RULE 1): the only two base predicates the codebase lacked.
    # ------------------------------------------------------------------ #
    @staticmethod
    def _calls_within(method: "JavaMethod", target: str) -> bool:
        """callsWithin(method, target): does `method`'s body invoke a method named exactly
        `target`? Used by Strategy (execute), D3 (delegation) and T3 (inversion of control).

        Phase 2, step 2: this reads `method.calls`, precomputed from the AST, and the separate
        `_calls_method(body, name)` regex it used to wrap is gone -- one source of truth. Exact
        name matching is unchanged, so `read` still never matches inside `readLine`; that came
        from the whole-token rule, which the tree gives for free.

        Four things the regex counted as a call and this does not: text in a comment or string
        literal, a constructor call (`new Wallet()` matched the name "Wallet"), a method
        DECLARED in the body, and -- unchanged -- nothing else, because the walk descends into
        anonymous and local class bodies exactly as the flat text did. Each is pinned by a
        fixture in tests/test_body_helpers_divergences.py; none occurs in either corpus, so the
        suites are not what protects them.
        """
        return any(name == target for _receiver, name in method.calls)

    @staticmethod
    def _field_of_type(jtype: "JavaType", type_name: str) -> bool:
        """fieldOfType(class, type): does `jtype` hold a class-scope field whose (base) type is
        `type_name`? Reuses the pass-3 class-scope-only field extraction (no method-local
        variables). Used by D2 (decorator holds a component-typed reference)."""
        return any(f.field_type == type_name for f in jtype.fields)

    @staticmethod
    def _delegates_to_field(
        method: "JavaMethod", field_name: str, super_delegates: bool = False
    ) -> bool:
        """delegatesTo(method, field): does `method` invoke something on the reference
        `field_name`? The structural signature of delegation (D3).

        Phase 2, step 2. Reads `method.calls`, whose receiver was normalised at parse time by
        `_qualifier`. The retired regex required `<name> . <ident> (`, optionally preceded by
        `this.`, and that narrowness is the meaning: D3 asks whether the wrapper forwards to THE
        HELD REFERENCE, so a chain through a call (`getX().op()`) or an array element
        (`arr[0].op()`) is not delegation to a field.

        A method_invocation query is naturally WIDER than that. Nothing here re-narrows it --
        the uniform qualifier rule does, by storing None for any receiver that is not a simple
        reference. None never equals a field name, so chains are rejected by comparison alone
        and there is no chain-detection branch anywhere.

        The sharp case is `f.g.op()`, which delegates to `g` and NOT to `f`: the old regex is
        satisfied by the text `g.op(` and not by `f.op(`. Pinned by
        tests/fixtures_parser/div5_chain_not_delegation.java; zero corpus coverage.

        `super_delegates` -- FORWARDING ONE LINK LONGER. In the canonical GoF shape the abstract
        base holds the component and the concrete decorators extend it, so a concrete decorator
        forwards by calling `super.m()`. `decorator_filterinputstream_analogue` is exactly that:
        `BufferedInputStream.read()` forwards with `super.read()`, not with `in.read()`.

        THE FLAG IS NOT OPTIONAL, and the caller must compute it. "Forwards through the base that
        HOLDS the reference" contains a condition, so the condition gets checked: the caller passes
        True only when a project-defined ancestor of the wrapper is ITSELF a decorator candidate.
        Accepting every `super` call unconditionally would re-open the hole F1b closed --
        `field_named_super.java` declares a `Duct` field, has no `extends` at all, and calls
        `super.write()`, so the loose rule would score it D3 = 1 by a different route from the
        string collision. Pinned by tests/test_super_delegation.py.
        """
        return any(
            receiver == field_name or (super_delegates and receiver == SUPER_RECEIVER)
            for receiver, _name in method.calls
        )

    @staticmethod
    def _assigns_field(method: "JavaMethod", field_name: str) -> bool:
        """True if `method` assigns to `field_name` -- `field = ...` or `this.field = ...`.

        Phase 2, step 2. Reads `method.assignments`, precomputed from the AST.
        """
        return field_name in method.assignments

    def _effective_methods(self, t: "JavaType", types: dict[str, "JavaType"]) -> list["JavaMethod"]:
        """`t`'s own methods plus those inherited from its project-defined `extends` ancestors.
        The Builder role is frequently split across an abstract Builder (declares the terminal
        getResult()) and a ConcreteBuilder (defines the void build-part steps); reasoning over
        the effective method set lets one detection see the whole builder family."""
        methods = list(t.methods)
        seen = {t.name}
        cur = t
        while cur.extends and cur.extends in types and cur.extends not in seen:
            parent = types[cur.extends]
            methods.extend(parent.methods)
            seen.add(parent.name)
            cur = parent
        return methods

    def _effective_fields(self, t: "JavaType", types: dict[str, "JavaType"]) -> list["JavaField"]:
        """`t`'s own class-scope fields plus those inherited from project-defined ancestors."""
        fields = list(t.fields)
        seen = {t.name}
        cur = t
        while cur.extends and cur.extends in types and cur.extends not in seen:
            parent = types[cur.extends]
            fields.extend(parent.fields)
            seen.add(parent.name)
            cur = parent
        return fields

    def _scope(
        self, t: "JavaType", m: "JavaMethod", types: dict[str, "JavaType"]
    ) -> dict[str, str | None]:
        """{identifier: declared base type} visible inside `m`, a method of `t`.

        Phase 2, step 1 -- the scope table. The single supported way to ask what a name means
        inside a method body. Sources, merged in Java shadowing order so that a later source
        overwrites an earlier one:

            1. fields of `t` and of its project-defined ancestors   (`_effective_fields`)
            2. `m`'s parameters
            3. names declared in `m`'s body                         (`m.locals`)

        A local named `x` therefore beats a field named `x`, which is what Java does.

        The value is the declared type's BASE name (`List<Observer> seen` -> "List"), or None
        for an untyped lambda parameter. Use `name in types` to decide whether a type is
        project-defined; see docs/PROPERTY_SPEC.md, "Identifier resolution".

        NOTHING READS THIS YET. It is built and tested on its own so that the verdict-moving
        change -- replacing the `t.body` text matching in `_evaluate_observer` and
        `_evaluate_composite` -- lands as a separate, separately-measured step.
        """
        # `reversed` is load-bearing. `_effective_fields` returns own fields FIRST, then the
        # parent's, then the grandparent's. A plain comprehension lets the LATER entry win, so
        # an inherited field would overwrite the subclass field that shadows it -- the inverse
        # of Java, where a subclass field hides a superclass field of the same name. Walking
        # ancestors-first makes the nearest declaration land last and win.
        #
        # `_effective_fields` itself is NOT reordered: its other caller (`_evaluate_builder`)
        # collapses the result into a set, so order is invisible there, and changing it would be
        # an unmeasured behaviour change somewhere else.
        #
        # Guarded by tests/fixtures_parser/shadowed_inherited_field.java. No corpus file shadows
        # an inherited field, so all four suites pass without this.
        scope: dict[str, str | None] = {
            f.name: f.field_type for f in reversed(self._effective_fields(t, types))
        }
        for pname, ptype in zip(m.param_names, m.param_types):
            if pname:
                scope[pname] = ptype or None
        scope.update(m.locals)
        return scope

    def _framework_roles_supplied(self, t: "JavaType", types: dict[str, "JavaType"]) -> list[str]:
        """Which pattern-bearing structures a framework-inheriting type declares ITSELF.

        Descriptive, never a verdict. We cannot know what a framework supertype *requires*
        without modelling that framework -- the policy does not need us to. Removing the
        framework shortcuts is what enforces it: a type is credited only for structure the
        ordinary predicates can see. This list just records what that structure is, so a
        reader can tell `AuditLog extends Observable` (supplies nothing) from a subclass that
        genuinely implements the roles its pattern asks of it.
        """
        roles = []
        if re.search(
            r"\b(?:List|Set|Collection|ArrayList|LinkedList|HashSet|CopyOnWriteArrayList|Vector)"
            r"\s*<\s*([A-Za-z_][A-Za-z0-9_]*)\s*>",
            t.body,
        ) and any(
            elem in types
            for elem in re.findall(
                r"\b(?:List|Set|Collection|ArrayList|LinkedList|HashSet|CopyOnWriteArrayList|Vector)"
                r"\s*<\s*([A-Za-z_][A-Za-z0-9_]*)\s*>",
                t.body,
            )
        ):
            roles.append("holds_collection_of_project_type")
        if any(
            re.search(r"for\s*\(\s*(?:final\s+)?[A-Za-z_][A-Za-z0-9_<>\[\]]*\s+[A-Za-z_]", m.body)
            and re.search(r"\.[A-Za-z_][A-Za-z0-9_]*\s*\(", m.body)
            for m in t.methods
        ):
            roles.append("traverses_collection_invoking_member")
        if any(
            pt in types and types[pt].is_abstract for m in t.methods for pt in m.param_types
        ):
            roles.append("accepts_project_abstraction")
        if any(s in types for s in self._declared_supertypes(t)):
            roles.append("implements_project_abstraction")
        if any(not m.has_body for m in t.methods):
            roles.append("declares_abstract_member")
        return roles

    @staticmethod
    def _declared_supertypes(t: "JavaType") -> list[str]:
        """`t`'s extends target plus every interface it implements."""
        return ([t.extends] if t.extends else []) + list(t.implements)

    def _classify_supertypes(
        self, types: dict[str, "JavaType"]
    ) -> tuple[list[tuple[str, str]], list[tuple[str, str]]]:
        """Split every supertype the project references but does not declare into
        (framework, unknown), each a list of (type_name, supertype_name).

        A supertype declared in the project is neither -- it is local, and the ordinary
        structural predicates already see it. Of the rest, one on _FRAMEWORK_SUPERTYPES is
        framework; anything else is UNKNOWN: a missing file, a third-party library, or a type
        the source referenced but never wrote. Unknown is reported, never silently folded into
        either bucket.
        """
        framework: list[tuple[str, str]] = []
        unknown: list[tuple[str, str]] = []
        for t in types.values():
            for supertype in self._declared_supertypes(t):
                if supertype in types:
                    continue
                bucket = framework if supertype in _FRAMEWORK_SUPERTYPES else unknown
                bucket.append((t.name, supertype))
        return sorted(set(framework)), sorted(set(unknown))

    def _conforms_to(self, t: "JavaType", target: str, types: dict[str, "JavaType"]) -> bool:
        """True if `t` is-a `target` -- implements/extends it directly or transitively through
        project-defined supertypes. An interface parent counts exactly like an abstract-class
        parent (the interface-as-abstract-role rule already used by the five patterns)."""
        seen = set()
        stack = [t]
        while stack:
            cur = stack.pop()
            if cur.name in seen:
                continue
            seen.add(cur.name)
            supers = list(cur.implements) + ([cur.extends] if cur.extends else [])
            if target in supers:
                return True
            for s in supers:
                if s in types:
                    stack.append(types[s])
        return False

    @staticmethod
    def _component_type_names(types: dict[str, "JavaType"]) -> set[str]:
        """The abstract component types: every interface and every abstract class. A Decorator
        component and a Template-Method abstract type are both 'abstract types' in this sense
        (RULE 1: a Java interface counts as an abstract type)."""
        return {t.name for t in types.values() if t.is_abstract}

    def _evaluate_factory_method(self, types: dict[str, JavaType]) -> tuple[dict[str, bool], dict[str, bool], list[dict]]:
        abstract_types = [t for t in types.values() if t.is_abstract]
        concrete_types = [t for t in types.values() if not t.is_abstract and t.kind == "class"]
        known_type_names = set(types.keys())

        extends_exists = any(t.extends for t in concrete_types)
        implements_exists = any(t.implements for t in concrete_types)
        has_method_exists = any(t.methods for t in types.values())
        returns_exists = any(m.return_type for t in types.values() for m in t.methods if not m.is_constructor)

        # A concrete type's abstract parents are the project types it extends OR
        # implements. An interface parent counts exactly like an abstract-class parent:
        # implementing an interface establishes the same abstract-parent relationship
        # that extending an abstract class does.
        def _declared_parents(t):
            parents = []
            if t.extends and t.extends in types:
                parents.append(t.extends)
            for iface in t.implements:
                if iface in types:
                    parents.append(iface)
            return parents

        overrides_exists = False
        for t in concrete_types:
            parent_method_names = set()
            for parent in _declared_parents(t):
                parent_method_names |= {m.name for m in types[parent].methods}
            if parent_method_names & {m.name for m in t.methods}:
                overrides_exists = True
                break

        products = [t for t in abstract_types if t.kind in {"interface", "class"}]
        product_names = {t.name for t in products}

        creates_exists = False
        has_factory_exists = False
        is_product_exists = False
        is_creator_exists = False

        for t in types.values():
            for m in t.methods:
                if m.is_constructor:
                    continue
                if m.return_type in product_names:
                    has_factory_exists = has_factory_exists or (t.is_abstract or "abstract" in m.modifiers)
                    if re.search(r"\bnew\s+[A-Za-z_][A-Za-z0-9_]*\s*\(", m.body):
                        creates_exists = True

        # Fix C: a PRODUCT is the type RETURNED by a factory method (the creates/returns
        # relationship), not any type that merely implements some unrelated interface.
        # factory_product_types = return types of factory methods (declared by an abstract
        # creator, or a method that instantiates via `new`). F5 then fires only when a
        # concrete class implements/extends an ABSTRACT product interface that a factory
        # actually returns -- so Strategy/Observer implementers no longer count as products.
        factory_product_types = set()
        for t in types.values():
            for m in t.methods:
                if m.is_constructor:
                    continue
                if m.return_type in known_type_names and (
                    t.is_abstract or re.search(r"\bnew\s+[A-Za-z_]", m.body)
                ):
                    factory_product_types.add(m.return_type)
        is_product_exists = any(
            (not c.is_abstract)
            and c.kind == "class"
            and any(
                (p in c.implements or c.extends == p) and p in types and types[p].is_abstract
                for p in factory_product_types
            )
            for c in types.values()
        )

        for c in concrete_types:
            for parent in _declared_parents(c):
                parent_methods = {m.name: m for m in types[parent].methods}
                for m in c.methods:
                    if m.name in parent_methods and (m.return_type in product_names or parent_methods[m.name].return_type in product_names):
                        is_creator_exists = True

        base = {
            "isAbstract(x)": bool(abstract_types),
            "isConcrete(x)": bool(concrete_types),
            "hasMethod(c,m)": has_method_exists,
            "returns(m,t)": returns_exists,
            "implements(x,y)": implements_exists,
            "extends(x,y)": extends_exists,
            "overrides(m1,m2)": overrides_exists,
        }

        derived = {
            "creates(c,p)": creates_exists,
            "hasFactory(c,m)": has_factory_exists,
            "isProduct(x)": is_product_exists,
            "isCreator(c)": is_creator_exists,
        }

        # --- Abstract creator detection (Factory Method F1) ------------------------
        # An abstract creator is an abstract TYPE -- a Java `interface` OR an
        # `abstract class` -- that plays the creator role: it declares a factory method
        # (a non-constructor method whose return type is a project-defined product type)
        # and is implemented/extended by at least one concrete class.
        #
        # DESIGN DECISION (interface-as-abstract-role; see Kim replication study):
        #   * Interface creators ARE accepted as the abstract creator, exactly like an
        #     abstract class. A concrete class that `implements` the creator interface
        #     counts the same as one that `extends` an abstract creator class.
        #   * A static/switch "simple factory" -- a single CONCRETE class exposing a
        #     static create() method, with no abstract creator type -- is DELIBERATELY
        #     REJECTED as NOT GoF Factory Method: it has no abstract creator, so F1 is
        #     false by construction. This is an intentional, documented distinction, not
        #     an oversight.
        abstract_creators = []
        for t in types.values():
            if not t.is_abstract:
                continue
            declares_factory = any(
                (not m.is_constructor) and m.return_type in known_type_names
                for m in t.methods
            )
            has_concrete_impl = any(
                (not c.is_abstract) and c.kind == "class"
                and (c.extends == t.name or t.name in c.implements)
                for c in types.values()
            )
            if declares_factory and has_concrete_impl:
                abstract_creators.append(t)

        f1 = bool(abstract_creators)
        f2 = any(
            t.kind == "class" and not t.is_abstract and (
                (t.extends in types and types[t.extends].is_abstract)
                or any(i in types and types[i].is_abstract for i in t.implements)
            )
            for t in types.values()
        )
        f3 = overrides_exists

        # Change 2: F4 -- factory methods create products of the correct type.
        #   A factory method is a non-constructor method that instantiates via `new` and
        #   returns a project-defined type (the product).
        #   * in-hierarchy: the returned type is abstract, or implements/extends an abstract
        #     type -> F4 passes (unchanged, classic behaviour).
        #   * single concrete product: the returned type is a concrete standalone type AND the
        #     program has no abstract product hierarchy that the factory bypasses (no factory
        #     returns an abstract product, and no concrete type created inside a factory method
        #     implements/extends an abstract type) -> accept the concrete product (single-
        #     product domain, e.g. one concrete Wallet with no abstract wallet type).
        #   * if an abstract product hierarchy DOES exist but the factory returns a concrete
        #     type outside it -> F4 still fails.
        _new_call_re = re.compile(r"\bnew\s+([A-Za-z_][A-Za-z0-9_]*)\s*\(")

        def _returns_in_hierarchy(rname):
            rt = types.get(rname)
            if rt is None:
                return False
            if rt.is_abstract:
                return True
            for sup in list(rt.implements) + ([rt.extends] if rt.extends else []):
                st = types.get(sup)
                if st is not None and st.is_abstract:
                    return True
            return False

        factory_methods = [
            m
            for t in types.values()
            for m in t.methods
            if not m.is_constructor and m.return_type in known_type_names and _new_call_re.search(m.body)
        ]

        abstract_product_exists = False
        for m in factory_methods:
            if _returns_in_hierarchy(m.return_type) and types[m.return_type].is_abstract:
                abstract_product_exists = True
            for xname in _new_call_re.findall(m.body):
                xt = types.get(xname)
                if xt is None:
                    continue
                for sup in list(xt.implements) + ([xt.extends] if xt.extends else []):
                    st = types.get(sup)
                    if st is not None and st.is_abstract:
                        abstract_product_exists = True

        f4_in_hierarchy = any(_returns_in_hierarchy(m.return_type) for m in factory_methods)
        f4_concrete = (
            any(not _returns_in_hierarchy(m.return_type) for m in factory_methods)
            and not abstract_product_exists
        )
        f4 = f4_in_hierarchy or f4_concrete
        f5 = is_product_exists

        rows = [
            self._row("F1", 2, f1, "Abstract creator class exists."),
            self._row("F2", 3, f2, "Abstract creator has concrete implementation."),
            self._row("F3", 3, f3, "Concrete creator overrides factory method."),
            self._row("F4", 3, f4, "Factory method creates product of correct abstract type."),
            self._row("F5", 2, f5, "Concrete products implement abstract product interfaces."),
        ]
        return base, derived, rows

    def _evaluate_strategy(self, types: dict[str, JavaType]) -> tuple[dict[str, bool], dict[str, bool], list[dict]]:
        interfaces = [t for t in types.values() if t.kind == "interface"]
        concrete_classes = [t for t in types.values() if t.kind == "class" and not t.is_abstract]

        implemented_by: dict[str, list[JavaType]] = {
            i.name: [c for c in concrete_classes if i.name in c.implements] for i in interfaces
        }
        strategy_ifaces = [name for name, impls in implemented_by.items() if impls]

        strategy_method_names = set()
        for iface_name in strategy_ifaces:
            iface = types.get(iface_name)
            if iface:
                strategy_method_names.update(m.name for m in iface.methods)

        accepts_exists = any(
            any(pt in strategy_ifaces for pt in m.param_types)
            for t in types.values()
            for m in t.methods
        )

        calls_exists = any(
            re.search(r"\.[A-Za-z_][A-Za-z0-9_]*\s*\(", m.body) is not None
            for t in types.values()
            for m in t.methods
        )

        is_context = False
        is_set_strategy = False
        is_execute_strategy = False
        delegates = False
        has_strategy = False

        for c in concrete_classes:
            field_strategy = any(f.field_type in strategy_ifaces for f in c.fields)
            setter = any(self._has_verb_prefix(m.name, "set") and any(pt in strategy_ifaces for pt in m.param_types) for m in c.methods)
            # Fix G: invoke-by-whole-token, not `"pay" in body` (which matched "payment").
            # Phase 2 step 2: the whole-token rule is now the tree's, via `method.calls`.
            execute = any(
                any(self._calls_within(m, name) for name in strategy_method_names)
                for m in c.methods
            )

            has_strategy = has_strategy or field_strategy or setter
            is_set_strategy = is_set_strategy or setter
            is_execute_strategy = is_execute_strategy or execute
            delegates = delegates or execute
            is_context = is_context or ((field_strategy or setter) and execute)

        is_algorithm = bool(strategy_method_names)
        algorithm_method = any(
            any(m.name in strategy_method_names for m in c.methods)
            for c in concrete_classes
            if any(i in strategy_ifaces for i in c.implements)
        )
        is_strategy = bool(strategy_ifaces)

        base = {
            "isAbstract(x)": bool(interfaces),
            "isConcrete(x)": bool(concrete_classes),
            "accepts(m,p)": accepts_exists,
            "hasMethod(c,m)": any(t.methods for t in types.values()),
            "calls(m1,m2)": calls_exists,
            "implements(x,y)": any(c.implements for c in concrete_classes),
        }

        derived = {
            "isAlgorithm(m)": is_algorithm,
            "algorithmMethod(m)": algorithm_method,
            "isStrategy(x)": is_strategy,
            "hasStrategy(c,s)": has_strategy,
            "isSetStrategy(m)": is_set_strategy,
            "isExecuteStrategy(m)": is_execute_strategy,
            "isContext(x)": is_context,
            "delegates(c,s)": delegates,
        }

        s1 = is_strategy
        s2 = bool(strategy_ifaces) and all(implemented_by.get(i) for i in strategy_ifaces)
        s3 = is_context
        s4 = algorithm_method

        rows = [
            self._row("S1", 3, s1, "Abstract strategy interface exists."),
            self._row("S2", 3, s2, "Every strategy interface has a concrete implementation."),
            self._row("S3", 2, s3, "Context class manages strategies."),
            self._row("S4", 3, s4, "Concrete strategies implement algorithm method."),
        ]
        return base, derived, rows

    def _evaluate_composite(self, types: dict[str, JavaType]) -> tuple[dict[str, bool], dict[str, bool], list[dict]]:
        abstract_components = [t for t in types.values() if t.kind == "interface" or t.is_abstract]
        component_names = {t.name for t in abstract_components}

        concrete_components = [
            t
            for t in types.values()
            if t.kind == "class" and not t.is_abstract and (t.extends in component_names or any(i in component_names for i in t.implements))
        ]

        # Fix G: recognise add/remove operations by whole-token camelCase verb prefix
        # (add, addChild, addComponent) -- not by substring ("add" also occurs in "address").
        # STILL NAME-BASED, and deliberately left so: `isAdd`/`isRemove` are evidence-trace
        # entries in `base`, recorded by run_scorer.py and read by nothing. No verdict uses them.
        is_add = any(self._has_verb_prefix(m.name, "add") for t in concrete_components for m in t.methods)
        is_remove = any(self._has_verb_prefix(m.name, "remove") for t in concrete_components for m in t.methods)

        accepts_exists = any(any(pt in component_names for pt in m.param_types) for t in concrete_components for m in t.methods)

        elem_re = re.compile(
            r"\b(?:List|Set|Collection|ArrayList|LinkedList|HashSet|CopyOnWriteArrayList|Vector)"
            r"\s*<\s*([A-Za-z_][A-Za-z0-9_]*)\s*>"
        )
        # As `elem_re`, but also capturing the FIELD NAME, because C3 has to check that the
        # collection a child is added to is the same collection the type holds. `elem_re` alone
        # cannot: it matches the type argument wherever it appears, including in a return type.
        child_field_re = re.compile(
            r"\b(?:List|Set|Collection|ArrayList|LinkedList|HashSet|CopyOnWriteArrayList|Vector)"
            r"\s*<\s*([A-Za-z_][A-Za-z0-9_]*)\s*>\s+([A-Za-z_][A-Za-z0-9_]*)"
        )

        # Fix D: a REAL Composite requires an actual part-whole hierarchy, not merely the
        # presence of some interface. For each abstract component, a COMPOSITE is a concrete
        # implementor that HOLDS A COLLECTION of that component type; a LEAF is a concrete
        # implementor that does not. C1/C4/C5 fire only when such a real hierarchy exists,
        # so programs whose only interfaces are Strategy/Observer (no part-whole structure)
        # no longer produce spurious component/composite detections.
        real_components = []
        for comp in abstract_components:
            impls = [
                t
                for t in types.values()
                if t.kind == "class"
                and not t.is_abstract
                and (t.extends == comp.name or comp.name in t.implements)
            ]
            comp_composites = [t for t in impls if comp.name in elem_re.findall(t.body)]
            comp_leaves = [t for t in impls if t not in comp_composites]
            if comp_composites:
                real_components.append((comp, comp_composites, comp_leaves))

        def _manages_children(holder: JavaType, component_name: str, fields: set[str]) -> bool:
            """Does `holder` let a caller put a child INTO its own child collection?

            A method whose PARAMETER TYPE is the component type, which operates on one of the
            component-typed collection fields or assigns it. Same shape as Observer's
            registration check, and for the same reason: "holds a collection" alone does not
            make a whole -- the whole has to accept parts.
            """
            return any(
                component_name in mm.param_types
                and (
                    any(receiver in fields for (receiver, _name) in mm.calls)
                    or bool(fields & mm.assignments)
                )
                for mm in holder.methods
            )

        # C3, STRUCTURALLY. This used to be "a concrete component declaring a method whose name
        # begins with the token `add` or `remove`" -- so `Register implements InventoryObserver`
        # with `addSale()` and a `List<Sale>` scored as a Composite in POSS/Copilot and
        # POSS/Gemini, two programs that contain no Composite at all. Their own C1 says so: no
        # abstract component exists, yet a composite type was reported.
        #
        # A composite is a concrete type that conforms to an abstract component, HOLDS a
        # collection of that component type, and ACCEPTS a child of that type into it. All three
        # come from declarations -- conformance, a field's type argument, a parameter's type --
        # and none from a method name. `add` and `addComponent` both qualify; so does `graft`.
        #
        # ONE CONSTRUCTION SITE, and it reuses `real_components`, which C1/C4/C5 already read.
        # The old code held TWO definitions of "composite" in this one function: this name-based
        # list, and `comp_composites` inside `real_components`. That is why C3 could be 1 while
        # C1 and C4 were 0 for the same program.
        composites = list(
            {
                t.name: t
                for (comp, comp_composites, _comp_leaves) in real_components
                for t in comp_composites
                if _manages_children(
                    t,
                    comp.name,
                    {n for (e, n) in child_field_re.findall(t.body) if e == comp.name},
                )
            }.values()
        )
        leaves = [t for t in concrete_components if t not in composites]

        has_children = any(re.search(r"\b(List|Set|Collection)<", t.body) for t in composites)
        contains_component = any(
            any(pt in component_names for m in t.methods for pt in m.param_types)
            for t in composites
        )
        is_add_child = any(any(self._has_verb_prefix(m.name, "add") for m in t.methods) for t in composites)
        is_remove_child = any(any(self._has_verb_prefix(m.name, "remove") for m in t.methods) for t in composites)

        base = {
            "isAbstract(x)": bool(abstract_components),
            "isConcrete(x)": bool(concrete_components),
            "accepts(m,p)": accepts_exists,
            "hasMethod(c,m)": any(t.methods for t in types.values()),
            "isAdd(m)": is_add,
            "isRemove(m)": is_remove,
            "implements(x,y)": any(t.implements for t in concrete_components),
        }

        derived = {
            "isComponent(x)": bool(component_names),
            "hasChildren(x)": has_children,
            "isAddChild(m)": is_add_child,
            "isRemoveChild(m)": is_remove_child,
            "containsComponent(x,y)": contains_component,
            "isComposite(x)": bool(composites),
            "isLeaf(x)": bool(leaves),
        }

        real_c5 = False
        for comp, comp_composites, comp_leaves in real_components:
            if comp_composites and comp_leaves:
                api = {m.name for m in comp.methods}
                if api and all(api <= {m.name for m in x.methods} for x in comp_composites) and all(
                    api <= {m.name for m in x.methods} for x in comp_leaves
                ):
                    real_c5 = True
                    break

        c1 = bool(real_components)                                        # real abstract component
        c2 = bool(leaves)                                                 # unchanged
        c3 = bool(composites)                                             # unchanged
        c4 = any(cc and lv for (_, cc, lv) in real_components)            # real composite AND leaf
        c5 = real_c5                                                      # uniform over the ACTUAL component API

        rows = [
            self._row("C1", 3, c1, "Abstract component exists."),
            self._row("C2", 2, c2, "Leaf type exists."),
            self._row(
                "C3",
                3,
                c3,
                "Composite type exists -- a concrete component that holds a collection of the "
                "component type and accepts a child of that type into it.",
            ),
            self._row("C4", 3, c4, "Composite and leaf implement component."),
            self._row("C5", 3, c5, "Uniform composite/leaf treatment is possible."),
        ]
        return base, derived, rows

    def _evaluate_observer(self, types: dict[str, JavaType]) -> tuple[dict[str, bool], dict[str, bool], list[dict]]:
        class_types = [t for t in types.values() if t.kind == "class"]

        # --- Fix B (JDK Observer framework) is GONE as of Fix J. `extends Observable` and
        # `implements Observer` used to fill the abstract subject / observer roles outright.
        # Under the framework-inheritance policy a type gets credit only for structure the
        # source itself declares, so both shortcuts are removed. Detection still happens --
        # in `evaluate`, via `_classify_supertypes` -- but it produces the informational
        # `framework_inheritance` flag, never a satisfied property.
        #
        # --- Fix A: detect the observer callback by STRUCTURE, not by the name `update`.
        # A subject notifies either (a) by iterating a collection of observers and invoking
        # a method on each element, or (b) by invoking a method on a single held observer
        # reference. The invoked method is the callback (ANY name -- update, notify,
        # onLogEvent, ...); the element/field type is the observer type.
        elem_field_re = re.compile(
            r"\b(?:List|Set|Collection|ArrayList|LinkedList|HashSet|CopyOnWriteArrayList|Vector)"
            r"\s*<\s*([A-Za-z_][A-Za-z0-9_]*)\s*>\s+([A-Za-z_][A-Za-z0-9_]*)"
        )
        # The `(?:this\s*\.\s*)?` is NOT cosmetic. `for (Channel c : this.channels)` did not
        # match at all, so the element type was never resolved and O2/O3/O4 -- the whole critical
        # set -- read 0 for an ordinary Observer. This is the resolution point for loop form 1;
        # forms 2-6 resolve through `_collection_of` in piqs/parser.py and are fixed there, in
        # the same commit. Fixing one site would have left the other five forms broken.
        #
        # NON-CAPTURING, so the two groups stay (element variable, collection field) and every
        # `.findall` unpacking below is unaffected.
        #
        # `this.` ONLY. `for (Observer o : other.observers)` still fails to match: the optional
        # group does not match `other.`, and `([A-Za-z_][A-Za-z0-9_]*)\s*\)` then cannot reach
        # the `)` past the `.`. Another object's collection is not ours -- pinned by
        # tests/test_this_receiver_loops.py::test_a_foreign_receiver_is_not_resolved_to_our_own_field.
        foreach_re = re.compile(
            r"for\s*\(\s*(?:final\s+)?[A-Za-z_][A-Za-z0-9_<>\[\]]*\s+"
            r"([A-Za-z_][A-Za-z0-9_]*)\s*:\s*(?:this\s*\.\s*)?([A-Za-z_][A-Za-z0-9_]*)\s*\)"
        )

        observer_type_names = set()
        callback_names = set()
        # (notifying type, observer type name) per notification site. This REPLACES the booleans
        # `notifies_loop` / `notifies_single`: O1 asks which type plays the abstract Subject
        # role, and a bool discards the only fact that can answer it -- WHO notified. The two
        # bools are re-derived below, so O3 is unaffected by the change of representation.
        # (notifying type, observer type name, the field notified THROUGH). The field is carried
        # because O3 must check that the collection being iterated is the same one registration
        # writes to -- see `_is_maintained`.
        loop_notifications: list[tuple[JavaType, str, str]] = []
        single_notifications: list[tuple[JavaType, str, str]] = []

        def _is_maintained(holder: JavaType, observer_name: str, field_name: str) -> bool:
            """Does `holder` let observers REGISTER into `field_name` at runtime?

            O3's published sentence has always been "Subject notifies all REGISTERED observers",
            and nothing in the code ever checked the registered half. Without it O3 was "a loop
            over a collection calls a method on each element", which a shopping cart totalling
            line items satisfies -- three of eleven points, critical weight, free in every
            experimental condition.

            REGISTRATION IS: a method whose parameter type is the observer type, which either
            operates on that field or assigns it. One definition covers both branches -- a
            collection is added to (`sinks.add(f)`, a call whose RECEIVER is the field), a single
            held observer is assigned (`this.sink = f`). Writing two rules would have left the
            single-observer branch gated by a rule authored only for collections.

            THE PARAMETER TYPE MUST BE THE OBSERVER TYPE, NOT THE COLLECTION. `setSinks(List<Feed>)`
            and `Station(List<Feed>)` replace the whole dependent set wholesale; no individual
            observer can subscribe or unsubscribe. The Strict General Rules require "a
            registration mechanism adds/removes observers at runtime" and name "the set and
            identity of dependents at runtime" as what varies. A list fixed at construction has
            no runtime dependent set.

            THE FIELD IDENTITY IS THE WHOLE CONTENT OF THE RULE. "Some method taking the element
            type touches some collection" passes a program that registers into `spare` and
            notifies `sinks`, where nobody who registers is ever notified. Pinned by
            o3_registration_into_a_different_collection.java.

            NO NAME IS READ. The parameter type comes from the method's own declaration and the
            field name from the holder's own field, compared to each other. Renaming moves both.
            """
            return any(
                observer_name in mm.param_types
                and (
                    any(receiver == field_name for (receiver, _name) in mm.calls)
                    or field_name in mm.assignments
                )
                for mm in holder.methods
            )

        def _is_child_traversal(holder: JavaType, method: JavaMethod, elem_name: str) -> bool:
            """A COMPOSITE walking its children, which is not a subject notifying observers.

            Both are "loop a collection of an abstract type and call a method on each element",
            so shape alone cannot separate them. The difference is WHOSE operation is being
            called:

                class Sale implements SaleComponent {          // Composite
                    List<SaleComponent> components;
                    public void print() { components.forEach(SaleComponent::print); }
                }

            `Sale` IS a `SaleComponent`, and `print` is `SaleComponent`'s own operation -- the
            type is recursing into itself, one level down. A subject is NOT one of its own
            observers, and `notifyObservers` is not part of the observer's interface: two roles,
            not one self-similar role.

            BOTH CONJUNCTS ARE REQUIRED, and the conjunction is deliberately narrower than
            either alone. Rejecting on "holder conforms to element" alone would reject a subject
            that legitimately implements its own observer interface (an event relay). Rejecting
            on "the loop method belongs to the element's API" alone would reject
            `void notify() { for (Observer o : obs) o.notify(); }`, a genuine subject whose
            notify method happens to share the callback's name. Each counter-case breaks only
            one conjunct, so the conjunction accepts both.

            NO IDENTIFIER IS READ. This compares two names TO EACH OTHER -- the loop method's
            and the element type's declared methods'. The obfuscator's rename map is name-keyed
            and consistent across files, so an override and its declaration are renamed to the
            SAME symbol and the comparison is preserved exactly. Verified, not assumed:
            `Sale.print` and `SaleComponent.print` both become `m2`, while `notifyObservers`
            becomes `m1` against `update` -> `m3`.
            """
            elem = types[elem_name]
            return self._conforms_to(holder, elem_name, types) and any(
                em.name == method.name for em in elem.methods
            )

        def _project_supertypes(t: JavaType) -> list[JavaType]:
            """Every PROJECT-DECLARED supertype of `t`, transitively, breadth-first.

            `java.util.Observable` is not in `types`, so a framework supertype never enters the
            closure. That is not a special case here -- it is what the Stage 2C framework policy
            requires, and it falls out of the closure being over project types only.
            """
            out: list[JavaType] = []
            seen = {t.name}
            stack = list(t.implements) + ([t.extends] if t.extends else [])
            while stack:
                name = stack.pop(0)
                if name in seen or name not in types:
                    continue
                seen.add(name)
                sup = types[name]
                out.append(sup)
                stack.extend(list(sup.implements) + ([sup.extends] if sup.extends else []))
            return out

        for t in class_types:
            coll_fields = {name: elem for (elem, name) in elem_field_re.findall(t.body)}
            single_obs_fields = {
                f.name: f.field_type
                for f in t.fields
                if f.field_type in types and types[f.field_type].is_abstract
            }
            for m in t.methods:
                body = m.body
                # (a) loop-based notification: for (X v : coll) { v.callback(...) }
                for (var, coll) in foreach_re.findall(body):
                    elem = coll_fields.get(coll)
                    if not elem or elem not in types:
                        continue
                    if not types[elem].is_abstract:
                        continue
                    if _is_child_traversal(t, m, elem):
                        continue
                    calls = re.findall(r"\b" + re.escape(var) + r"\.([A-Za-z_][A-Za-z0-9_]*)\s*\(", body)
                    if calls:
                        observer_type_names.add(elem)
                        callback_names.update(calls)
                        loop_notifications.append((t, elem, coll))
                # (a2) Phase 2 step 3: loop forms the enhanced-for regex above cannot express.
                # The parser reports (collection, callback); the element type is resolved HERE,
                # from the same `coll_fields` the enhanced-for branch uses, so no new way of
                # identifying a collection is introduced.
                for (coll, cb, qual) in m.traversals:
                    elem = coll_fields.get(coll)
                    if not elem or elem not in types:
                        continue
                    # A method reference is a notification only when its qualifier NAMES the
                    # element type. `observers.forEach(logger::record)` passes each observer as an
                    # ARGUMENT to something else -- the loopN2 failure mode in method-reference
                    # clothes. Exact match, deliberately: a qualifier naming a SUPERTYPE of the
                    # element is legal Java and is recorded as a known limitation rather than
                    # accepted, because narrower is safe where the corpus cannot decide.
                    if qual is not None and qual != elem:
                        continue
                    if not types[elem].is_abstract:
                        continue
                    if _is_child_traversal(t, m, elem):
                        continue
                    observer_type_names.add(elem)
                    callback_names.add(cb)
                    loop_notifications.append((t, elem, coll))
                # (b) single held observer of an abstract type that has a concrete impl
                for fname, ftype in single_obs_fields.items():
                    has_impl = any(
                        (not c.is_abstract) and c.kind == "class"
                        and (c.extends == ftype or ftype in c.implements)
                        for c in class_types
                    )
                    if not has_impl:
                        continue
                    calls = re.findall(r"\b" + re.escape(fname) + r"\.([A-Za-z_][A-Za-z0-9_]*)\s*\(", body)
                    if calls:
                        observer_type_names.add(ftype)
                        callback_names.update(calls)
                        single_notifications.append((t, ftype, fname))

        # Re-derived from the notification sites, so every predicate below that used to read
        # these bools is bit-identical unless a notification was actually added or removed.
        notifies_loop = bool(loop_notifications)
        notifies_single = bool(single_notifications)

        # The REGISTERED subset -- notification sites whose field is also the one observers
        # register into. This is O3; `notifies_observers` above stays the raw "does it notify at
        # all", which is honest evidence and is what keeps the two claims distinguishable in the
        # predicate trace: a constructor-injected subject notifies but registers nobody.
        registered_notifications = [
            (holder, observer_name, field_name)
            for (holder, observer_name, field_name) in loop_notifications + single_notifications
            if _is_maintained(holder, observer_name, field_name)
        ]

        observer_type_objs = [types[n] for n in observer_type_names if n in types]
        # Fix J (framework-inheritance policy): the observer role is whatever the source
        # structurally declares. A class that merely `implements Observer` inherits the role
        # from the framework and no longer contributes one here.
        observer_names = set(observer_type_names)

        # THE SUBJECT ROLE, STRUCTURALLY. Stage 3.
        #
        # This used to select any type declaring a method whose name was in a hardcoded set --
        # {attach, detach, notifyObservers, register, remove, notify}. Same structure, different
        # names, different verdict:
        #
        #     attach / notifyObservers   ->  O1 = 1
        #     subscribe / broadcast      ->  O1 = 0
        #
        # which is precisely the artefact this instrument exists to avoid: under the unnamed
        # condition a model invents its own vocabulary, and a name-matching checker marks it
        # down for a naming reason that looks exactly like the paper's finding.
        #
        # It also admitted the WRONG ROLE. In SWS/Copilot the only abstract name-match was
        # `TransactionObserver`, the OBSERVER interface, admitted as a SUBJECT because its
        # callback happens to be named `notify`. The actual subject, `Wallet`, is concrete with
        # no supertype -- so O1 = 1 was reported for a program that has no abstract subject at
        # all, and it agreed with Kim for a structurally false reason.
        #
        # THE STRUCTURAL RULE, in three parts:
        #
        #   1. the CONCRETE subject is whichever type actually notifies -- it is known now,
        #      because the notification sites carry their holder;
        #   2. the ABSTRACT subject is normally its SUPERTYPE, so search upward. The type
        #      running the loop is usually the concrete one; O1 asks for the abstract role;
        #   3. a supertype counts only if it declares THE REGISTRATION CONTRACT -- a method
        #      whose parameter type is the observer type. Otherwise any unrelated abstract
        #      supertype (a project `Printable`, `Comparable`-alike) would grant O1.
        #
        # Part 3 is name-free and it is what the corpus's two positive cases actually declare,
        # under two DIFFERENT names -- `addObserver(InventoryObserver)` in POSS/ChatGPT and
        # `registerObserver(InventoryObserver)` in POSS/Meta. Neither name is in the old
        # hardcoded set; both types matched only via `notifyObservers`. That is the fragility,
        # demonstrated by the corpus rather than argued.
        #
        # ONE CONSTRUCTION SITE, NO STRING LITERALS. Both are required of this expression: the
        # eight readers below must never disagree about what a subject is, and a literal here is
        # the defect being removed. Dict-keyed by name to dedupe while keeping insertion order,
        # so the list is deterministic.
        subject_candidates = list(
            {
                cand.name: cand
                for holder, observer_name, _field in loop_notifications + single_notifications
                for cand in (
                    holder,
                    *(
                        sup
                        for sup in _project_supertypes(holder)
                        if any(observer_name in mm.param_types for mm in sup.methods)
                    ),
                )
            }.values()
        )

        reads = any(re.search(r"\bget[A-Z][A-Za-z0-9_]*\s*\(", m.body) for t in types.values() for m in t.methods)
        modifies = any(re.search(r"\bset[A-Z][A-Za-z0-9_]*\s*\(", m.body) for t in types.values() for m in t.methods)
        modifies_collection = any(
            re.search(r"\.(add|remove|clear)\s*\(", m.body)
            for t in subject_candidates
            for m in t.methods
        )
        traverses_collection = notifies_loop
        increases = any(re.search(r"\.add\s*\(", m.body) for t in subject_candidates for m in t.methods)
        decreases = any(re.search(r"\.remove\s*\(", m.body) for t in subject_candidates for m in t.methods)

        calls_exists = any(re.search(r"\.[A-Za-z_][A-Za-z0-9_]*\s*\(", m.body) for t in types.values() for m in t.methods)

        is_register = any(m.name in {"attach", "register"} for t in subject_candidates for m in t.methods)
        is_unregister = any(m.name in {"detach", "remove"} for t in subject_candidates for m in t.methods)
        is_notify = any(m.name in {"notifyObservers", "notify"} for t in subject_candidates for m in t.methods)

        notifies_observers = notifies_loop or notifies_single

        concrete_observers = [
            t
            for t in class_types
            if any(obs == t.extends or obs in t.implements for obs in observer_names)
        ]

        # O4: every concrete observer declares the callback the subject actually invokes.
        # `callback_names` is harvested from the invocation sites themselves, never from a
        # literal set, so the callback may carry ANY name (update, ping, onLogEvent, ...).
        # Matching the observer's declared method against it is override matching by name,
        # which Java requires of an override -- not a name lookup.
        #
        # Fix K: the `or ("Observer" in t.implements)` escape is removed. It granted O4 for
        # implementing a type merely SPELLED `Observer`, with no callback in the source --
        # the same shortcut Fix J took out of o2, and the one that would have rewarded a
        # model for using the canonical name while denying an equivalent interface under
        # any other name. Framework inheritance is reported via `framework_inheritance`.
        observers_update = bool(concrete_observers) and all(
            bool(callback_names & {m.name for m in t.methods})
            for t in concrete_observers
        )

        base = {
            "isAbstract(x)": any(t.is_abstract for t in types.values()),
            "isConcrete(x)": any(t.kind == "class" and not t.is_abstract for t in types.values()),
            "reads(m,p)": reads,
            "modifies(m,p)": modifies,
            "modifiesCollection(m,c,p)": modifies_collection,
            "traversesCollection(m,c)": traverses_collection,
            "increases(m,c)": increases,
            "decreases(m,c)": decreases,
            "hasMethod(c,m)": any(t.methods for t in types.values()),
            "calls(m1,m2)": calls_exists,
            "implements(x,y)": any(t.implements for t in types.values() if t.kind == "class"),
        }

        derived = {
            "isObserver(x)": bool(observer_type_objs),
            "isUpdate(m)": bool(callback_names),
            "isSubject(x)": bool(subject_candidates),
            "isRegisterObserver(m)": is_register,
            "isUnregisterObserver(m)": is_unregister,
            "isNotify(m)": is_notify,
            "notifies(s,o)": notifies_observers,
            "updates(o,s)": observers_update,
        }

        # O1: an ABSTRACT subject exists -- a supertype of a type that actually notifies, which
        #     declares the registration contract. `any([])` is False, so a program that notifies
        #     nothing has no candidate and O1 is 0; that is the clause holding SWS/Meta at 0,
        #     where `AuditLog extends Observable` performs no traversal the source declares.
        # O2: an ABSTRACT observer exists -- a structurally-detected observer interface or
        #     abstract class.
        # Fix J (framework-inheritance policy): both clauses that credited a type for merely
        # extending Observable / implementing Observer are gone. Inheriting the structure from
        # a framework is not producing it; see docs/PROPERTY_SPEC.md, "Framework inheritance".
        # The detector survives as a flag on the result, never as a verdict.
        o1 = any(t.is_abstract for t in subject_candidates)
        o2 = any(t.is_abstract for t in observer_type_objs)
        # O3: the subject notifies its REGISTERED observers -- it iterates the same field that
        #     observers register themselves into, regardless of the callback's name (Fix A).
        #     The raw "does it notify at all" is `notifies_observers`, and it is NOT enough: a
        #     shopping cart totalling line items satisfied it, for 3 critical points of 11.
        #     O3 => O2, and O2 does NOT imply O3 -- a constructor-injected subject has an
        #     abstract observer role and no registration. That strictness is what keeps the two
        #     properties from becoming one rule under two names, which would put the same
        #     sentence twice into the generated prompt.
        o3 = bool(registered_notifications)
        # O4: concrete observers implement the callback (any name) / the JDK Observer.
        o4 = observers_update

        rows = [
            self._row(
                "O1",
                2,
                o1,
                "At least one abstract subject exists -- a notifying type has an abstract "
                "supertype declaring a method that takes the observer type.",
            ),
            self._row(
                "O2",
                3,
                o2,
                "At least one abstract observer exists -- an interface or abstract class "
                "that is the element type of a notification.",
            ),
            self._row(
                "O3",
                3,
                o3,
                "Subject notifies all registered observers -- it iterates the same "
                "observer-typed field that observers register themselves into.",
            ),
            self._row("O4", 3, o4, "Observers implement update behavior."),
        ]
        return base, derived, rows

    def _evaluate_singleton(self, types: dict[str, JavaType]) -> tuple[dict[str, bool], dict[str, bool], list[dict]]:
        classes = [t for t in types.values() if t.kind == "class"]
        enums = [t for t in types.values() if t.kind == "enum"]

        has_private_ctor = False
        has_static_instance = False
        has_instance_method = False
        has_singleton = False

        is_private = False
        is_static = False
        field_type = False
        belongs_to = False
        has_constructor = False
        accesses_field = False
        returns = False
        calls = False

        # A static instance of `cname` may be declared in the singleton class itself OR in a
        # nested static holder class (Bill Pugh idiom) -- so look across ALL classes for a
        # static field whose type is the singleton's type.
        def static_instance_of(cname: str) -> bool:
            return any(
                "static" in f.modifiers and f.field_type == cname
                for other in classes
                for f in other.fields
            )

        for c in classes:
            ctors = [m for m in c.methods if m.is_constructor]
            has_constructor = has_constructor or bool(ctors)
            priv_ctor = bool(ctors) and all("private" in m.modifiers for m in ctors)
            # Accessor: a static method returning the class's own type (a private ctor makes
            # any such method the single access point). Name-independent.
            accessor = [
                m for m in c.methods
                if not m.is_constructor and "static" in m.modifiers and m.return_type == c.name
            ]
            has_inst = static_instance_of(c.name)

            if priv_ctor:
                has_private_ctor = True
                is_private = True
            if has_inst:
                has_static_instance = True
                is_static = True
                field_type = True
                belongs_to = True
            if accessor:
                has_instance_method = True
                returns = True
                for m in accessor:
                    if any(self._mentions_within(m, f.name) for c2 in classes for f in c2.fields
                           if "static" in f.modifiers and f.field_type == c.name):
                        accesses_field = True
                    if re.search(rf"\bnew\s+{c.name}\s*\(", m.body):
                        calls = True

            # Change 1 (idiom i & ii): classic in-class field singleton AND Bill Pugh holder
            # idiom -- both require a private ctor, a static accessor returning the type, and a
            # static instance of the type (in the class or a nested static holder).
            if priv_ctor and accessor and has_inst:
                has_singleton = True

        # Change 1 (idiom iii): an enum with exactly ONE constant is a singleton -- the single
        # constant is the sole instance, and an enum's constructor is implicitly private.
        enum_singleton = any(self._enum_constant_count(e.body) == 1 for e in enums)
        if enum_singleton:
            has_singleton = True
            has_private_ctor = True
            has_static_instance = True
            has_instance_method = True
            is_private = is_static = True

        base = {
            "isPrivate(x)": is_private,
            "isStatic(x)": is_static,
            "fieldType(f,t)": field_type,
            "belongsTo(f,c)": belongs_to,
            "hasConstructor(c,m)": has_constructor,
            "accessesField(m,f)": accesses_field,
            "returns(m,t)": returns,
            "calls(m1,m2)": calls,
        }

        derived = {
            "isSingleton(x)": has_singleton,
            "hasPrivateConstructor(x)": has_private_ctor,
            "hasInstanceMethod(x)": has_instance_method,
            "hasStaticInstance(x,f)": has_static_instance,
        }

        rows = [
            self._row(
                "G1",
                3,
                has_singleton,
                "Singleton exists (classic in-class field, Bill Pugh holder, or single-constant enum).",
            )
        ]
        return base, derived, rows

    # ================================================================== #
    # Builder
    # ================================================================== #
    def _evaluate_builder(self, types: dict[str, JavaType]) -> tuple[dict[str, bool], dict[str, bool], list[dict]]:
        """Builder: a builder object assembles a distinct product through step/configuration
        methods, replacing a telescoping constructor.

        Derived roles (structural, never name-keyed):
          isBuilder(T)        -- T has configuration step methods (fluent return-this OR
                                 void build-part) over its effective (inherited) method set.
          isTerminalMethod(m) -- a concrete instance method of a builder whose return type is a
                                 type DISTINCT from the builder (the built product).
          isProduct(P)        -- the return type of a terminal method.
          isStepMethod(m)     -- fluent step (returns the builder type) OR void build-part
                                 (a void method that populates state: assigns a field or mutates
                                 a held field via a method call).

        Accepted variants (RULE 3): interface / abstract-class / concrete static-nested builder;
        builder() static factory OR public constructor; mutable OR immutable product (B5 weight
        handles the difference); fluent chaining OR Director orchestration.
        """
        classes = [t for t in types.values() if t.kind in {"class", "enum"}]

        # Per-candidate role analysis over the EFFECTIVE (inherited) method/field set, so a
        # classic GoF builder -- abstract Builder.getResult() + ConcreteBuilder void steps -- is
        # seen as one builder family.
        builder_infos = []  # (type, fluent_steps, void_steps, terminals, step_names)
        for t in classes:
            em = self._effective_methods(t, types)
            ef = self._effective_fields(t, types)
            field_names = {f.name for f in ef}

            fluent_steps, void_steps, terminals = [], [], []
            for m in em:
                if m.is_constructor:
                    continue
                # Fluent step: "return this;" chaining. The returned type is the builder's own
                # concrete type OR an ABSTRACTION the builder conforms to -- an interface/superclass
                # Builder that the concrete implementor returns `this` as (idiomatic fluent
                # *interface* builders). Keying only on the own concrete type would miss those.
                if m.return_type == t.name or (
                    m.return_type not in (None, "void")
                    and self._conforms_to(t, m.return_type, types)
                ):
                    fluent_steps.append(m)
                    continue
                # Void build-part: a void concrete method that populates the product's state
                # (assigns a field, or mutates a held field through a call on it).
                if m.return_type == "void" and m.has_body:
                    if any(self._assigns_field(m, fn) or self._delegates_to_field(m, fn) for fn in field_names):
                        void_steps.append(m)
                    continue
                # Terminal: a concrete method returning a type distinct from the builder (and not
                # void / not a constructor) -- this is the build() output, the product. It must
                # actually CONSUME the builder's configured state -- its body references a builder
                # (effective) field OR passes `this` to the product constructor. Without this, a
                # method that returns some distinct type while IGNORING every configured field
                # (a hollow builder: `build() { return new Gadget(); }` with defaults) would be
                # mistaken for a genuine terminal.
                if (
                    m.has_body
                    and m.return_type not in (None, "void", t.name)
                    and (self._mentions_within(m, "this")
                         or any(self._mentions_within(m, fn) for fn in field_names))
                ):
                    terminals.append(m)

            if fluent_steps or void_steps or terminals:
                step_names = {m.name for m in fluent_steps + void_steps}
                builder_infos.append((t, fluent_steps, void_steps, terminals, step_names))

        # A builder is a candidate that has configuration steps AND a terminal producing a
        # distinct product. (isBuilder ∧ isTerminalMethod)
        real_builders = [
            info for info in builder_infos
            if (info[1] or info[2]) and info[3]
        ]

        # B1 -- build() returns a product distinct from the builder (the enabling behaviour).
        b1 = bool(real_builders)

        # B2 -- step/configuration methods assemble the product: fluent-return-this, XOR
        # void-build-part paired with a terminal getResult(). (The two idiomatic assembly forms.)
        b2 = any(
            bool(info[1]) or (bool(info[2]) and bool(info[3]))
            for info in builder_infos
        )

        # Product = the return type of a real builder's terminal method.
        product_names = {m.return_type for info in real_builders for m in info[3]}
        builder_names = {info[0].name for info in real_builders}

        # B3 -- builder type and product type are distinct (true by construction of a terminal).
        b3 = any(
            m.return_type != info[0].name
            for info in real_builders for m in info[3]
        )

        # B4 -- telescoping-constructor avoidance / staged construction: a fluent chain, or >= 2
        # discrete configuration step methods (build the product incrementally, not in one ctor).
        b4 = any(
            bool(info[1]) or (len(info[1]) + len(info[2]) >= 2)
            for info in real_builders
        )

        # B5 -- product effectively immutable: the product type exposes no public mutator for a
        # built field. A product that is a JDK/non-project type (e.g. String) is treated as
        # immutable. (Weight 1: mutable products still score, just lower.)
        def _product_immutable(pname: str) -> bool:
            pt = types.get(pname)
            if pt is None:
                return True  # non-project product (e.g. String) -- treat as immutable
            for m in pt.methods:
                if m.is_constructor:
                    continue
                if "public" in m.modifiers and self._has_verb_prefix(m.name, "set"):
                    return False
            return True

        b5 = bool(product_names) and any(_product_immutable(p) for p in product_names)

        # B6 -- Director orchestrates XOR client drives the fluent chain. Fluent steps => the
        # client drives the chain; else look for a Director: a non-builder/non-product type whose
        # method invokes a builder's step method (callsWithin a step name).
        all_step_names = {n for info in real_builders for n in info[4]}
        fluent_exists = any(info[1] for info in real_builders)
        director_exists = False
        for t in types.values():
            if t.name in builder_names or t.name in product_names:
                continue
            for m in t.methods:
                if any(self._calls_within(m, sn) for sn in all_step_names):
                    director_exists = True
                    break
            if director_exists:
                break
        b6 = fluent_exists or director_exists

        base = {
            "isAbstract(x)": any(t.is_abstract for t in types.values()),
            "isConcrete(x)": any(t.kind == "class" and not t.is_abstract for t in types.values()),
            "hasMethod(c,m)": any(t.methods for t in types.values()),
            "returns(m,t)": any(m.return_type for t in types.values() for m in t.methods if not m.is_constructor),
            "modifies(m,f)": any(
                self._assigns_field(m, f.name)
                for t in types.values() for m in t.methods for f in t.fields
            ),
            "callsWithin(m,t)": bool(all_step_names) and director_exists,
        }

        derived = {
            "isBuilder(x)": bool(real_builders),
            "isProduct(x)": bool(product_names),
            "isTerminalMethod(m)": any(info[3] for info in real_builders),
            "isStepMethod(m)": any(info[1] or info[2] for info in builder_infos),
            "hasFluentChain(x)": fluent_exists,
            "hasDirector(x)": director_exists,
        }

        rows = [
            self._row("B1", 3, b1, "build() returns a product distinct from the builder."),
            self._row("B2", 3, b2, "Step/configuration methods assemble the product (fluent-return-this XOR void build-part + getResult)."),
            self._row("B3", 2, b3, "Builder type and product type are distinct."),
            self._row("B4", 2, b4, "Telescoping-constructor avoidance / staged construction."),
            self._row("B5", 1, b5, "Product effectively immutable (no public mutators for built fields)."),
            self._row("B6", 1, b6, "Director orchestrates XOR client drives the fluent chain."),
        ]
        return base, derived, rows

    # ================================================================== #
    # Decorator
    # ================================================================== #
    def _evaluate_decorator(self, types: dict[str, JavaType]) -> tuple[dict[str, bool], dict[str, bool], list[dict]]:
        """Decorator: a wrapper that IS-A component and HAS-A component, forwarding the
        component's operations to the wrapped instance while adding behaviour.

        KNOWN LIMITATION (RULE 4 -- encoded, NOT fixed): Decorator and Proxy are STRUCTURALLY
        IDENTICAL under static analysis -- both conform to the component interface, hold a
        component-typed reference, and delegate to it. "Adds behaviour" (Decorator) vs "controls
        access" (Proxy) is a semantic intent that is NOT statically decidable. This checker does
        NOT attempt to distinguish them: any structurally-conforming wrapper is accepted as a
        Decorator. This is disclosed in the paper's threats to validity.

        Derived roles (structural, never name-keyed):
          isComponent(C) -- an abstract type (interface or abstract class).
          isDecorator(W) -- a class that conforms to a component C AND holds a field of type C.
          wraps(W,C)     -- W's held reference is of the component type C it conforms to.
          delegatesTo(W) -- a method of W invokes an operation on the wrapped reference.
        """
        component_names = self._component_type_names(types)
        classes = [t for t in types.values() if t.kind == "class"]

        # A decorator conforms to a component C AND holds a field of THAT SAME C.
        # decorators: list of (W, conformed_components, wrapped_fields[(field, comp_type)])
        #
        # THE SAME C IS THE POINT, AND IT WAS NOT ENFORCED UNTIL NOW. `conformed` and the field
        # list used to be computed independently and never required to intersect, so a textbook
        # object adapter -- conforms to `Target`, holds a `Source` -- satisfied the critical set
        # {D2, D3} and was recognised as a Decorator (PIQS 53.33, "Moderate"). The same-type
        # requirement existed only in D1 and D4, both weight 2 and NON-CRITICAL, so they flagged
        # the interface conversion without affecting recognition. See
        # tests/fixtures_parser/object_adapter_not_a_decorator.java and PROPERTY_SPEC.md
        # ("a conflict-pair separator must be load-bearing for recognition").
        #
        # THE FILTER IS ON THE FIELD LIST, NOT ONLY ON ADMISSION. Gating admission alone leaves
        # every component-typed field in `wrapped_fields`, and D3/D4/D6 all read that list -- so
        # a class conforming to C, holding both a C and an unrelated abstract D, and forwarding
        # only to D would still score D3=1: recognised while never forwarding to what it wraps.
        # Pinned by tests/fixtures_parser/decorator_delegates_to_unrelated_component.java, the
        # only fixture where the two forms of the rule disagree.
        decorators = []
        for w in classes:
            conformed = {c for c in component_names if self._conforms_to(w, c, types)}
            if not conformed:
                continue
            # EFFECTIVE fields, not own fields. In the canonical GoF shape the abstract base
            # declares the component reference and the concrete decorators extend it, so a
            # concrete decorator has NO component-typed field of its own -- and reading `w.fields`
            # meant it was never a decorator candidate at all. Only the base was ever judged, and
            # every property was an `any(...)` over the candidate list, so one compliant base
            # carried the whole program: a subclass forwarding NOTHING scored a perfect four
            # (tests/fixtures_parser/decorator_subclass_forwards_nothing.java).
            #
            # This matters in one direction, which is why it is fixed rather than documented. The
            # abstract-base shape is what a model reproduces from memory under condition N; under
            # O it works from rule sentences and is likelier to write one flat class, which IS
            # examined and CAN fail. Same quality of code, higher score in the shape N produces --
            # inflating C1 = N - O, the headline result. See docs/PROPERTY_SPEC.md.
            wrapped_fields = [
                (f, f.field_type)
                for f in self._effective_fields(w, types)
                if f.field_type in conformed
            ]
            if wrapped_fields:
                decorators.append((w, conformed, wrapped_fields))

        # D2 -- decorator holds a component-typed reference (composition). CRITICAL.
        d2 = bool(decorators)

        # D3 -- decorator delegates to the wrapped reference in its component methods. CRITICAL.
        # WHEN DOES `super.m()` COUNT AS DELEGATION? Only when the wrapper forwards THROUGH a base
        # that actually holds the component -- i.e. when a project-defined ancestor is itself a
        # decorator candidate. This is the STRICT reading, and it was chosen over "accept any
        # `super` call" for two reasons that agree:
        #
        #   * On the merits: `super.m()` on a class whose base holds nothing forwards to something
        #     that wraps nothing. tests/fixtures_parser/super_call_base_holds_nothing.java is that
        #     program -- `Leaky extends Plain implements Spout`, declares a `Spout`, forwards with
        #     `super.emit()`, and `Plain` holds nothing. Strict scores it D3=0; loose scores it 1.
        #   * On the guard: the loose rule re-opens the hole F1b closed, by a different route.
        #     `field_named_super.java` declares a `Duct`, has NO `extends`, and calls
        #     `super.write()`. Loose scores it D3=1 -- exactly the verdict F1b removed. One fix
        #     would have undone the other.
        #
        # Walks `extends` only, matching `_effective_fields` and `_effective_methods`: an
        # interface cannot hold a field, so it can never be the base a wrapper forwards through.
        candidate_names = {w.name for (w, _c, _wf) in decorators}

        def _forwards_through_base(w) -> bool:
            cur, seen = w, {w.name}
            while cur.extends and cur.extends in types and cur.extends not in seen:
                parent = types[cur.extends]
                if parent.name in candidate_names:
                    return True
                seen.add(parent.name)
                cur = parent
            return False

        # `all`, NOT `any` -- EVERY candidate must forward. With admission fixed, `any` would
        # still let one compliant base carry a non-compliant subclass, so the two changes only
        # work together.
        #
        # `bool(decorators) and ...` IS NOT OPTIONAL: `all([])` is True in Python, so a program
        # containing no decorator at all would score D3=1 and D6=1. Measured against the unguarded
        # build: t5_object_adapter_rejected_as_decorator__FAIL and
        # decorator_plain_inheritance_no_ref__FAIL both go
        #
        #     D2 0  D3 1  D4 0  D6 1     PSR 50.0  CPC 44.44  PIQS 0 -> 47.78
        #
        # D4 is 0 because it stays `any`, and `any([])` is False -- so TWO rules are falsely
        # satisfied here, not three. Their LABELS survive, because recognition is D2 AND D3 and
        # D2=0 -- but the paper reports per-rule verdicts, not labels, and two falsely satisfied
        # rules on a program with no decorator is worse than the defect being fixed.
        #
        # THIS FIGURE WAS FIRST RECORDED AS 71.67, AND THE DIFFERENCE IS KEPT ON RECORD RATHER
        # THAN DELETED, because it says WHICH DESIGN was measured. 71.67 is the unguarded build
        # with D4 ALSO switched to `all` (D2 0 D3 1 D4 1 D6 1, PSR 75.0, CPC 66.67) -- both
        # numbers verified by building both variants. A metric quoted without its design is the
        # kind of number that propagates.
        #
        # Pinned by tests/test_decorator_field_scope_fixed.py.
        d3 = bool(decorators) and all(
            any(
                self._delegates_to_field(m, f.name, _forwards_through_base(w))
                for m in w.methods
                for (f, _c) in wrapped_fields
            )
            for (w, _conf, wrapped_fields) in decorators
        )

        # D1 IS GONE. It read "decorator conforms to the SAME component type it wraps", which
        # became the admission test itself when the same-component rule landed (e2acb66):
        # `wrapped_fields` contains only conformed types, so `any(ctype in conformed ...)` ranged
        # over a list built by filtering on exactly the predicate it tested. `D1 == D2` for every
        # program, by construction -- no Java program could separate them.
        #
        # THE REASON FOR REMOVING IT IS PROMPT GENERATION, NOT PSR. The experiment emits one
        # sentence per rule to build conditions O and P, so a duplicated rule is a duplicated
        # sentence in the prompt and contaminates the conditions directly. The PSR/CPC inflation
        # is real but secondary, and it is not sufficient on its own to argue the property back.
        # See PROPERTY_SPEC.md; pinned by
        # tests/test_decorator_property_independence.py::test_decorator_property_set_is_exactly_the_surviving_ids

        # D4 -- transparent enhancement, no interface conversion (distinguishes from Adapter):
        # the decorator exposes the wrapped component's whole operation set (its method names are
        # a subset of the decorator's effective methods) -- calls pass straight through, no
        # conversion to a different interface. (An Adapter would expose a DIFFERENT interface.)
        def _transparent(w, wrapped_fields):
            wnames = {m.name for m in self._effective_methods(w, types) if not m.is_constructor}
            for (_f, ctype) in wrapped_fields:
                comp = types.get(ctype)
                if comp is None:
                    continue
                comp_ops = {m.name for m in comp.methods if not m.is_constructor}
                if comp_ops and comp_ops <= wnames:
                    return True
            return False

        # D4 STAYS `any`, DELIBERATELY, while D3 and D6 became `all`. It asks about the EXPOSED API
        # OF THE TYPE -- "does this wrapper present the component's whole operation set, or does it
        # convert to a different interface?" -- and not about per-class behaviour. Whether one
        # subclass re-declares every operation is not the question; whether the decorator family
        # exposes the component's interface is. D3 and D6 ask behavioural questions ("does it
        # forward?"), which every candidate must answer for itself.
        #
        # `any([])` is False, so the empty-candidate case needs no guard here -- unlike D3 and D6,
        # where `all([])` is vacuously True.
        #
        # Revisit only if the battery objects. It does not today.
        d4 = any(_transparent(w, wf) for (w, _conf, wf) in decorators)

        # D5 IS GONE. It read "abstract decorator base / recursive composability", and was
        # computed as `abstract_decorator_base or d2`. That is a tautology by construction, and
        # the `or` is where it died: `abstract_decorator_base` is an `any(...)` over the SAME list
        # that decides d2, so
        #
        #     decorators empty     -> d2 False, and any() over empty is False  -> D5 False
        #     decorators non-empty -> d2 True                                  -> D5 True
        #
        # D5 == D2 for every program. The accept-a-collapsed-single-decorator decision (RULE 3)
        # that the `or d2` encoded is not lost: it lives in D2's admission rule, which never
        # required an abstract base in the first place.
        #
        # THE REASON FOR REMOVING IT IS PROMPT GENERATION, NOT PSR -- see the D1 note above and
        # PROPERTY_SPEC.md. `abstract_decorator_base` is KEPT: it still feeds the
        # `hasAbstractDecoratorBase(x)` derived predicate, which is descriptive output, and D6's
        # `not m.has_body` clause exists because of the shape it identifies.
        abstract_decorator_base = any(w.is_abstract for (w, _c, _wf) in decorators)

        # D6 -- full/transparent delegation (NON-CRITICAL diagnostic, weight 1). D3 (critical)
        # only requires that AT LEAST ONE component method delegates -- this is deliberate:
        # a legitimate method-suppressing decorator (a read-only view whose mutators throw)
        # forwards some operations and not others, and must still be accepted. D6 adds VISIBILITY
        # without changing recognition: it is satisfied only when the decorator forwards EVERY
        # component operation it implements to the wrapped reference. A partial-delegation wrapper
        # (delegates some methods, hard-codes others) keeps D2=D3=1 (still recognised) but D6=0,
        # flagging the incomplete forwarding. Recognition stays keyed to the critical {D2,D3} set.
        def _fully_delegates(w, wrapped_fields):
            # Consider only the wrapper's IMPLEMENTED operations. D6 asks whether every component
            # operation the wrapper implements forwards to the wrapped reference, so a method with
            # no implementation is not in scope: an ABSTRACT decorator base may leave part of the
            # component API abstract for its concrete decorators to supply (D5's
            # abstract_decorator_base), and those declarations neither forward nor fail to forward.
            #
            # This guard was originally written to skip the bodyless pseudo-methods the signature
            # regex harvested from call expressions. That reason is gone with the regex, but the
            # rule is not: dropping it scores an abstract decorator base with one abstract
            # component method as D6=0 (PIQS 100 -> 86.67 on such a program).
            #
            # DO NOT DELETE THE `not m.has_body` CLAUSE BELOW. No file in fixtures/ exercises it,
            # so removing it passes all four suites while silently changing behaviour. It is
            # pinned by tests/test_decorator_d6_abstract_base.py against
            # tests/fixtures_parser/abstract_decorator_base.java, which is the only thing that
            # will catch the deletion.
            w_ops = {}
            for m in w.methods:
                if m.is_constructor or not m.has_body:
                    continue
                w_ops.setdefault(m.name, m)
            for (f, ctype) in wrapped_fields:
                comp = types.get(ctype)
                if comp is None:
                    continue
                comp_ops = {m.name for m in comp.methods if not m.is_constructor}
                implemented = [op for op in comp_ops if op in w_ops]
                if implemented and all(
                    self._delegates_to_field(w_ops[op], f.name, _forwards_through_base(w))
                    for op in implemented
                ):
                    return True
            return False

        d6 = bool(decorators) and all(_fully_delegates(w, wf) for (w, _conf, wf) in decorators)

        base = {
            "isAbstract(x)": bool(component_names),
            "isConcrete(x)": any(t.kind == "class" and not t.is_abstract for t in types.values()),
            "hasMethod(c,m)": any(t.methods for t in types.values()),
            "implements(x,y)": any(t.implements for t in classes),
            "extends(x,y)": any(t.extends for t in classes),
            "fieldOfType(c,t)": any(
                self._field_of_type(w, c) for w in classes for c in component_names
            ),
            "callsWithin(m,t)": d3,
        }

        derived = {
            "isComponent(x)": bool(component_names),
            "isDecorator(x)": bool(decorators),
            # The `wraps(W,C)` ROLE survives the removal of the D1 property: it is enforced at
            # admission now, so it holds exactly when a decorator candidate exists.
            #
            # WHY IT IS KEPT. The derived predicates are the published EVIDENCE TRACE -- the
            # record of which structural roles were found, reported alongside the score rather
            # than feeding it. Stage 5 exists to make that trace structural instead of name-based,
            # so the keys are its subject matter. Dropping a reported key is a separate change
            # from dropping a scored property, and it belongs to Stage 5.
            #
            # A PREVIOUS VERSION OF THIS COMMENT SAID "compare.py reads that dict". IT DOES NOT.
            # Nothing in the repository reads `derived_predicates` or `base_predicates`:
            # `run_scorer.py` copies both into results/kim_replication_raw.json and never reads
            # them back, and compare.py reads only psr/cpc/piqs/properties/satisfaction/pattern/
            # case_study/llm. The decision to keep the key stands; the reason given for it was
            # wrong, and a false "X depends on this" is the kind of note that makes a later
            # session treat dead weight as load-bearing.
            #
            # FOR STAGE 5, NOT FOR NOW: `wraps(d,c)` is `bool(decorators)`, which is exactly D2.
            # The trace now carries a key definitionally identical to a scored verdict -- the D1
            # shape again, moved out of the score and into the evidence. Recorded in STATE.md.
            "wraps(d,c)": bool(decorators),
            "delegatesTo(d,c)": d3,
            "isTransparent(d)": d4,
            "hasAbstractDecoratorBase(x)": abstract_decorator_base,
            "fullyDelegates(d)": d6,
        }

        rows = [
            self._row("D2", 3, d2, "Decorator holds a reference typed as a component it itself conforms to (composition)."),
            self._row("D3", 3, d3, "Decorator delegates to the wrapped reference in its component methods."),
            self._row("D4", 2, d4, "Transparent enhancement -- no interface conversion (distinguishes from Adapter; NOT from Proxy)."),
            self._row("D6", 1, d6, "Full delegation -- every implemented component operation forwards to the wrapped reference (non-critical diagnostic; partial delegation still recognised)."),
        ]
        return base, derived, rows

    # ================================================================== #
    # Template Method
    # ================================================================== #
    def _evaluate_template_method(self, types: dict[str, JavaType]) -> tuple[dict[str, bool], dict[str, bool], list[dict]]:
        """Template Method: an abstract type fixes an algorithm skeleton in a concrete method
        that calls primitive/hook operations deferred to subclasses (inversion of control).

        Derived roles (structural, never name-keyed):
          isAbstractClassType(A) -- an abstract type (abstract class or interface).
          isTemplateMethod(m)    -- a CONCRETE method of A that invokes >=1 deferred operation.
          isPrimitiveOp(m)       -- an abstract method of A (no body) implemented by subclasses.
          isHook(m)              -- a concrete overridable method of A that a subclass overrides
                                    and the template invokes (a default-body extension point).
        """
        abstract_types = [t for t in types.values() if t.is_abstract]
        concrete_classes = [t for t in types.values() if t.kind == "class" and not t.is_abstract]

        t1 = t2 = t3 = t4 = t5 = False
        any_primitive = any_template = any_hook = False

        for a in abstract_types:
            concrete_methods = [m for m in a.methods if m.has_body and not m.is_constructor]
            # An abstract primitive is a bodyless, non-constructor method: a step the abstract type
            # declares and defers to its subclasses.
            abstract_methods = [
                m for m in a.methods
                if (not m.has_body) and not m.is_constructor
            ]
            primitive_names = {m.name for m in abstract_methods}

            subclasses = [
                s for s in concrete_classes
                if s.extends == a.name or a.name in s.implements or self._conforms_to(s, a.name, types)
            ]

            # Hooks: concrete, overridable methods of A that a subclass actually overrides
            # (proving they are extension points), not internal/final helpers.
            hook_names = set()
            for m in concrete_methods:
                if {"final", "private", "static"} & m.modifiers:
                    continue
                if any(
                    m.name in {sm.name for sm in s.methods if sm.has_body}
                    for s in subclasses
                ):
                    hook_names.add(m.name)

            deferred = primitive_names | hook_names

            # Template methods: concrete methods that invoke >= 1 deferred operation (IoC).
            templates = [
                m for m in concrete_methods
                if any(self._calls_within(m, op) for op in deferred)
            ]
            template_names = {m.name for m in templates}

            if concrete_methods:
                t1 = True  # a concrete skeleton method exists in an abstract type
            if abstract_methods or hook_names:
                t2 = True  # >=1 deferred primitive/hook
            if templates:
                t3 = True  # the skeleton invokes the deferred operations (inversion of control)
                any_template = True
            if any("final" in m.modifiers for m in templates):
                t4 = True  # template is final / non-overridable
            for s in subclasses:
                s_bodies = {sm.name for sm in s.methods if sm.has_body}
                if (s_bodies & deferred) and not (s_bodies & template_names):
                    t5 = True  # subclass overrides the primitives, not the template

            any_primitive = any_primitive or bool(abstract_methods)
            any_hook = any_hook or bool(hook_names)

        base = {
            "isAbstract(x)": bool(abstract_types),
            "isConcrete(x)": bool(concrete_classes),
            "hasMethod(c,m)": any(t.methods for t in types.values()),
            "overrides(m1,m2)": t5,
            "extends(x,y)": any(t.extends for t in types.values() if t.kind == "class"),
            "callsWithin(m,t)": any_template,
        }

        derived = {
            "isAbstractClassType(x)": bool(abstract_types),
            "isTemplateMethod(m)": any_template,
            "isPrimitiveOp(m)": any_primitive,
            "isHook(m)": any_hook,
        }

        rows = [
            self._row("T1", 2, t1, "A concrete template method exists in an abstract type."),
            self._row("T2", 2, t2, ">=1 abstract primitive and/or hook deferred to subclasses."),
            self._row("T3", 3, t3, "The template body invokes the primitive/hook operations (inversion of control)."),
            self._row("T4", 2, t4, "Template method is final / non-overridable (non-final accepted, lower-scoring)."),
            self._row("T5", 2, t5, "Subclass overrides the primitives, not the template method."),
        ]
        return base, derived, rows

    @staticmethod
    def _base_name(name: str) -> str:
        if not name:
            return ""
        cleaned = re.sub(r"<.*>", "", name).strip()
        cleaned = cleaned.split(".")[-1]
        cleaned = cleaned.replace("[]", "").strip()
        return cleaned

    @staticmethod
    def _row(property_id: str, weight: int, satisfaction: bool, justification: str) -> dict:
        return {
            "property_id": property_id,
            "weight": weight,
            "satisfaction": 1 if satisfaction else 0,
            "justification": justification,
        }

    @staticmethod
    def _grade(score: float) -> str:
        if score > 90:
            return "Excellent"
        if score >= 70:
            return "Good"
        if score >= 50:
            return "Moderate"
        return "Poor"
