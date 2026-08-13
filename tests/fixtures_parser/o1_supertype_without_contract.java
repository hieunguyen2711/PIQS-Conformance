// O1 RED FIXTURE -- an abstract supertype that does NOT declare the registration contract.
//
// THE CORPUS COULD NOT PROVIDE THIS CASE. In all ten Kim observer units a notifying type either
// has no abstract supertype at all, or has one that declares the contract -- so the WEAK rule
// ("any abstract supertype grants O1") and the STRONG rule ("only a supertype declaring a method
// whose parameter type is the observer type") give identical verdicts on every one of them. The
// corpus cannot distinguish the two designs. This fixture is the only thing that can.
//
// `Station` notifies `Feed` observers, exactly as its twin does. Its only abstract supertype is
// `Serialisable`, which has nothing to do with observing -- it declares `encode()`, no parameter
// of the observer type. There is no abstract SUBJECT here: `Station` is the subject and it is
// concrete.
//
//     weak rule    -> O1 = 1   WRONG: any unrelated abstract supertype grants the subject role
//     strong rule  -> O1 = 0   what this file asserts
//
// Differs from o1_supertype_with_contract only in the supertype: `Broadcaster` declaring
// `enrol(Feed)` becomes `Serialisable` declaring `encode()`. The notification is byte-identical.

import java.util.*;

interface Feed {
    void ping();
}

class Display implements Feed {
    public void ping() {
    }
}

interface Serialisable {
    String encode();
}

class Station implements Serialisable {
    private List<Feed> sinks = new ArrayList<>();

    public void enrol(Feed f) {
        sinks.add(f);
    }

    public String encode() {
        return "";
    }

    public void publish() {
        for (Feed f : sinks) {
            f.ping();
        }
    }
}
