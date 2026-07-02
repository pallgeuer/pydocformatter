# missing-class-attribute-documentation (PDF508)

Fix is not available.

Rule is ignored if `docstring-convention` is `none` or `pep257`.

## What it does
Checks that public class attributes are documented either in the class docstring attribute documentation or by an adjacent attribute docstring.

The rule compares supported class attribute assignments against names documented in Google `Attributes` sections, NumPy `Attributes` sections, reStructuredText `:ivar:`, `:cvar:`, `:var:`, and `:vartype:` fields, and adjacent attribute docstrings. Class-scope assignments, annotated assignments, multi-target assignments, and tuple-unpacked assignment leaves are inventoried. Private attributes are never required.

By default, class-scope attributes are required and `self.*` assignments from `__init__` are accepted as existing attributes but are not required. Enable `docstring-require-init-attribute-documentation` to require supported `self.*` assignments too. Assignments inside methods other than `__init__`, list destructuring targets, unsupported tuple leaves, subscript targets, `cls.*`, and arbitrary object attributes are not class attribute inventory entries for this rule.

## Why is this useful?
Class attribute documentation can otherwise drift from the actual class surface.

## Ruff compatibility
None.

## Examples
Missing class attribute documentation is reported when a class has attribute documentation but omits a public class attribute:

```pydocfmt-example
[settings]
docstring-convention = "google"

[input]
class Client:
    """HTTP client.

    Attributes:
        timeout: Request timeout.
    """

    timeout: float
    retries: int

[output=unchanged]
[findings]
PDF508: Line 9: Class attribute 'retries' is missing docstring documentation
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
PDF508: Line 7: Class attribute 'timeout' is missing docstring documentation
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
PDF508: Line 11: Class attribute 'retries' is missing docstring documentation
```

reStructuredText attribute fields are parsed under the `rest` convention:

```pydocfmt-example
[settings]
docstring-convention = "rest"

[input]
class Client:
    """HTTP client.

    :ivar timeout: Request timeout.
    """

    timeout: float
    retries: int

[output=unchanged]
[findings]
PDF508: Line 8: Class attribute 'retries' is missing docstring documentation
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
        timeout: Request timeout.
    """

    timeout: float

    def __init__(self):
        self.retries = 3

[output=unchanged]
[findings]
PDF508: Line 11: Class attribute 'retries' is missing docstring documentation
```

## Options
- `docstring-convention`: Controls whether Google `Attributes` sections, NumPy `Attributes` sections, or reST attribute fields are parsed. Ignored by broad rule selections under `none` and `pep257`.
- `docstring-missing-documentation`: Controls when PDF508 is active. `has-section` reports only owners with recognized attribute documentation, including attached attribute docstrings. `non-summary-docstrings` additionally reports public class docstrings with more than just a summary. `all-docstrings` additionally reports all public class docstrings.
- `docstring-missing-documentation-public-only`: When `true`, missing-attribute checks skip private classes. Private attributes are never required by PDF508.
- `docstring-require-init-attribute-documentation`: When `true`, supported `self.*` assignments in `__init__` are also required by PDF508.
