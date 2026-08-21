"""The identifier renamer, rebuilt on tree-sitter. Same policy as `piqs.obfuscator`, new mechanism.

    from piqs.obfuscator_ts import obfuscate
    renamed = obfuscate({"Bus.java": src, "Watcher.java": src2})

Input and output are both `{filename: source}`, exactly as before. Classes and enums become
`C1, C2, ...`, interfaces `I1, I2, ...`, methods `m1, ...`, fields `f1, ...`, parameters
`p1, ...`, locals `v1, ...`, assigned once for the whole source set.

## What is unchanged

Everything about *what* gets renamed. The policy constants are IMPORTED from `piqs.obfuscator`
rather than restated -- `_KEYWORDS`, `_JDK_NAMES`, `_JDK_OVERRIDABLE`,
`_ALWAYS_PRESERVE_METHODS`, `_COMMON_JDK_MEMBERS`, `_base_type`, `_Decls`, `RenameMap` -- so
the two modules cannot drift apart on policy. If a difference shows up in
`validation/obfuscator_diff.py`, it is a difference in *reading the source*, which is the only
difference this module is allowed to have.

Three policies are load-bearing and are restated here because they are easy to "improve" into
bugs:

* **Renaming is global by name, not per declaration site.** Every occurrence of the method
  name `update` in a source set becomes the same `m3`. A parser could rename each declaration
  separately, and that would break overriding: `interface Watcher { void update(String); }`
  and `class Screen implements Watcher { public void update(String){} }` must get the SAME new
  name or the override silently detaches. Global-by-name gives that for free.

* **A member access is renamed only when its receiver is one of ours.** `kids.add(item)` where
  `kids` is a `List` is `java.util.List.add`; `folder.add(item)` where `folder` is a user type
  is ours. This is one field lookup here -- `node.child_by_field_name("object")` -- where the
  regex needed a hand-written backwards scan over masked text.

* **One unresolvable occurrence withholds the name everywhere.** Not the declaration, not any
  call site. Renaming too little breaks the code exactly as badly as renaming too much: a
  declaration `add` renamed to `m1` whose call site `folder.add(x)` was left behind no longer
  resolves. `withheld_names` records each one with its reason.

## What is different

`piqs.obfuscator` is regex-based and has two defects this module does not:

* `_LOCAL_RE` opens with `(?:^|[;{}])`, which CONSUMES the `;` ending the previous statement,
  so `finditer` has no anchor left for the next one and every second declaration in a run is
  skipped. Measured on the Kim corpus: 29 locals missed, 22 of them surviving unrenamed in the
  output. Here a local declaration is a `local_variable_declaration` node, and `int a = 1, b =
  2;` is ONE node with TWO `variable_declarator` children -- both of which are visited.

* `_METHOD_SIG_RE` matches *word word `(`*, so `new DecimalFormat("$0.00")` reads as a
  declaration named `DecimalFormat` with return type `new`, and a JDK class gets renamed to
  `m1`. Here that text is an `object_creation_expression`, which is not a declaration node, so
  the question never arises.

## Mechanism

1. **Parse.** One tree per file. `root_node.has_error` raises `JavaParseError` -- the same
   class `piqs.parser` raises, and for the same reason: tree-sitter is error-tolerant by
   design and returns a tree no matter what, so a walk over a broken subtree yields an EMPTY
   result that is indistinguishable from "this file declares nothing". An obfuscator that
   silently renames nothing would make the invariance suite pass for the wrong reason. Note
   this is STRICTER than `piqs.parser`, which checks method bodies only; renaming touches
   every byte of the file, so every byte has to have parsed.

2. **Index.** One walk per tree collecting declared types, methods, fields, parameters, locals
   and `type_of` (name -> declared base type). The table is GLOBAL and keyed by name, matching
   the rename map's own basis: a name declared with two different base types anywhere in the
   set is `ambiguous` and resolves to nothing.

3. **Decide.** Build the map, then classify every identifier occurrence and drop any name with
   an unresolvable member-access site.

4. **Rewrite.** Collect `(start_byte, end_byte, new_text)` for every identifier to change,
   sort DESCENDING by start byte, and splice. Right-to-left keeps the earlier offsets valid.
   Every byte outside a span is copied unchanged, so whitespace, comments, string literals,
   `package` and `import` lines survive byte-for-byte with no masking pass at all -- the
   `_mask`/`_unmask` round trip the regex module needs simply has no counterpart here.

## Coverage beyond the regex

Declaration forms tree-sitter sees that the regexes never matched: `enum_constant`,
`record_declaration`, try-with-resources `resource`, `spread_parameter` (`String... args`) and
untyped lambda parameters. They are collected here because a name that is never renamed was
never tested. Records, resources and spread parameters are absent from the current corpora;
enum constants appear 3 times.

Never renamed, and each verified against the tree rather than assumed: `package_declaration`
and `import_declaration` subtrees, annotation NAMES (their arguments are ordinary expressions
and are renamed), `element_value_pair` keys, `labeled_statement` labels together with their
`break`/`continue` targets, type parameters (`T` in `class Box<T>` is a type variable, not a
user class), and every keyword node -- `this` and `super` are nodes of their own type here,
not identifiers.
"""

from __future__ import annotations

import tree_sitter_java
from tree_sitter import Language, Parser

from piqs.obfuscator import (
    _ALWAYS_PRESERVE_METHODS,
    _COMMON_JDK_MEMBERS,
    _EXTERNAL,
    _JDK_NAMES,
    _JDK_OVERRIDABLE,
    _KEYWORDS,
    _SOME_USER,
    JDK,
    UNRESOLVED,
    USER,
    RenameMap,
    _base_type,
    _Decls,
)
from piqs.parser import JavaParseError

__all__ = [
    "obfuscate",
    "build_rename_map",
    "RenameMap",
    "JavaParseError",
]

JAVA_LANGUAGE = Language(tree_sitter_java.language())

# A parser instance of our own rather than `piqs.parser._PARSER`. Sharing one would couple the
# obfuscator's state to the checker's, and `piqs/parser.py` is snapshotted by `golden_facts`.
_PARSER = Parser(JAVA_LANGUAGE)

# Type declarations. `record_declaration` is included even though the corpora contain none:
# this module's contract is that a name it does not rename was never tested, and a record is a
# type whose name leaks exactly as much as a class's. `annotation_type_declaration` is NOT a
# user type -- `@interface Ann { int value(); }` declares an annotation whose members are
# reached by the compiler, not by user calls -- and its subtree is skipped outright.
_TYPE_DECL_NODES = {
    "class_declaration": "class",
    "interface_declaration": "interface",
    "enum_declaration": "enum",
    "record_declaration": "class",
}

# Subtrees that contribute no renameable identifier and no declaration.
_SKIP_SUBTREES = {
    "package_declaration",
    "import_declaration",
    "annotation_type_declaration",
    "comment",
    "line_comment",
    "block_comment",
}

# Leaf node types that carry a renameable name. `this` and `super` are keyword nodes with their
# own types and are therefore excluded automatically, as are every primitive type node
# (`integral_type`, `void_type`, `floating_point_type`, `boolean_type`).
_NAME_NODES = {"identifier", "type_identifier"}

_LABEL_PARENTS = {"labeled_statement", "break_statement", "continue_statement"}


def _text(node, src: bytes) -> str:
    return src[node.start_byte : node.end_byte].decode("utf-8", errors="ignore")


def _same(a, b) -> bool:
    """Node identity. `Node.id` is the underlying pointer and is stable for one tree."""
    return a is not None and b is not None and a.id == b.id


def parse(filename: str, source: str):
    """`(tree, src_bytes)` for one file, refusing anything that did not parse cleanly.

    See the module docstring: tree-sitter always returns a tree, so the check has to be
    explicit or a broken file renames to nothing and the suites stay green.
    """
    src = source.encode("utf-8")
    tree = _PARSER.parse(src)
    root = tree.root_node
    if root.has_error:
        bad = _first_error(root)
        where = f" at byte {bad.start_byte}" if bad is not None else ""
        raise JavaParseError(
            f"{filename}: tree-sitter reported a parse error{where}. Renaming a file that did "
            "not parse would silently leave identifiers behind; refusing to continue."
        )
    return tree, src


def _first_error(root):
    stack = [root]
    while stack:
        n = stack.pop()
        if n.type == "ERROR" or n.is_missing:
            return n
        stack.extend(n.children)
    return None


def _parse_all(java_files: dict[str, str]) -> list[tuple[str, object, bytes]]:
    """`[(filename, tree, src)]` in sorted filename order -- the order the regex module's
    `_collect` sees its inputs in, so counter assignment matches."""
    return [(fn, *parse(fn, src)) for fn, src in sorted(java_files.items())]


# --------------------------------------------------------------------------------------- #
# Indexing
# --------------------------------------------------------------------------------------- #

def _supertype_names(decl, src: bytes) -> set[str]:
    """Every type named in this declaration's `extends` / `implements` clause.

    The regex took the FIRST identifier of each comma-separated part, which drops the type
    arguments of `implements Comparable<Foo>` and keeps `Comparable`. `_base_type` does the
    same thing to a `generic_type` node's text, so the two agree.
    """
    out: set[str] = set()
    for child in decl.children:
        if child.type not in {"superclass", "super_interfaces", "extends_interfaces", "permits"}:
            continue
        for node in child.named_children:
            if node.type == "type_list":
                for t in node.named_children:
                    base = _base_type(_text(t, src))
                    if base:
                        out.add(base)
            else:
                base = _base_type(_text(node, src))
                if base:
                    out.add(base)
    return out


def _declarator_names(node):
    """The `variable_declarator` children of a field or local declaration.

    `int a = 1, b = 2;` is ONE node with TWO of them. This is the 29-locals hole in the regex
    module, and it closes here by iterating rather than by matching.
    """
    return [c for c in node.named_children if c.type == "variable_declarator"]


def _collect(parsed: list[tuple[str, object, bytes]]) -> _Decls:
    """Populate the same `_Decls` the regex module builds, from trees instead of masked text."""
    d = _Decls()

    def note(name: str, type_node, src: bytes) -> None:
        d.note_type(name, _text(type_node, src) if type_node is not None else "")

    def walk(n, src: bytes, enclosing: str | None) -> None:
        t = n.type
        if t in _SKIP_SUBTREES:
            return

        if t in _TYPE_DECL_NODES:
            name_node = n.child_by_field_name("name")
            if name_node is not None:
                name = _text(name_node, src)
                if name and name not in _KEYWORDS:
                    d.types[name] = _TYPE_DECL_NODES[t]
                    d.supertypes.setdefault(name, set()).update(_supertype_names(n, src))
                    d.methods_of.setdefault(name, set())
                    d.fields_of.setdefault(name, {})
                    enclosing = name

        elif t == "field_declaration":
            type_node = n.child_by_field_name("type")
            base = _base_type(_text(type_node, src)) if type_node is not None else ""
            own = d.fields_of.setdefault(enclosing, {}) if enclosing else {}
            for dec in _declarator_names(n):
                nm = dec.child_by_field_name("name")
                if nm is None:
                    continue
                fname = _text(nm, src)
                if not fname or fname in _KEYWORDS:
                    continue
                d.fields.add(fname)
                note(fname, type_node, src)
                if base and base not in _KEYWORDS:
                    prev = own.get(fname)
                    own[fname] = base if prev in (None, base) else ""

        elif t == "enum_constant":
            nm = n.child_by_field_name("name")
            if nm is not None:
                name = _text(nm, src)
                if name and name not in _KEYWORDS:
                    d.fields.add(name)
                    # An enum constant's type IS its enum, which makes `Colour.RED.shade()`
                    # resolvable. The regex never saw enum constants at all.
                    if enclosing:
                        d.note_type(name, enclosing)

        elif t == "method_declaration":
            nm = n.child_by_field_name("name")
            if nm is not None:
                name = _text(nm, src)
                if name and name not in _KEYWORDS:
                    d.methods.add(name)
                    if enclosing:
                        d.methods_of.setdefault(enclosing, set()).add(name)

        # constructor_declaration deliberately contributes NO method name. Its `name` field
        # must equal the enclosing class's, and it is renamed by following that class.

        elif t in {"formal_parameter", "catch_formal_parameter"}:
            nm = n.child_by_field_name("name")
            if nm is not None:
                name = _text(nm, src)
                if name and name not in _KEYWORDS:
                    # A catch parameter is method-scope like a local; the regex's `_CATCH_RE`
                    # put it in `locals` and that is preserved here.
                    (d.locals if t == "catch_formal_parameter" else d.params).add(name)
                    type_node = n.child_by_field_name("type")
                    if type_node is None:
                        # catch has no `type` field: the declared type is a `catch_type` node,
                        # whose text is `A | B` for a multi-catch. `_base_type` returns "" for
                        # that, which is the right answer -- there is no single type.
                        type_node = next(
                            (c for c in n.named_children if c.type == "catch_type"), None
                        )
                    note(name, type_node, src)

        elif t == "spread_parameter":
            # `String... args` has no `name` field: its children are [type, declarator].
            named = [c for c in n.named_children if c.type != "modifiers"]
            type_node = named[0] if named else None
            for dec in _declarator_names(n):
                nm = dec.child_by_field_name("name")
                if nm is not None:
                    name = _text(nm, src)
                    if name and name not in _KEYWORDS:
                        d.params.add(name)
                        note(name, type_node, src)

        elif t == "local_variable_declaration":
            type_node = n.child_by_field_name("type")
            for dec in _declarator_names(n):
                nm = dec.child_by_field_name("name")
                if nm is None:
                    continue
                name = _text(nm, src)
                if name and name not in _KEYWORDS:
                    d.locals.add(name)
                    note(name, type_node, src)

        elif t in {"enhanced_for_statement", "resource"}:
            nm = n.child_by_field_name("name")
            if nm is not None:
                name = _text(nm, src)
                if name and name not in _KEYWORDS:
                    d.locals.add(name)
                    note(name, n.child_by_field_name("type"), src)

        elif t == "lambda_expression":
            params = n.child_by_field_name("parameters")
            if params is not None:
                for nm, type_node in _lambda_params(params):
                    name = _text(nm, src)
                    if name and name not in _KEYWORDS:
                        d.params.add(name)
                        note(name, type_node, src)

        for c in n.children:
            walk(c, src, enclosing)

    for _, tree, src in parsed:
        walk(tree.root_node, src, None)

    return d


def _lambda_params(params):
    """`[(name_node, type_node|None)]` for a lambda's parameter list.

    Three shapes: `o -> ...` (a bare `identifier`), `(Observer o) -> ...` (`formal_parameters`)
    and `(a, b) -> ...` (`inferred_parameters`, untyped). An untyped parameter yields a None
    type, which `note_type` drops -- the name is in scope, the type is not knowable here.
    """
    if params.type == "identifier":
        return [(params, None)]
    out = []
    for p in params.named_children:
        if p.type == "formal_parameter":
            nm = p.child_by_field_name("name")
            if nm is not None:
                out.append((nm, p.child_by_field_name("type")))
        elif p.type == "identifier":
            out.append((p, None))
    return out


# --------------------------------------------------------------------------------------- #
# Receiver resolution
#
# `kids.add(n)` and `folder.add(n)` are opposite answers to a renamer, and what separates them
# is the declared type of the receiver. The regex module reconstructed the receiver by walking
# backwards over masked text; here the receiver IS a field of the node.
# --------------------------------------------------------------------------------------- #

class _Receivers:
    """Answers one question per site: is the thing the member is reached through one of ours?

    Resolution is global and by name, matching how the rename map itself is built. `_of_name`,
    `_of_field` and `_of_super` reproduce `piqs.obfuscator._Receivers` exactly; only `resolve`
    is new, and it replaces a text scan with a walk over the receiver's own subtree.
    """

    def __init__(self, decls: _Decls) -> None:
        self.d = decls
        self.declared = decls.fields | decls.params | decls.locals

    # -- the three name lookups, identical to the regex module -------------------------- #

    def _of_name(self, name: str) -> str | None:
        if name in self.d.ambiguous:
            return None
        base = self.d.type_of.get(name)
        if base is not None:
            return base if base in self.d.types else _EXTERNAL
        if name in self.d.types:
            return name  # a static call on one of our types
        if name in _JDK_NAMES:
            return _EXTERNAL  # a static call on a JDK type
        return None

    def _of_field(self, owner: str, fname: str) -> str | None:
        seen: set[str] = set()
        stack = [owner]
        while stack:
            cls = stack.pop()
            if cls in seen:
                continue
            seen.add(cls)
            base = self.d.fields_of.get(cls, {}).get(fname)
            if base == "":  # declared twice in this class with two types
                return None
            if base:
                return base if base in self.d.types else _EXTERNAL
            stack.extend(s for s in self.d.supertypes.get(cls, ()) if s in self.d.types)
        return None

    def _of_super(self, enclosing: str | None) -> str | None:
        if enclosing is None:
            return None
        supers = self.d.supertypes.get(enclosing) or set()
        if not supers:
            return _EXTERNAL  # implicit java.lang.Object
        user = {s for s in supers if s in self.d.types}
        if not user:
            return _EXTERNAL
        if len(user) != len(supers):
            return None  # `extends Ours implements Theirs`: which one?
        return next(iter(user)) if len(user) == 1 else _SOME_USER

    # -- resolving a receiver NODE ------------------------------------------------------ #

    def resolve(self, node, src: bytes, enclosing: str | None, depth: int = 0):
        """The type a receiver expression has: a user type name, `_EXTERNAL`, `_SOME_USER`, or
        None when it cannot be told.

        None is not "assume JDK". It withholds the name everywhere, which is the only response
        that always emits valid Java -- see `_withhold_unresolvable`.
        """
        if node is None or depth > 16:
            return None
        t = node.type

        if t == "identifier":
            return self._of_name(_text(node, src))
        if t == "type_identifier":
            return self._of_name(_text(node, src))
        if t == "this":
            return enclosing
        if t == "super":
            return self._of_super(enclosing)
        if t in {"string_literal", "character_literal"}:
            return _EXTERNAL  # a literal receiver is java.lang.String / Character
        if t == "field_access":
            obj = node.child_by_field_name("object")
            fld = node.child_by_field_name("field")
            if fld is not None and fld.type == "this":
                # `Outer.this` -- the ENCLOSING INSTANCE, whose type is named by `obj`.
                return self._as_type(obj, src)
            cur = self.resolve(obj, src, enclosing, depth + 1)
            if cur is None or cur == _SOME_USER or cur == _EXTERNAL:
                return _EXTERNAL if cur == _EXTERNAL else None
            if fld is None:
                return None
            return self._of_field(cur, _text(fld, src))
        if t in {"scoped_identifier", "scoped_type_identifier"}:
            # `com.demo.Foo` / `Node.Builder`: the rightmost segment names the type.
            last = node.child_by_field_name("name")
            if last is None:
                kids = [c for c in node.children if c.type in _NAME_NODES]
                last = kids[-1] if kids else None
            return self._of_name(_text(last, src)) if last is not None else None
        if t == "generic_type":
            base = next((c for c in node.children if c.type in _NAME_NODES
                         or c.type == "scoped_type_identifier"), None)
            return self.resolve(base, src, enclosing, depth + 1)

        # A call, an index, a cast, a parenthesised expression, `new Foo()`. The regex module
        # answers UNRESOLVED for all of these ("receiver is an expression, not a name") and
        # that is preserved: narrowing it would be a policy change, not a mechanism change.
        return None

    def _as_type(self, node, src: bytes) -> str | None:
        """`node` read as a TYPE name rather than as a value -- the `Outer` of `Outer.this`."""
        if node is None:
            return None
        name = _text(node, src).split(".")[-1]
        if name in self.d.types:
            return name
        return _EXTERNAL if name in _JDK_NAMES else None

    # -- the verdict for one identifier occurrence -------------------------------------- #

    def verdict(self, node, src: bytes, enclosing: str | None) -> tuple[str, str]:
        """`(USER | JDK | UNRESOLVED, reason)` for a renameable identifier occurrence."""
        receiver = _member_receiver(node)
        if receiver is None:
            return USER, ""  # not a member access: always ours

        if _is_qualified_super(node):
            # `Anchor.super.pull()` -- a QUALIFIED superclass call from an inner class. The
            # member lives on Anchor's SUPERTYPE, not on Anchor, and tree-sitter reports
            # `object = identifier "Anchor"` with the `super` as a separate child, so reading
            # the object alone names the wrong type. (The regex module gets this wrong in the
            # other direction: it reconstructs the chain `Anchor.super` and then looks for a
            # FIELD called `super` on Anchor, finds none, and withholds `pull` everywhere.)
            cur = self._of_super(self._as_type(receiver, src))
        else:
            cur = self.resolve(receiver, src, enclosing)
        if cur == _EXTERNAL:
            return JDK, ""
        if cur == _SOME_USER or (cur is not None and cur in self.d.types):
            return USER, ""

        chain = _text(receiver, src)
        head = _text(receiver, src).split(".")[0].split("(")[0].strip()
        if head in self.d.ambiguous:
            kinds = ", ".join(sorted(self.d.seen_types.get(head, ())))
            return UNRESOLVED, f"ambiguous type for receiver `{chain}`: {kinds}"
        if receiver.type not in {"identifier", "this", "super", "field_access",
                                 "scoped_identifier", "scoped_type_identifier",
                                 "type_identifier"}:
            return UNRESOLVED, "receiver is an expression, not a name"
        if head in self.declared:
            return UNRESOLVED, f"no declared type found for receiver `{chain}`"
        return UNRESOLVED, f"receiver `{chain}` is not declared in these sources"


def _is_qualified_super(node) -> bool:
    """True for the `name` of `Outer.super.m()`.

    Plain `super.m()` has the `super` node AS its `object` field, so it is excluded here and
    resolved by `resolve` in the ordinary way. Only the qualified form puts a bare `super`
    beside an `object`, and no other shape does.
    """
    p = node.parent
    if p is None or p.type != "method_invocation":
        return False
    if not _same(node, p.child_by_field_name("name")):
        return False
    obj = p.child_by_field_name("object")
    if obj is None or obj.type == "super":
        return False
    return any(c.type == "super" for c in p.children)


def _member_receiver(node):
    """The receiver node that makes `node` a member access, or None when it is not one.

    Four positions put a name after a `.` or a `::`:

        method_invocation   name   <- object      `kids.add(n)`, `helper()` (object absent)
        field_access        field  <- object      `this.parent`, `System.out`
        method_reference    name   <- qualifier   `Watcher::update`, `list::add`
        scoped_type_identifier      <- qualifier   `Node.Builder`

    A `method_invocation` with NO `object` is an implicit `this` call and is never a foreign
    member, so it returns None and is renamed.
    """
    p = node.parent
    if p is None:
        return None
    t = p.type

    if t == "method_invocation":
        if _same(node, p.child_by_field_name("name")):
            return p.child_by_field_name("object")  # None -> implicit this -> not a member
        return None

    if t == "field_access":
        if _same(node, p.child_by_field_name("field")):
            return p.child_by_field_name("object")
        return None

    if t == "method_reference":
        # `<qualifier> :: <name>`. A constructor reference (`Foo::new`) has the `new` KEYWORD
        # there, not an identifier, so it never reaches this branch.
        kids = [c for c in p.children if c.type != "::"]
        if len(kids) >= 2 and _same(node, kids[-1]):
            return kids[0]
        return None

    if t == "scoped_type_identifier":
        kids = [c for c in p.children if c.type != "."]
        if len(kids) >= 2 and _same(node, kids[-1]):
            return kids[0]
        return None

    return None


# --------------------------------------------------------------------------------------- #
# Walking the renameable identifier occurrences
# --------------------------------------------------------------------------------------- #

def _iter_names(root, src: bytes):
    """Yield `(node, name, enclosing_type)` for every identifier that MAY be renamed.

    "May" means the position is renameable -- the receiver question is asked separately, by
    `_Receivers.verdict`, because the two passes that need this walk ask it against different
    rename maps. Positions excluded here are excluded structurally and can never come back:
    package and import subtrees, annotation names, annotation element keys, statement labels
    and their `break` / `continue` targets, and type parameters.
    """
    out = []

    def walk(n, enclosing: str | None) -> None:
        t = n.type
        if t in _SKIP_SUBTREES:
            return

        if t in {"marker_annotation", "annotation"}:
            # `@Override` / `@Ann(value = SC)`: the NAME is not ours, the ARGUMENTS are
            # ordinary expressions and are visited.
            name_node = n.child_by_field_name("name")
            for c in n.children:
                if not _same(c, name_node):
                    walk(c, enclosing)
            return

        if t == "element_value_pair":
            # `value = SC`: the key names a member of the annotation type, the value does not.
            key = n.child_by_field_name("key")
            for c in n.children:
                if not _same(c, key):
                    walk(c, enclosing)
            return

        if t in _LABEL_PARENTS:
            # `outer:` and `break outer;` must both change or both stay. Never renaming a
            # label is the simplest choice that is always correct, and labels leak nothing
            # about pattern structure.
            for c in n.children:
                if c.type != "identifier":
                    walk(c, enclosing)
            return

        if t == "type_parameter":
            # `T` in `class Box<T>` is a type VARIABLE, not a user class. It is never in the
            # type table, so its references are never in the map either.
            return

        if t in _TYPE_DECL_NODES:
            name_node = n.child_by_field_name("name")
            if name_node is not None:
                enclosing = _text(name_node, src) or enclosing

        if t in _NAME_NODES:
            out.append((n, _text(n, src), enclosing))
            return

        for c in n.children:
            walk(c, enclosing)

    walk(root, None)
    return out


# --------------------------------------------------------------------------------------- #
# The map
# --------------------------------------------------------------------------------------- #

def build_rename_map(java_files: dict[str, str]) -> RenameMap:
    """The identifier map for `java_files`, without applying it.

    The assignment order -- types, then methods, then fields, then parameters, then locals,
    each sorted by name -- is copied from `piqs.obfuscator.build_rename_map` deliberately, so
    that where the two modules discover the same set of names they also produce the same
    numbering and `validation/obfuscator_diff.py` reports an empty diff rather than noise.
    """
    parsed = _parse_all(java_files)
    d = _collect(parsed)

    user_types = set(d.types)
    result = RenameMap(decls=d)

    def preserve_method(name: str) -> str | None:
        if name in _ALWAYS_PRESERVE_METHODS:
            return "entry point" if name == "main" else "overrides java.lang.Object"
        if name in _JDK_OVERRIDABLE:
            for owner, supers in d.supertypes.items():
                external = supers - user_types
                if external and name in d.methods_of.get(owner, ()):
                    return f"{owner} inherits from {', '.join(sorted(external))} (not ours)"
        return None

    counters = {"C": 0, "I": 0, "m": 0, "f": 0, "p": 0, "v": 0}

    def assign(name: str, prefix: str) -> None:
        if name in result.mapping or name in _KEYWORDS or name in _JDK_NAMES:
            return
        counters[prefix] += 1
        result.mapping[name] = f"{prefix}{counters[prefix]}"

    for name in sorted(d.types):
        assign(name, "I" if d.types[name] == "interface" else "C")

    for name in sorted(d.methods):
        if name in result.mapping:
            continue
        why = preserve_method(name)
        if why is not None:
            result.preserved_overrides[name] = why
            continue
        if name in _COMMON_JDK_MEMBERS:
            result.shadowed_jdk_members[name] = "also a common JDK member name"
        assign(name, "m")

    for name in sorted(d.fields):
        assign(name, "f")
    for name in sorted(d.params):
        assign(name, "p")
    for name in sorted(d.locals):
        assign(name, "v")

    _withhold_unresolvable(result, parsed)
    _assign_file_names(result, java_files, d)
    return result


def _assign_file_names(result: RenameMap, java_files: dict[str, str], d: _Decls) -> None:
    """Filenames leak names too. The key follows its primary type where there is one."""
    used: set[str] = set()
    for fname in sorted(java_files):
        stem = fname[:-5] if fname.endswith(".java") else fname
        new_stem = result.mapping.get(stem, stem)
        if new_stem == stem and stem not in d.types:
            new_stem = f"F{len(used) + 1}"
        candidate, n = f"{new_stem}.java", 1
        while candidate in used:
            n += 1
            candidate = f"{new_stem}_{n}.java"
        used.add(candidate)
        result.file_mapping[fname] = candidate


def _withhold_unresolvable(result: RenameMap, parsed) -> None:
    """Classify every member-access site, then drop from the map any name with an
    unresolvable one.

    Both halves of getting this wrong emit Java that does not compile. Renaming too much turns
    `kids.add(n)` into `f1.m1(n)`, and `List` has no `m1`. Renaming too little renames the
    declaration `add` to `m1` and leaves `folder.add(x)` calling a method that no longer
    exists. So "skip the occurrence when unsure" is not a safe rule: the only safe response to
    one unresolvable site is to leave the name alone EVERYWHERE, declaration included.
    """
    rec = _Receivers(result.decls)
    reasons: dict[str, str] = {}
    jdk_hits: dict[str, int] = {}

    for _, tree, src in parsed:
        for node, name, enclosing in _iter_names(tree.root_node, src):
            if name not in result.mapping:
                continue
            kind, why = rec.verdict(node, src, enclosing)
            if kind == JDK:
                jdk_hits[name] = jdk_hits.get(name, 0) + 1
            elif kind == UNRESOLVED and name not in reasons:
                reasons[name] = why

    for name, why in sorted(reasons.items()):
        result.withheld_names[name] = why
        result.mapping.pop(name, None)

    # A withheld name is left alone everywhere, so its JDK sites are not a decision this made.
    result.jdk_member_sites = {n: c for n, c in sorted(jdk_hits.items()) if n in result.mapping}


# --------------------------------------------------------------------------------------- #
# Rewriting
# --------------------------------------------------------------------------------------- #

def _apply(tree, src: bytes, rmap: RenameMap) -> str:
    """Splice the renames into `src`, right to left.

    Descending order matters: every edit shifts the bytes after it, so applying the rightmost
    first leaves every remaining span's offsets valid. Bytes outside a span are copied
    untouched, which is what makes comments, literals, whitespace and `import` lines survive
    exactly -- there is nothing to mask and nothing to restore.
    """
    rec = _Receivers(rmap.decls) if rmap.decls is not None else None
    edits: list[tuple[int, int, bytes]] = []

    for node, name, enclosing in _iter_names(tree.root_node, src):
        new = rmap.mapping.get(name)
        if new is None:
            continue
        if rec is not None and rec.verdict(node, src, enclosing)[0] != USER:
            continue  # a member of something that is not ours
        edits.append((node.start_byte, node.end_byte, new.encode("utf-8")))

    out = src
    for start, end, replacement in sorted(edits, key=lambda e: -e[0]):
        out = out[:start] + replacement + out[end:]
    return out.decode("utf-8", errors="ignore")


def obfuscate(java_files: dict[str, str], *, rename_files: bool = True) -> dict[str, str]:
    """Rename every user-defined identifier in `java_files`, consistently across the set.

    Returns a new `{filename: source}`; the input is not modified. Pass `rename_files=False`
    to keep the original keys. Use `build_rename_map` when the mapping itself is wanted.

    Raises `JavaParseError` if any file does not parse cleanly.
    """
    rmap = build_rename_map(java_files)
    parsed = _parse_all(java_files)
    renamed = {fn: _apply(tree, src, rmap) for fn, tree, src in parsed}
    return {
        (rmap.file_mapping.get(fn, fn) if rename_files else fn): renamed[fn]
        for fn in java_files
    }
