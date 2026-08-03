# missing-public-class-attribute-documentation (PDF508)

Fix is not available.

Rule is disabled if `docstring-convention` is `none` or `pep257`.

## What it does
Checks that public class attributes are documented either in the class docstring attribute documentation or by an adjacent attribute docstring.

The rule compares supported class attribute assignments against names documented in Google `Attributes` sections, NumPy `Attributes` sections, reStructuredText `:ivar:`, `:cvar:`, and `:var:` value fields, and adjacent attribute docstrings. A type-only `:vartype:` field activates the consistency check but does not document the attribute value. Class-scope assignments, annotated assignments, multi-target assignments, tuple-unpacked assignment leaves, and proven literal slot members are inventoried. Private attributes are never required.

By default, class-scope attributes are required and instance attributes from `self.*` assignments in `__init__` or literal slot declarations are accepted as existing attributes but are not required. Enable `docstring-require-init-attribute-documentation` to require both instance-attribute sources. Inventory deduplication follows that eligibility policy: if a slot member later has a real class declaration, the real declaration is still required by default and owns the finding line, while enabling instance requirements lets the earlier slot literal own the first-source position. Slot names are collected only from the final effective direct class-body `__slots__` assignment when it is a string literal or a tuple made entirely of string literals. Mutable list values do not provide proven inventory because later mutation or aliasing can change the runtime slots. Every exact class-scope rebinding or deletion is considered in source order, including structural pattern captures: a dynamic, conditional, compound, captured, or deleted final binding contributes no slot members, while a later supported direct assignment recovers a static inventory and an annotation-only declaration does not rebind the previous value.

Evaluated slot strings must satisfy `str.isidentifier()`; their exact decoded spellings and literal order are retained without keyword rejection or private-name mangling. Duplicates, `__dict__`, `__weakref__`, and non-identifiers are ignored. Slots are never inherited into a subclass inventory. Assignments inside methods other than `__init__`, list destructuring targets, unsupported tuple leaves, subscript targets, `cls.*`, and arbitrary object attributes are not class attribute inventory entries for this rule.

PDF508 checks whether public class attributes have any recognized documentation. It does not care whether that documentation is in the class docstring or attached to the assignment; use PDF518 or PDF519 for a location policy, PDF509 for stale class docstring entries, and PDF512 for duplicated class attribute documentation.

## Why is this useful?
Class attribute documentation can otherwise drift from the actual class surface.

## Ruff compatibility
Ruff's `RUF023` sorts literal `__slots__` declarations, while `PLE0237` reports assignments to attributes absent from slots. PDF508 instead uses proven slot members to check documentation completeness.

## Examples
Missing public class attribute documentation is reported when a class has attribute documentation but omits a public class attribute:

```pydocfmt-example
[settings]
docstring-convention = "google"

[input]
class Client:
    """HTTP client.

    Attributes:
        timeout (float): Request timeout.
    """

    timeout: float
    retries: int

[output=unchanged]
[findings]
PDF508: Line 9: Public class attribute 'retries' is missing docstring documentation
```

An empty recognized `Attributes` section still opts the class into missing attribute checks:

```pydocfmt-example
[settings]
docstring-convention = "google"

[input]
class Client:
    """HTTP client.

    Attributes:
    """

    timeout: float

[output=unchanged]
[findings]
PDF508: Line 7: Public class attribute 'timeout' is missing docstring documentation
```

Adjacent attribute docstrings document their assignments, including every simple target in a multi-target assignment and supported tuple-unpacked assignment. Private attributes are not required:

```pydocfmt-example
[settings]
docstring-convention = "google"

[input]
class Client:
    timeout: float
    """Request timeout."""

    primary = fallback = "https://example.com"
    """Request endpoints."""

    host, (port, *aliases) = endpoint_parts
    """Unpacked endpoint parts."""

    _token: str

[output=unchanged]
```

NumPy comma-separated attribute entries document each listed name independently:

```pydocfmt-example
[settings]
docstring-convention = "numpy"

[input]
class Client:
    """HTTP client.

    Attributes
    ----------
    primary, fallback : str
        Request endpoints.
    """

    primary = fallback = "https://example.com"
    retries: int

[output=unchanged]
[findings]
PDF508: Line 11: Public class attribute 'retries' is missing docstring documentation
```

Under the reST convention, a type-only field activates the consistency check but does not document any inventory attribute. An empty value field does document its named attribute for PDF508; description quality is handled by PDF712:

```pydocfmt-example
[settings]
docstring-convention = "rest"

[input]
class Client:
    """HTTP client.

    :vartype removed: int
    :var retries:
    """

    timeout: float
    retries: int

[output=unchanged]
[findings]
PDF508: Line 8: Public class attribute 'timeout' is missing docstring documentation
```

The `all-docstrings` policy can require attributes even when a public class has only a summary. With the public-only setting enabled, a private class without explicit attribute documentation is skipped:

```pydocfmt-example
[settings]
docstring-convention = "google"
docstring-missing-documentation = "all-docstrings"
docstring-missing-documentation-public-only = true

[input]
class PublicClient:
    """Public client."""

    timeout: float


class _PrivateClient:
    """Private client."""

    retries: int

[output=unchanged]
[findings]
PDF508: Line 4: Public class attribute 'timeout' is missing docstring documentation
```

`self.*` assignments in `__init__` are required only when `docstring-require-init-attribute-documentation` is enabled:

```pydocfmt-example
[settings]
docstring-convention = "google"
docstring-require-init-attribute-documentation = true

[input]
class Client:
    """HTTP client.

    Attributes:
        timeout (float): Request timeout.
    """

    timeout: float

    def __init__(self):
        self.retries = 3

[output=unchanged]
[findings]
PDF508: Line 11: Public class attribute 'retries' is missing docstring documentation
```

The same setting controls proven literal slot members. With it enabled, each undocumented public member of the final effective literal `__slots__` declaration is required:

```pydocfmt-example
[settings]
docstring-convention = "google"
docstring-require-init-attribute-documentation = true

[input]
class Point:
    """Point.

    Attributes:
        x (float): Horizontal coordinate.
    """

    __slots__ = ("x", "y")

[output=unchanged]
[findings]
PDF508: Line 8: Public class attribute 'y' is missing docstring documentation
```

## Options
- `docstring-missing-documentation`: Controls whether missing class attribute documentation is reported only when attribute documentation already exists, for non-summary class docstrings, or for all eligible class docstrings.
- `docstring-missing-documentation-public-only`: Skips private classes for broad missing-class-attribute checks when enabled.
- `docstring-require-init-attribute-documentation`: Requires supported `self.*` assignments in `__init__` and proven literal slot members to have class attribute documentation when enabled.
