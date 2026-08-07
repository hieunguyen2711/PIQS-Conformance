"""Synthetic generality tests for the scorer fixes (passes 2 & 3). None of these programs
come from Kim's corpus; they exercise the STRUCTURAL rules, never class/method names.

Every case carries a POLICY: line naming the documented decision that fixes its expected
value, so that when a policy changes it is mechanical to find the cases it governs. The
expectations are derived from those policies -- from docs/PROPERTY_SPEC.md and the referenced
in-code decision comments -- never read back out of the checker's current output.
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from piqs.checker import PIQSChecker  # noqa: E402

svc = PIQSChecker()


def props(pattern, files):
    r = svc.evaluate(pattern, files)
    return {x["property_id"]: x["satisfaction"] for x in r["logical_assessment"]}


results = []

# ---------------- Pass 2 (A, B, D, E) ----------------
# POLICY: Fix A -- the observer callback is detected by STRUCTURE (a subject iterating a
# collection of observers and invoking a method on each element), never by the name `update`.
# The callback here is `ping`, and the observer type is the loop's element type.
# O1 is NOT asserted: O1 needs an ABSTRACT subject, and `Bus` is a concrete class with no
# subject abstraction above it, so O1=0 is the correct reading, not a shortfall of this case.
obs_named = {
    "Watcher.java": "interface Watcher { void ping(String msg); }",
    "LogWatcher.java": "class LogWatcher implements Watcher { public void ping(String msg){ System.out.println(msg); } }",
    "Bus.java": ("import java.util.*; class Bus { private List<Watcher> ws = new ArrayList<>();"
                 " public void sub(Watcher w){ ws.add(w); }"
                 " public void fire(String m){ for (Watcher w : ws){ w.ping(m); } } }"),
}
p = props("observer", obs_named)
results.append(("A: observer callback 'ping' in notify loop -> O2/O3/O4 pass", p, p["O2"] == 1 and p["O3"] == 1 and p["O4"] == 1))

# POLICY: Framework inheritance (docs/PROPERTY_SPEC.md, "Framework inheritance"; Fix J, and
# Fix K for the O4 clause). "A type that obtains its pattern structure by extending or
# implementing a type the project does not declare is scored as NOT conforming, unless the
# source still declares the roles the pattern requires of it. Framework inheritance by itself
# never satisfies a property."
#
# `Observable` and `Observer` are both on _FRAMEWORK_SUPERTYPES and neither is declared here,
# so both supertypes are framework. Deriving each property from what THIS SOURCE declares:
#   O1 (abstract subject)   -> 0: `Sensor` is a concrete class and no abstract/interface
#                                subject type is declared anywhere in these two files.
#   O2 (abstract observer)  -> 0: no observer collection and no observer-typed field exist,
#                                so no observer type is structurally detectable. `Display`
#                                naming `Observer` as a supertype is exactly the shortcut the
#                                policy removes.
#   O3 (subject notifies)   -> 0: no collection, no held observer reference, no traversal --
#                                the notification lives entirely in java.util.Observable.
#   O4 (observers update)   -> 0: callback names are harvested from invocation sites in the
#                                source, and there are none.
# This is the spec's own worked example (`AuditLog extends java.util.Observable`, whose whole
# body is setChanged()/notifyObservers()): "There is no observer collection, no registration
# method, no callback interface and no traversal in the source."
#
# The policy's other half is that detection is RECORDED, not acted on -- so the same case
# pins that both supertypes surface under `framework_inheritance` with no roles supplied, and
# that neither is misfiled as `unknown_supertypes`. Without that half, this case would assert
# only that four numbers are zero, which a checker that had simply lost Observer support
# would also satisfy.
obs_jdk = {
    "Sensor.java": "import java.util.Observable; class Sensor extends Observable { void tick(){ setChanged(); notifyObservers(); } }",
    "Display.java": "import java.util.Observer; import java.util.Observable; class Display implements Observer { public void update(Observable o, Object arg){} }",
}
r_jdk = svc.evaluate("observer", obs_jdk)
p = {x["property_id"]: x["satisfaction"] for x in r_jdk["logical_assessment"]}
fw = {(e["type"], e["supertype"], tuple(e["pattern_roles_supplied"])) for e in r_jdk["framework_inheritance"]}
results.append((
    "B: framework inheritance alone satisfies nothing -> O1..O4 = 0, both supertypes flagged",
    {"props": p, "framework_inheritance": sorted(fw), "unknown_supertypes": r_jdk["unknown_supertypes"]},
    p["O1"] == 0 and p["O2"] == 0 and p["O3"] == 0 and p["O4"] == 0
    and fw == {("Sensor", "Observable", ()), ("Display", "Observer", ())}
    and r_jdk["unknown_supertypes"] == [],
))

# POLICY: Fix D (composite part-whole requirement, _evaluate_composite "Fix D" comment). C1/C4/C5
# require a REAL part-whole hierarchy -- a concrete implementor that HOLDS A COLLECTION of the
# component type -- not merely the presence of some interface. A Strategy family has implementors
# but no containment, so it must not read as a Composite.
no_comp = {
    "Sorter.java": "interface Sorter { void sort(int[] a); }",
    "QuickSort.java": "class QuickSort implements Sorter { public void sort(int[] a){} }",
    "BubbleSort.java": "class BubbleSort implements Sorter { public void sort(int[] a){} }",
}
p = props("composite", no_comp)
results.append(("D: Strategy-only, no part-whole -> C1/C4/C5 = 0", p, p["C1"] == 0 and p["C4"] == 0 and p["C5"] == 0))

# POLICY: Fix D, positive direction. `Dir` implements `Node` AND holds `List<Node>`, so the
# part-whole hierarchy is real: C1 (component), C4 (composite and leaf both implement it) and
# C5 (uniform API over the ACTUAL component operations) all hold.
real_comp = {
    "Node.java": "interface Node { int size(); }",
    "File.java": "class File implements Node { public int size(){ return 1; } }",
    "Dir.java": ("import java.util.*; class Dir implements Node { private List<Node> kids = new ArrayList<>();"
                 " public void add(Node n){ kids.add(n);} public int size(){ int s=0; for(Node k: kids){ s+=k.size(); } return s; } }"),
}
p = props("composite", real_comp)
results.append(("D: genuine part-whole -> C1/C4/C5 = 1", p, p["C1"] == 1 and p["C4"] == 1 and p["C5"] == 1))

# POLICY: a `throws` clause must not hide a declaration. A `throws` clause sits between the
# parameter list and the brace/semicolon; if the extractor stops short of it the declaration is
# invisible and its return type -- which is what F4 reads -- is lost. Originally a fix to
# _METHOD_SIG_RE, which had to be taught the clause explicitly; since the parser migration the
# clause is just a node in the method declaration and cannot truncate anything. Kept as a
# regression case because the property it pins is about F4's input, not about the extractor.
# F1 additionally exercises the interface-as-abstract-role rule (docs/PROPERTY_SPEC.md): an
# INTERFACE creator is accepted as the abstract creator.
throws_factory = {
    "Doc.java": "interface Doc { }",
    "PdfDoc.java": "class PdfDoc implements Doc { }",
    "DocFactory.java": "interface DocFactory { Doc create() throws Exception; }",
    "PdfFactory.java": "class PdfFactory implements DocFactory { public Doc create() throws Exception { return new PdfDoc(); } }",
}
p = props("factory-method", throws_factory)
results.append(("E: factory method with `throws` -> F1 & F4 pass", p, p["F1"] == 1 and p["F4"] == 1))

# ---------------- Pass 3 (F, G) ----------------
# POLICY: class-scope-only field extraction. Fields are declared at class scope; anything inside a
# method, constructor, initialiser or nested-type body is a local variable and must not be captured
# as a field. docs/PROPERTY_SPEC.md, "Reused scaffolding": method-local-variable-as-field is not
# reintroduced. Originally enforced by _class_scope_only, which stripped every brace-delimited
# block from the class body text before applying a field regex; since the parser migration class
# scope is read off the syntax tree (fields are the field_declaration children of the type's own
# body node) and _class_scope_only is deleted. The guarantee is unchanged.
# F: a method-local variable must NOT be extracted as a class field.
local_only = {"C.java": "class C { void run(){ Foo f = new Foo(); f.bar(); } } class Foo { void bar(){} }"}
types = svc._extract_types(local_only)
c_foo_fields = [f for f in types["C"].fields if f.field_type == "Foo"]
results.append(("F: local var not a field -> C has 0 Foo fields", {"C.fields(Foo)": len(c_foo_fields)}, len(c_foo_fields) == 0))

# F: a genuine class-scope field is still captured.
real_field = {"C.java": "class C { private Foo f; void run(){ f.bar(); } } class Foo { void bar(){} }"}
types = svc._extract_types(real_field)
c_foo_fields = [f for f in types["C"].fields if f.field_type == "Foo"]
results.append(("F: genuine class-scope field kept -> C has 1 Foo field", {"C.fields(Foo)": len(c_foo_fields)}, len(c_foo_fields) == 1))

# POLICY: Fix G (whole-token identifier matching -- _calls_within, _mentions_token,
# _has_verb_prefix). docs/PROPERTY_SPEC.md, "Reused scaffolding": substring name matching is not
# reintroduced.
#
# Phase 2 step 2: `_calls_method(body_text, name)` is gone. The call predicate is
# `_calls_within(method, name)`, reading `method.calls` precomputed from the AST, so these cases
# now go through a real parse instead of a bare string. That is the point -- the assertion is
# unchanged, only the way the body reaches the predicate.


def _body(src_body):
    """The JavaMethod for a one-method class wrapping `src_body`."""
    src = "class __G { void __m(Obj obj, int amount) {" + src_body + "} }\nclass Obj { void pay(int a){} }"
    return next(m for m in svc._extract_types({"G.java": src})["__G"].methods if m.name == "__m")


# G: identifier must match as a whole token, not a substring.
m_sub = _body("PaymentStrategy payment = PaymentFactory.get();")
g_sub = (svc._calls_within(m_sub, "pay") is False) and (svc._mentions_token(m_sub.body, "pay") is False)
results.append(("G: 'pay' does NOT match inside 'payment'/'PaymentFactory'",
                {"calls_pay": svc._calls_within(m_sub, "pay"), "mentions_pay": svc._mentions_token(m_sub.body, "pay")}, g_sub))

# G: an exact token / call DOES match; verb-prefix distinguishes addChild from address.
m_tok = _body("obj.pay(amount);")
g_tok = (svc._calls_within(m_tok, "pay")
         and svc._has_verb_prefix("addChild", "add")
         and not svc._has_verb_prefix("address", "add"))
results.append(("G: 'pay(' matches; add-prefix addChild yes / address no",
                {"calls_pay": svc._calls_within(m_tok, "pay"),
                 "addChild": svc._has_verb_prefix("addChild", "add"),
                 "address": svc._has_verb_prefix("address", "add")}, g_tok))

# POLICY: Fix A, re-asserted after Fix G (see the case-A comment above).
#
# FLAGGED -- this case is VACUOUS. It re-runs `props("observer", obs_named)` on the same fixture
# with the same assertion as case A, so it cannot fail unless case A also fails and guards nothing
# independently. It was intended to prove that Fix G's whole-token matching did not re-break Fix
# A's structurally-detected callback; to actually do that it needs a fixture where the callback
# name is a SUBSTRING of another identifier in the same body (e.g. a callback `ping` alongside a
# `pinger` local), which is the case Fix G could plausibly break. Left as-is deliberately: making
# it a real guard means adding a new fixture, which is a change to test COVERAGE rather than to a
# stale expectation, and is out of scope for this pass.
p = props("observer", obs_named)
results.append(("A-not-rebroken: 'ping' callback still detected after Fix G -> O2/O3/O4 pass",
                p, p["O2"] == 1 and p["O3"] == 1 and p["O4"] == 1))

ok = True
for label, detail, passed in results:
    ok = ok and passed
    print(("PASS" if passed else "FAIL"), "|", label)
    print("      ->", detail)

# The old summary printed "ALL FAIL (10 tests)" when ANY case failed, which reads as "10
# failures" rather than "the suite fails, over 10 cases". Report the counts instead.
failed = [label for label, _detail, passed in results if not passed]
print("\n%d/%d cases passed." % (len(results) - len(failed), len(results)))
if failed:
    print("FAILED:")
    for label in failed:
        print("  -", label)
else:
    print("ALL PASS")
sys.exit(0 if ok else 1)
