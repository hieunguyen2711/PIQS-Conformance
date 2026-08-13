// `this.`-RECEIVER TWIN of loop1_enhanced_for.java -- loop form: enhanced-for
//
// Byte-identical to its twin except that every reference to the field `observers` inside a
// method body is written `this.observers`. Nothing else differs: same types, same field, same
// method names, same imports. Generated from the twin by a mechanical receiver rewrite, so the
// difference can be verified by diff rather than asserted.
//
// THE DEFECT THIS PINS. `this.observers` is a field_access node, not an identifier. Loop forms
// 2-6 resolve the collection through `_collection_of` in piqs/parser.py, which returned None for
// anything that was not a bare identifier; form 1 resolves it through `foreach_re` in
// `_evaluate_observer`, whose collection group matched a bare identifier only. Either way the
// element type was never resolved, the loop did not exist as far as the evaluator was concerned,
// and O2, O3 and O4 -- the WHOLE CRITICAL SET -- were 0. The program was not recognised as
// Observer at all, scoring PIQS 0 against 77.73 for the same program written without `this.`.
//
// It is not a naming defect, so tests/test_renaming_invariance.py cannot catch it. It is a
// SHAPE defect: it scores one way of writing a program far above another. `this.field` is the
// ordinary style when a parameter shadows a field, which is exactly what a setter does.
//
// Kim's corpus contains zero `this.`-prefixed traversals, so all five suites stay green with the
// defect present. These twins are the only thing that can see it.

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
        this.observers.add(o);
    }

    public void notifyObservers() {
        for (Observer o : this.observers) {
            o.update();
        }
    }
}
