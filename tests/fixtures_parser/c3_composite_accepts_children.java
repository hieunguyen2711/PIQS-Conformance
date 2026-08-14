// C3 POSITIVE -- a whole that holds parts AND accepts them.
//
// `graft` is deliberately outside the {add..., remove...} vocabulary the old rule matched. The
// structure is textbook Composite, so the verdict must not depend on the verb: under the old
// name-based C3 this program scored C3 = 0, and under the new one it scores 1. Same defect as
// O1's, in the Composite evaluator.
//
// The control for every negative beside it: a rule answering C3 = 0 everywhere would satisfy all
// three and fail here.

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

    public void graft(Node n) {
        kids.add(n);
    }

    public void show() {
        for (Node n : kids) {
            n.show();
        }
    }
}
