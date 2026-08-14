// KNOWN LIMITATION -- C3 = 1 here, and the honest answer is arguably 0.
//
// THIS FIXTURE WAS WRITTEN AS A FALSIFIER AND IT FAILED TO FALSIFY. It was predicted to score
// C3 = 0, by analogy with the Observer registration rule, which requires the registered field and
// the notified field to be THE SAME field. It scores 1. The prediction was wrong, and the fixture
// is kept asserting what the code ACTUALLY does, with the reason, rather than being deleted or
// having its expectation quietly bent.
//
// WHY. `graft(Node)` writes `pending`, while `show()` walks `kids`. Both are `List<Node>`, so
// both are component-typed collection fields, and the rule asks only whether a child is accepted
// into ONE OF THEM. Nothing grafted here ever becomes part of the whole.
//
// WHY IT IS NOT FIXED HERE. The Observer rule can demand field identity because a notification
// site NAMES the field it iterates. The Composite side has no equivalent: `real_components`
// records "this type holds a collection of the component type" without identifying which field is
// the children. Tying C3 to the walked collection would mean detecting the traversal -- Observer
// machinery imported into the Composite evaluator -- which is a second change, and this commit
// would stop being attributable. Recorded, not fixed.
//
// THE CORPUS CANNOT SEE IT EITHER: every Composite in Kim holds exactly one component-typed
// collection, so no suite distinguishes the strict rule from this one. That is the same situation
// as the O1 contract clause, and it is stated for the same reason.

import java.util.*;

interface Node {
    void show();
}

class Leaf implements Node {
    public void show() {
    }
}

class Folder implements Node {
    private List<Node> kids = new ArrayList<>();
    private List<Node> pending = new ArrayList<>();

    public void graft(Node n) {
        pending.add(n);
    }

    public void show() {
        for (Node n : kids) {
            n.show();
        }
    }
}
