"""Rename every user-defined identifier in a set of Java sources, in memory.

    from piqs.obfuscator import obfuscate
    renamed = obfuscate({"Bus.java": src, "Watcher.java": src2})

Input and output are both `{filename: source}`. Classes and enums become `C1, C2, ...`,
interfaces `I1, I2, ...`, methods `m1, m2, ...`, fields `f1, f2, ...`, parameters
`p1, p2, ...`, local variables `v1, v2, ...`. Names are assigned once for the whole set, so
a type renamed `C3` is `C3` in every file that mentions it.

Nothing else changes: same declarations in the same order, same modifiers, same types, same
`extends`/`implements`, same call graph, same literals, same comments, same whitespace.

## The safety rule

**Only identifiers that were declared in the given sources are ever renamed.** The rename map
is built exclusively from declarations found in the input. `list.add(x)` where `add` is never
declared by the user leaves `add` alone; a user-declared `void add(Node n)` is renamed, and so
are its call sites. That single rule is what keeps the JDK untouched -- `String`, `List`,
`ArrayList`, `Map`, `Integer`, `System`, `Object`, `println` and everything else in the JDK is
never declared here, so it is never in the map. `_JDK_NAMES` below is only a backstop for the
rare case where user code declares a type that shadows a JDK name.

Never touched: Java keywords, JDK names, annotation names, string and character literals,
comments, and `package` / `import` lines.

## Renaming is by name, but decided per call site

Every occurrence of one original name maps to one new name across the whole set. Two
consequences follow, and both are wanted:

* Overrides keep matching names automatically, which Java requires. A method declared in a
  supertype and in a subtype shares one original name, so it shares one new name.
* Two unrelated classes that both declare `run()` get the same new name. That leaks no
  information and preserves every call.

What does *not* follow is that every token spelled `add` is ours. A user `add(Node)` in a
class that also calls `list.add(n)` used to rename both, turning `kids.add(n)` into
`f1.m1(n)` -- `List` has no `m1`, so the output did not compile. A renaming tool that changes
which method is called cannot be used to argue that verdicts are name-independent.

So a token immediately after `.` (or `::`) is renamed only when the receiver's declared type
is one of ours. `_collect` records the declared type of every name it sees; `_Receivers`
reads a chain like `this.parent`, `super`, `Type` or `x` and answers user / JDK / unresolved.
Resolution is global and by name, like the rename map itself, not lexically scoped.

The two ways to get this wrong both emit invalid Java -- renaming a JDK call site, or
renaming a declaration whose call sites were left behind -- so "skip the occurrence when
unsure" is not a safe rule. One unresolvable occurrence withholds the name **everywhere**,
declaration included. That is always valid, and it costs a name the reader can still see:
`withheld_names` records each one with the reason, and `jdk_member_sites` counts the call
sites deliberately left alone. Both are read by tests. (`shadowed_jdk_members` predates this
and only flags a name collision; it never looked at a call site.)

Methods that override something *outside* the given sources keep their names, since the
supertype cannot be renamed with them: `toString` / `equals` / `hashCode` / `clone` and `main`
always, and any `_JDK_OVERRIDABLE` name declared by a type whose supertype is not user-defined
(`class Display implements Observer { public void update(...) }` keeps `update`).
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

__all__ = ["obfuscate", "build_rename_map", "RenameMap"]


_KEYWORDS = {
    "abstract", "assert", "boolean", "break", "byte", "case", "catch", "char", "class",
    "const", "continue", "default", "do", "double", "else", "enum", "extends", "final",
    "finally", "float", "for", "goto", "if", "implements", "import", "instanceof", "int",
    "interface", "long", "native", "new", "package", "private", "protected", "public",
    "return", "short", "static", "strictfp", "super", "switch", "synchronized", "this",
    "throw", "throws", "transient", "try", "void", "volatile", "while",
    "true", "false", "null", "var", "record", "sealed", "permits", "yield",
}

# Backstop only -- see the module docstring. A name here is never renamed even if the user
# declared it, because renaming it would collide with the JDK meaning of the same token.
_JDK_NAMES = {
    # java.lang
    "Object", "String", "StringBuilder", "StringBuffer", "CharSequence", "Character",
    "Integer", "Long", "Short", "Byte", "Double", "Float", "Boolean", "Number", "Math",
    "System", "Thread", "Runnable", "Exception", "RuntimeException", "Error", "Throwable",
    "IllegalArgumentException", "IllegalStateException", "NullPointerException",
    "UnsupportedOperationException", "IndexOutOfBoundsException", "Class", "Enum",
    "Iterable", "Comparable", "Cloneable", "AutoCloseable", "Override", "Deprecated",
    "SuppressWarnings", "FunctionalInterface", "SafeVarargs",
    # java.util
    "List", "ArrayList", "LinkedList", "Map", "HashMap", "TreeMap", "LinkedHashMap",
    "Set", "HashSet", "TreeSet", "LinkedHashSet", "Collection", "Collections", "Arrays",
    "Iterator", "Optional", "Objects", "Comparator", "Queue", "Deque", "ArrayDeque",
    "Stack", "Vector", "Scanner", "Random", "UUID", "Date", "Calendar", "Observable",
    "Observer", "Properties", "Stream", "Collectors", "Function", "Supplier", "Consumer",
    "Predicate", "BiFunction", "Entry", "NoSuchElementException", "ConcurrentHashMap",
    # java.io / java.nio / java.time / java.math
    "InputStream", "OutputStream", "Reader", "Writer", "File", "IOException",
    "BufferedReader", "BufferedWriter", "FileReader", "FileWriter", "PrintStream",
    "PrintWriter", "Serializable", "Path", "Paths", "Files", "BigDecimal", "BigInteger",
    "LocalDate", "LocalDateTime", "LocalTime", "Instant", "Duration", "Period",
    # javax / jakarta servlet names used by the template-method fixtures
    "HttpServlet", "HttpServletRequest", "HttpServletResponse", "ServletException",
}

# Method names that mean something to the JDK when the declaring type's supertype is not one
# of ours. Renaming these would silently detach an override from the contract it implements.
_JDK_OVERRIDABLE = {
    "toString", "equals", "hashCode", "clone", "finalize", "compareTo", "compare",
    "run", "call", "update", "accept", "apply", "test", "get", "getAsInt",
    "iterator", "hasNext", "next", "remove", "close", "read", "write", "flush",
    "doGet", "doPost", "doPut", "doDelete", "service", "init", "destroy",
    "size", "isEmpty", "contains", "add", "clear", "put", "containsKey", "values",
    "keySet", "entrySet", "getKey", "getValue", "length", "charAt", "start",
}

# Always preserved: these override java.lang.Object regardless of the declared supertype, and
# main is the entry point.
_ALWAYS_PRESERVE_METHODS = {"toString", "equals", "hashCode", "clone", "finalize", "main"}

# Members commonly reached on JDK receivers. A user declaration of one of these is still
# renamed -- it is a user declaration -- but it is recorded so callers can spot the ambiguity.
_COMMON_JDK_MEMBERS = {
    "add", "remove", "clear", "get", "set", "size", "put", "contains", "isEmpty",
    "next", "hasNext", "length", "charAt", "append", "toString", "iterator", "values",
    "keySet", "containsKey", "read", "write", "close", "flush", "start", "run", "update",
}

_IDENT = r"[A-Za-z_$][A-Za-z0-9_$]*"
_IDENT_RE = re.compile(_IDENT)

_TYPE_DECL_RE = re.compile(
    r"\b(?P<kind>class|interface|enum)\s+(?P<name>" + _IDENT + r")"
    r"(?:\s*<[^{]*?>)?"
    r"(?:\s+extends\s+(?P<extends>[^{]*?))?"
    r"(?:\s+implements\s+(?P<implements>[^{]*?))?"
    r"\s*\{"
)

_METHOD_SIG_RE = re.compile(
    r"(?<![.\w$])"
    r"(?P<mods>(?:(?:public|protected|private|static|final|abstract|synchronized|native|"
    r"strictfp|default)\s+)*)"
    r"(?:(?P<ret>" + _IDENT + r"(?:\s*<[^;{}()]*?>)?(?:\s*\[\s*\])*)\s+)?"
    r"(?P<name>" + _IDENT + r")\s*\((?P<params>[^)]*)\)\s*"
    r"(?:throws\s+[\w$,.\s]*?)?"
    r"(?P<tail>\{|;)"
)

_FIELD_RE = re.compile(
    r"(?m)^\s*(?P<mods>(?:(?:public|protected|private|static|final|volatile|transient)\s+)*)"
    r"(?P<type>" + _IDENT + r"(?:\s*<[^;]*?>)?(?:\s*\[\s*\])*)\s+"
    r"(?P<name>" + _IDENT + r")\s*(?:=[^;]*)?;"
)

_LOCAL_RE = re.compile(
    r"(?:^|[;{}])\s*(?:final\s+)?"
    r"(?P<type>" + _IDENT + r"(?:\s*<[^;{}]*?>)?(?:\s*\[\s*\])*)\s+"
    r"(?P<name>" + _IDENT + r")\s*(?:=[^;]*)?;"
)
# The same declaration, anchored zero-width. `_LOCAL_RE` *consumes* the `;` that ends the
# previous statement, so `finditer` cannot use that `;` to anchor the next match and every
# second declaration in a run is missed. Only the type table reads this wider scan: closing
# the gap in `_LOCAL_RE` itself would change which names are renamed, which is a separate
# change needing its own evidence. But a missing declaration is worse here than a miss --
# it is a confidently wrong answer. With `Map<Integer,Integer> inventory` visible in one
# class and `ItemInventory inventory` invisible in another, `inventory.addInventory(...)`
# resolves to the JDK, the call site is left behind, and its declaration is renamed anyway.
_LOCAL_TYPE_RE = re.compile(
    r"(?:(?<=[;{}])|^)(?:\s|\x00\d+\x00)*(?:final\s+)?"     # a masked comment may sit here
    r"(?P<type>" + _IDENT + r"(?:\s*<[^;{}]*?>)?(?:\s*\[\s*\])*)\s+"
    r"(?P<name>" + _IDENT + r")\s*(?:=[^;]*)?;"
)
_FOREACH_RE = re.compile(
    r"\bfor\s*\(\s*(?:final\s+)?"
    r"(?P<type>" + _IDENT + r"(?:\s*<[^)]*?>)?(?:\s*\[\s*\])*)\s+"
    r"(?P<name>" + _IDENT + r")\s*:"
)
_FORINIT_RE = re.compile(
    r"\bfor\s*\(\s*(?:final\s+)?(?:int|long|short|byte|char|double|float|boolean|" + _IDENT
    + r")\s+(?P<name>" + _IDENT + r")\s*="
)
_CATCH_RE = re.compile(
    r"\bcatch\s*\(\s*(?:final\s+)?(?P<type>[\w$.|\s]*?)\s+(?P<name>" + _IDENT + r")\s*\)"
)


# --------------------------------------------------------------------------------------- #
# Masking: everything that must survive verbatim is lifted out before any rewriting.
# --------------------------------------------------------------------------------------- #

def _mask(src: str) -> tuple[str, list[str]]:
    """Replace comments, string/char literals, package/import lines and annotation names with
    opaque placeholders. Returns the masked text and the pieces needed to restore it."""
    out: list[str] = []
    held: list[str] = []
    i, n = 0, len(src)

    def hold(text: str) -> str:
        held.append(text)
        return f"\x00{len(held) - 1}\x00"

    while i < n:
        ch = src[i]
        two = src[i : i + 2]

        if two == "//":
            j = src.find("\n", i)
            j = n if j == -1 else j
            out.append(hold(src[i:j]))
            i = j
        elif two == "/*":
            j = src.find("*/", i + 2)
            j = n if j == -1 else j + 2
            out.append(hold(src[i:j]))
            i = j
        elif ch == '"':
            j = i + 1
            while j < n and src[j] != '"':
                j += 2 if src[j] == "\\" else 1
            j = min(j + 1, n)
            out.append(hold(src[i:j]))
            i = j
        elif ch == "'":
            j = i + 1
            while j < n and src[j] != "'":
                j += 2 if src[j] == "\\" else 1
            j = min(j + 1, n)
            out.append(hold(src[i:j]))
            i = j
        elif ch == "@":
            m = re.match(r"@\s*" + _IDENT + r"(?:\s*\.\s*" + _IDENT + r")*", src[i:])
            if m:
                out.append(hold(m.group(0)))
                i += m.end()
            else:
                out.append(ch)
                i += 1
        elif (
            ch in "pi"
            and (i == 0 or src[i - 1] == "\n")
            and re.match(r"(?:package|import)\b", src[i:])
        ):
            j = src.find(";", i)
            j = n if j == -1 else j + 1
            out.append(hold(src[i:j]))
            i = j
        else:
            out.append(ch)
            i += 1

    return "".join(out), held


def _unmask(masked: str, held: list[str]) -> str:
    return re.sub(r"\x00(\d+)\x00", lambda m: held[int(m.group(1))], masked)


def _block_end(text: str, open_brace_idx: int) -> int:
    """Index of the `}` matching the `{` at `open_brace_idx`, or the end of the text."""
    depth = 0
    for i in range(open_brace_idx, len(text)):
        if text[i] == "{":
            depth += 1
        elif text[i] == "}":
            depth -= 1
            if depth == 0:
                return i
    return len(text)


def _extract_block(text: str, open_brace_idx: int) -> str:
    """The text between a `{` and its matching `}`."""
    return text[open_brace_idx + 1 : _block_end(text, open_brace_idx)]


def _class_scope_only(body: str) -> str:
    """Only the text at brace-depth 0 of a class body -- where fields live."""
    out: list[str] = []
    depth = 0
    for ch in body:
        if ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
        elif depth == 0:
            out.append(ch)
    return "".join(out)


def _base_type(raw: str) -> str:
    """The bare type token of a declared type: `List<Node>` -> `List`, `Node[]` -> `Node`,
    `java.util.Map` -> `Map`. Empty when there is no single type (multi-catch, or a form the
    declaration regexes matched loosely enough to have caught something that is not a type)."""
    t = raw.strip()
    if "|" in t:                                    # multi-catch names no single type
        return ""
    t = t.split("<", 1)[0].split("[", 1)[0]
    toks = _IDENT_RE.findall(t)
    return toks[-1] if toks else ""                 # last segment of a qualified name


def _split_params(params: str) -> list[tuple[str, str]]:
    """(base type, name) per parameter, splitting on top-level commas so generics survive.

    The type is "" when this parameter's declared type could not be read off cleanly."""
    parts, depth, current = [], 0, []
    for ch in params:
        if ch in "<([":
            depth += 1
        elif ch in ">)]":
            depth -= 1
        if ch == "," and depth == 0:
            parts.append("".join(current))
            current = []
        else:
            current.append(ch)
    if current:
        parts.append("".join(current))

    out = []
    for raw in parts:
        cleaned = raw.replace("...", " ")
        toks = [t for t in _IDENT_RE.findall(cleaned) if t != "final"]
        if not toks:
            continue
        name = toks[-1]
        # Everything left of the name is the declared type. A bare `(int)` with no name at all
        # yields one token, which _collect discards as a keyword.
        head = cleaned[: cleaned.rindex(name)] if len(toks) > 1 else ""
        out.append((_base_type(head), name))
    return out


# --------------------------------------------------------------------------------------- #
# Declaration collection
# --------------------------------------------------------------------------------------- #

@dataclass
class _Decls:
    types: dict[str, str] = field(default_factory=dict)            # name -> class|interface|enum
    supertypes: dict[str, set[str]] = field(default_factory=dict)  # type -> declared supers
    methods_of: dict[str, set[str]] = field(default_factory=dict)  # type -> method names
    methods: set[str] = field(default_factory=set)
    fields: set[str] = field(default_factory=set)
    params: set[str] = field(default_factory=set)
    locals: set[str] = field(default_factory=set)

    # Declared types, for resolving what a call receiver is. One table for the whole source
    # set, keyed by name -- the same by-name basis the rename map itself uses.
    type_of: dict[str, str] = field(default_factory=dict)          # name -> base declared type
    ambiguous: set[str] = field(default_factory=set)               # name -> two different types
    seen_types: dict[str, set[str]] = field(default_factory=dict)  # name -> every type seen
    # class -> field name -> base type. "" marks a field name this class declares twice with
    # different types, which is no more usable than not knowing it at all.
    fields_of: dict[str, dict[str, str]] = field(default_factory=dict)

    def note_type(self, name: str, raw_type: str) -> None:
        """Record `name`'s declared type, or mark it ambiguous if it already had another.

        Primitives and the keywords the declaration regexes sometimes catch in place of a type
        (`return foo;`, `var x = ...`) are not types worth keeping: nothing is ever called on
        them, so they are dropped rather than allowed to collide with a real declaration."""
        base = _base_type(raw_type)
        if not base or base in _KEYWORDS:
            return
        self.seen_types.setdefault(name, set()).add(base)
        if name in self.ambiguous:
            return
        prev = self.type_of.get(name)
        if prev is None:
            self.type_of[name] = base
        elif prev != base:
            del self.type_of[name]
            self.ambiguous.add(name)


def _collect(masked_sources: list[str]) -> _Decls:
    d = _Decls()

    for src in masked_sources:
        for tm in _TYPE_DECL_RE.finditer(src):
            name = tm.group("name")
            if name in _KEYWORDS:
                continue
            d.types[name] = tm.group("kind")

            supers = set()
            for group in ("extends", "implements"):
                for part in (tm.group(group) or "").split(","):
                    toks = _IDENT_RE.findall(part)
                    if toks:
                        supers.add(toks[0])
            d.supertypes.setdefault(name, set()).update(supers)

            body = _extract_block(src, src.index("{", tm.end() - 1))
            owned = d.methods_of.setdefault(name, set())

            own_fields = d.fields_of.setdefault(name, {})
            for fm in _FIELD_RE.finditer(_class_scope_only(body)):
                fname = fm.group("name")
                if fname in _KEYWORDS:
                    continue
                d.fields.add(fname)
                d.note_type(fname, fm.group("type"))
                base = _base_type(fm.group("type"))
                if base and base not in _KEYWORDS:
                    prev = own_fields.get(fname)
                    own_fields[fname] = base if prev in (None, base) else ""

            for mm in _METHOD_SIG_RE.finditer(body):
                mname = mm.group("name")
                if mname in _KEYWORDS:
                    continue
                # A bare `foo();` is a call, not a declaration: require modifiers or a
                # return type, or that the name is the enclosing type (a constructor).
                if not (mm.group("mods").strip() or mm.group("ret") or mname == name):
                    continue
                if mname != name:
                    d.methods.add(mname)
                    owned.add(mname)
                for ptype, pname in _split_params(mm.group("params") or ""):
                    if pname not in _KEYWORDS:
                        d.params.add(pname)
                        d.note_type(pname, ptype)
                if mm.group("tail") == "{":
                    mbody = _extract_block(body, body.index("{", mm.end() - 1))
                    for rx in (_LOCAL_RE, _FOREACH_RE, _FORINIT_RE, _CATCH_RE):
                        for lm in rx.finditer(mbody):
                            if lm.group("name") not in _KEYWORDS:
                                d.locals.add(lm.group("name"))
                                # _FORINIT_RE matches the type but does not capture it: a
                                # `for (int i = ...)` counter is never a call receiver.
                                d.note_type(lm.group("name"), lm.groupdict().get("type") or "")
                    # Types only -- see _LOCAL_TYPE_RE. Deliberately not added to d.locals.
                    for lm in _LOCAL_TYPE_RE.finditer(mbody):
                        if lm.group("name") not in _KEYWORDS:
                            d.note_type(lm.group("name"), lm.group("type"))

    return d


# --------------------------------------------------------------------------------------- #
# Receiver resolution
#
# `kids.add(n)` and `folder.add(n)` are the same three tokens to a regex and opposite answers
# to a renamer: the first is `java.util.List.add`, the second is ours. What separates them is
# the declared type of the receiver, which `_collect` now has. Resolution is global and
# by-name, matching how the rename map itself is built -- one mechanism, not two. Real lexical
# scoping would be a second mechanism, and a mechanism change that also changes meaning makes
# any movement in the results ambiguous.
# --------------------------------------------------------------------------------------- #

USER, JDK, UNRESOLVED = "user", "jdk", "unresolved"

_EXTERNAL = "\x00external"      # a type that is not declared in these sources
_SOME_USER = "\x00some-user"    # one of ours, but which one is not known


def _class_spans(masked: str) -> list[tuple[int, int, str]]:
    """(body start, body end, type name) for every type declared in one masked source."""
    spans = []
    for tm in _TYPE_DECL_RE.finditer(masked):
        name = tm.group("name")
        if name in _KEYWORDS:
            continue
        open_idx = masked.find("{", tm.end() - 1)
        if open_idx == -1:
            continue
        spans.append((open_idx, _block_end(masked, open_idx), name))
    return spans


def _enclosing_type(spans: list[tuple[int, int, str]], idx: int) -> str | None:
    """The innermost type whose body contains `idx`."""
    best: tuple[int, int, str] | None = None
    for span in spans:
        if span[0] <= idx <= span[1] and (best is None or span[1] - span[0] < best[1] - best[0]):
            best = span
    return best[2] if best else None


def _prev_significant(masked: str, held: list[str], i: int) -> tuple[int, str]:
    """Walk left from `i`, skipping whitespace and masked comments.

    Returns `(index, "char")` for an ordinary character, `(index, "literal")` when a masked
    string or character literal ends there, or `(-1, "none")` at the start of the text."""
    while i > 0:
        j = i - 1
        ch = masked[j]
        if ch.isspace():
            i = j
            continue
        if ch == "\x00":
            start = masked.rfind("\x00", 0, j)
            text = held[int(masked[start + 1 : j])]
            if text.startswith("//") or text.startswith("/*"):
                i = start                       # a comment is not part of any expression
                continue
            return start, "literal"
        return j, "char"
    return -1, "none"


def _receiver_parts(masked: str, held: list[str], i: int) -> list[str] | None:
    """The receiver chain immediately left of `i`, outermost first.

    `[]` means a string or character literal -- a JDK receiver with no names in it. `None`
    means the receiver is not a plain chain of names: a call, an index, a parenthesised
    expression, a cast. Those are unresolvable here by design."""
    parts: list[str] = []
    while True:
        j, kind = _prev_significant(masked, held, i)
        if kind == "none":
            return None
        if kind == "literal":
            return []
        end = j + 1
        while j >= 0 and (masked[j].isalnum() or masked[j] in "_$"):
            j -= 1
        tok = masked[j + 1 : end]
        if not _IDENT_RE.fullmatch(tok) or (tok in _KEYWORDS and tok not in ("this", "super")):
            return None
        parts.append(tok)
        k, kind2 = _prev_significant(masked, held, j + 1)
        if kind2 != "char" or masked[k] != ".":
            parts.reverse()
            return parts
        i = k


def _member_access_at(masked: str, held: list[str], start: int) -> int | None:
    """The index just left of the `.` or `::` that makes the token at `start` a member
    access, or None when the token is not one."""
    j, kind = _prev_significant(masked, held, start)
    if kind != "char":
        return None
    if masked[j] == ".":
        return j
    if masked[j] == ":":
        k, kind2 = _prev_significant(masked, held, j)
        if kind2 == "char" and masked[k] == ":":        # a `Type::member` method reference
            return k
    return None


class _Receivers:
    """Answers one question per call site: is the thing left of the dot one of ours?"""

    def __init__(self, decls: _Decls) -> None:
        self.d = decls
        self.declared = decls.fields | decls.params | decls.locals

    def _of_name(self, name: str) -> str | None:
        """The type a bare name has: a user type name, `_EXTERNAL`, or None when unknown."""
        if name in self.d.ambiguous:
            return None
        base = self.d.type_of.get(name)
        if base is not None:
            return base if base in self.d.types else _EXTERNAL
        if name in self.d.types:
            return name                     # a static call on one of our types
        if name in _JDK_NAMES:
            return _EXTERNAL                # a static call on a JDK type
        return None                         # declared in a form we could not read, or not here

    def _of_field(self, owner: str, fname: str) -> str | None:
        """The type of field `fname` on user type `owner`, searching its user supertypes."""
        seen: set[str] = set()
        stack = [owner]
        while stack:
            cls = stack.pop()
            if cls in seen:
                continue
            seen.add(cls)
            base = self.d.fields_of.get(cls, {}).get(fname)
            if base == "":                  # declared twice in this class with two types
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
            return _EXTERNAL                # implicit java.lang.Object
        user = {s for s in supers if s in self.d.types}
        if not user:
            return _EXTERNAL
        if len(user) != len(supers):
            return None                     # `extends Ours implements Theirs`: which one?
        return next(iter(user)) if len(user) == 1 else _SOME_USER

    def verdict(self, masked: str, held: list[str], spans, start: int) -> tuple[str, str]:
        """`(USER | JDK | UNRESOLVED, reason)` for the member-access token at `start`."""
        dot = _member_access_at(masked, held, start)
        if dot is None:
            return USER, ""                             # not a member access: always renamed
        parts = _receiver_parts(masked, held, dot)
        if parts is None:
            return UNRESOLVED, "receiver is an expression, not a name"
        if not parts:
            return JDK, ""                              # a literal receiver

        head, rest = parts[0], parts[1:]
        if head == "this":
            cur: str | None = _enclosing_type(spans, start)
        elif head == "super":
            cur = self._of_super(_enclosing_type(spans, start))
        else:
            cur = self._of_name(head)

        for step in rest:
            if cur is None:
                break
            if cur == _EXTERNAL:
                return JDK, ""                          # everything under a JDK type is theirs
            if cur == _SOME_USER:
                cur = None
                break
            cur = self._of_field(cur, step)

        if cur == _EXTERNAL:
            return JDK, ""
        if cur == _SOME_USER or (cur is not None and cur in self.d.types):
            return USER, ""

        chain = ".".join(parts)
        if head in self.d.ambiguous:
            kinds = ", ".join(sorted(self.d.seen_types.get(head, ())))
            return UNRESOLVED, f"ambiguous type for receiver `{chain}`: {kinds}"
        if head in self.declared:
            return UNRESOLVED, f"no declared type found for receiver `{chain}`"
        return UNRESOLVED, f"receiver `{chain}` is not declared in these sources"


# --------------------------------------------------------------------------------------- #
# The map
# --------------------------------------------------------------------------------------- #

@dataclass
class RenameMap:
    """The identifier mapping for one set of sources, plus what was deliberately left alone."""

    mapping: dict[str, str] = field(default_factory=dict)
    preserved_overrides: dict[str, str] = field(default_factory=dict)
    shadowed_jdk_members: dict[str, str] = field(default_factory=dict)
    file_mapping: dict[str, str] = field(default_factory=dict)

    # Names that are renamed nowhere -- not the declaration, not one call site -- because at
    # least one `.name` occurrence had a receiver that could not be resolved. Each one is a
    # hole in the name-blindness proof, so each one is named and counted rather than dropped.
    withheld_names: dict[str, str] = field(default_factory=dict)
    # name -> how many `.name` sites were left alone because the receiver is not ours.
    jdk_member_sites: dict[str, int] = field(default_factory=dict)

    # The declarations the mapping was built from, kept so `_apply` can re-ask the receiver
    # question at each site. Internal.
    decls: _Decls | None = field(default=None, repr=False, compare=False)

    def __len__(self) -> int:
        return len(self.mapping)


def build_rename_map(java_files: dict[str, str]) -> RenameMap:
    """The identifier map for `java_files`, without applying it."""
    masked = [_mask(src)[0] for _, src in sorted(java_files.items())]
    d = _collect(masked)

    user_types = set(d.types)
    result = RenameMap(decls=d)

    def preserve_method(name: str) -> str | None:
        """Reason this method name must keep its name, or None."""
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

    # Precedence: a name used in two roles is renamed once, by its strongest role.
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

    _withhold_unresolvable(result, java_files)

    # Filenames leak names too. The key follows its primary type where there is one.
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

    return result


def _withhold_unresolvable(result: RenameMap, java_files: dict[str, str]) -> None:
    """Classify every `.name` site, then drop from the map any name with an unresolvable one.

    Both halves of getting this wrong emit Java that does not compile. Renaming too much turns
    `kids.add(n)` into `f1.m1(n)`, and `List` has no `m1`. Renaming too little renames the
    declaration `add` to `m1` and leaves `folder.add(x)` calling a method that no longer
    exists. So "skip the occurrence when unsure" is not a safe rule: the only safe response to
    one unresolvable site is to leave the name alone *everywhere*, declaration included.

    That keeps the output valid at the cost of a name the reader can still see. The cost is
    recorded in `withheld_names` so it can be stated, not discovered later.
    """
    rec = _Receivers(result.decls)
    verdicts: dict[str, str] = {}
    jdk_hits: dict[str, int] = {}

    for _, src in sorted(java_files.items()):
        masked, held = _mask(src)
        spans = _class_spans(masked)
        for m in _IDENT_RE.finditer(masked):
            name = m.group(0)
            if name not in result.mapping:
                continue
            kind, why = rec.verdict(masked, held, spans, m.start())
            if kind == JDK:
                jdk_hits[name] = jdk_hits.get(name, 0) + 1
            elif kind == UNRESOLVED and name not in verdicts:
                verdicts[name] = why

    for name, why in sorted(verdicts.items()):
        result.withheld_names[name] = why
        result.mapping.pop(name, None)

    # A withheld name is left alone everywhere, so its JDK sites are not a decision this made.
    result.jdk_member_sites = {n: c for n, c in sorted(jdk_hits.items()) if n in result.mapping}


def _apply(src: str, rmap: RenameMap) -> str:
    masked, held = _mask(src)
    spans = _class_spans(masked)
    rec = _Receivers(rmap.decls) if rmap.decls is not None else None

    def rename(m: re.Match) -> str:
        name = m.group(0)
        new = rmap.mapping.get(name)
        if new is None:
            return name
        if rec is not None and rec.verdict(masked, held, spans, m.start())[0] != USER:
            return name                     # a member of something that is not ours
        return new

    return _unmask(_IDENT_RE.sub(rename, masked), held)


def obfuscate(java_files: dict[str, str], *, rename_files: bool = True) -> dict[str, str]:
    """Rename every user-defined identifier in `java_files`, consistently across the set.

    Returns a new `{filename: source}`; the input is not modified. Pass `rename_files=False`
    to keep the original keys. Use `build_rename_map` when the mapping itself is wanted.
    """
    rmap = build_rename_map(java_files)
    return {
        (rmap.file_mapping.get(fname, fname) if rename_files else fname): _apply(src, rmap)
        for fname, src in java_files.items()
    }
