// NEGATIVE CONTROL 5 of 5 -- a stream chain that CHANGES the element type.
//
// Form 5 is `observers.stream().forEach(o -> o.update())`, and the obvious implementation is
// "walk the object chain down to the base identifier, then resolve the element type from it".
// That is right when every operation in the chain preserves the element type:
//
//     observers.stream().forEach(...)                        base = observers, elements Observer  OK
//     observers.stream().filter(o -> o.isActive()).forEach(...)   filter preserves the type       OK
//
// It is WRONG here. `map` replaces each element with whatever the mapper returns, so the things
// reaching forEach are Tag, not Observer -- but the base identifier is still `observers`, so a
// naive chain walk resolves Observer and credits a notification loop that does not exist.
//
// map() is common in generated Java. This is not a theoretical case.
//
// THE RULE TAKEN (docs/PROPERTY_SPEC.md): walk the chain, but STOP at any operation not known to
// preserve the element type. Allowed: stream, filter, sorted, distinct, limit, skip, peek,
// parallelStream, unmodifiableList/Set/Collection. Everything else -- map, flatMap, mapToObj,
// mapToDouble, and anything unrecognised -- rejects the chain. Unrecognised is rejected rather
// than allowed, because the corpus cannot tell us and narrower is the safe default for a NEW
// detector.
//
// EXPECTED, BEFORE AND AFTER form 5 lands: O1=1 O2=0 O3=0 O4=0, PIQS 22.27.
// A flip here means the chain walk is resolving the element type from the wrong end.

import java.util.*;

interface Observer {
    void update();
}

class Tag {
    void update() {
    }
}

class ConcreteObserver implements Observer {
    private Tag tag = new Tag();

    public void update() {
    }

    Tag getTag() {
        return tag;
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
        observers.stream().map(o -> o.getTag()).forEach(t -> t.update());
    }
}
