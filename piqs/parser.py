"""Tree-sitter-backed Java declaration extractor.

Phase 1 of the parser migration: this module replaces the regex declaration scanning in
`piqs.checker` -- types, methods, fields, parameters, modifiers, extends/implements. It
produces exactly the `JavaType` / `JavaMethod` / `JavaField` model the checker already
consumes, so every predicate is untouched and indifferent to which extractor built it.

Method BODIES are still handed to the predicates as text strings; the body-level helpers
(`_calls_method`, `_delegates_to_field`, ...) remain regex-based and are phase 2.

Pinned versions (the tree-sitter Python API changed between 0.21 and 0.22 -- these are fixed
in requirements.txt):

    tree-sitter      == 0.25.2   -- `Language(<PyCapsule>)`, `Parser(language)`
    tree-sitter-java == 0.23.5

Behavioural notes that matter for parity with the regex extractor it replaces:

* **Nested types are flattened.** Every declared type, at any nesting depth, becomes a
  top-level entry keyed by its simple name -- matching `_DECL_RE.finditer`, which scanned
  whole-file text and so never saw nesting at all. Singleton detection depends on this:
  `static_instance_of` searches *all* classes for a static field of the singleton's type,
  which is how the Bill Pugh holder idiom is recognised. Types are emitted in source order,
  so a duplicate simple name resolves last-wins exactly as before.

* **A nested type's members belong to the nested type only.** The regex ran its signature
  scan over the enclosing type's whole body text, which includes nested type bodies, so a
  nested class's methods were also recorded on the enclosing class. The parser knows the
  difference. (Fields were already scoped correctly, by `_class_scope_only`.)

* **No phantom methods.** The regex harvested bodyless pseudo-methods from call expressions
  inside bodies (`inner.add(s)` yielding a spurious `add`). A parser cannot: a call
  expression is not a declaration.

* **`has_body` keeps its meaning** -- True for `{ ... }`, False for a `;`-terminated
  declaration. This is the only way to tell an abstract primitive from an empty concrete
  method, and Template Method depends on it.

* **`content` and `body`** stay populated with the same text as before: `content` is the
  whole file, `body` is the text between the declaration's braces.

* **Type names are normalised by `PIQSChecker._base_name`** -- generics stripped, last dotted
  segment, `[]` dropped: `List<Observer>` -> `List`, `java.util.Map` -> `Map`,
  `String[]` -> `String`.
"""

from __future__ import annotations

import tree_sitter_java
from tree_sitter import Language, Parser

from piqs.checker import JavaField, JavaMethod, JavaType, PIQSChecker

JAVA_LANGUAGE = Language(tree_sitter_java.language())

# One parser instance is reused; tree-sitter parsers are cheap to reuse and not thread-shared
# here (the checker is single-threaded).
_PARSER = Parser(JAVA_LANGUAGE)

# The three declaration forms the regex extractor recognised (`class|interface|enum`). Records
# and annotation types are deliberately NOT added: neither appears in the corpora, and adding
# them would be a scope change rather than a migration.
_DECL_NODES = {
    "class_declaration": "class",
    "interface_declaration": "interface",
    "enum_declaration": "enum",
}

_BODY_NODES = {"class_body", "interface_body", "enum_body"}

# Children of a `modifiers` node that are annotations rather than modifier keywords.
_ANNOTATION_NODES = {"marker_annotation", "annotation"}

# Leaf nodes that count as a "whole token named in the body", for `_mentioned_tokens`.
#
# `this` and `super` are KEYWORDS, not identifiers, and they get their own node types. The regex
# this replaces was a whole-word text match, so it found them like any other word. Dropping them
# is not a cosmetic loss: Builder B1 accepts a terminal only if its body consumes the builder's
# configured state, and one of the two routes is passing `this` to the product constructor.
#
# Measured with them omitted: 4 divergence tests fail AND the BDT battery reports 3 mismatches --
# `builder_bloch_fluent_static_nested` and `t5_builder_immutable_product` both flip B1=1 -> 0,
# PIQS 100 -> 20. Kim does not move, because Kim never scores Builder. This is the one divergence
# in the set with a live verdict.
_TOKEN_NODES = {"identifier", "type_identifier", "this", "super"}

_base_name = PIQSChecker._base_name


def _text(node, src: bytes) -> str:
    return src[node.start_byte : node.end_byte].decode("utf-8", errors="ignore")


def _modifiers(node, src: bytes) -> set[str]:
    """The declared modifier keywords. Annotations are not modifiers and are dropped, which
    is also what the regex did -- its `mods` group matched keywords only."""
    mods_node = next((c for c in node.children if c.type == "modifiers"), None)
    if mods_node is None:
        return set()
    out = set()
    for child in mods_node.children:
        if child.type in _ANNOTATION_NODES:
            continue
        token = _text(child, src).strip()
        if token:
            out.add(token)
    return out


def _brace_inner(node, src: bytes) -> str:
    """The text between a body node's outer braces, exclusive -- the same span
    `_extract_block` returned."""
    if node is None:
        return ""
    text = _text(node, src)
    if text.startswith("{"):
        text = text[1:]
        if text.endswith("}"):
            text = text[:-1]
    return text


def _body_node(decl, src: bytes):
    return next((c for c in decl.children if c.type in _BODY_NODES), None)


def _params(node, src: bytes) -> tuple[list[str], list[str]]:
    """(param_types, param_names) for a method/constructor declaration.

    Types are `_base_name`-normalised, so a generic parameter (`Map<String,Integer> m`) and a
    varargs parameter (`String... args`) both reduce to their base type -- the regex split the
    parameter list on commas and so mis-parsed both.
    """
    formals = next((c for c in node.children if c.type == "formal_parameters"), None)
    if formals is None:
        return [], []
    types: list[str] = []
    names: list[str] = []
    for child in formals.named_children:
        if child.type not in {"formal_parameter", "spread_parameter"}:
            continue  # receiver_parameter (`Foo this`) is not a parameter
        type_node = child.child_by_field_name("type")
        name_node = child.child_by_field_name("name")
        if type_node is None:
            # spread_parameter has no `type` field: its children are [type, variable_declarator]
            named = [c for c in child.named_children if c.type != "modifiers"]
            type_node = named[0] if named else None
            if name_node is None and len(named) > 1:
                name_node = named[1].child_by_field_name("name") or named[1]
        types.append(_base_name(_text(type_node, src)) if type_node is not None else "")
        names.append(_text(name_node, src) if name_node is not None else "")
    return types, names


def _member_declarations(body_node):
    """Method/constructor declarations DIRECTLY in this type's body.

    An enum wraps its members in `enum_body_declarations`, which is a container rather than a
    nesting level, so it is transparent here. A nested TYPE's body is not: its members belong
    to the nested type.
    """
    for child in body_node.named_children:
        if child.type in {"method_declaration", "constructor_declaration"}:
            yield child
        elif child.type == "enum_body_declarations":
            for inner in child.named_children:
                if inner.type in {"method_declaration", "constructor_declaration"}:
                    yield inner


def _field_declarations(body_node):
    for child in body_node.named_children:
        if child.type == "field_declaration":
            yield child
        elif child.type == "enum_body_declarations":
            for inner in child.named_children:
                if inner.type == "field_declaration":
                    yield inner


def _declared_in_body(node, src: bytes) -> dict[str, str | None]:
    """{identifier: declared base type} for every name declared inside a method body.

    Phase 2, step 1. Five declaration forms carry a name into method scope:

        local_variable_declaration    List<Observer> seen = ...;   (one entry per declarator)
        enhanced_for_statement        for (Observer o : seen)
        resource                      try (Scanner s = ...)
        catch_formal_parameter        catch (IOException e)
        lambda_expression parameters  o -> ...   /   (Observer o) -> ...

    A lambda parameter with no written type maps to None: the name is in scope, the type is
    not knowable here. Callers that need the element type take it from the iterated
    collection instead.

    The walk STOPS at a nested type body. A field of a local or anonymous class, and a
    variable declared inside one, belong to that class -- not to the enclosing method. This
    is the same boundary `_member_declarations` draws for methods, and it is what keeps the
    scope table honest where the old `t.body` text matching was not: text matching cannot see
    a brace, so it absorbed nested declarations and method signatures alike.

    A lambda BODY is not such a boundary -- a lambda shares the enclosing method's scope --
    so the walk descends into it.
    """
    out: dict[str, str | None] = {}

    def add(name_node, type_node) -> None:
        if name_node is None:
            return
        name = _text(name_node, src)
        if not name:
            return
        out[name] = _base_name(_text(type_node, src)) if type_node is not None else None

    def walk(n) -> None:
        for child in n.children:
            # A nested type's body is a different scope. Do not descend.
            # This covers a local class (`class_declaration` -> `class_body`) and an anonymous
            # class (`object_creation_expression` -> `class_body`) alike.
            if child.type in _BODY_NODES:
                continue

            if child.type == "local_variable_declaration":
                type_node = child.child_by_field_name("type")
                for d in child.named_children:
                    if d.type == "variable_declarator":
                        add(d.child_by_field_name("name"), type_node)

            elif child.type == "enhanced_for_statement":
                add(child.child_by_field_name("name"), child.child_by_field_name("type"))

            elif child.type == "resource":
                add(child.child_by_field_name("name"), child.child_by_field_name("type"))

            elif child.type == "catch_formal_parameter":
                add(
                    child.child_by_field_name("name"),
                    next((c for c in child.named_children if c.type == "catch_type"), None),
                )

            elif child.type == "lambda_expression":
                params = child.child_by_field_name("parameters")
                if params is not None:
                    if params.type == "identifier":
                        # `o -> ...`: one untyped parameter.
                        add(params, None)
                    else:
                        # `formal_parameters` (typed) or `inferred_parameters` (`(a, b) -> ...`).
                        for p in params.named_children:
                            if p.type == "formal_parameter":
                                add(p.child_by_field_name("name"), p.child_by_field_name("type"))
                            elif p.type == "identifier":
                                add(p, None)

            walk(child)

    walk(node)
    return out


class JavaParseError(ValueError):
    """A method body tree-sitter could not parse cleanly.

    Raised rather than swallowed. Every body-level fact -- `locals`, `calls` -- is collected by
    walking the body's subtree, and a walk over a broken subtree returns an EMPTY result, which
    is indistinguishable from a correct "this method declares nothing and calls nothing". The
    predicates would then quietly report False and the four suites would stay green.

    tree-sitter is error-tolerant by design: it always returns a tree, inserting ERROR and
    MISSING nodes around what it could not parse. That tolerance is what makes the silence
    possible, so it has to be checked for explicitly.

    Measured: 0 of 434 method bodies across all 189 .java files in the repo produce an ERROR or
    MISSING node -- including the five Kim programs that FAIL `javac`, whose errors are semantic
    (unresolved symbols, bad types) rather than syntactic. So this never fires today. It exists
    for generated code, which is what the checker is actually for.
    """


def _assert_parsable(node, owner: str, name: str) -> None:
    if node is None:
        return
    stack = [node]
    while stack:
        n = stack.pop()
        if n.type == "ERROR" or n.is_missing:
            raise JavaParseError(
                f"{owner}.{name}: method body contains a tree-sitter "
                f"{'MISSING' if n.is_missing else 'ERROR'} node at byte {n.start_byte}. "
                "Body-level facts would be silently empty; refusing to continue."
            )
        stack.extend(n.children)


def _qualifier(node, src: bytes) -> str | None:
    """The receiver a call or assignment is written against, as the old regexes saw it.

    One rule reproduces both `_delegates_to_field` and `_assigns_field` on every shape they
    accept or reject:

        identifier    -> its own text          f.op()        -> "f"
        field_access  -> its FIELD's text      this.f.op()   -> "f"
                                               f.g.op()      -> "g"   (not "f")
        anything else -> None                  getX().op()   -> None
                                               arr[0] = x    -> None

    `f.g.op()` yielding "g" is not an accident: the regex needs `<name> . <ident> (`, and in
    `f.g.op()` the text `g.op(` satisfies it while `f.op(` does not. Returning None there would
    silently drop a real match.
    """
    if node is None:
        return None
    if node.type == "identifier":
        return _text(node, src)
    if node.type == "field_access":
        field = node.child_by_field_name("field")
        return _text(field, src) if field is not None else None
    return None


def _invocations(node, src: bytes) -> list[tuple[str | None, str]]:
    """[(receiver, method_name)] for every method call in a method body.

    Phase 2, step 2. Replaces `_calls_method`'s regex, which matched a bare identifier followed
    by '(' anywhere in the body text. Four things that regex counted as a call are not one:

      * text inside a COMMENT or STRING LITERAL. `// observers.add(o)` is not a call.
      * a CONSTRUCTOR call. `new Wallet()` matched `_calls_method(body, "Wallet")`; an
        object_creation_expression is not a method_invocation.
      * a method DECLARATION inside the body -- a local or anonymous class declaring
        `void ping(){}` matched "ping". This is the phantom-method problem phase 1 removed at
        the type level, reappearing at the body level.
      * nothing else: the walk does NOT stop at a nested type body.

    That last point is deliberate and is the one place this walk differs from
    `_declared_in_body`. A field of an anonymous class belongs to that class, so the SCOPE walk
    stops there. A call written inside an anonymous class body still runs against the enclosing
    instance's fields -- `new Runnable(){ public void run(){ inner.write(s); } }` really is the
    enclosing class delegating to `inner` -- so the CALL walk descends. Reusing the scope
    walker's boundary here would silently drop D3 for that shape.

    Collecting only `method_invocation` nodes is what keeps declarations out, descent or not,
    with no special case.
    """
    out: list[tuple[str | None, str]] = []

    def walk(n) -> None:
        if n.type == "method_invocation":
            name_node = n.child_by_field_name("name")
            if name_node is not None:
                out.append(
                    (_qualifier(n.child_by_field_name("object"), src), _text(name_node, src))
                )
        for c in n.children:
            walk(c)

    if node is not None:
        walk(node)
    return out


def _mentioned_tokens(node, src: bytes) -> set[str]:
    """Every whole token named in a method body -- identifiers AND keywords.

    Phase 2, step 2. Replaces `_mentions_token`'s regex, which matched any whole word anywhere
    in the body text. Two things follow, and they pull in opposite directions:

      * Comments and string literals are NOT tokens (divergence #4). `// this` is not a mention.

      * `this` and `super` ARE tokens, and they are KEYWORD nodes, not identifiers. A walk over
        `identifier` alone silently answers False for every `this` -- and Builder B1 reads
        exactly that: `_evaluate_builder` accepts a terminal only if its body consumes the
        builder's configured state, one route being passing `this` to the product constructor.
        Lose it and a legitimate `build()` stops being a terminal.

    Measured: 43 real call sites pass "this", 3 of them True, all in the BDT battery. Omitting
    the keyword produces exactly those 3 disagreements, in two distinct node positions --
    `new Pizza(this)` (constructor argument) and `synchronized (this)` (statement lock). A fix
    covering only one of the two is not a fix; see tests/fixtures_parser/div1_this_keyword.java.
    """
    out: set[str] = set()

    def walk(n) -> None:
        if n.type in _TOKEN_NODES:
            out.add(_text(n, src))
        for c in n.children:
            walk(c)

    if node is not None:
        walk(node)
    return out


def _build_method(decl, owner: str, src: bytes) -> JavaMethod:
    is_ctor = decl.type == "constructor_declaration"
    name_node = decl.child_by_field_name("name")
    name = _text(name_node, src) if name_node is not None else ""

    if is_ctor:
        return_type = None
    else:
        type_node = decl.child_by_field_name("type")
        return_type = _base_name(_text(type_node, src)) if type_node is not None else None
        return_type = return_type or None

    param_types, param_names = _params(decl, src)

    body_node = next((c for c in decl.children if c.type in {"block", "constructor_body"}), None)
    has_body = body_node is not None
    if has_body:
        _assert_parsable(body_node, owner, name)

    return JavaMethod(
        name=name,
        owner=owner,
        return_type=return_type,
        param_types=param_types,
        param_names=param_names,
        modifiers=_modifiers(decl, src),
        body=_brace_inner(body_node, src) if has_body else "",
        is_constructor=is_ctor,
        has_body=has_body,
        locals=_declared_in_body(body_node, src) if has_body else {},
        mentions=_mentioned_tokens(body_node, src) if has_body else set(),
        calls=_invocations(body_node, src) if has_body else [],
    )


def _build_fields(decl, src: bytes) -> list[JavaField]:
    """One JavaField per declarator, so `private int a, b;` yields two fields."""
    type_node = decl.child_by_field_name("type")
    field_type = _base_name(_text(type_node, src)) if type_node is not None else ""
    if not field_type:
        return []
    mods = _modifiers(decl, src)
    out = []
    for child in decl.named_children:
        if child.type != "variable_declarator":
            continue
        name_node = child.child_by_field_name("name")
        if name_node is None:
            continue
        out.append(
            JavaField(name=_text(name_node, src), field_type=field_type, modifiers=set(mods))
        )
    return out


def _supertypes(decl, kind: str, src: bytes) -> tuple[str | None, list[str]]:
    """(extends, implements) for a declaration.

    A class has at most one `superclass` and any number of `super_interfaces`. An INTERFACE's
    supertypes arrive under `extends_interfaces`; the first is reported as `extends` and the
    rest as `implements`. That mirrors the regex for the single-supertype case (`interface A
    extends B` gave `extends == "B"`), and it keeps `_effective_methods`, which walks `extends`
    only, seeing the same ancestry. Every predicate that reads supertypes treats the two lists
    alike, so the split is not observable beyond that.
    """
    extends_name: str | None = None
    implements: list[str] = []

    for child in decl.children:
        if child.type == "superclass":
            for t in child.named_children:
                extends_name = _base_name(_text(t, src)) or None
                break
        elif child.type == "super_interfaces":
            for tl in child.named_children:
                if tl.type == "type_list":
                    implements.extend(
                        n for n in (_base_name(_text(t, src)) for t in tl.named_children) if n
                    )
        elif child.type == "extends_interfaces":
            for tl in child.named_children:
                if tl.type == "type_list":
                    names = [n for n in (_base_name(_text(t, src)) for t in tl.named_children) if n]
                    if names:
                        extends_name = names[0]
                        implements.extend(names[1:])

    return extends_name, implements


def _iter_declarations(node):
    """Every type declaration in the tree, pre-order (= source order), at any depth.

    Pre-order matters: the regex scanned the file top to bottom and wrote `types[name] = t`,
    so on a duplicate simple name the LAST declaration won. Emitting outer-before-nested in
    source order reproduces that resolution exactly.
    """
    if node.type in _DECL_NODES:
        yield node
    for child in node.children:
        yield from _iter_declarations(child)


def extract_types(java_files: dict[str, str]) -> dict[str, JavaType]:
    """{simple_name: JavaType} across all files. Same contract as the regex extractor."""
    types: dict[str, JavaType] = {}

    for content in java_files.values():
        src = content.encode("utf-8")
        tree = _PARSER.parse(src)

        for decl in _iter_declarations(tree.root_node):
            kind = _DECL_NODES[decl.type]
            name_node = decl.child_by_field_name("name")
            if name_node is None:
                continue
            name = _text(name_node, src)

            mods = _modifiers(decl, src)
            extends_name, implements = _supertypes(decl, kind, src)
            body_node = _body_node(decl, src)

            t = JavaType(
                name=name,
                kind=kind,
                is_abstract=("abstract" in mods) or kind == "interface",
                extends=extends_name,
                implements=implements,
                content=content,
                body=_brace_inner(body_node, src),
            )

            if body_node is not None:
                t.methods = [_build_method(m, name, src) for m in _member_declarations(body_node)]
                for f in _field_declarations(body_node):
                    t.fields.extend(_build_fields(f, src))

            types[name] = t

    return types
