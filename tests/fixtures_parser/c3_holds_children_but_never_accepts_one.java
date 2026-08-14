// C3 = 0 WITH C1 = 1 -- holds parts, but nothing can ever become one.
//
// `Folder` conforms to `Node` and holds a `List<Node>`, so a real part-whole hierarchy exists and
// C1 and C4 are 1. But the list is handed in at construction and there is no method taking a
// `Node` that puts one into it. A whole that cannot accept a part is not a Composite: the
// pattern's point is composing a tree at runtime.
//
// This is the witness that C3 is strictly stronger than "a component-typed collection exists".
// Without it, "holds a collection" and "is a composite" would be the same test under two names --
// the tautology check that O2/O3 needed, applied here before it could be introduced.

import java.util.*;

interface Node {
    void show();
}

class Leaf implements Node {
    public void show() {
    }
}

class Folder implements Node {
    private List<Node> kids;

    public Folder(List<Node> initial) {
        this.kids = initial;
    }

    public void show() {
        for (Node n : kids) {
            n.show();
        }
    }
}
