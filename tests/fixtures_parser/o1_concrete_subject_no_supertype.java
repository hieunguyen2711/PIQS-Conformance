// O1 = 0 with the CRITICAL SET SATISFIED -- the SWS/Copilot shape.
//
// `Station` notifies its observers correctly, so O2, O3 and O4 are all 1 and the program IS
// recognised as Observer. But `Station` has no supertype at all, so there is no ABSTRACT subject
// and O1 is 0. O1 is weight 2 and non-critical; it does not decide recognition.
//
// This is the shape that moved the one Kim cell. SWS/Copilot scored O1 = 1 before Stage 3 --
// not because an abstract subject existed, but because `TransactionObserver`, the OBSERVER
// interface, declared a callback named `notify`, which was in the hardcoded set. The observer
// was admitted as the subject. Kim also recorded satisfied, so the checker agreed with the
// ground truth for a structurally false reason, and any correct rule has to break that
// agreement.

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
