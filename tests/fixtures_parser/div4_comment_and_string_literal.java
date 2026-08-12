// Divergence #4 -- comments and string literals are not code.
//
// The retired `_calls_method(body, name)` searched method-body TEXT for a bare identifier
// followed by '('. Body text includes comments and string contents, so all three calls in
// `quiet()` below matched. A tree query cannot see them: a line_comment, a block_comment and a
// string_literal are nodes, and none of them contains a method_invocation.
//
// This is the ONE divergence the corpus exercises in bulk -- 34,190 characters of comment and
// string content across the 184 files -- and blanking all of it moved 0 of the 40 scoring units.
// So it is well covered but never load-bearing. The fixture pins the decision anyway.
//
// It matters for the paper's claim: a model must not earn a property for a call it commented out.
//
// `loud()` is the anti-vacuity control. Without it, a query that returned False for everything
// would pass all three negative assertions.

class Subject {
    void quiet() {
        // notifyObservers();
        /* fire(); */
        String s = "update()";
    }

    void loud() {
        notifyObservers();
    }

    void notifyObservers() { }
    void fire() { }
    void update() { }
}
