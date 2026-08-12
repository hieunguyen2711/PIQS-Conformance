// Divergence #2 -- compound assignment is NOT an assignment, for parity.
//
// The retired regex was `name\s*=(?!=)`. A compound operator puts a character between the name
// and the `=`, so the regex never matched one. In the tree, EVERY compound form is an
// `assignment_expression` with a different `operator` field -- identical node type to `f = x`.
//
// So a query that collects assignment_expression targets without filtering on the operator
// breaks parity in TEN ways, not the one that divergence #2 is usually described by:
//
//     +=  -=  *=  /=  %=  &=  |=  ^=  <<=  >>=  >>>=
//
// This fixture carries five of them, not just `+=`, because "we handled +=" is exactly the
// half-fix that would pass a one-operator test.
//
// THE DECISION IS EXACT PARITY: filter on `operator == "="`. `_assigns_field` is documented as
// signalling a step that POPULATES STATE, and `total += x` does populate state, so the regex is
// arguably wrong. It is preserved anyway, because a mechanism change that ALSO changes meaning
// makes any resulting movement unattributable -- you could not say whether a moved verdict came
// from the tree or from the new meaning. Parked in docs/STATE.md as a candidate meaning change
// with its own prediction, after the migration.
//
// `f++` and `f--` need no filter: they are `update_expression`, a different node type entirely.
// `==` and `!=` are `binary_expression`. Both are here as controls.
//
// THE FOR-INIT CASE. `for (plain = 0; ...)` is an assignment_expression that is NOT inside an
// expression_statement. The regex matches it. A walk that only looked under expression_statement
// would miss it, so `loopInit` pins that the walk is over the whole subtree.
//
// Zero corpus coverage: no `_assigns_field` call site in either corpus has a compound assignment
// to the queried name.

class Compound {
    private int plain;
    private int add;
    private int sub;
    private int mul;
    private int shift;
    private int mask;
    private int n;

    // POSITIVE control -- a simple assignment must still be found.
    void simple() {
        plain = 1;
    }

    // NEGATIVE -- five distinct compound operators, none of which the regex matched.
    void compounds() {
        add += 1;
        sub -= 1;
        mul *= 2;
        shift <<= 1;
        mask |= 4;
    }

    // NEGATIVE -- update_expression, not assignment_expression.
    void updates() {
        plain++;
        add--;
    }

    // NEGATIVE -- binary_expression, not assignment_expression.
    boolean compare() {
        return plain == n && add != n;
    }

    // POSITIVE -- an assignment in a for-INIT, outside any expression_statement.
    void loopInit() {
        for (plain = 0; plain < n; plain++) {
        }
    }
}
