// O3 NEGATIVE -- a shopping cart adding up prices notifies nobody.
//
// THE DEFECT THIS PINS. O3 is weight 3 and CRITICAL, and its published sentence is "Subject
// notifies all registered observers." Before this change O3 read "a loop over a collection calls
// a method on each element", and this program satisfied it: O3 = 1, PIQS 25.91, for a program
// containing no Observer at all. Three of eleven points, free, in every experimental condition.
//
// TWO INDEPENDENT REASONS IT IS NOT NOTIFICATION, and the fixture is built so either alone would
// catch it:
//
//   * `LineItem` is CONCRETE. An observer is an abstract role -- a subject notifies through an
//     interface, which is what lets the dependent set vary. A loop over concrete records is
//     arithmetic.
//   * even with an abstract element, `total()` reads values back to accumulate a sum rather than
//     pushing a change outward.
//
// Note `add(LineItem l) { lines.add(l); }` is EXACTLY the "maintains the collection" shape, which
// is why the maintenance rule alone does not reject this program. It takes the abstract-element
// rule to do that. Both are implemented; this fixture is why neither is sufficient alone.

import java.util.*;

class LineItem {
    private int amt;

    public int getSubTotal() {
        return amt;
    }
}

class Cart {
    private List<LineItem> lines = new ArrayList<>();

    public void add(LineItem l) {
        lines.add(l);
    }

    public int total() {
        int t = 0;
        for (LineItem l : lines) {
            t += l.getSubTotal();
        }
        return t;
    }
}
