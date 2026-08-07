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
    assert scope["inner"] == "Sink", "the field is in scope"
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
