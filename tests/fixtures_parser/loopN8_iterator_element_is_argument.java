// NEGATIVE CONTROL 8 -- form 6's version of the loopN2 failure mode.
//
//     while (it.hasNext()) it.next().update();   element IS the receiver  -> traversal
//     while (it.hasNext()) log(it.next());       element is an ARGUMENT   -> NOT a traversal
//
// loopN2 guards this for the lambda form and loopN6 for the method-reference form. Nothing guarded
// it for the iterator form until this fixture, and the three are separate code paths -- a fix on
// one does not imply a fix on the others.
//
// The subject here is logging its observers, not notifying them: nothing is invoked ON the element.
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

    public void attach(Observer o) {
        observers.add(o);
    }

    private void log(Observer o) {
    }

    public void notifyObservers() {
        Iterator<Observer> it = observers.iterator();
        while (it.hasNext()) {
            log(it.next());
        }
    }
}
