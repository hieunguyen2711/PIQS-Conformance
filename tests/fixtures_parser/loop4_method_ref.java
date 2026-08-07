// Loop form 4 of 6 -- forEach with a method reference -- NO element variable and NO call expression at all
//
// One of six minimal Observer programs that differ ONLY in how the subject iterates its
// observers. Every other byte is identical: same types, same field, same method names, same
// imports. If they differed in anything else the comparison would be worthless, so they are
// generated from one template and the difference is verified by diff, not asserted.
//
// `foreach_re` in `_evaluate_observer` matches loop form 1 and nothing else. Kim's corpus is
// 2015-era Java, so five of these six shapes never occur in it and the gap is invisible there.
// Generated 2026 Java uses forms 3 and 5 routinely. The failure is SILENT: an undetected notify
// loop looks exactly like a model that failed to write Observer at all.
//
// O1 is name-based (`subject_candidates` reads a hardcoded method-name set) so it does not depend
// on the loop and should hold across all six. O2, O3 and O4 are structural and all flow from
// detecting the notification loop, so they are what moves.

import java.util.*;

interface Observer {
    void update();
}

class ConcreteObserver implements Observer {
    public void update() {
    }
}

interface Subject {
    void attach(Observer o);

    void notifyObservers();
}

class ConcreteSubject implements Subject {
    private List<Observer> observers = new ArrayList<>();

    public void attach(Observer o) {
        observers.add(o);
    }

    public void notifyObservers() {
        observers.forEach(Observer::update);
    }
}
