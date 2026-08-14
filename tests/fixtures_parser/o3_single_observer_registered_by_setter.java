// O3 POSITIVE for the SINGLE-HELD-OBSERVER branch -- registration by assignment.
//
// Branch (b) holds one observer rather than a collection, so "maintained" cannot mean "calls a
// method on the collection". It means a method taking the observer type that ASSIGNS the field.
// One definition covers both branches: a method whose parameter is the observer type, which
// either operates on the field or assigns it.
//
// Without this fixture the single-observer branch would be gated by a rule written only for
// collections, and every branch-(b) program would silently lose O3.

import java.util.*;

interface Feed {
    void ping();
}

class Display implements Feed {
    public void ping() {
    }
}

class Station {
    private Feed sink;

    public void enrol(Feed f) {
        this.sink = f;
    }

    public void publish() {
        sink.ping();
    }
}
