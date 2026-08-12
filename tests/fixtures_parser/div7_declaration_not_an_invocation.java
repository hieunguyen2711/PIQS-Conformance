// Divergence #7 -- a declaration is not an invocation.
//
// The retired regex saw `ping(` inside `void ping() { }` and answered True. This is the
// phantom-method problem phase 1 removed at the TYPE level (the signature regex harvested
// pseudo-methods from call expressions), reappearing at the BODY level in the opposite
// direction: a real declaration read as a call.
//
// Collecting only method_invocation nodes excludes declarations automatically -- no special case,
// and it keeps holding after divergence #8 makes the walk DESCEND into these bodies. That
// interaction is the reason this fixture keeps both a local class and an anonymous class.
//
// Zero sites in either corpus.
//
// `run` is the anti-vacuity control, and a sharp one: it is BOTH declared inside the anonymous
// class AND invoked as `r.run()`. A correct implementation answers True because of the
// invocation. An implementation that counted declarations would also answer True -- but it would
// additionally answer True for `ping` and `beep`, which the other two assertions catch.

class Host {
    void run() {
        class Helper {
            void ping() { }
        }

        Runnable r = new Runnable() {
            public void beep() { }
            public void run() { }
        };

        r.run();
    }
}
