# duplicate-module-attribute-documentation (PDF513)

Fix is not available.

Rule is ignored if `docstring-convention` is `none` or `pep257`.

## What it does
Checks for module attributes documented both in the module docstring attribute documentation and by an adjacent attached attribute docstring.

The rule compares names documented in Google `Attributes` sections, NumPy `Attributes` sections, and reStructuredText `:ivar:`, `:cvar:`, `:var:`, and `:vartype:` fields against adjacent module attribute docstrings. Module assignments, annotated assignments, multi-target assignments, and tuple-unpacked assignment leaves are matched by target name. Class attributes, function-local assignments, list destructuring targets, unsupported tuple leaves, subscript targets, and arbitrary object attributes are not module attribute docstrings for this rule.

Findings are reported on the attached attribute docstring, not on the module docstring entry. This lets one duplicate be suppressed or removed without suppressing duplicate checks for the rest of the module docstring. If one attached docstring documents multiple targets, the rule reports one finding for each target that is also documented in the module docstring. If the module docstring repeats the same attribute entry, each repeated owner entry is reported against the attached docstring.

## Why is this useful?
Duplicated attribute documentation can drift when one copy is updated and the other is missed.

## Ruff compatibility
None.

## Examples
A module attribute documented in both places is reported on the attached attribute docstring:

```pydocfmt-example
[settings]
docstring-convention = "google"

[input]
"""Client defaults.

Attributes:
    timeout: Request timeout.
"""

timeout: float
"""Request timeout in seconds."""

[output=unchanged]
[findings]
PDF513: Line 8: Attached docstring for module attribute 'timeout' duplicates module docstring attribute documentation
```

Using only one attribute documentation style is accepted:

```pydocfmt-example
[settings]
docstring-convention = "google"

[input]
"""Client defaults.

Attributes:
    timeout: Request timeout.
"""

timeout: float

retries: int
"""Retry attempts."""

[output=unchanged]
```

NumPy comma-separated attribute entries are checked name by name:

```pydocfmt-example
[settings]
docstring-convention = "numpy"

[input]
"""Client defaults.

Attributes
----------
primary, fallback : str
    Request endpoints.
"""

primary = fallback = "https://example.com"
"""Request endpoint values."""

[output=unchanged]
[findings]
PDF513: Line 10: Attached docstring for module attribute 'primary' duplicates module docstring attribute documentation
PDF513: Line 10: Attached docstring for module attribute 'fallback' duplicates module docstring attribute documentation
```

Only names documented in the module docstring are reported when an attached docstring belongs to multiple targets:

```pydocfmt-example
[settings]
docstring-convention = "google"

[input]
"""Client defaults.

Attributes:
    primary: Primary endpoint.
    aliases: Endpoint aliases.
"""

primary, (fallback, *aliases) = endpoints
"""Request endpoints."""

[output=unchanged]
[findings]
PDF513: Line 9: Attached docstring for module attribute 'primary' duplicates module docstring attribute documentation
PDF513: Line 9: Attached docstring for module attribute 'aliases' duplicates module docstring attribute documentation
```

reStructuredText `:ivar:`, `:cvar:`, `:var:`, and `:vartype:` fields are attribute documentation under the `rest` convention:

```pydocfmt-example
[settings]
docstring-convention = "rest"

[input]
"""Client defaults.

:cvar timeout: Request timeout.
:vartype retries: int
"""

timeout: float
"""Request timeout in seconds."""
retries: int
"""Retry attempts."""

[output=unchanged]
[findings]
PDF513: Line 8: Attached docstring for module attribute 'timeout' duplicates module docstring attribute documentation
PDF513: Line 10: Attached docstring for module attribute 'retries' duplicates module docstring attribute documentation
```

Class attribute docstrings and function-local attached docstrings do not duplicate module docstring attribute documentation:

```pydocfmt-example
[settings]
docstring-convention = "google"

[input]
"""Client defaults.

Attributes:
    timeout: Request timeout.
    retries: Retry count.
"""

class Client:
    timeout: float
    """Request timeout in seconds."""

def configure():
    retries = 3
    """Retry attempts."""

[output=unchanged]
```

## Options
- `docstring-convention`: Controls whether Google `Attributes` sections, NumPy `Attributes` sections, or reST attribute fields are parsed. Ignored by broad rule selections under `none` and `pep257`.
