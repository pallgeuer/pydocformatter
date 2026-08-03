# class-attribute-type-mismatch (PDF715)

Fix is not available.

Rule is disabled if `docstring-convention` is `none` or `pep257`.

Rule is incompatible with `PDF714`.

## What it does
Checks that parsed class attribute docstring types conservatively match annotated class or instance attributes. It checks only entries in the owning class docstring that match inventoried attributes and have both a documented type and a usable annotation. Proven literal slot members participate in the inventory, but a slot-only member has no annotation to compare; the first real annotated assignment of the same name supplies the comparison annotation without changing first-source order, and later redeclarations do not replace it. Attached attribute docstrings are outside the scope of PDF7xx rules.

The comparison uses a syntax-only type-expression subset that covers common names, qualified names, subscriptions, tuples, unions, and stringized annotations. Unshadowed import aliases are normalized before comparison. Unparseable, unsupported, or ambiguous expressions are skipped instead of guessed.

Google, NumPy, and inline or paired reStructuredText types are supported. NumPy entries that document multiple names are checked once per matching attribute. Unlike PDF713, this rule does not invert its policy for enum-like classes. Findings are diagnostic-only because choosing between conflicting documentation and code requires human judgment.

## Why is this useful?
Stale class attribute type text can mislead readers when annotations have changed.

## Ruff compatibility
Ruff's `RUF023` and `PLE0237` inspect slot order and non-slot assignments. PDF715 instead compares documented slot types with annotations from real declarations of the same name.

## Examples
PDF715 reports class attribute docstring types that do not match annotations:

```pydocfmt-example
[settings]
docstring-convention = "google"

[input]
class Client:
    """Client.

    Attributes:
        timeout (str): Timeout in seconds.
    """

    timeout: int = 1

[output=unchanged]
[findings]
PDF715: Line 5: Class attribute 'timeout' docstring type does not match the annotation
```

Matching class attribute types are accepted:

```pydocfmt-example
[settings]
docstring-convention = "google"

[input]
class Client:
    """Client.

    Attributes:
        timeout (int): Timeout in seconds.
    """

    timeout: int = 1

[output=unchanged]
```

For paired reStructuredText fields, a mismatch is reported on the `:vartype:` field:

```pydocfmt-example
[settings]
docstring-convention = "rest"

[input]
class Client:
    """Client.

    :var timeout: Timeout in seconds.
    :vartype timeout: str
    """

    timeout: int = 1

[output=unchanged]
[findings]
PDF715: Line 5: Class attribute 'timeout' docstring type does not match the annotation
```

NumPy entries that document multiple names are checked once per matching attribute:

```pydocfmt-example
[settings]
docstring-convention = "numpy"

[input]
class Client:
    """Client.

    Attributes
    ----------
    primary, fallback : str
        Request endpoints.
    """

    primary: str
    fallback: int

[output=unchanged]
[findings]
PDF715: Line 6: Class attribute 'fallback' docstring type does not match the annotation
```

A later real annotation supplies comparison data for a slot name. Slot-only members without annotations remain outside mismatch comparison rather than being guessed:

```pydocfmt-example
[settings]
docstring-convention = "google"

[input]
class Point:
    """Point.

    Attributes:
        x (str): Horizontal coordinate.
        y (bytes): Vertical coordinate.
    """

    __slots__ = ("x", "y")
    x: float

[output=unchanged]
[findings]
PDF715: Line 5: Class attribute 'x' docstring type does not match the annotation
```

## Options
None.
