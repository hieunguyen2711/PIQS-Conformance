// NEGATIVE CONTROL for the `this.`-receiver fix -- guards `_collection_of` in piqs/parser.py (loop forms 2-6)
//
// `other.observers` is a DIFFERENT OBJECT'S collection. Resolving it to this type's own field
// `observers` would be wrong: the subject does not iterate its own observers here, and O3 asks
// whether THE SUBJECT notifies ITS observers.
//
// This is the falsifier for the `this.` widening. The trivial way to make every `this.` twin
// pass is to strip any receiver and keep the trailing name, which would light this fixture up
// too. Only `this.` may resolve.
//
// Two negatives exist rather than one because the fix has TWO SITES -- `foreach_re` in
// piqs/checker.py for loop form 1, and `_collection_of` in piqs/parser.py for forms 2-6. A
// single fixture would leave one site unguarded and the leak unattributable.

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

class Registry {
    List<Observer> observers = new ArrayList<>();
}

class ConcreteSubject implements Subject {
    private List<Observer> observers = new ArrayList<>();
    private Registry other = new Registry();

    public void attach(Observer o) {
        observers.add(o);
    }

    public void notifyObservers() {
        other.observers.forEach(o -> o.update());
    }
}
