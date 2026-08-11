// A DECORATOR THAT FORWARDS NOTHING, FULLY RECOGNISED. Kept VERBATIM as reported.
//
// MEASURED VERDICT ON THIS FILE, 2026-08-10, commit 0591488:
//
//     D2 1   D3 1   D4 1   D6 1      PSR 100.0   CPC 100.0   PIQS 100.0   Excellent
//
// Before D1 and D5 were deleted it scored a perfect SIX. It now scores a perfect FOUR. The
// deletions did not cause this and do not affect it.
//
// WHY IT HAPPENS. The candidate loop in `_evaluate_decorator` reads `w.fields` -- OWN fields only,
// never `_effective_fields`. `Broken extends Base` inherits `inner` and declares no field of its
// own, so `w.fields` is empty for it and it is never a decorator candidate. `Base` is the only
// class judged, and `Base` is impeccable.
//
// That is the canonical GoF Decorator shape: an abstract base holds the component, concrete
// decorators extend it. ONLY THE BASE IS EVER JUDGED. And D2, D3, D4 and D6 are each an
// `any(...)` over the candidate list, so one compliant class carries the whole program.
//
// TWO INDEPENDENT DEFECTS, AND FIXING EITHER ALONE LEAVES THIS AT 100:
//
//     admission        quantifier          D2 D3 D4 D6   PIQS
//     own fields       any    (CURRENT)     1  1  1  1   100.0
//     own fields       all                  1  1  1  1   100.0     Base is the only candidate
//     effective fields any                  1  1  1  1   100.0     Base still satisfies every any()
//     effective fields all                  1  0  1  0    52.22    the only one that catches it
//
// NOTHING IS FIXED HERE. Both questions are open design decisions, recorded in docs/STATE.md.
// This file exists so the reproduction stays exact while they are decided.
//
// NOTE ON NAMES: TWO type names here are also declared elsewhere in this directory --
// `Conduit` by d4_abstract_base_partial_api.java, and `Base` by shadowed_inherited_field.java.
// The duplicates are deliberate: the program is kept VERBATIM as reported so the reproduction
// stays exact, and every tool that reads this directory (golden_facts.py, the checker, every
// test) parses ONE FILE AT A TIME, so a collision cannot affect any measurement. It would matter
// only to a `javac` run over the whole directory, which nothing in this repo does.
// Elsewhere in this directory collisions ARE avoided -- the probe was renamed Sink -> Conduit for
// exactly that reason -- so this exception is a deliberate trade for verbatim reproduction, not
// an oversight.
interface Conduit { void write(String s); void flush(); }
abstract class Base implements Conduit {
    protected Conduit inner;
    Base(Conduit i){ inner = i; }
    public void write(String s){ inner.write(s); }
    public void flush(){ inner.flush(); }
}
class Broken extends Base {
    Broken(Conduit i){ super(i); }
    public void write(String s){ System.out.println(s); }   // NEVER forwards
    public void flush(){ System.out.println("done"); }      // NEVER forwards
}
