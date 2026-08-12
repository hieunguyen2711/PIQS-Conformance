// THE COLLISION GUARD. A field literally named `super`.
//
// This does NOT compile -- javac says `error: <identifier> expected`. That is precisely why it is
// here. This project scores generated code, and generated code that does not compile is the
// normal case, not an edge case: `run_scorer.py` records compilation as a separate fact because
// six of the twelve Kim programs fail it. tree-sitter accepts this file (`has_error` is False) and
// `extract_types` stores the field as ('super', 'Duct').
//
// THE ATTACK. `super.write(s)` calls the PARENT CLASS. The field named `super` is a different
// thing entirely. If the parser records the receiver as the bare text "super", the two become the
// same string, `_delegates_to_field` compares them equal, and the checker credits delegation to a
// field that is never touched. Same shape as the object adapter: two different things collapsing
// into one string.
//
// MEASURED, commit cb5b974, with the receiver stored as bare "super":
//
//     D2 1   D3 1   D4 1   D6 1      PIQS 100.0        <- WRONG, and that commit introduced it
//
// MEASURED, commit 1bdb99e, before any super handling:
//
//     Weird.write calls=[(None, 'write')]              <- no collision, because super was invisible
//
// So the bare-text sentinel did not leave a pre-existing hole open, it OPENED one. The fix stores
// the receiver as `<super>`, which contains characters that are not JavaLetters (JLS 3.8) and
// therefore cannot be any identifier -- verified against the parser, not merely argued: declaring
// `private Duct <super>;` yields a field whose name is the empty string, never "<super>".
//
// D3 must be 0 here. Pinned by tests/test_super_receiver.py.
interface Duct {
    void write(String s);
}

class Weird implements Duct {
    private Duct super;

    public void write(String s) {
        super.write(s);
    }
}
