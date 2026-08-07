// NEGATIVE CONTROL 2 of 4 -- the element is PASSED, never called on
//
// The six loop*.java fixtures are all POSITIVE: each says "this MUST be detected". A widening
// change measured only against positives can only look successful. These four say "this must NOT
// be detected", and they are what makes the widening falsifiable.
//
// `observers.forEach(o -> log(o))` names the element and iterates the right collection, but never
// invokes anything ON it -- `o` is an argument, not a receiver. O3 asks whether the subject
// CALLS the callback on each observer. A form-3 matcher that only checks 'the lambda parameter
// appears in the body' would wrongly fire here; it must require the parameter to be the RECEIVER.
//
// EXPECTED, BEFORE AND AFTER every loop-form change: O1=1 O2=0 O3=0 O4=0, PIQS 22.27.
// O1 is 1 for a reason unrelated to loops -- see the note in tests/test_loop_forms.py.
// If any of O2/O3/O4 flips to 1, the widening went too far and the change stops.

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
        observers.forEach(o -> log(o));
    }


    private void log(Observer o) {
    }
}
