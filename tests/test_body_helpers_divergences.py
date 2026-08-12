"""Divergences between the retired body regexes and the tree queries that replace them.

Phase 2 step 2. Each case here is a construct where a regex over method-body TEXT and a query
over the AST necessarily disagree. Every one is a recorded decision in docs/PROPERTY_SPEC.md,
not an accident of implementation.

WHY THIS FILE HAS TO EXIST.

Measured across both corpora -- Kim's 40 scoring units and the 39 mutation-battery cases, over
422 method bodies in 184 files -- these constructs occur as follows:

    #4  comments / string literals   34,190 characters masked, 0 of 40 units moved
    #6  `new Wallet()`               0 call sites
    #7  declaration inside a body    0 call sites
    #8  anonymous / local class body 0 bodies (7 contain a lambda, which is NOT the affected
                                     shape -- a lambda body is a `block`, not a `class_body`)

So all four suites stay green whichever behaviour is chosen. The suites cannot distinguish a
correct migration from a wrong one here. This file is the only thing that can. It is the same
situation as the D6 guard, four times over -- see docs/PROPERTY_SPEC.md, "What a green suite
does not prove".

Each case lives in its own `.java` file under `tests/fixtures_parser/`, named after the
divergence it guards, so the decision in PROPERTY_SPEC.md and the program that pins it can be
found from one another.

Each test therefore asserts BOTH directions where the direction is meaningful: that the tree
rejects what the regex accepted, and that the tree still accepts the ordinary case, so a query
that simply returned False everywhere would fail too.
"""

from __future__ import annotations

import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from piqs.checker import PIQSChecker  # noqa: E402
from piqs.parser import extract_types  # noqa: E402


FIXTURES = os.path.join(os.path.dirname(os.path.abspath(__file__)), "fixtures_parser")


def fixture(name: str) -> str:
    """Load a named divergence fixture. Each is a real .java file, named after the divergence it
    guards, so a future reader can find the case from the decision and back again."""
    with open(os.path.join(FIXTURES, name), encoding="utf-8") as fh:
        return fh.read()


def method(src: str, type_name: str, method_name: str):
    return next(
        m for m in extract_types({"T.java": src})[type_name].methods if m.name == method_name
    )


def calls(src: str, type_name: str, method_name: str, target: str) -> bool:
    return PIQSChecker._calls_within(method(src, type_name, method_name), target)


# --------------------------------------------------------------------------------------- #
# Divergence #4 -- comments and string literals are not code.
# --------------------------------------------------------------------------------------- #

COMMENTS = fixture("div4_comment_and_string_literal.java")


def test_call_in_line_comment_is_not_a_call():
    assert calls(COMMENTS, "Subject", "quiet", "notifyObservers") is False


def test_call_in_block_comment_is_not_a_call():
    assert calls(COMMENTS, "Subject", "quiet", "fire") is False


def test_call_in_string_literal_is_not_a_call():
    assert calls(COMMENTS, "Subject", "quiet", "update") is False


def test_the_same_call_written_as_code_is_still_found():
    """Without this, a query returning False everywhere would pass the three tests above."""
    assert calls(COMMENTS, "Subject", "loud", "notifyObservers") is True


# --------------------------------------------------------------------------------------- #
# Divergence #6 -- a constructor call is not a method call.
# --------------------------------------------------------------------------------------- #

CONSTRUCTOR = fixture("div6_constructor_not_a_call.java")


def test_constructor_call_is_not_a_method_call():
    """`new Wallet()` matched the old regex for the name "Wallet" -- a bare identifier followed
    by '('. An object_creation_expression is not a method_invocation."""
    assert calls(CONSTRUCTOR, "Client", "build", "Wallet") is False


def test_an_ordinary_call_in_the_same_body_is_still_found():
    assert calls(CONSTRUCTOR, "Client", "build", "open") is True


# --------------------------------------------------------------------------------------- #
# Divergence #7 -- a declaration is not an invocation.
# --------------------------------------------------------------------------------------- #

DECLARATION = fixture("div7_declaration_not_an_invocation.java")


def test_local_class_method_declaration_is_not_a_call():
    """This is the phantom-method problem phase 1 removed at the type level, reappearing at the
    body level: the regex saw `ping(` in `void ping() { }`."""
    assert calls(DECLARATION, "Host", "run", "ping") is False


def test_anonymous_class_method_declaration_is_not_a_call():
    assert calls(DECLARATION, "Host", "run", "beep") is False


def test_a_real_invocation_of_a_declared_name_is_still_found():
    """`run` is BOTH declared in the anonymous class and invoked as `r.run()`. The declaration
    must not be what makes this True -- the invocation must."""
    assert calls(DECLARATION, "Host", "run", "run") is True


# --------------------------------------------------------------------------------------- #
# Divergence #8 -- descend into anonymous and local class bodies.
#
# This is the ONE place the call walk deliberately differs from the scope walk
# (`_declared_in_body`), which stops at a nested type body. A field of an anonymous class
# belongs to that class. A CALL inside one still runs against the enclosing instance.
# --------------------------------------------------------------------------------------- #

DIV8 = fixture("div8_anonymous_class_descend.java")
ANONYMOUS = LOCAL_CLASS = LAMBDA = DIV8


def test_call_inside_anonymous_class_body_is_seen():
    """Decorator D3 depends on this. Reusing the scope walker's nested-type boundary here would
    silently return False and drop delegation."""
    m = method(ANONYMOUS, "Logger", "write")
    assert ("inner", "write") in m.calls


def test_call_inside_local_class_body_is_seen():
    m = method(LOCAL_CLASS, "Logger2", "write")
    assert ("inner", "write") in m.calls


def test_call_inside_lambda_body_is_seen():
    """A lambda body is a `block`, not a `class_body`, so the step 1 boundary never stopped
    here. Pinned anyway: the two walks must not be accidentally unified later."""
    m = method(LAMBDA, "Logger3", "write")
    assert ("inner", "write") in m.calls


def test_scope_walk_still_stops_where_the_call_walk_descends():
    """The two walks differ ON PURPOSE. If someone unifies them, this fails.

    `s` is the enclosing method's parameter, so it is in scope. Nothing declared inside the
    anonymous class body is.
    """
    types = extract_types({"T.java": ANONYMOUS})
    t = types["Logger"]
    m = next(x for x in t.methods if x.name == "write")
    scope = PIQSChecker()._scope(t, m, types)
    assert "r" in m.locals, "the enclosing method's own local is in scope"
    assert scope["inner"] == "Forwardable", "the field is in scope"
    # the call walk saw into the anonymous class; the scope walk did not
    assert ("inner", "write") in m.calls


# --------------------------------------------------------------------------------------- #
# Receiver normalisation -- the uniform qualifier rule.
# --------------------------------------------------------------------------------------- #

RECEIVERS = """
class R {
    private Inner f;
    void go(R other) {
        f.op();
        this.f.op();
        other.f.op();
        getX().op();
        plain();
    }
    R getX() { return this; }
    void plain() { }
}
class Inner { void op() { } }
"""


def test_receiver_normalisation_matches_the_retired_regex():
    """identifier -> its text; field_access -> its FIELD's text; anything else -> None.

    `other.f.op()` stores "f", not "other" -- the old regex needed `<name> . <ident> (`, which
    `f.op(` satisfies and `other.op(` does not. Returning None there would drop a real match.
    """
    m = method(RECEIVERS, "R", "go")
    assert m.calls == [
        ("f", "op"),        # f.op()
        ("f", "op"),        # this.f.op()      -> field_access(this, f) -> "f"
        ("f", "op"),        # other.f.op()     -> field_access(other, f) -> "f"
        (None, "op"),       # getX().op()      -> receiver is a call, not a reference
        (None, "getX"),     # getX()           -> unqualified
        (None, "plain"),    # plain()          -> unqualified
    ]


def test_chain_and_unqualified_receivers_are_none():
    """None can never equal a field name, so chains and unqualified calls are rejected by
    comparison alone -- no special case in the predicate."""
    m = method(RECEIVERS, "R", "go")
    assert all(r is None for r, n in m.calls if n in {"getX", "plain"})


# --------------------------------------------------------------------------------------- #
# Unchanged behaviour: exact-name matching, which is what Fix G bought.
# --------------------------------------------------------------------------------------- #

PREFIX = """
class P {
    void go(Reader in) {
        in.readLine();
    }
}
class Reader { void readLine() { } }
"""


def test_exact_name_matching_survives_the_migration():
    assert calls(PREFIX, "P", "go", "readLine") is True
    assert calls(PREFIX, "P", "go", "read") is False


BODYLESS = """
interface Contract { void op(); }
"""


def test_bodyless_method_has_no_calls():
    m = method(BODYLESS, "Contract", "op")
    assert m.has_body is False
    assert m.calls == []


# --------------------------------------------------------------------------------------- #
# Divergence #1 -- `this` and `super` are KEYWORD nodes, not identifiers.
#
# The only divergence in the set with a live verdict. Builder B1 accepts a method as the
# TERMINAL only if its body consumes configured state, and one of the two ways to do that is
# passing `this` to the product constructor. A mentions set built from `identifier` nodes alone
# answers False for every `this`, so a legitimate build() stops being a terminal and B1 fails.
#
# 43 real call sites pass "this"; 3 are True, all in the BDT battery.
# --------------------------------------------------------------------------------------- #

THIS_KEYWORD = fixture("div1_this_keyword.java")


def mentions(method_name: str, token: str) -> bool:
    return PIQSChecker._mentions_within(method(THIS_KEYWORD, "Assembler", method_name), token)


def test_this_as_constructor_argument_is_mentioned():
    """`return new Loaf(this);` -- `this` in ARGUMENT position. This is the shape Builder B1
    reads to accept a terminal."""
    assert mentions("bake", "this") is True


def test_this_as_synchronized_lock_is_mentioned():
    """`synchronized (this) { ... }` -- a DIFFERENT node position from the argument case. A fix
    that special-cased only the constructor argument would pass the test above and fail this."""
    assert mentions("guarded", "this") is True


def test_this_as_field_qualifier_is_mentioned():
    """`this.size = size;`"""
    assert mentions("handOff", "this") is True


def test_super_is_mentioned():
    """`super` is a keyword node too, and the old whole-word regex matched it."""
    assert mentions("handOff", "super") is True


def test_this_in_comment_or_string_is_not_mentioned():
    """Divergence #4 applies to mentions as well as calls. The body of `quiet()` contains the
    text `this` twice -- once commented out, once inside a string literal -- and neither is a
    mention."""
    assert mentions("quiet", "this") is False


def test_method_without_this_does_not_mention_it():
    """Anti-vacuity. Without this, an implementation returning True for everything would pass
    every assertion above."""
    assert mentions("plain", "this") is False
    assert mentions("plain", "super") is False


def test_ordinary_identifiers_still_resolve():
    """The migration must not lose what the regex already did right: a plain field name is still
    a mention, and a substring is still not one."""
    assert mentions("handOff", "size") is True
    assert mentions("handOff", "siz") is False


# --------------------------------------------------------------------------------------- #
# Divergence #5 -- a chain is not delegation to a field.
#
# D3 asks whether a wrapper forwards to THE HELD REFERENCE. The retired regex required
# `<name> . <ident> (`, so a call or an array element as receiver was rejected. A
# method_invocation query is naturally wider; the uniform qualifier rule is what keeps it narrow,
# with no chain-detection branch anywhere.
#
# Zero corpus coverage: 0 of 41 real call sites have a body containing `).op(`.
# --------------------------------------------------------------------------------------- #

CHAIN = fixture("div5_chain_not_delegation.java")


def delegates(method_name: str, field_name: str) -> bool:
    return PIQSChecker._delegates_to_field(method(CHAIN, "Chained", method_name), field_name)


def test_plain_field_receiver_is_delegation():
    """Anti-vacuity: an implementation rejecting everything would pass every negative below."""
    assert delegates("direct", "f") is True


def test_this_qualified_field_receiver_is_delegation():
    assert delegates("viaThis", "f") is True


def test_call_receiver_is_not_delegation():
    """`getF().op()` -- the receiver is a call expression, not a reference. A naive query taking
    the first identifier under the object would answer True for "getF"."""
    assert delegates("throughCall", "getF") is False
    assert delegates("throughCall", "f") is False


def test_array_element_receiver_is_not_delegation():
    """`arr[0].op()` -- an element is not the array reference."""
    assert delegates("throughIndex", "arr") is False


def test_two_level_access_delegates_to_the_inner_field_only():
    """The sharp case. `f.g.op()` delegates to `g`, NOT to `f` -- the old regex needed
    `<name> . <ident> (`, which `g.op(` satisfies and `f.op(` does not. Taking the object's text
    instead of the field's would be wrong in both directions at once."""
    assert delegates("twoLevel", "g") is True
    assert delegates("twoLevel", "f") is False


# --------------------------------------------------------------------------------------- #
# Divergence #2 -- compound assignment is not an assignment (exact parity).
# Divergence #3 -- a local declaration is not an assignment to the field it shadows.
#
# Both have zero corpus coverage, so all four suites stay green whichever way they are decided.
# --------------------------------------------------------------------------------------- #

COMPOUND = fixture("div2_compound_assignment.java")
DECLARES = fixture("div3_declaration_not_assignment.java")


def assigns(src: str, type_name: str, method_name: str, field: str) -> bool:
    return PIQSChecker._assigns_field(method(src, type_name, method_name), field)


def test_simple_assignment_is_an_assignment():
    """Anti-vacuity for everything below."""
    assert assigns(COMPOUND, "Compound", "simple", "plain") is True


def test_compound_operators_are_not_assignments():
    """TEN operators are `assignment_expression` in the tree and none matched the regex. Five
    distinct ones are checked, because "we handled +=" is the half-fix that a one-operator test
    would pass."""
    for fld in ("add", "sub", "mul", "shift", "mask"):
        assert assigns(COMPOUND, "Compound", "compounds", fld) is False, fld


def test_increment_and_decrement_are_not_assignments():
    """`update_expression`, a different node type -- no operator filter needed."""
    assert assigns(COMPOUND, "Compound", "updates", "plain") is False
    assert assigns(COMPOUND, "Compound", "updates", "add") is False


def test_equality_is_not_assignment():
    """`binary_expression`. The regex blocked these with `(?!=)`."""
    assert assigns(COMPOUND, "Compound", "compare", "plain") is False
    assert assigns(COMPOUND, "Compound", "compare", "add") is False


def test_assignment_in_a_for_init_is_found():
    """`for (plain = 0; ...)` is an assignment_expression that is NOT inside an
    expression_statement. A walk restricted to expression_statement would miss it."""
    assert assigns(COMPOUND, "Compound", "loopInit", "plain") is True


def test_local_declaration_is_not_an_assignment_to_the_shadowed_field():
    """Divergence #3. `int count = 5;` is a local_variable_declaration; the field is untouched.
    Here the tree is simply right and the regex was wrong."""
    assert assigns(DECLARES, "Declares", "declaresLocal", "count") is False


def test_real_field_assignment_is_still_found():
    assert assigns(DECLARES, "Declares", "assignsField", "count") is True


def test_this_qualified_assignment_is_found():
    assert assigns(DECLARES, "Declares", "assignsViaThis", "count") is True


def test_assignment_to_a_shadowing_local_is_a_recorded_limitation():
    """NOT a correctness assertion -- a parity one. `held = another;` assigns the LOCAL, but both
    the regex and the tree report the FIELD as assigned. `m.locals` could resolve it; using it
    here would be a meaning change belonging to Step 3. See docs/PROPERTY_SPEC.md."""
    assert assigns(DECLARES, "Declares", "shadowedWrite", "held") is True
