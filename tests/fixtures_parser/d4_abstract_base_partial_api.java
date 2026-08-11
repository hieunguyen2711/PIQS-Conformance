// THE D4 PROBE. Does D4 carry information D2 does not?
//
// In the BDT battery D4 == 1 in all 8 recognised decorators, which proves nothing: `d4` is an
// `any(...)` over every decorator in the program, and for a CONCRETE class the Java compiler
// already forces the implemented method set to cover the whole interface. One concrete decorator
// therefore sets D4 for the whole program, and every battery case has one.
//
// This program has NO concrete decorator. `Damper` is abstract and implements only `write`,
// leaving `flush` for its subclasses -- which is legal Java, and is exactly what an abstract
// decorator base looks like before any concrete decorator is written.
//
// The check in `_transparent` is `comp_ops <= wnames`, where wnames comes from
// `_effective_methods`. That helper walks `extends` ONLY, never `implements` (checker.py:353), so
// `wnames` here is {write} while `comp_ops` is {write, flush}. D4 = 0, with D2 = 1.
//
// If this fixture ever scores D4 = 1, D4 has become another restatement of D2 and the Decorator
// property set is down to three. Pinned by tests/test_decorator_property_independence.py.
//
// Names are `Conduit` / `Damper` rather than the obvious `Sink` / `Filter` because
// shadowed_inherited_field.java in this same directory already declares a `Sink`.
interface Conduit {
    void write(String s);
    void flush();
}

abstract class Damper implements Conduit {
    protected Conduit inner;

    Damper(Conduit inner) {
        this.inner = inner;
    }

    public void write(String s) {
        inner.write(s);
    }
}
