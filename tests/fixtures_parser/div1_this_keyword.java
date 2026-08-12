// Divergence #1 -- `this` is a KEYWORD node, not an identifier.
//
// THE ONLY DIVERGENCE IN THE WHOLE SET WITH A LIVE VERDICT.
//
// The retired `_mentions_token(body, name)` was a whole-word regex over body TEXT, so it found
// `this` like any other word. A tree walk that collects `identifier` nodes does NOT: tree-sitter
// gives `this` its own node type, and `super` likewise. Omitting them makes the predicate answer
// False for every `this`, silently.
//
// Builder property B1 depends on it. `_evaluate_builder` accepts a method as the TERMINAL only if
// its body consumes the builder's configured state -- either by referencing a builder field or by
// passing `this` to the product constructor. That second clause is
// `_mentions_token(m.body, "this")`. Lose it and a legitimate `build()` stops being a terminal,
// so B1 fails and the whole Builder recognition collapses.
//
// Measured across both corpora: 43 call sites pass "this", of which 3 are True, and all 3 are in
// the BDT battery. Dropping `this` from the node set produces exactly those 3 disagreements:
//
//     return new Pizza(this);
//     synchronized (this) { return inner.size(); }
//     return new Point(this);
//
// TWO DIFFERENT NODE POSITIONS, WHICH IS WHY BOTH ARE HERE.
//
//     `new Loaf(this)`       -- `this` as an ARGUMENT of an object_creation_expression
//     `synchronized (this)`  -- `this` as the LOCK of a synchronized_statement
//
// A naive fix that special-cased only the argument position would pass one and fail the other.
// They are not the same case, so this fixture carries both.
//
// `super` rides along for the same reason: also a keyword node, also matched by the old
// whole-word regex. `handOff` exercises it.
//
// DIVERGENCE #4 APPLIES HERE TOO. A `this` written inside a comment or a string literal is not a
// mention. `quiet()` is the negative control -- the regex counted those, the tree does not.
//
// `plain()` is the anti-vacuity control: no `this`, no `super`. Without it, an implementation
// that answered True for everything would pass every positive assertion in this file.
//
// NAMES. `Assembler`/`Loaf`/`Marker` rather than Builder/Pizza/Point, which are declared in
// fixtures/mutation_battery_bdt/. `extract_types` keys types by simple name, and a collision is
// the trap this repo keeps paying for -- see the collapse note in docs/STATE.md. The names carry
// no meaning for the assertions; only the shape does.

class Loaf {
    Loaf(Assembler a) { }
}

class Marker {
    Marker(Assembler a) { }
}

class Assembler {
    private int size;

    // `this` as a constructor ARGUMENT
    Loaf bake() {
        return new Loaf(this);
    }

    // `this` as the LOCK of a synchronized statement -- a different node position
    int guarded(Assembler inner) {
        synchronized (this) {
            return inner.size();
        }
    }

    // `this` as a constructor argument again
    Marker plot() {
        return new Marker(this);
    }

    // `this` as an explicit field qualifier, and `super` as a keyword node
    void handOff(int size) {
        this.size = size;
        super.hashCode();
    }

    // Divergence #4: neither of these is a mention of `this`
    void quiet() {
        // return new Loaf(this);
        String s = "this";
        s.length();
    }

    // Anti-vacuity: no `this`, no `super`
    int plain() {
        return 7;
    }

    int size() {
        return size;
    }
}
