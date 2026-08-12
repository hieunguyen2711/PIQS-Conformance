// NEGATIVE CONTROL 1 of 4 -- an enhanced-for that is not a notification
//
// The six loop*.java fixtures are all POSITIVE: each says "this MUST be detected". A widening
// change measured only against positives can only look successful. These four say "this must NOT
// be detected", and they are what makes the widening falsifiable.
//
// The loop form is the ONE form already detected, so this isolates the ELEMENT TYPE from the loop
// shape. `names` holds String, which is not a project type. The body DOES invoke a method on the
// element -- `s.trim()` -- so the receiver rule cannot be what blocks detection here. The only
// thing standing between this and a false positive is `elem not in types`.
//
// REBUILT 2026-08-07. The first version called `System.out.println(s)`, which passes the element
// as an ARGUMENT rather than invoking on it. Detection was therefore blocked by the receiver rule,
// making this a weaker duplicate of loopN2 -- and no mutation of the element-type check could
// flip it. It was only caught by running the mutations and seeing this fixture flip under NONE of
// them. A negative that cannot fail is not a guard; see docs/PROPERTY_SPEC.md, "What a green
// suite does not prove".
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
    private List<String> names = new ArrayList<>();

    public void attach(Observer o) {
        observers.add(o);
    }

    public void notifyObservers() {
        for (String s : names) {
            s.trim();
        }
    }
}
