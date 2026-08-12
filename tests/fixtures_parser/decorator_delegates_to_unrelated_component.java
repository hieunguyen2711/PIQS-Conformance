// The fixture that separates the two ways of writing the same-component rule.
//
// `Router` conforms to `Pump` and holds a `Pump` -- so it IS a decorator candidate under either
// rule. But it also holds a `Valve`, an unrelated abstract type, and its `drive()` forwards to
// the VALVE, never to the pump it wraps.
//
//   (A) gate ADMISSION only  -- keep wrapped_fields = every component-typed field.
//       `Router` is admitted because of `held`, then D3 searches ALL its component-typed
//       fields and finds the delegation to `aux`. D3 = 1. Recognised as a Decorator while
//       never once forwarding to the thing it wraps.
//
//   (B) filter the FIELD LIST -- wrapped_fields keeps only fields of a conformed type.
//       D3 asks only about `held`. `drive()` does not touch it. D3 = 0.
//
// (B) is implemented. Without this fixture, (A) and (B) are indistinguishable: every program in
// the corpus holds exactly one component-typed field, so the filter has nothing to remove and
// the two rules agree everywhere.
interface Pump { void drive(); }
interface Valve { void open(); }
class Router implements Pump {
    private Pump held;
    private Valve aux;
    public Router(Pump held, Valve aux) { this.held = held; this.aux = aux; }
    public void drive() { aux.open(); }
}
