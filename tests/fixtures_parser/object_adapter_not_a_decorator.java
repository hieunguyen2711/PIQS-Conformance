// A TEXTBOOK OBJECT ADAPTER. It must NOT be recognised as a Decorator.
//
// `Adapt` conforms to `Target` and holds a `Source`. Two DIFFERENT abstract types: that is
// what makes it an adapter -- it converts one interface into another. A decorator conforms to
// and holds the SAME type, which is why it can wrap another decorator.
//
// Before the same-component rule this scored D1 0 D2 1 D3 1 D4 0 D5 1 D6 0, PIQS 53.33
// "Moderate". D2 and D3 are the critical set, so it was RECOGNISED as a Decorator. The
// docstring for isDecorator already said "conforms to a component C AND holds a field of type
// C" -- same C twice -- but the code compared two independent sets and never required them to
// intersect. The same-type requirement lived only in D1 and D4, both weight 2 and non-critical,
// so they flagged the conversion without affecting recognition.
//
// This file is kept VERBATIM as it was first reported, so the reproduction stays exact.
interface Target { void run(); }
interface Source { void go(); }
class Adapt implements Target {
    private Source s;
    public Adapt(Source s) { this.s = s; }
    public void run() { s.go(); }
}
