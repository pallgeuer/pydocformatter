# duplicate-class-attribute-documentation (PDF512)

Fix is not available.

Rule is ignored if `docstring-convention` is `none` or `pep257`.

## What it does
Checks for class attributes documented both in the class docstring attribute documentation and by an adjacent attached attribute docstring.

The rule compares names documented in Google `Attributes` sections, NumPy `Attributes` sections, and reStructuredText `:ivar:`, `:cvar:`, `:var:`, and `:vartype:` fields against adjacent class-scope and supported `self.*` `__init__` attribute docstrings. Class-scope assignments, annotated assignments, multi-target assignments, and tuple-unpacked assignment leaves are matched by target name. Attached docstrings for `self.*` assignments in `__init__` are treated as class attribute docstrings, independent of missing-attribute settings. Assignments inside methods other than `__init__`, nested class attributes owned by another class, list destructuring targets, unsupported tuple leaves, subscript targets, `cls.*`, and arbitrary object attributes are not class attribute docstrings for this rule.

Findings are reported on the attached attribute docstring, not on the class docstring entry. This lets one duplicate be suppressed or removed without suppressing duplicate checks for the rest of the class docstring. If one attached docstring documents multiple targets, the rule reports one finding for each target that is also documented in the class docstring. If the class docstring repeats the same attribute entry, each repeated owner entry is reported against the attached docstring.

PDF512 reports duplicate class attribute documentation but does not choose which location is preferred. Projects that enforce a strict location policy with PDF518 or PDF519 may not need PDF512, especially if the preferred location rule already makes the duplicate impossible.

## Why is this useful?
Duplicated attribute documentation can drift when one copy is updated and the other is missed.

## Ruff compatibility
None.

## Examples
A class attribute documented in both places is reported on the attached attribute docstring:

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
    """Request timeout in seconds."""

[output=unchanged]
[findings]
PDF512: Line 9: Attached docstring for class attribute 'timeout' duplicates class docstring attribute documentation
```

Using only one attribute documentation style is accepted:

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

class Transport:
    retries: int
    """Retry attempts."""

[output=unchanged]
```

NumPy comma-separated attribute entries are checked name by name:

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
    """Request endpoint values."""

[output=unchanged]
[findings]
PDF512: Line 11: Attached docstring for class attribute 'primary' duplicates class docstring attribute documentation
PDF512: Line 11: Attached docstring for class attribute 'fallback' duplicates class docstring attribute documentation
```

Only names documented in the class docstring are reported when an attached docstring belongs to multiple targets:

```pydocfmt-example
[settings]
docstring-convention = "google"

[input]
class Client:
    """HTTP client.

    Attributes:
        primary (str): Primary endpoint.
        aliases (tuple[str, ...]): Endpoint aliases.
    """

    primary, (fallback, *aliases) = endpoints
    """Request endpoints."""

[output=unchanged]
[findings]
PDF512: Line 10: Attached docstring for class attribute 'primary' duplicates class docstring attribute documentation
PDF512: Line 10: Attached docstring for class attribute 'aliases' duplicates class docstring attribute documentation
```

reStructuredText `:ivar:`, `:cvar:`, `:var:`, and `:vartype:` fields are attribute documentation under the `rest` convention:

```pydocfmt-example
[settings]
docstring-convention = "rest"

[input]
class Client:
    """HTTP client.

    :cvar timeout: Request timeout.
    :vartype retries: int
    """

    timeout: float
    """Request timeout in seconds."""
    retries: int
    """Retry attempts."""

[output=unchanged]
[findings]
PDF512: Line 9: Attached docstring for class attribute 'timeout' duplicates class docstring attribute documentation
PDF512: Line 11: Attached docstring for class attribute 'retries' duplicates class docstring attribute documentation
```

Attached `self.*` attribute docstrings from `__init__` are checked even when missing-attribute checks do not require instance attributes. Similar docstrings inside other methods are not class attribute docstrings for this rule:

```pydocfmt-example
[settings]
docstring-convention = "google"
docstring-require-init-attribute-documentation = false

[input]
class Client:
    """HTTP client.

    Attributes:
        timeout (float): Request timeout.
        retries (int): Retry count.
    """

    def __init__(self):
        self.timeout = 30.0
        """Request timeout in seconds."""

    def configure(self):
        self.retries = 3
        """Retry attempts."""

[output=unchanged]
[findings]
PDF512: Line 11: Attached docstring for class attribute 'timeout' duplicates class docstring attribute documentation
```

## Options
- `docstring-convention`: Controls whether Google `Attributes` sections, NumPy `Attributes` sections, or reST attribute fields are parsed. Ignored by broad rule selections under `none` and `pep257`.
- `docstring-require-init-attribute-documentation`: Does not control PDF512. Attached `self.*` docstrings from `__init__` can duplicate class docstring attribute documentation whether or not missing-attribute rules require instance attribute documentation.
