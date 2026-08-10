// NEGATIVE CONTROL 9 -- the iterator map must be keyed BY IDENTIFIER, not one value per method.
//
//     Iterator<String>   it2 = names.iterator();
//     Iterator<Observer> it1 = observers.iterator();
//     while (it2.hasNext()) { it2.next().trim(); }        // iterating NAMES, not observers
//
// If the `iterator -> collection` link is a single per-method value, the SECOND declaration
// overwrites the first and `it2` silently resolves to `observers`. The loop then looks like a
// notification over Observer, and O2/O3/O4 all flip on a method that never touches an observer.
//
// The declaration order here is deliberate: the observer collection is declared LAST, so a
// last-wins bug credits exactly the wrong collection. Written the other way round the bug would
// hide, because `names` holds String, which is not a project type and would be rejected anyway.
//
// This is the disjoint-block last-wins behaviour already documented for the scope table
// (`docs/STATE.md`, "Block scope is not modelled"), reappearing somewhere it can change a VERDICT
// rather than just a scope entry.
//
// EXPECTED: O1=1 O2=0 O3=0 O4=0, PIQS 22.27.

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
    private List<String> names = new ArrayList<>();

    public void attach(Observer o) {
        observers.add(o);
    }

    public void notifyObservers() {
        Iterator<String> it2 = names.iterator();
        Iterator<Observer> it1 = observers.iterator();
        while (it2.hasNext()) {
            it2.next().trim();
        }
    }
}
