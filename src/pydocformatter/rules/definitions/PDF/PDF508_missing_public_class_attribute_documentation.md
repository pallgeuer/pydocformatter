# missing-public-class-attribute-documentation (PDF508)

Fix is not available.

Rule is disabled if `docstring-convention` is `none` or `pep257`.

## What it does
Checks that public class attributes are documented either in the class docstring attribute documentation or by an adjacent attribute docstring.

The rule compares supported class attribute assignments against names documented in Google `Attributes` sections, NumPy `Attributes` sections, reStructuredText `:ivar:`, `:cvar:`, and `:var:` value fields, and adjacent attribute docstrings. A type-only `:vartype:` field activates the consistency check but does not document the attribute value. Class-scope assignments, annotated assignments, multi-target assignments, and tuple-unpacked assignment leaves are inventoried. Private attributes are never required.

By default, class-scope attributes are required and `self.*` assignments from `__init__` are accepted as existing attributes but are not required. Enable `docstring-require-init-attribute-documentation` to require supported `self.*` assignments too. Assignments inside methods other than `__init__`, list destructuring targets, unsupported tuple leaves, subscript targets, `cls.*`, and arbitrary object attributes are not class attribute inventory entries for this rule.

PDF508 checks whether public class attributes have any recognized documentation. It does not care whether that documentation is in the class docstring or attached to the assignment; use PDF518 or PDF519 for a location policy, PDF509 for stale class docstring entries, and PDF512 for duplicated class attribute documentation.

## Why is this useful?
Class attribute documentation can otherwise drift from the actual class surface.

## Ruff compatibility
None.

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

## Options
- `docstring-missing-documentation`: Controls whether missing class attribute documentation is reported only when attribute documentation already exists, for non-summary class docstrings, or for all eligible class docstrings.
- `docstring-missing-documentation-public-only`: Skips private classes for broad missing-class-attribute checks when enabled.
- `docstring-require-init-attribute-documentation`: Requires supported `self.*` assignments in `__init__` to have class attribute documentation when enabled.
