# public-class-attribute-docstring-must-be-attached (PDF519)

Fix is not available.

Rule is disabled if `docstring-convention` is `none` or `pep257`.

Rule must by default be explicitly selected, unless it is removed from `require-explicit`.

Rule is incompatible with `PDF518`.

## What it does
Checks for public class attributes documented in class docstring attribute entries when public class attribute documentation must use attached docstrings.

PDF519 checks parsed Google `Attributes` sections, NumPy `Attributes` sections, and reStructuredText attribute fields when the matching convention is active. The documented name must also match a supported class-scope attribute or supported `self.*` attribute assigned in `__init__`.

PDF519 is a location policy: it reports inventory-backed public class attributes documented in the class docstring because attached docstrings are required. It does not report stale class docstring entries; use PDF509 for those, PDF508 for missing documentation, and PDF512 for duplicates when both locations are allowed.

## Why is this useful?
Attached docstrings keep attribute documentation next to the assignment, which can be clearer for projects with many class attributes or conditional instance attributes.

## Ruff compatibility
None.

## Examples
A public class attribute documented in the class docstring is reported:

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

[output=unchanged]
[findings]
PDF519: Line 5: Public class attribute 'timeout' must use attached docstring, not class docstring documentation
```

NumPy entries are checked name by name. Stale documented names are left to PDF509, while repeated owner entries are reported independently:

```pydocfmt-example
[settings]
docstring-convention = "numpy"

[input]
class Client:
    """HTTP client.

    Attributes
    ----------
    primary, fallback, stale : str
        Endpoint values.
    primary : str
        Repeated primary endpoint.
    """

    primary = fallback = ""

[output=unchanged]
[findings]
PDF519: Line 6: Public class attribute 'primary' must use attached docstring, not class docstring documentation
PDF519: Line 6: Public class attribute 'fallback' must use attached docstring, not class docstring documentation
PDF519: Line 8: Public class attribute 'primary' must use attached docstring, not class docstring documentation
```

reStructuredText fields and supported `self.*` assignments from `__init__` are also checked:

```pydocfmt-example
[settings]
docstring-convention = "rest"

[input]
class Client:
    """HTTP client.

    :ivar timeout: Request timeout.
    :vartype retries: int
    """

    def __init__(self):
        self.timeout = 30.0
        self.retries = 3

[output=unchanged]
[findings]
PDF519: Line 4: Public class attribute 'timeout' must use attached docstring, not class docstring documentation
PDF519: Line 5: Public class attribute 'retries' must use attached docstring, not class docstring documentation
```

When the active convention does not parse attribute entries, class docstring attribute-looking text is ignored:

```pydocfmt-example
[settings]
docstring-convention = "pep257"

[input]
class Client:
    """HTTP client.

    Attributes:
        timeout: Request timeout.
    """

    timeout: float

[output=unchanged]
```

## Options
None.
