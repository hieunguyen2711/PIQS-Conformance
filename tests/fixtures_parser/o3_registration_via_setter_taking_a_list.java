// O3 = 0 -- the whole list is replaced by a setter; individual observers never register.
//
// `setSinks(List<Feed>)` takes a LIST, not a `Feed`. No individual observer can subscribe or
// unsubscribe; the dependent set is swapped wholesale by whoever owns the Station. Same reasoning
// as the constructor-injected fixture, one step less obvious, and it is the case that shows why
// the maintenance rule keys on the ELEMENT type rather than on "a method that writes the field".
//
// Recorded as part of the narrowing in the same commit, not as an oversight.

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

    public void setSinks(List<Feed> s) {
        this.sinks = s;
    }

    public void publish() {
        for (Feed f : sinks) {
            f.ping();
        }
    }
}
