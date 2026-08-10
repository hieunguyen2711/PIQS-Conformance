// An OBJECT ADAPTER, not a Decorator: PrinterAdapter IS-A Printer but HAS-A LegacyWriter.
// Two different abstract types -- it converts an interface rather than wrapping one.
interface Printer { void print(String text); }
interface LegacyWriter { void writeLine(String s); }
class PrinterAdapter implements Printer {
    private final LegacyWriter legacy;
    public PrinterAdapter(LegacyWriter legacy) { this.legacy = legacy; }
    public void print(String text) { legacy.writeLine(text); }
}
