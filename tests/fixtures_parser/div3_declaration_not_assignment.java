// Divergence #3 -- a local DECLARATION is not an assignment to the field it shadows.
//
// `int held = 5;` matched the retired regex `held\s*=(?!=)` -- the regex cannot tell a
// declaration from an assignment, because both contain `held =`. In the tree the first is a
// `local_variable_declaration` and only the second is an `assignment_expression`.
//
// HERE THE TREE IS SIMPLY RIGHT AND THE REGEX IS WRONG, which is why this divergence is decided
// differently from #2. `int held = 5;` declares a LOCAL that shadows the field and initialises
// the local; the field is untouched. `_assigns_field` asks whether the method assigns THE FIELD.
// There is no reading under which the regex's answer is defensible, so the tree's is taken.
//
// Contrast #2, where the regex is also arguably wrong but is PRESERVED, because changing it
// would be a meaning change rather than a mechanism change. The difference: #2 changes which
// programs satisfy a property; #3 removes an answer that was never correct for any program.
//
// Zero corpus coverage: no `_assigns_field` call site in either corpus has a local declaration
// shadowing the queried field name.
//
// KNOWN LIMITATION, recorded in docs/PROPERTY_SPEC.md and NOT fixed here. In `shadowedWrite`
// below, `held = another;` assigns the LOCAL, not the field -- but it is a genuine
// assignment_expression whose target is the bare name `held`, so `_assigns_field` still reports
// the field as assigned. The regex does the same, so parity holds. Resolving it needs
// `m.locals`, which exists, but using it here would be a meaning change: it belongs to Step 3
// with its own prediction.

class Declares {
    private Object held;
    private int count;

    // NEGATIVE -- declares and initialises a LOCAL that shadows the field.
    void declaresLocal() {
        int count = 5;
        System.out.println(count);
    }

    // POSITIVE control -- a real assignment to the field.
    void assignsField() {
        count = 5;
    }

    // POSITIVE -- `this.` qualified, unambiguous even with a shadowing parameter.
    void assignsViaThis(int count) {
        this.count = count;
    }

    // The recorded limitation: `held` here is the LOCAL, but both the regex and the tree
    // report the FIELD as assigned. Parity, not correctness.
    void shadowedWrite(Object other, Object another) {
        Object held = other;
        held = another;
    }
}
