// Category: generics -- a field whose type has TWO type arguments was invisible to the regex.
//
// _FIELD_RE's type group is [A-Za-z_][A-Za-z0-9_<>\[\]\.]*? -- it admits < and > but neither a
// comma nor a space, so it cannot span `Map<String, Handler>`. The group cannot reach the field
// name, the whole declaration fails to match, and the field vanished from the model rather than
// being recorded with a wrong type.
//
// `ordered` and below are the controls: one type argument, an array, and a plain type all
// matched the regex, and must keep matching under the parser.

import java.util.*;

class Registry {
    private Map<String, Handler> handlers;                     // two type arguments -- regex saw nothing
    private static final Map<String, Double> RATES = new HashMap<>();  // and with modifiers
    private Map<String, List<Handler>> grouped;                // nested generic
    private List<Handler> ordered;                             // one type argument -- regex saw this
    private Handler[] cached;                                  // array
    private Handler primary;                                   // plain
}

interface Handler {
    void handle(String s);
}
