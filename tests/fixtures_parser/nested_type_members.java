// Category: nested-type -- a nested type's members were also recorded on the ENCLOSING type.
//
// The regex ran its signature scan over the enclosing type's whole body TEXT, and that text
// contains the nested type's body, so `Outer` was credited with `Inner`'s `label` and `build`
// (owner="Outer"). `Inner` was extracted correctly too -- this was duplication onto the parent,
// not loss.
//
// Fields were already scoped correctly, because _class_scope_only stripped everything at
// brace-depth > 0, which includes nested type bodies.
//
// Both types must still appear as TOP-LEVEL entries keyed by simple name: the flattening the
// regex got for free by scanning whole-file text is load-bearing for singleton detection
// (static_instance_of searches every class for a static field of the singleton's type, which is
// how the Bill Pugh holder idiom is recognised).

class Outer {
    private int value;

    public int getValue() {
        return value;
    }

    public static class Inner {
        private String label;

        public Inner label(String l) {
            this.label = l;
            return this;
        }

        public Outer build() {
            return new Outer();
        }
    }
}
