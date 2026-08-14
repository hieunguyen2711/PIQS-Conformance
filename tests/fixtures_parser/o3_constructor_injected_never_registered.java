// O3 = 0 WITH O2 = 1 AND O4 = 1 -- THE DELIBERATE NARROWING. Read this before disagreeing.
//
// `Station` is handed its list once at construction and never adds to it. It notifies correctly,
// the observer role is abstract, and the concrete observer implements the callback -- so O2 and
// O4 are 1. But there is no registration mechanism, so O3 is 0 and the program is NOT recognised
// as Observer.
//
// THIS IS A STRICTNESS INCREASE AND IT COSTS A REAL STYLE. It is defended from the definition,
// not from convenience. The Strict General Rules for Observer require "(2) a registration
// mechanism adds/removes observers at runtime", and name "the set and identity of dependents at
// runtime" as what varies. A list fixed at construction has no runtime dependent set: nothing can
// subscribe or unsubscribe, which is the whole point of the pattern.
//
// A reader who thinks constructor injection should count can disagree knowingly -- that is why
// this file states the cost rather than hiding it.
//
// IT IS ALSO WHY O3 IS NOT ALLOWED TO GATE THE NOTIFICATION SITE. If registration were a
// condition of the site itself, O2 and O4 would collapse to 0 here too, and the program would
// score as though it had no observer role at all. It has one; what it lacks is registration.
// O3 => O2, and O2 does not imply O3. This file is the witness that the implication is strict.

import java.util.*;

interface Feed {
    void ping();
}

class Display implements Feed {
    public void ping() {
    }
}

class Station {
    private List<Feed> sinks;

    public Station(List<Feed> s) {
        this.sinks = s;
    }

    public void publish() {
        for (Feed f : sinks) {
            f.ping();
        }
    }
}
