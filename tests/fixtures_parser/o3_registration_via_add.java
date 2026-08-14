// O3 POSITIVE -- the ordinary Observer: register at runtime, then notify.
//
// `enrol(Feed)` takes the observer type and operates on `sinks`, the same field `publish()`
// iterates. That is the "registered" half of "notifies all REGISTERED observers", which nothing
// in the code had ever checked.
//
// The control for every negative beside it: a rule that answered O3 = 0 everywhere would satisfy
// all of them and fail here.

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

    public void enrol(Feed f) {
        sinks.add(f);
    }

    public void publish() {
        for (Feed f : sinks) {
            f.ping();
        }
    }
}
