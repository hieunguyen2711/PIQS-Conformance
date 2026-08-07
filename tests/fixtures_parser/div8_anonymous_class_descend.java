// Divergence #8 -- DESCEND into anonymous and local class bodies for calls.
//
// This is the one place the call walk deliberately differs from the scope walk.
//
//     _declared_in_body  (locals) STOPS at a nested type body.
//     _invocations       (calls)  DESCENDS into it.
//
// Both are right. A FIELD of an anonymous class belongs to that class, so it must not leak into
// the enclosing method's scope. A CALL written inside an anonymous class body still runs against
// the ENCLOSING instance's fields -- `inner` below is Logger's field, reached through the
// implicit outer reference -- so it really is Logger delegating to `inner`.
//
// D3 asks whether a wrapper forwards to the held reference. Reusing the scope walker's boundary
// here would return False and silently drop delegation for this shape.
//
// PRECISION NOTE, because the obvious example is the wrong one: a LAMBDA body is a `block`, not
// a `class_body`, so the step 1 boundary never stopped there. `Logger3` is pinned anyway, so that
// a future session unifying the two walks fails loudly rather than quietly.
//
// Corpus coverage: of 422 method bodies across the 184 corpus files, 7 contain a lambda and
// ZERO contain an anonymous class body. Nothing here is exercised by any suite.

interface Sink {
    void write(String s);
}

class Logger implements Sink {
    private Sink inner;

    public void write(String s) {
        Runnable r = new Runnable() {
            public void run() { inner.write(s); }
        };
        r.run();
    }
}

class Logger2 implements Sink {
    private Sink inner;

    public void write(String s) {
        class Task {
            void go() { inner.write(s); }
        }
        new Task().go();
    }
}

class Logger3 implements Sink {
    private Sink inner;

    public void write(String s) {
        Runnable r = () -> inner.write(s);
        r.run();
    }
}
