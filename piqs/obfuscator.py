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

## Renaming is by name, not by declaration site

Every occurrence of one original name maps to one new name across the whole set. Java is not
parsed to types here, so `x.foo()` cannot be resolved to a declaration -- renaming by name is
the only way to keep call sites attached to their targets. Three consequences:

* Overrides keep matching names automatically, which Java requires. A method declared in a
  supertype and in a subtype shares one original name, so it shares one new name.
* Two unrelated classes that both declare `run()` get the same new name. That leaks no
  information and preserves every call.
* A user method sharing a name with a JDK member it does not override -- a user `add(Node)`
  in a class that also calls `list.add(n)` -- renames both occurrences. `shadowed_jdk_members`
  in `RenameMap` records exactly these, so a caller can tell an obfuscator ambiguity apart
  from a genuine name dependence in whatever consumes the output.

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
_FOREACH_RE = re.compile(
    r"\bfor\s*\(\s*(?:final\s+)?" + _IDENT + r"(?:\s*<[^)]*?>)?(?:\s*\[\s*\])*\s+"
    r"(?P<name>" + _IDENT + r")\s*:"
)
_FORINIT_RE = re.compile(
    r"\bfor\s*\(\s*(?:final\s+)?(?:int|long|short|byte|char|double|float|boolean|" + _IDENT
    + r")\s+(?P<name>" + _IDENT + r")\s*="
)
_CATCH_RE = re.compile(
    r"\bcatch\s*\(\s*(?:final\s+)?[\w$.|\s]*?\s+(?P<name>" + _IDENT + r")\s*\)"
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


def _extract_block(text: str, open_brace_idx: int) -> str:
    """The text between a `{` and its matching `}`."""
    depth = 0
    for i in range(open_brace_idx, len(text)):
        if text[i] == "{":
            depth += 1
        elif text[i] == "}":
            depth -= 1
            if depth == 0:
                return text[open_brace_idx + 1 : i]
    return text[open_brace_idx + 1 :]


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


def _split_params(params: str) -> list[str]:
    """Parameter names, splitting on top-level commas so generics survive."""
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
        toks = [t for t in _IDENT_RE.findall(raw.replace("...", " ")) if t != "final"]
        if toks:
            out.append(toks[-1])
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

            for fm in _FIELD_RE.finditer(_class_scope_only(body)):
                if fm.group("name") not in _KEYWORDS:
                    d.fields.add(fm.group("name"))

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
                for pname in _split_params(mm.group("params") or ""):
                    if pname not in _KEYWORDS:
                        d.params.add(pname)
                if mm.group("tail") == "{":
                    mbody = _extract_block(body, body.index("{", mm.end() - 1))
                    for rx in (_LOCAL_RE, _FOREACH_RE, _FORINIT_RE, _CATCH_RE):
                        for lm in rx.finditer(mbody):
                            if lm.group("name") not in _KEYWORDS:
                                d.locals.add(lm.group("name"))

    return d


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

    def __len__(self) -> int:
        return len(self.mapping)


def build_rename_map(java_files: dict[str, str]) -> RenameMap:
    """The identifier map for `java_files`, without applying it."""
    masked = [_mask(src)[0] for _, src in sorted(java_files.items())]
    d = _collect(masked)

    user_types = set(d.types)
    result = RenameMap()

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


def _apply(src: str, mapping: dict[str, str]) -> str:
    masked, held = _mask(src)
    rewritten = _IDENT_RE.sub(lambda m: mapping.get(m.group(0), m.group(0)), masked)
    return _unmask(rewritten, held)


def obfuscate(java_files: dict[str, str], *, rename_files: bool = True) -> dict[str, str]:
    """Rename every user-defined identifier in `java_files`, consistently across the set.

    Returns a new `{filename: source}`; the input is not modified. Pass `rename_files=False`
    to keep the original keys. Use `build_rename_map` when the mapping itself is wanted.
    """
    rmap = build_rename_map(java_files)
    return {
        (rmap.file_mapping.get(fname, fname) if rename_files else fname): _apply(src, rmap.mapping)
        for fname, src in java_files.items()
    }
