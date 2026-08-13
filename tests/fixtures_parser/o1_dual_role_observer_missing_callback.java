// O4 GUARD -- a class in BOTH roles that declares only the Composite operation.
//
// The O1 plan flagged this as an unresolved risk: `concrete_observers` and `callback_names`
// shrink together when the separator removes a Composite traversal, so an `all(...)` that was
// True normally stays True -- UNLESS one class sits in both role sets. `Hybrid` implements the
// observer interface `Feed` but declares only `show()`, the Composite operation.
//
//   before the separator  callback_names = {ping, show}; Hybrid declares show -> O4 = 1
//   after  the separator  callback_names = {ping};       Hybrid declares neither -> O4 = 0
//
// O4 = 0 IS THE CORRECT ANSWER. `Hybrid` is a declared observer that does not implement the
// callback the subject invokes. The old 1 was granted by a callback borrowed from an unrelated
// pattern. So the separator makes O4 stricter here, and the risk the plan recorded resolves in
// the safe direction rather than needing a deferral.
//
// No class in the Kim corpus has more than one supertype, so the corpus cannot reach this case.

import java.util.*;

interface Feed {
    void ping();
}

interface Node {
    void show();
}

class Hybrid implements Feed, Node {
    public void show() {
    }
}

class Folder implements Node {
    private List<Node> kids = new ArrayList<>();

    public void show() {
        for (Node n : kids) {
            n.show();
        }
    }
}

class Station {
    private List<Feed> sinks = new ArrayList<>();

    public void enrol(Feed f) {
        sinks.add(f);
    }

    public void publish() {
        for (Feed f : sinks) {
            f.ping();
        }
    }
}
