// O1 POSITIVE -- an abstract supertype that DECLARES THE REGISTRATION CONTRACT.
//
// `Broadcaster` is abstract and declares `enrol(Feed)`, whose PARAMETER TYPE IS THE OBSERVER
// TYPE. That is the contract, and it is what makes `Broadcaster` the abstract Subject.
//
// EVERY IDENTIFIER HERE IS DELIBERATELY OUTSIDE THE OLD HARDCODED SET
// {attach, detach, notifyObservers, register, remove, notify}. On the name-based O1 this exact
// program scored O1 = 0; the structure is textbook Observer. That was the defect: same
// structure, different vocabulary, different verdict -- and under the unnamed condition a model
// invents its own vocabulary, so the checker would have marked it down for a naming reason
// indistinguishable from the paper's finding.
//
// This is also the control for the red fixture next to it. A rule that answered 0 everywhere
// would satisfy o1_supertype_without_contract and fail here.

import java.util.*;

interface Feed {
    void ping();
}

class Display implements Feed {
    public void ping() {
    }
}

interface Broadcaster {
    void enrol(Feed f);
}

class Station implements Broadcaster {
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
