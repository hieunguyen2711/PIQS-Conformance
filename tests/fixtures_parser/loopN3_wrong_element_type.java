// NEGATIVE CONTROL 3 of 4 -- the iterated collection is not the observer collection
//
// The six loop*.java fixtures are all POSITIVE: each says "this MUST be detected". A widening
// change measured only against positives can only look successful. These four say "this must NOT
// be detected", and they are what makes the widening falsifiable.
//
// Two collections are present. The observer collection is never iterated; the one that IS iterated
// holds String. If the detector attributes the loop to the wrong field -- picking `observers`
// because it is the only observer-typed collection in scope -- O3 flips wrongly. The element type
// must come from the collection ACTUALLY iterated.
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
    private List<String> widgets = new ArrayList<>();

    public void attach(Observer o) {
        observers.add(o);
    }

    public void notifyObservers() {
        widgets.forEach(w -> w.trim());
    }
}
