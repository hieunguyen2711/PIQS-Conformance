// NEGATIVE CONTROL 6 of 6 -- a method reference whose ELEMENT IS AN ARGUMENT, not the receiver.
//
// This is the loopN2 failure mode wearing method-reference clothes. Only one of these is a
// notification:
//
//     observers.forEach(Observer::update);    element IS the receiver   -> traversal
//     observers.forEach(logger::record);      element is an ARGUMENT    -> NOT a traversal
//     observers.forEach(Helper::process);     element is an ARGUMENT    -> NOT a traversal
//     observers.forEach(Observer::new);       constructor reference     -> NOT a traversal
//
// `logger::record` means "for each observer o, call logger.record(o)". The observer is passed IN.
// Nothing is invoked ON it, so the subject is not notifying anybody -- it is logging.
//
// THE DISTINGUISHING RULE: the method reference's QUALIFIER must name the ELEMENT TYPE.
//
// It has to be a NAME COMPARISON against the resolved element type, not a node-kind test.
// tree-sitter gives an `identifier` for the qualifier in BOTH `Observer::update` and
// `logger::record` -- Java resolves type-vs-variable semantically, and the parser does not do
// semantic resolution. So the check lives in the CHECKER, where the element type is known from
// coll_fields, and the parser merely carries the qualifier along.
//
// `logger` is a PROJECT-LOCAL field, deliberately, so this fixture does not depend on any
// knowledge of the JDK. A version using System.out::println would be testing whether we know what
// System.out is, which is a different and weaker thing.
//
// EXPECTED, BEFORE AND AFTER form 4 lands: O1=1 O2=0 O3=0 O4=0, PIQS 22.27.
// A version that accepts ANY method_reference must flip this and must NOT flip N1/N2/N3.

import java.util.*;

interface Observer {
    void update();
}

class ConcreteObserver implements Observer {
    public void update() {
    }
}

class Logger {
    void record(Observer o) {
    }
}

interface Subject {
    void attach(Observer o);

    void notifyObservers();
}

class ConcreteSubject implements Subject {
    private List<Observer> observers = new ArrayList<>();
    private Logger logger = new Logger();

    public void attach(Observer o) {
        observers.add(o);
    }

    public void notifyObservers() {
        observers.forEach(logger::record);
    }
}
