// A PURE COMPOSITE, WHICH MUST NOT SCORE AS AN OBSERVER AT ALL.
//
// NOT PREDICTED BY THE O1 PLAN. The plan justified the self-recursion separator as preventing a
// Composite from supplying a false abstract SUBJECT (O1). It does more than that: on the
// name-based build this program scored O2 = O3 = O4 = 1 and was FULLY RECOGNISED AS AN OBSERVER,
// because `Folder.show()` iterating `List<Node>` and calling `show()` on each element is
// literally "loop a collection of an abstract type and call a method on each element". The
// separator closes a cross-pattern false positive, not merely an O1 one.
//
// WHAT SEPARATES THEM. `Folder` IS a `Node`, and `show` is `Node`'s own operation -- the type is
// recursing into itself one level down. A subject is not one of its own observers, and its
// notify method is not part of the observer's interface. Two roles, not one self-similar role.
//
// All four properties must read 0.

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

    public void addChild(Node n) {
        kids.add(n);
    }

    public void show() {
        for (Node n : kids) {
            n.show();
        }
    }
}
