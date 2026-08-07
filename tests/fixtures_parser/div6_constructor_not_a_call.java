// Divergence #6 -- a constructor call is not a method call.
//
// `new Wallet()` is a bare identifier followed by '(', so the retired regex answered True for
// `_calls_method(body, "Wallet")`. In the tree it is an object_creation_expression, which is not
// a method_invocation.
//
// The predicate is callsWithin(method, target), and `target` is a METHOD. Strategy reads it for
// the execute step; D3 and T3 read it through _calls_within. Counting a constructor as a call
// means a strategy method named the same as an instantiated class scores as "invoked".
//
// Zero sites in either corpus -- measured across every real call site the checker evaluates. All
// four suites are green whichever way this is decided.
//
// `w.open()` is the anti-vacuity control: an ordinary call in the same body must still be found.
// `Wallet` also declares a method literally named `Wallet` so the name exists as a method
// somewhere in the program -- the point is that THIS body never invokes it.

class Client {
    void build() {
        Wallet w = new Wallet();
        w.open();
    }
}

class Wallet {
    void open() { }
    void Wallet() { }
}
