// Category: scope table -- a subclass field SHADOWS an inherited field of the same name.
//
// Java resolution: inside Sub.write, the bare name `held` is Sub's `Component held`, NOT Base's
// `Object held`. A subclass field hides a superclass field of the same name; the inherited one is
// reachable only as `super.held` or through a cast.
//
// What went wrong. `PIQSChecker._effective_fields` returns own fields FIRST, then the parent's,
// then the grandparent's:
//
//     [('held', 'Component'), ('held', 'Object')]
//
// `_scope` built its dict with a plain comprehension over that list, so the LATER entry won and
// the ancestor overwrote the subclass field. `_scope['held']` reported `Object`. Inverted.
//
// Why it matters beyond tidiness. D3 asks whether a wrapper forwards to THE HELD REFERENCE. Step
// 3 resolves the receiver's type through the scope table, so a shadowed field resolving to the
// ancestor's type makes the wrapper look like it delegates to the wrong thing -- or to nothing.
//
// NO CORPUS FILE SHADOWS AN INHERITED FIELD. All four suites stay green with the bug present, so
// the suites are not what protects this. This fixture and its test are.
//
// The distinction that made the bug survive review: the scope table already had two proven
// shadowing guards, but both cover LOCAL-vs-FIELD ("a local named x beats a field named x").
// FIELD-vs-INHERITED-FIELD is a third relationship and nothing covered it.

interface Component {
    void write(String s);
}

class Base {
    protected Object held;
}

class Sub extends Base implements Component {
    private Component held;

    public void write(String s) {
        held.write(s);
    }
}
