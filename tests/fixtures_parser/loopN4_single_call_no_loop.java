// NEGATIVE CONTROL 4 of 4 -- one observer, no loop -- the guard for forms 2 and 6
//
// The six loop*.java fixtures are all POSITIVE: each says "this MUST be detected". A widening
// change measured only against positives can only look successful. These four say "this must NOT
// be detected", and they are what makes the widening falsifiable.
//
// THE MOST IMPORTANT NEGATIVE. `get(...)` and `next()` carry no repetition of their own: the
// repetition lives in the for/while AROUND them. So `observers.get(0).update()` and
// `it.next().update()` have the SAME call shape as the traversal versions and are not traversal --
// they touch one observer. O3 asks whether the subject notifies EVERY observer.
//
// For forms 2 and 6 the enclosing loop is therefore PART OF THE PATTERN, not context: the matched
// call must sit inside a for_statement (form 2) or a while_statement (form 6). None of the six
// positive fixtures can raise this alarm, because every one of them contains a loop.
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
        observers.get(0).update();
        Iterator<Observer> it = observers.iterator();
        it.next().update();
    }
}
