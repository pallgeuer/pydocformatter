# missing-module-attribute-documentation (PDF510)

Fix is not available.

Rule is ignored by broad selectors for all `docstring-convention` values. Select `PDF510` exactly to opt into this module-level check.

## What it does
Checks that public module attributes are documented either in the module docstring attribute documentation or by an adjacent attribute docstring.

The rule compares supported module-level assignments against names documented in Google `Attributes` sections, NumPy `Attributes` sections, reStructuredText `:ivar:`, `:cvar:`, `:var:`, and `:vartype:` fields, and adjacent attribute docstrings. Module assignments, annotated assignments, multi-target assignments, and tuple-unpacked assignment leaves are inventoried. Private module attributes are never required.

PDF510 is ignored by broad selectors for every docstring convention, so select `PDF510` exactly to opt into this module-level check. With the default public-only setting, files named like private modules or private packages are skipped.

## Why is this useful?
Module attribute documentation can otherwise drift from exported module state.

## Ruff compatibility
None.

## Examples
Missing module attribute documentation is reported when a module has attribute documentation but omits a public module attribute:

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

[output=unchanged]
[findings]
PDF510: Line 8: Module attribute 'retries' is missing docstring documentation
```

An empty recognized `Attributes` section still opts the module into missing attribute checks:

```pydocfmt-example
[settings]
docstring-convention = "google"

[input]
"""Client defaults.

Attributes:
"""

timeout: float

[output=unchanged]
[findings]
PDF510: Line 6: Module attribute 'timeout' is missing docstring documentation
```

Adjacent module attribute docstrings document their assignments, including every simple target in a multi-target assignment and supported tuple-unpacked assignment. Private module attributes are not required:

```pydocfmt-example
[settings]
docstring-convention = "google"

[input]
timeout: float
"""Request timeout."""

retries: int

[output=unchanged]
[findings]
PDF510: Line 4: Module attribute 'retries' is missing docstring documentation
```

```pydocfmt-example
[settings]
docstring-convention = "google"

[input]
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
"""Client defaults.

Attributes
----------
primary, fallback : str
    Request endpoints.
"""

primary = fallback = "https://example.com"
retries: int

[output=unchanged]
[findings]
PDF510: Line 10: Module attribute 'retries' is missing docstring documentation
```

reStructuredText attribute fields are parsed under the `rest` convention:

```pydocfmt-example
[settings]
docstring-convention = "rest"

[input]
"""Client defaults.

:ivar timeout: Request timeout.
"""

timeout: float
retries: int

[output=unchanged]
[findings]
PDF510: Line 7: Module attribute 'retries' is missing docstring documentation
```

The `non-summary-docstrings` policy reports missing attributes for public modules whose docstring has more than a summary, even without an attribute section:

```pydocfmt-example
[settings]
docstring-convention = "google"
docstring-missing-documentation = "non-summary-docstrings"

[input]
"""Client defaults.

Used by the transport layer.
"""

timeout: float

[output=unchanged]
[findings]
PDF510: Line 6: Module attribute 'timeout' is missing docstring documentation
```

## Options
- `docstring-convention`: Controls whether Google `Attributes` sections, NumPy `Attributes` sections, or reST attribute fields are parsed. Ignored by broad rule selections under every convention, so exact `PDF510` selection is required.
- `docstring-missing-documentation`: Controls when PDF510 is active after exact selection. `has-section` reports only modules with recognized attribute documentation, including attached attribute docstrings. `non-summary-docstrings` additionally reports public module docstrings with more than just a summary. `all-docstrings` additionally reports all public module docstrings.
- `docstring-missing-documentation-public-only`: When `true`, missing-attribute checks skip private module paths. A file such as `_internal.py` or `_package/__init__.py` is private, while `package/__init__.py` is public. Private attributes are never required by PDF510.
