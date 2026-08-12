// THE LIMIT OF THE super-DELEGATION RULE. A `super` call whose base holds nothing.
//
// Commit F2 accepts `super.m()` as delegation, because a concrete decorator extending an abstract
// decorator base forwards THROUGH the base that holds the component reference. That justification
// has a condition in it, and this fixture is the condition.
//
// `Leaky` IS a decorator candidate: it implements `Spout` and declares a `Spout` field. But it
// extends `Plain`, which holds nothing at all, so `super.emit()` forwards to a class that wraps
// nothing. The held `Spout` is never touched.
//
//     STRICT rule (implemented): D3 = 0, D6 = 0
//         a <super> receiver counts only when a project-defined ancestor of the wrapper is
//         ITSELF a decorator candidate. `Plain` is not, so the call does not count.
//
//     LOOSE rule (rejected):     D3 = 1, D6 = 1
//         any <super> call counts as delegation.
//
// WHY LOOSE WAS REJECTED, and it is not a matter of taste. Apply it to
// tests/fixtures_parser/field_named_super.java: `Weird` implements `Duct`, declares a `Duct`
// field, has NO `extends` at all -- so its super is `Object` -- and calls `super.write(s)`. The
// loose rule scores it D3 = 1, D6 = 1: precisely the verdict F1b was written to eliminate,
// arriving by a different route. One fix would have undone the other.
//
// The merits agree with the guard. "Forwards through the base that HOLDS the reference" is the
// entire justification for accepting `super`, so the rule has to check that the base holds it.
interface Spout {
    void emit();
}

class Plain {
    public void emit() {
    }
}

class Leaky extends Plain implements Spout {
    private Spout held;

    Leaky(Spout held) {
        this.held = held;
    }

    public void emit() {
        super.emit();
    }
}
