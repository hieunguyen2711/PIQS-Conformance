// C3 NEGATIVE -- THE DEFECT THIS CHANGE EXISTS FOR. This is the POSS/Copilot and POSS/Gemini
// shape, reduced.
//
// `Watcher` implements `Signal`, which is an OBSERVER interface, and it has `addRecord(Record)`
// over a `List<Record>` -- a collection of a CONCRETE type that has nothing to do with `Signal`.
// The old C3 asked only "is there a concrete implementor of some interface with a method whose
// name starts with the token add or remove", so this scored C3 = 1: a composite type, in a
// program containing no Composite at all.
//
// The checker already said so in the same breath -- C1 = 0, C4 = 0, "no abstract component
// exists" -- while C3 said one did. Two definitions of "composite" lived in one function: this
// name-based one, and the structural `comp_composites` that C1 and C4 read. C3 now reads the
// same one they do.
//
// KIM RECORDS C3 = satisfied FOR BOTH REAL PROGRAMS, so this fixture is where the checker
// deliberately disagrees with the published ground truth, and Kim's own C1 = 0 is the internal
// evidence that it should.

import java.util.*;

interface Signal {
    void fire();
}

class Record {
    private int amount;

    public int getAmount() {
        return amount;
    }
}

class Watcher implements Signal {
    private List<Record> log = new ArrayList<>();

    public void addRecord(Record r) {
        log.add(r);
    }

    public void fire() {
    }
}
