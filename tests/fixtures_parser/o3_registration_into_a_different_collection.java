// O3 = 0 -- registers into one collection and notifies a DIFFERENT one.
//
// `enrol(Feed)` takes the observer type and operates on a collection, and `publish()` iterates a
// collection of the observer type. Both halves are present -- but they are not the same field, so
// nobody who registers is ever notified.
//
// THE FALSIFIER FOR THE MAINTENANCE RULE. The cheap implementation is "the holder has SOME method
// taking the element type that touches SOME collection", which passes here. The field identity is
// the whole content of the rule: `sinks` must be the field that is both maintained and iterated.

import java.util.*;

interface Feed {
    void ping();
}

class Display implements Feed {
    public void ping() {
    }
}

class Station {
    private List<Feed> sinks = new ArrayList<>();
    private List<Feed> spare = new ArrayList<>();

    public void enrol(Feed f) {
        spare.add(f);
    }

    public void publish() {
        for (Feed f : sinks) {
            f.ping();
        }
    }
}
