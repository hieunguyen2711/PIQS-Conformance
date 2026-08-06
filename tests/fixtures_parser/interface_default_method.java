// Category: modifier -- `default` is absent from the regex's modifier alternation.
//
// _METHOD_SIG_RE's mods group is
//     (?:(?:public|protected|private|static|final|abstract|synchronized)\s+)*
// which does not list `default`. For `default String render() {` the group matched empty, the
// engine resynchronised on `String render(` and produced the method with modifiers == set().
// The declaration was found, but the modifier that makes it a concrete interface method was not
// recorded.
//
// This matters beyond bookkeeping: docs/PROPERTY_SPEC.md accepts an interface default-method
// template as a valid Template Method (T3), and has_body already carried the concrete/abstract
// distinction the properties read -- but the modifier naming the idiom was itself unobservable.
// The parser records it.

interface Report {
    String header();

    String body();

    default String render() {
        return header() + "\n" + body();
    }

    static Report empty() {
        return null;
    }
}
