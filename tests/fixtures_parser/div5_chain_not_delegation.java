// Divergence #5 -- a CHAIN is not delegation to a field.
//
// D3 asks whether a wrapper forwards to THE HELD REFERENCE. The retired regex encoded that
// narrowly: it required `<name> . <ident> (`, optionally preceded by `this.`. So it accepted
// `f.op()` and rejected `getX().op()`, because a call expression is not a name.
//
// A `method_invocation` query is naturally WIDER than that. The obvious implementation -- take
// the first identifier under the call's object -- accepts all three of the rejects below:
//
//     getX().op()    would yield "getX"   -- a chain through a call, not a field
//     arr[0].op()    would yield "arr"    -- an element, not the array reference itself
//     f.g.op()       would yield "f"      -- but the regex delegates to `g`, NOT to `f`
//
// The last one is the sharp case, and it is the reason the rule is stated as "field_access ->
// its FIELD's text" rather than "-> its object's text". In `f.g.op()` the text `g.op(` satisfies
// the old regex while `f.op(` does not, so `g` is the receiver. Returning `f` would be wrong in
// both directions at once: it credits delegation to a field that is not forwarded to, and it
// loses the one that is.
//
// THE UNIFORM RULE, which makes all of this fall out with no special cases:
//
//     identifier    -> its own text
//     field_access  -> its FIELD's text
//     anything else -> None
//
// `None` can never equal a field name, so chains and unqualified calls are rejected by
// comparison alone. There is no chain-detection branch anywhere in the implementation.
//
// ZERO CORPUS COVERAGE. Measured: 0 of 41 `_delegates_to_field` call sites have a body
// containing `).op(`. All four suites stay green whichever implementation is chosen, so this
// fixture is the only thing that distinguishes them -- the D6 guard situation again.
//
// `direct` and `viaThis` are the anti-vacuity controls: an implementation that returned False
// for every receiver would pass all the negative assertions and fail these.

interface Op {
    void op();
}

class Held implements Op {
    Op g;
    public void op() { }
}

class Chained {
    private Held f;
    private Op[] arr;

    // POSITIVE: plain field receiver. This is delegation.
    void direct() {
        f.op();
    }

    // POSITIVE: `this.` qualifier. Same field, same answer.
    void viaThis() {
        this.f.op();
    }

    // NEGATIVE: the receiver is a CALL, not a reference. Not delegation to `getF`.
    void throughCall() {
        getF().op();
    }

    // NEGATIVE: the receiver is an array ELEMENT. Not delegation to `arr`.
    void throughIndex() {
        arr[0].op();
    }

    // The sharp case: delegates to `g`, NOT to `f`.
    void twoLevel() {
        f.g.op();
    }

    Held getF() {
        return f;
    }
}
