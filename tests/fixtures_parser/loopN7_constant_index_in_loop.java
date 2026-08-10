// NEGATIVE CONTROL 7 -- an enclosing loop is NECESSARY but NOT SUFFICIENT (form 2).
//
// The rule agreed for form 2 was "the matched call must sit inside a for_statement", because
// `get(i)` carries no repetition of its own. That rule alone accepts this:
//
//     for (int i = 0; i < 10; i++) {
//         observers.get(0).update();      // inside a loop -- and the SAME observer, ten times
//     }
//
// One observer notified repeatedly is not "the subject notifies every observer". So the rule needs
// its second half: THE ARGUMENT TO get(...) MUST BE THE FOR-INIT'S DECLARED VARIABLE.
//
//     for (int i = 0; i < observers.size(); i++) observers.get(i).update();   accept
//     for (int i = 0; i < 10; i++)               observers.get(0).update();   reject
//
// That also buys reverse iteration for free, with no extra case:
//
//     for (int i = observers.size() - 1; i >= 0; i--) observers.get(i).update();   accept
//
// EXPECTED: O1=1 O2=0 O3=0 O4=0, PIQS 22.27.
// A version requiring only the enclosing loop must flip this and nothing else.

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
        for (int i = 0; i < 10; i++) {
            observers.get(0).update();
        }
    }
}
