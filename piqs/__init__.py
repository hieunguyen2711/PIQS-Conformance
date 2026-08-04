"""piqs -- structural design-pattern conformance checking for Java source.

Two public pieces:

* :class:`~piqs.checker.PIQSChecker` -- decides whether a set of Java source files
  structurally conforms to a design pattern, and scores that conformance (PSR / CPC / PIQS).
* :mod:`piqs.obfuscator` -- renames every user-defined identifier in a set of Java sources,
  so the checker's verdicts can be shown not to depend on identifier names.
"""

from piqs.checker import PIQSChecker, _CRITICAL_PROPERTIES, _PATTERN_WEIGHTS

__all__ = ["PIQSChecker", "_PATTERN_WEIGHTS", "_CRITICAL_PROPERTIES"]

SUPPORTED_PATTERNS = tuple(sorted(_PATTERN_WEIGHTS))
