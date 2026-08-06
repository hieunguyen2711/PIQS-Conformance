// Guards the `not m.has_body` skip in _fully_delegates (Decorator D6, piqs/checker.py).
//
// An abstract decorator base may implement part of the component API by forwarding and leave
// the rest abstract for its concrete decorators to supply. A bodyless declaration is NOT
// implemented, so it is out of D6's scope -- D6 asks whether every operation the wrapper
// IMPLEMENTS forwards to the wrapped reference.
//
// Remove the skip and `describe` enters `implemented`, `_delegates_to_field("")` returns False,
// and this correct abstract base scores D6=0 instead of 1.
//
// Shape matters here:
//   * ComponentDecorator is ABSTRACT, holds the Component field, forwards `read`, and leaves
//     `describe` abstract. It is the only entry in `decorators`, so it alone decides D6.
//   * LoudDecorator deliberately declares NO component-typed field of its own -- it inherits
//     `inner`. `decorators` is built from `w.fields` (own fields only), so a field here would
//     put LoudDecorator in the list, `d6 = any(...)` would find its fully-forwarding self, and
//     D6 would be 1 whether or not the skip exists. The case would prove nothing.

interface Component {
    String read();

    String describe();
}

class BaseComponent implements Component {
    public String read() {
        return "raw";
    }

    public String describe() {
        return "base";
    }
}

abstract class ComponentDecorator implements Component {
    protected Component inner;

    ComponentDecorator(Component inner) {
        this.inner = inner;
    }

    public String read() {
        return inner.read();
    }

    public abstract String describe();
}

class LoudDecorator extends ComponentDecorator {
    LoudDecorator(Component inner) {
        super(inner);
    }

    public String describe() {
        return inner.describe().toUpperCase();
    }
}
