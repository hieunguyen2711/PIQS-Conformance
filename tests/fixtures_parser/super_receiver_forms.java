// The four receiver forms a call can have, and what the parser must record for each.
//
//     src.pull()          receiver "src"      delegation to a held field
//     super.pull()        receiver <super>    delegation THROUGH the base that holds the field
//     pull()              receiver None       a self-call
//     this.pull()         receiver None       THE SAME CALL as `pull()` -- not a separate form
//     this.src.pull()     receiver "src"      a field_access -- already correct
//     Anchor.super.pull() receiver <super>    qualified superclass call from an inner class
//     Anchor.this.pull()  receiver None       a call on the ENCLOSING INSTANCE, not on a field
//
// Before this fixture, `_qualifier` mapped every receiver that was not a simple reference to
// None, so `super.pull()` and a bare `pull()` were the SAME FACT. That is why
// decorator_filterinputstream_analogue looked as though BufferedInputStream.read() forwarded to
// nothing: it forwards with `super.read()`, and the parser could not see it.
//
// `Anchor.super.pull()` is the sharp one. tree-sitter reports `object = identifier "Anchor"` with the
// `super` as a SEPARATE child, so the old rule returned "Anchor" -- meaning a class with a field
// named `Anchor` would have counted this as delegation to that field. `_qualifier` cannot fix it
// because it only ever receives the object node; the check belongs in `_invocations`.
//
// `this.pull()` staying None is CORRECT and is pinned here so nobody "fixes" it: `this.m()` and
// `m()` are the same call, and neither is delegation to a field.
interface Feed {
    int pull();
}

abstract class RelayBase implements Feed {
    protected Feed src;

    RelayBase(Feed src) {
        this.src = src;
    }

    public int pull() {
        return src.pull();
    }
}

class Relay extends RelayBase {
    Relay(Feed src) {
        super(src);
    }

    public int pull() {
        return super.pull();
    }

    int selfCall() {
        return pull();
    }

    int viaThis() {
        return this.pull();
    }

    int viaFieldChain() {
        return this.src.pull();
    }
}

class Anchor extends RelayBase {
    Anchor(Feed src) {
        super(src);
    }

    class Nested {
        int reach() {
            return Anchor.super.pull();
        }

        int outerInstance() {
            return Anchor.this.pull();
        }
    }
}
